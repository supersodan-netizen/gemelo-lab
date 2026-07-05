# -*- coding: utf-8 -*-
"""Modo VIVO — el bot en papel, autosuficiente.

Cada ejecución hace UN paso de decisión con el MISMO motor validado del backtest
(mismas salidas, mismas entradas, mismo freno), sobre un estado persistente:

  descarga datos recientes -> indicadores/scores de HOY -> vende/compra (papel)
  -> guarda estado_vivo.json -> exporta docs/estado.json para el panel web.

El estado del bot es SUYO (no depende del Apps Script): posiciones, líquido,
P&L, historial de operaciones y curva de patrimonio viven en estado_vivo.json.
Programa la ejecución (p. ej. Task Scheduler a diario tras el cierre USA) y el
bot vive solo. Con --publicar hace git commit+push para que la web se actualice.
"""
import json
import os
import subprocess
import time
from datetime import datetime

import numpy as np

from config import PARAMS, TICKERS, SECTORES, NOMBRES, VERSION_ALGORITMO
from motor import construir_frames, replay
import senales

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_ESTADO = os.path.join(RAIZ, "estado_vivo.json")
RUTA_WEB = os.path.join(RAIZ, "docs", "estado.json")


# ------------------------------------------------------------------ estado
def cargar_estado():
    if not os.path.exists(RUTA_ESTADO):
        return None
    with open(RUTA_ESTADO, encoding="utf-8") as f:
        e = json.load(f)
    if "carteras" not in e:                      # migración desde v1: lo existente pasa a ser la cartera PURA
        e = {"version": 2, "carteras": {"puro": e, "completo": iniciar_estado(e.get("aportado", PARAMS["LIQUIDO_INICIAL"]))}}
        print("Estado migrado a v2: cartera PURA (histórica) + COMPLETA (nueva, misma aportación).")
    return e


def guardar_estado(e):
    with open(RUTA_ESTADO, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)


def iniciar_estado(aportacion: float):
    return {"inicio": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "liquido": float(aportacion), "aportado": float(aportacion), "pnlAcum": 0.0,
            "pos": {}, "cooldown": {}, "operaciones": [], "historico": []}


# ------------------------------------------------------------------- ciclo
def ciclo(anos_datos: int = 2, aportar: float = 0.0, reset: bool = False, publicar: bool = False):
    import yfinance as yf

    estado = None if reset else cargar_estado()
    if estado is None:
        inicial = aportar if aportar > 0 else PARAMS["LIQUIDO_INICIAL"]
        estado = {"version": 2, "carteras": {"puro": iniciar_estado(inicial),
                                             "completo": iniciar_estado(inicial)}}
        print(f"Estado nuevo: DOS motores en papel (puro y completo), {inicial:.2f} € cada uno.")
    elif aportar > 0:
        for ec in estado["carteras"].values():
            ec["liquido"] += aportar
            ec["aportado"] += aportar
        print(f"Aportación registrada en ambos motores: +{aportar:.2f} € (A/B justo).")

    print(f"Descargando {len(TICKERS) + 1} símbolos ({anos_datos} años, para indicadores de hoy)…")
    todos = list(dict.fromkeys(TICKERS + [PARAMS["BENCHMARK"]]))
    cierres = None
    for intento in range(3):                                   # Yahoo a veces frena IPs de datacenter: insistir
        try:
            cierres = yf.download(todos, period=f"{anos_datos}y", interval="1d",
                                  auto_adjust=True, progress=False)["Close"]
            if cierres is not None and not cierres.dropna(how="all").empty:
                break
        except Exception as err:
            print(f"  intento {intento + 1} falló: {err}")
        time.sleep(20 * (intento + 1))
    if cierres is None or cierres.dropna(how="all").empty:
        raise SystemExit("No pude descargar datos tras 3 intentos. El bot no opera con datos vacíos; "
                         "reintentará en la próxima ejecución programada.")
    cierres = cierres.dropna(how="all")
    ts_datos = int(time.time() * 1000)

    # Señales externas para el motor COMPLETO (caché diaria / 12 h; degradación elegante)
    fund = {}
    sent = None
    try:
        fund = senales.fundamentales(TICKERS)
    except Exception as err:
        print(f"⚠ Fundamentales no disponibles este ciclo: {err}")
    try:
        sent = senales.sentimiento(sorted(set(SECTORES.values())), [(t, NOMBRES[t]) for t in TICKERS])
    except Exception as err:
        print(f"⚠ Sentimiento no disponible este ciclo: {err}")
    overlays = {}
    for tk in TICKERS:
        s_acc = (sent or {}).get("acciones", {}).get(tk)
        s_sec = (sent or {}).get("sectores", {}).get(SECTORES.get(tk, ""))
        f = fund.get(tk, {})
        overlays[tk] = {"sent": s_acc if s_acc is not None else s_sec,
                        "analyst": f.get("analyst"), "fund": f.get("fund")}

    # frames con el MISMO constructor del backtest; cada motor decide sobre el ÚLTIMO
    cfg1 = dict(PARAMS, REBALANCEO_DIAS=1)
    frames_por_motor = {"puro": construir_frames(cierres, SECTORES, cfg1),
                        "completo": construir_frames(cierres, SECTORES, cfg1, overlays=overlays)}
    ts_now = ts_datos
    F0 = frames_por_motor["puro"]
    fecha_dato = str(F0["fechas"][-1])[:10]
    hoy = datetime.strptime(fecha_dato, "%Y-%m-%d")
    es_finde = datetime.now().weekday() >= 5          # sáb(5)/dom(6): mercado de acciones cerrado -> solo cripto
    if es_finde:
        print("Fin de semana: mercado de acciones cerrado; solo se opera cripto (como en el Gemelo).")

    resumen_web = {}
    registros_por_motor = {}
    for nombre in ("puro", "completo"):
        ec = estado["carteras"][nombre]
        F = frames_por_motor[nombre]
        ultimo = {k: (v[-1:] if isinstance(v, np.ndarray) and len(v) == len(F["fechas"]) else v)
                  for k, v in F.items()}
        ultimo["fechas"] = F["fechas"][-1:]
        ultimo["bench0"] = float(ultimo["bench"][0])

        cd = ec.get("cooldown", {})
        bloqueados = {tk for tk, f in cd.items()
                      if (hoy - datetime.strptime(f, "%Y-%m-%d")).days < PARAMS["COOLDOWN_DIAS"]}
        ec["cooldown"] = {tk: f for tk, f in cd.items() if tk in bloqueados}

        pnl_antes = {tk: p for tk, p in ec["pos"].items()}
        r = replay(PARAMS, ultimo, estado={"liquido": ec["liquido"], "pos": ec["pos"]},
                   bloqueados=bloqueados, forzar_solo_cripto=es_finde)
        for op in r["registro"]:
            if op["accion"] == "VENTA":
                pm = pnl_antes[op["tk"]]["pm"]
                ec["pnlAcum"] += (op["px"] - pm) * op["u"] - PARAMS["COMISION"]
                ec["cooldown"][op["tk"]] = op["t"]
            else:
                ec["pnlAcum"] -= PARAMS["COMISION"]
            op["nombre"] = NOMBRES.get(op["tk"], op["tk"])
            op["alg"] = VERSION_ALGORITMO
            ec["operaciones"].append(op)
        ec["operaciones"] = ec["operaciones"][-120:]
        ec["liquido"] = r["liquido"]
        ec["pos"] = r["pos"]

        idx = {t: j for j, t in enumerate(ultimo["tickers"])}
        px = ultimo["precio"][0]

        def precio_de(tk, pm):
            v = px[idx[tk]] if tk in idx else np.nan
            return pm if (v is None or np.isnan(v)) else float(v)

        valor_pos = sum(p["u"] * precio_de(t, p["pm"]) for t, p in ec["pos"].items())
        equity = ec["liquido"] + valor_pos
        ec["historico"].append([fecha_dato, round(ec["liquido"], 2), round(valor_pos, 2), round(equity, 2)])
        vistos = {}
        for h in ec["historico"]:
            vistos[h[0]] = h
        ec["historico"] = list(vistos.values())[-400:]

        registros_por_motor[nombre] = r["registro"]
        resumen_web[nombre] = armar_web(ec, ultimo, px, idx, ts_now, fecha_dato, equity, valor_pos)
        print(f"\n— Motor {nombre.upper()} ({fecha_dato}) —")
        if r["registro"]:
            for op in r["registro"]:
                print(f"  {op['accion']:6} {op['tk']:8} {op['u']:.4f} uds @ {op['px']:.2f}  · {op['motivo']}")
        else:
            print("  Sin operaciones.")
        print(f"  Patrimonio: {equity:.2f} € · líquido {ec['liquido']:.2f} € · "
              f"{len(ec['pos'])} posiciones · P&L realizado {ec['pnlAcum']:+.2f} €")

    guardar_estado(estado)
    # Fase 4 (opcional, seguro por defecto): enviar las órdenes del motor elegido a IBKR paper.
    # Sin IBKR_EJECUTAR=SI en el entorno, esta llamada no hace absolutamente nada.
    try:
        import ejecutor
        ejecutor.enviar_ordenes(registros_por_motor.get(ejecutor.CONFIG["CARTERA"], []))
    except Exception as err:
        print(f"⚠ Ejecutor no disponible ({err}); el bot continúa en papel interno.")
    salida = dict(resumen_web["puro"])                      # compatibilidad: el nivel raíz = motor puro
    salida["carteras"] = resumen_web
    salida["fuente"] = "bot-python"
    os.makedirs(os.path.dirname(RUTA_WEB), exist_ok=True)
    with open(RUTA_WEB, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\nEstado exportado para la web (2 motores): {RUTA_WEB}")

    if publicar:
        _git_publicar()


# ------------------------------------------------------- exportar a la web
def armar_web(e, F, px, idx, ts_datos, fecha_dato, equity, valor_pos):
    """Devuelve el estado de UNA cartera con el MISMO contrato que la API del Gemelo."""
    sc = F["score"][0]
    filas_pos = [["Ticker", "Nombre", "Uds", "PrecioMedio", "PrecioActual",
                  "Valor", "PnL", "PnL%", "Fecha", "Horizonte", "PrecioMax"]]
    for tk, p in e["pos"].items():
        act = px[idx[tk]] if tk in idx and not np.isnan(px[idx[tk]]) else p["pm"]
        val, pnl = p["u"] * act, (act - p["pm"]) * p["u"]
        filas_pos.append([tk, NOMBRES.get(tk, tk), round(p["u"], 6), round(p["pm"], 2),
                          round(float(act), 2), round(val, 2), round(pnl, 2),
                          round((act / p["pm"] - 1) * 100, 2) if p["pm"] else 0,
                          "", "Bot", round(p["pmax"], 2)])

    filas_ops = [["Fecha", "Ticker", "Nombre", "Accion", "Uds", "Precio", "Importe",
                  "Comision", "Score", "Horizonte", "Motivo", "Estado"]]
    for op in e["operaciones"][-60:]:
        filas_ops.append([op["t"], op["tk"], op.get("nombre", op["tk"]), op["accion"],
                          round(op["u"], 6), round(op["px"], 2), round(op["u"] * op["px"], 2),
                          PARAMS["COMISION"], "", "Bot",
                          op["motivo"] + " · alg v" + op.get("alg", VERSION_ALGORITMO), "EJECUTADA"])

    filas_hist = [["Fecha", "Liquido", "ValorPos", "Patrimonio"]] + e["historico"]

    # radar: mejores scores de hoy (esquema de 14 columnas como la hoja Datos)
    orden = sorted(range(len(F["tickers"])), key=lambda j: -(sc[j] if not np.isnan(sc[j]) else -1))
    filas_datos = [["Ticker", "Nombre", "Sector", "Precio"] + [""] * 9 + ["Score"]]
    for j in orden[:20]:
        if np.isnan(sc[j]):
            continue
        tk = F["tickers"][j]
        filas_datos.append([tk, NOMBRES.get(tk, tk), F["sector"][j],
                            round(float(px[j]), 2)] + [""] * 9 + [round(float(sc[j]), 1)])

    # sectores en cabeza (por score medio de hoy)
    agg = {}
    for j, s in enumerate(F["sector"]):
        if not np.isnan(sc[j]):
            agg.setdefault(s, []).append(float(sc[j]))
    sectores = [s for s, _ in sorted(((s, sum(v) / len(v)) for s, v in agg.items()),
                                     key=lambda x: -x[1])]

    # banda vivo-vs-esperado (mismas fórmulas que el cuaderno del Gemelo)
    seg = []
    try:
        t0 = datetime.strptime(e["inicio"][:10], "%Y-%m-%d")
        eq0 = e["historico"][0][3] if e["historico"] else e["aportado"]
        t = max((datetime.now() - t0).days / 365.25, 1 / 365.25)
        semana = int((datetime.now() - t0).days // 7)
        esperado = eq0 * (1 + PARAMS["TEST_CAGR_ESPERADO"] / 100) ** t
        sig = PARAMS["TEST_VOL_ESPERADA"] / 100 * (t ** 0.5)
        inf, sup = esperado * np.exp(-sig), esperado * np.exp(sig)
        inf2 = esperado * np.exp(-2 * sig)
        estado_txt = ("🔴 −2σ: el vivo NO se parece al modelo" if equity < inf2 else
                      "🟠 bajo la banda: vigilar" if equity < inf else
                      "🔵 sobre la banda (no extrapoles)" if equity > sup else
                      "🟢 en banda: como el modelo")
        seg = [[e["inicio"], semana, round(equity, 2), round(esperado, 2), round(inf, 2),
                round(sup, 2), round((equity / esperado - 1) * 100, 2), "—", "—", estado_txt]]
    except Exception:
        pass

    salida = {
        "version_algoritmo": VERSION_ALGORITMO, "actualizado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fecha_dato": fecha_dato,
        "config": {"benchmark": PARAMS["BENCHMARK"], "usarTrailing": PARAMS["USAR_TRAILING"],
                   "trailingAtr": PARAMS["TRAILING_ATR"]},
        "frescura": {"precios": ts_datos, "datos": ts_datos},
        "liquidez": {"liquido": round(e["liquido"], 2), "aportado": round(e["aportado"], 2),
                     "pnlAcum": round(e["pnlAcum"], 2), "pico": round(equity, 2)},
        "posiciones": filas_pos, "operaciones": filas_ops, "historico": filas_hist,
        "seguimiento": seg, "datos": filas_datos, "fuerzaSectores": sectores,
        "carteraReal": [], "recomendaciones": [],
    }
    return salida


def _git_publicar():
    try:
        subprocess.run(["git", "add", "docs/estado.json"], cwd=RAIZ, check=True)
        subprocess.run(["git", "commit", "-m", "bot: estado " +
                        datetime.now().strftime("%Y-%m-%d %H:%M")], cwd=RAIZ, check=True)
        subprocess.run(["git", "push"], cwd=RAIZ, check=True)
        print("Publicado en GitHub: la web se actualizará en ~1 min.")
    except Exception as err:
        print(f"⚠ No se pudo publicar (¿repo git configurado?): {err}")
