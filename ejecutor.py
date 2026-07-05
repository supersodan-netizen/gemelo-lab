# -*- coding: utf-8 -*-
"""EJECUTOR IBKR — fase 4: el bot envía sus órdenes a Interactive Brokers (PAPER).

El cerebro no cambia: este módulo solo traduce las decisiones del motor a órdenes
del broker. Diseñado para que tocar dinero real POR ACCIDENTE sea físicamente difícil.

TRIPLE SEGURIDAD (las tres deben pasar, en este orden):
  1. Interruptor explícito: solo actúa si la variable de entorno IBKR_EJECUTAR=SI.
     (En GitHub Actions no existe → el bot en la nube JAMÁS envía órdenes.)
  2. Kill switch: si existe el archivo KILL_SWITCH en la carpeta, no se envía nada.
     Crear el archivo = frenazo inmediato sin tocar código (touch KILL_SWITCH).
  3. Cuenta PAPER verificada: tras conectar, la cuenta debe empezar por "DU"
     (las paper de IBKR empiezan por DU; las reales por U). Para operar en real
     algún día harán falta DOS llaves más: PERMITIR_REAL=True aquí Y la variable
     de entorno GEMELO_DINERO_REAL=SI. Hoy, imposible por construcción.

LÍMITES DUROS: máximo de órdenes por ciclo y de importe por orden. Todo intento
(enviado o bloqueado) queda registrado en ordenes_ibkr.json (auditoría).

REQUISITOS: cuenta IBKR Pro abierta (te da la paper DU… automáticamente),
IB Gateway o TWS corriendo en modo PAPER (puertos 4002/7497), y `pip install ib_async`.
"""
import json
import os
from datetime import datetime

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_KILL = os.path.join(RAIZ, "KILL_SWITCH")
RUTA_LOG = os.path.join(RAIZ, "ordenes_ibkr.json")

CONFIG = {
    "HOST": "127.0.0.1",
    "PUERTO": 4002,               # 4002 = IB Gateway PAPER · 7497 = TWS PAPER · (4001/7496 = REAL: bloqueados abajo)
    "CLIENT_ID": 7,
    "CARTERA": "puro",            # qué motor se ejecuta en el broker (el validado)
    "MAX_ORDENES_CICLO": 10,      # techo de órdenes por pasada (anti-descontrol)
    "MAX_IMPORTE_ORDEN": 600.0,   # techo de € por orden (anti-error de tamaño)
    "PERMITIR_REAL": False,       # NO tocar hasta que el test en vivo apruebe (y ni aun así solo)
}

PUERTOS_PAPER = (4002, 7497)

# Sufijo Yahoo -> (bolsa primaria IBKR, divisa). Cripto: IBKR no la ofrece en EUR para
# cuentas europeas → se queda en el papel interno del bot (limitación honesta).
_SUFIJOS = {
    ".DE": ("IBIS", "EUR"), ".MC": ("BM", "EUR"), ".PA": ("SBF", "EUR"),
    ".MI": ("BVME", "EUR"), ".AS": ("AEB", "EUR"), ".BR": ("ENEXT.BE", "EUR"),
    ".L": ("LSE", "GBP"), ".SW": ("EBS", "CHF"), ".ST": ("SFB", "SEK"),
    ".T": ("TSEJ", "JPY"),
}


def hay_kill_switch():
    return os.path.exists(RUTA_KILL)


def _registrar(entrada):
    log = []
    try:
        with open(RUTA_LOG, encoding="utf-8") as f:
            log = json.load(f)
    except Exception:
        pass
    entrada["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.append(entrada)
    with open(RUTA_LOG, "w", encoding="utf-8") as f:
        json.dump(log[-500:], f, ensure_ascii=False, indent=1)


def contrato_de(tk, sector=""):
    """Mapea un ticker Yahoo a un contrato IBKR. Devuelve (Stock, nota) o (None, motivo)."""
    if sector == "Cripto" or tk.endswith("-EUR"):
        return None, "cripto: IBKR no la ofrece en EUR para cuentas UE (queda en papel interno)"
    from ib_async import Stock
    for suf, (bolsa, divisa) in _SUFIJOS.items():
        if tk.endswith(suf):
            return Stock(tk[: -len(suf)], "SMART", divisa, primaryExchange=bolsa), ""
    return Stock(tk, "SMART", "USD"), ""     # sin sufijo = EEUU


def _puertas(n_ordenes):
    """Las puertas de seguridad previas a la conexión. Devuelve None si todo OK, o el motivo del bloqueo."""
    if os.environ.get("IBKR_EJECUTAR", "").strip().upper() != "SI":
        return "IBKR_EJECUTAR≠SI (modo normal: el bot opera solo en su papel interno)"
    if hay_kill_switch():
        return "KILL_SWITCH presente: ejecución detenida por el operador"
    if CONFIG["PUERTO"] not in PUERTOS_PAPER and not (
        CONFIG["PERMITIR_REAL"] and os.environ.get("GEMELO_DINERO_REAL") == "SI"
    ):
        return f"puerto {CONFIG['PUERTO']} no es PAPER y el modo real no está doblemente autorizado"
    if n_ordenes > CONFIG["MAX_ORDENES_CICLO"]:
        return f"{n_ordenes} órdenes supera el techo de {CONFIG['MAX_ORDENES_CICLO']} por ciclo"
    return None


def enviar_ordenes(registro, precios=None):
    """Envía las operaciones del motor (registro de replay) a IBKR. Seguro por defecto:
    sin IBKR_EJECUTAR=SI no hace NADA. Nunca lanza excepción hacia el bot."""
    if not registro:
        return
    bloqueo = _puertas(len(registro))
    if bloqueo:
        if "IBKR_EJECUTAR" not in bloqueo:                     # el modo normal no ensucia el log
            _registrar({"evento": "BLOQUEO", "motivo": bloqueo, "ordenes": len(registro)})
            print(f"🛑 Ejecutor IBKR bloqueado: {bloqueo}")
        return
    try:
        from ib_async import IB, MarketOrder
        ib = IB()
        ib.connect(CONFIG["HOST"], CONFIG["PUERTO"], clientId=CONFIG["CLIENT_ID"], timeout=20)
        cuentas = ib.managedAccounts()
        es_paper = cuentas and all(c.startswith("DU") for c in cuentas)
        if not es_paper and not (CONFIG["PERMITIR_REAL"] and os.environ.get("GEMELO_DINERO_REAL") == "SI"):
            _registrar({"evento": "BLOQUEO", "motivo": f"cuenta no-paper detectada: {cuentas}"})
            print(f"🛑 Cuenta {cuentas} NO es paper (DU…) y el modo real no está autorizado. Desconectando.")
            ib.disconnect()
            return
        print(f"Ejecutor IBKR conectado · cuenta {cuentas} ({'PAPER' if es_paper else 'REAL ⚠'})")
        for op in registro:
            contrato, nota = contrato_de(op["tk"], "")
            if contrato is None:
                _registrar({"evento": "OMITIDA", "tk": op["tk"], "motivo": nota})
                continue
            importe = op["u"] * op["px"]
            if importe > CONFIG["MAX_IMPORTE_ORDEN"]:
                _registrar({"evento": "BLOQUEADA", "tk": op["tk"],
                            "motivo": f"importe {importe:.0f}€ > techo {CONFIG['MAX_IMPORTE_ORDEN']}€"})
                continue
            qty = op["u"] if float(op["u"]).is_integer() else max(int(op["u"]), 0)
            if qty <= 0:                                        # fraccionadas: v2 (requiere activarlas en IBKR)
                _registrar({"evento": "OMITIDA", "tk": op["tk"],
                            "motivo": f"{op['u']:.4f} uds fraccionadas (v1 = enteras); queda en papel interno"})
                continue
            ib.qualifyContracts(contrato)
            orden = MarketOrder("BUY" if op["accion"] == "COMPRA" else "SELL", qty)
            trade = ib.placeOrder(contrato, orden)
            ib.sleep(3)
            _registrar({"evento": "ORDEN", "tk": op["tk"], "accion": op["accion"], "uds": qty,
                        "estado": trade.orderStatus.status, "fill": trade.orderStatus.avgFillPrice,
                        "motivo_motor": op.get("motivo", "")})
            print(f"  {op['accion']} {qty}×{op['tk']} → {trade.orderStatus.status}")
        ib.disconnect()
    except Exception as err:
        _registrar({"evento": "ERROR", "motivo": str(err)})
        print(f"⚠ Ejecutor IBKR falló ({err}). El bot sigue: su papel interno es la fuente de verdad.")


def estado_cuenta():
    """CLI: muestra la cuenta paper de IBKR para conciliar con el estado del bot."""
    from ib_async import IB
    ib = IB()
    ib.connect(CONFIG["HOST"], CONFIG["PUERTO"], clientId=CONFIG["CLIENT_ID"] + 1, timeout=20)
    print("Cuentas:", ib.managedAccounts())
    for v in ib.accountSummary():
        if v.tag in ("NetLiquidation", "TotalCashValue", "GrossPositionValue"):
            print(f"  {v.tag}: {v.value} {v.currency}")
    print("Posiciones IBKR:")
    for p in ib.positions():
        print(f"  {p.contract.symbol}: {p.position} @ {p.avgCost:.2f}")
    ib.disconnect()
