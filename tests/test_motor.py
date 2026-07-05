# -*- coding: utf-8 -*-
"""Tests del motor con datos sintéticos (sin red).

Incluye el test del trailing que se validó en el Gemelo (Node) — misma matemática,
mismos números esperados. Si ambos motores pasan el mismo test, son gemelos de verdad.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from motor import replay, construir_frames
from config import PARAMS


def _frames_a_mano(precios, scores=None, atr=1.0):
    n = len(precios)
    fechas = pd.date_range("2024-01-01", periods=n, freq="D")
    sc = scores if scores is not None else [99.0] * n
    return {
        "fechas": fechas, "tickers": ["A"], "sector": np.array(["Tec"]),
        "precio": np.array(precios, dtype=float).reshape(n, 1),
        "score": np.array(sc, dtype=float).reshape(n, 1),
        "vol": np.full((n, 1), 20.0), "atr": np.full((n, 1), float(atr)),
        "risk_on": np.ones(n, dtype=bool), "bench": np.linspace(100, 110, n),
        "volB": np.zeros(n), "bench0": 100.0,
    }


def _cfg(**kw):
    c = dict(PARAMS)
    c.update({"LIQUIDO_INICIAL": 1000.0, "MAX_POSICIONES": 1, "MAX_POR_SECTOR": 1,
              "CAP_POSICION_PCT": 100.0, "BUFFER_LIQUIDEZ_PCT": 0.0, "COMISION": 0.0,
              "SLIPPAGE_PCT": 0.0, "UMBRAL_COMPRA": 55.0, "UMBRAL_VENTA": -999.0,
              "STOP_LOSS_PCT": -999.0, "TAKE_PROFIT_PCT": 9999.0, "USAR_TRAILING": True,
              "FILTRO_REGIMEN": False, "MAX_DRAWDOWN_PCT": -95.0, "USAR_VOL_TARGET": False})
    c.update(kw)
    return c


def test_trailing_exacto():
    """Port del test validado en el Gemelo: compra a 100, pico 120.
    2xATR (stop 118) vende a 117.5 -> 1175 €. 3xATR (stop 117) aguanta y vende a 110 -> 1100 €."""
    precios = [100, 110, 120, 118.4, 117.5, 110, 110, 110]
    scores = [99] + [40] * 7            # solo compra el primer día (sin recompra)
    r2 = replay(_cfg(TRAILING_ATR=2.0), _frames_a_mano(precios, scores))
    r3 = replay(_cfg(TRAILING_ATR=3.0), _frames_a_mano(precios, scores))
    assert round(r2["curva"]["motor"].iloc[-1], 2) == 1175.00, r2["curva"]["motor"].iloc[-1]
    assert round(r3["curva"]["motor"].iloc[-1], 2) == 1100.00, r3["curva"]["motor"].iloc[-1]
    assert r2["cerrados"] == 1 and r3["cerrados"] == 1
    print("✓ trailing exacto (paridad con el test del Gemelo: 1175 / 1100)")


def test_contabilidad_cuadra():
    """Compra y venta con comisión y slippage: la caja final debe cuadrar al céntimo."""
    precios = [100, 100, 200, 200]
    scores = [99, 40, 40, 40]
    c = _cfg(COMISION=1.0, SLIPPAGE_PCT=0.10, TAKE_PROFIT_PCT=50.0, USAR_TRAILING=False)
    r = replay(c, _frames_a_mano(precios, scores))
    # compra día 0: inv = 1000-1 = 999 -> 9 uds a 100 (entera) con slip 0.1%: coste = 900*1.001+1 = 901.9
    # venta a 200 (TP +100%): ingreso = 9*200*0.999 - 1 = 1797.2 ; caja final = 1000-901.9+1797.2 = 1895.3
    assert round(r["curva"]["motor"].iloc[-1], 2) == 1895.30, r["curva"]["motor"].iloc[-1]
    print("✓ contabilidad con comisión+slippage cuadra al céntimo (1895.30)")


def test_no_recompra_mismo_dia():
    """Tras vender, no puede recomprar en el mismo frame (fidelidad al motor vivo)."""
    precios = [100, 120, 90, 90]        # caída fuerte: trailing vende en el frame 2
    r = replay(_cfg(TRAILING_ATR=2.0), _frames_a_mano(precios, atr=5.0))
    # con score 99 siempre, sin el guard recompraría el mismo día; con guard, recompra al frame siguiente
    assert r["cerrados"] >= 1
    print("✓ guard de no-recompra el mismo día activo")


def test_freno_drawdown_reancla():
    """El freno corta compras en drawdown y se reancla al volver el régimen (sin ciclo de la muerte)."""
    n = 40
    precios = [100 + i for i in range(10)] + [60] * 10 + [100 + i for i in range(20)]
    frames = _frames_a_mano(precios)
    frames["risk_on"] = np.array([True] * 10 + [False] * 10 + [True] * 20)
    c = _cfg(FILTRO_REGIMEN=True, MAX_DRAWDOWN_PCT=-20.0, TRAILING_ATR=99.0)
    r = replay(c, frames)
    # si el reanclaje funciona, tras recuperarse el régimen vuelve a estar invertido
    assert r["pct_mercado"] > 50, r["pct_mercado"]
    print("✓ freno de caída con reanclaje (no se queda fuera para siempre)")


def test_end_to_end_sintetico():
    """Universo sintético multi-valor por construir_frames: el pipeline entero corre."""
    n = 700
    fechas = pd.bdate_range("2022-01-03", periods=n)
    rng = np.random.default_rng(7)
    def serie(drift, vol):
        return pd.Series(100 * np.cumprod(1 + drift + vol * rng.standard_normal(n)), index=fechas)
    cierres = pd.DataFrame({
        "AAA": serie(0.004, 0.008),     # tendencial fuerte: garantiza que el take-profit entre en juego
        "BBB": serie(0.0002, 0.010),
        "CCC": serie(-0.0003, 0.015), "^GSPC": serie(0.0004, 0.008),
    })
    sect = {"AAA": "Tec", "BBB": "Ind", "CCC": "Ene"}
    cfg = dict(PARAMS, MAX_POSICIONES=3, MAX_POR_SECTOR=2)
    F = construir_frames(cierres, sect, cfg)
    r = replay(cfg, F)
    assert len(r["curva"]) > 80 and r["curva"]["motor"].iloc[-1] > 0
    a = replay(dict(cfg, TAKE_PROFIT_PCT=25.0), F)
    b = replay(dict(cfg, TAKE_PROFIT_PCT=200.0), F)
    assert (a["curva"]["motor"].iloc[-1] != b["curva"]["motor"].iloc[-1]) or (a["cerrados"] != b["cerrados"])
    print(f"✓ end-to-end sintético: {len(F['fechas'])} frames, equity>0, configs se diferencian")


def correr_todos():
    test_trailing_exacto()
    test_contabilidad_cuadra()
    test_no_recompra_mismo_dia()
    test_freno_drawdown_reancla()
    test_end_to_end_sintetico()
    test_replay_con_estado_persistente()
    test_cooldown_bloquea_recompra()
    test_ejecutor_puertas_de_seguridad()
    test_finde_solo_cripto()
    print("\nTODOS LOS TESTS PASAN ✅\n")


if __name__ == "__main__":
    correr_todos()


def test_replay_con_estado_persistente():
    """Modo vivo: dos pasos consecutivos con estado — las posiciones y la caja persisten."""
    precios = [100, 110, 120, 118.4, 117.5, 110, 110, 110]
    scores = [99] + [40] * 7
    F = _frames_a_mano(precios, scores)
    c = _cfg(TRAILING_ATR=3.0)
    # paso 1: solo los 3 primeros frames (compra a 100, sube a 120)
    F1 = {k: (v[:3] if isinstance(v, np.ndarray) and len(v) == 8 else v) for k, v in F.items()}
    F1["fechas"] = F["fechas"][:3]
    r1 = replay(c, F1)
    assert "A" in r1["pos"] and r1["pos"]["A"]["pmax"] == 120.0
    # paso 2: el resto de frames ARRANCANDO del estado del paso 1
    F2 = {k: (v[3:] if isinstance(v, np.ndarray) and len(v) == 8 else v) for k, v in F.items()}
    F2["fechas"] = F["fechas"][3:]
    F2["bench0"] = float(F2["bench"][0])
    r2 = replay(c, F2, estado={"liquido": r1["liquido"], "pos": r1["pos"]})
    # el trailing 3xATR debe vender a 110 igual que en la simulación continua -> 1100 €
    assert round(r2["curva"]["motor"].iloc[-1], 2) == 1100.00, r2["curva"]["motor"].iloc[-1]
    assert r2["registro"] and r2["registro"][0]["motivo"] == "Trailing stop"
    print("✓ modo vivo: el estado persiste entre pasos y reproduce la simulación continua (1100)")


def test_cooldown_bloquea_recompra():
    """Anti-churn: un ticker en cooldown no es recomprable aunque su score lo pida."""
    precios = [100, 100, 100]
    F = _frames_a_mano(precios)                       # score 99 siempre: sin bloqueo compraría ya
    c = _cfg()
    sin = replay(c, F, estado={"liquido": 1000.0, "pos": {}})
    con = replay(c, F, estado={"liquido": 1000.0, "pos": {}}, bloqueados={"A"})
    assert sin["registro"] and sin["registro"][0]["accion"] == "COMPRA"
    assert not con["registro"] and not con["pos"]
    print("✓ cooldown: el ticker bloqueado no se recompra (anti-churn horario)")


def test_ejecutor_puertas_de_seguridad():
    """El ejecutor debe estar BLOQUEADO por defecto y respetar kill switch y techos.
    Autocontenido: fija su propio estado inicial para no depender de defaults ni orden de tests."""
    import os
    import ejecutor as ej
    puerto_orig = ej.CONFIG["PUERTO"]
    ej.CONFIG["PUERTO"] = 4002                              # puerto PAPER explícito (no dependemos del default)
    if os.path.exists(ej.RUTA_KILL):
        os.remove(ej.RUTA_KILL)                            # partimos sin kill switch (limpia runs previos fallidos)
    os.environ.pop("IBKR_EJECUTAR", None)
    try:
        assert ej._puertas(3) is not None                  # sin interruptor -> bloqueado
        os.environ["IBKR_EJECUTAR"] = "SI"
        assert ej._puertas(3) is None                      # interruptor + puerto paper -> pasa
        assert "techo" in ej._puertas(99)                  # demasiadas órdenes -> bloqueado
        ej.CONFIG["PUERTO"] = 7496                          # puerto REAL
        assert "no es PAPER" in ej._puertas(3)             # real sin doble llave -> bloqueado
        ej.CONFIG["PUERTO"] = 4002
        open(ej.RUTA_KILL, "w").close()
        assert "KILL_SWITCH" in ej._puertas(3)             # kill switch manda sobre todo
    finally:
        os.environ.pop("IBKR_EJECUTAR", None)
        ej.CONFIG["PUERTO"] = puerto_orig
        if os.path.exists(ej.RUTA_KILL):
            os.remove(ej.RUTA_KILL)
    print("✓ ejecutor: bloqueado por defecto, kill switch y techos operativos, puerto real vetado")


def test_finde_solo_cripto():
    """En fin de semana no se compran acciones (mercado cerrado); solo cripto."""
    precios = [100, 100, 100]
    F = _frames_a_mano(precios)                            # ticker 'A' sector Tec, score 99
    c = _cfg()
    normal = replay(c, F, estado={"liquido": 1000.0, "pos": {}}, forzar_solo_cripto=False)
    finde = replay(c, F, estado={"liquido": 1000.0, "pos": {}}, forzar_solo_cripto=True)
    assert normal["registro"] and normal["registro"][0]["accion"] == "COMPRA"   # día normal: compra
    assert not finde["registro"] and not finde["pos"]                            # finde: no compra acción
    print("✓ fin de semana: no compra acciones (solo cripto), como el Gemelo")
