# -*- coding: utf-8 -*-
"""Análisis avanzado — lo que Apps Script no puede hacer (o no a esta escala).

- rejilla: robustez de parámetros (la misma del Gemelo, aquí en segundos y ampliable).
- walk_forward: estabilidad en ventanas rodantes (¿la ventaja vive en todos los tramos?).
- montecarlo: distribución de resultados a N meses por bootstrap de bloques
  (muestreo PAREADO motor/índice: conserva su correlación).

Regla de la casa: estos análisis VALIDAN, no optimizan. Elegir la celda máxima
de una rejilla es sobreajustar con la herramienta anti-sobreajuste.
"""
import numpy as np
import pandas as pd

from motor import construir_frames, replay
from metricas import max_dd, riesgo, cagr


def rejilla(cfg, cierres, sectores, tps=(25, 60, 200), tas=(2, 3, 4), anos=5):
    F = construir_frames(cierres, sectores, cfg)
    ppy = 252 / cfg["REBALANCEO_DIAS"]
    filas, bench_row = [], None
    for tp in tps:
        for ta in tas:
            c = dict(cfg, TAKE_PROFIT_PCT=float(tp), TRAILING_ATR=float(ta))
            r = replay(c, F)
            cur = r["curva"]
            if bench_row is None:
                bench_row = {"cagr": cagr(cur["bench"].iloc[-1], cfg["LIQUIDO_INICIAL"], anos),
                             "dd": max_dd(cur["bench"]), "sharpe": riesgo(cur["bench"], ppy)["sharpe"]}
            filas.append({
                "take_profit": tp, "trailing_atr": ta,
                "cagr_%": round(cagr(cur["motor"].iloc[-1], cfg["LIQUIDO_INICIAL"], anos), 2),
                "dd_%": round(-max_dd(cur["motor"]), 2),
                "sharpe": round(riesgo(cur["motor"], ppy)["sharpe"], 2),
                "aciertos_%": round(100 * r["ganados"] / r["cerrados"], 1) if r["cerrados"] else 0.0,
                "ops": r["cerrados"],
            })
    df = pd.DataFrame(filas)
    df["bate_indice"] = df["cagr_%"] > bench_row["cagr"]
    n_bate, n = int(df["bate_indice"].sum()), len(df)
    if n_bate >= np.ceil(0.75 * n):
        veredicto = f"🟢 MESETA: bate al índice en {n_bate}/{n} combinaciones → robusta a los parámetros."
    elif n_bate <= np.floor(0.34 * n):
        veredicto = f"🔴 PICO AGUDO: solo {n_bate}/{n} baten → alta sospecha de sobreajuste."
    else:
        veredicto = f"🟡 MIXTO: {n_bate}/{n} baten → robustez parcial; busca el patrón de las que fallan."
    return df, bench_row, veredicto


def walk_forward(cfg, cierres, sectores, ventana_anios=2.0, paso_meses=6):
    """Backtest completo en ventanas rodantes: cada ventana arranca con caja fresca."""
    F = construir_frames(cierres, sectores, cfg)
    fechas = F["fechas"]
    ppy = 252 / cfg["REBALANCEO_DIAS"]
    frames_ventana = int(round(ventana_anios * ppy))
    salto = int(round(paso_meses / 12 * ppy))
    filas = []
    ini = 0
    while ini + frames_ventana <= len(fechas):
        sub = {k: (v[ini:ini + frames_ventana] if isinstance(v, np.ndarray) and v.ndim >= 1
                   and len(v) == len(fechas) else v) for k, v in F.items()}
        sub["fechas"] = fechas[ini:ini + frames_ventana]
        sub["bench0"] = float(sub["bench"][0])
        r = replay(cfg, sub)
        cur = r["curva"]
        m = cagr(cur["motor"].iloc[-1], cfg["LIQUIDO_INICIAL"], ventana_anios)
        b = cagr(cur["bench"].iloc[-1], cfg["LIQUIDO_INICIAL"], ventana_anios)
        filas.append({"desde": str(sub["fechas"][0].date()), "hasta": str(sub["fechas"][-1].date()),
                      "motor_cagr_%": round(m, 1), "bench_cagr_%": round(b, 1), "dif_pp": round(m - b, 1)})
        ini += salto
    df = pd.DataFrame(filas)
    ganadas = int((df["dif_pp"] > 0).sum())
    resumen = (f"Ventanas ganadas al índice: {ganadas}/{len(df)} "
               f"({100 * ganadas / len(df):.0f}%) · dif mediana {df['dif_pp'].median():+.1f} pp")
    return df, resumen


def montecarlo(cfg, cierres, sectores, meses=4, n_caminos=5000, bloque=4, semilla=42):
    """Bootstrap de bloques sobre los retornos por periodo del backtest.

    Responde: en {meses} meses, ¿qué distribución de resultados es COMPATIBLE con
    esta estrategia? (percentiles, prob. de pérdida, prob. de ir peor que el índice,
    drawdown esperado). Bloques pareados motor/índice → conserva su correlación.
    """
    F = construir_frames(cierres, sectores, cfg)
    r = replay(cfg, F)
    cur = r["curva"]
    rm = cur["motor"].pct_change().dropna().to_numpy()
    rb = cur["bench"].pct_change().dropna().to_numpy()
    ppy = 252 / cfg["REBALANCEO_DIAS"]
    horizonte = max(2, int(round(meses / 12 * ppy)))
    rng = np.random.default_rng(semilla)
    n_per = len(rm)
    n_bloques = int(np.ceil(horizonte / bloque))
    finales_m, finales_b, dds = np.empty(n_caminos), np.empty(n_caminos), np.empty(n_caminos)
    for k in range(n_caminos):
        starts = rng.integers(0, n_per - bloque + 1, size=n_bloques)
        idx = np.concatenate([np.arange(s, s + bloque) for s in starts])[:horizonte]
        path_m = np.cumprod(1 + rm[idx])
        finales_m[k] = path_m[-1] - 1
        finales_b[k] = np.prod(1 + rb[idx]) - 1
        peak = np.maximum.accumulate(path_m)
        dds[k] = ((peak - path_m) / peak).max() * 100
    pct = lambda a, q: float(np.percentile(a, q)) * 100
    return {
        "meses": meses, "caminos": n_caminos,
        "p5": pct(finales_m, 5), "p25": pct(finales_m, 25), "p50": pct(finales_m, 50),
        "p75": pct(finales_m, 75), "p95": pct(finales_m, 95),
        "prob_perdida": float((finales_m < 0).mean()) * 100,
        "prob_peor_que_indice": float((finales_m < finales_b).mean()) * 100,
        "dd_mediano": float(np.median(dds)), "dd_p95": float(np.percentile(dds, 95)),
    }


def experimento_volumen(cfg, cierres, sectores, volumenes, peso_volumen=15.0,
                        tps=(60, 200), tas=(2, 3), anos=5):
    """A/B riguroso: la MISMA rejilla SIN volumen (W_VOLUMEN=0) vs CON volumen.
    Responde con datos si el factor volumen aporta, resta o da igual. Respeta el método:
    no se elige la mejor celda, se compara la meseta completa."""
    if volumenes is None:
        raise ValueError("No hay volumen cacheado. Ejecuta antes: python main.py descargar --anos N")
    ppy = 252 / cfg["REBALANCEO_DIAS"]

    def corre(wv):
        c0 = dict(cfg, W_VOLUMEN=float(wv))
        F = construir_frames(cierres, sectores, c0, volumenes=(volumenes if wv > 0 else None))
        filas = []
        for tp in tps:
            for ta in tas:
                c = dict(c0, TAKE_PROFIT_PCT=float(tp), TRAILING_ATR=float(ta))
                r = replay(c, F)
                cur = r["curva"]
                filas.append({"tp": tp, "ta": ta,
                              "cagr": cagr(cur["motor"].iloc[-1], cfg["LIQUIDO_INICIAL"], anos),
                              "dd": -max_dd(cur["motor"]), "sharpe": riesgo(cur["motor"], ppy)["sharpe"],
                              "ops": r["cerrados"]})
        return pd.DataFrame(filas)

    sin = corre(0.0)
    con = corre(peso_volumen)
    comp = sin[["tp", "ta"]].copy()
    comp["cagr_sin"] = sin["cagr"].round(2)
    comp["cagr_con"] = con["cagr"].round(2)
    comp["dif_cagr"] = (con["cagr"] - sin["cagr"]).round(2)
    comp["sharpe_sin"] = sin["sharpe"].round(2)
    comp["sharpe_con"] = con["sharpe"].round(2)
    comp["dd_con"] = con["dd"].round(2)

    mejora_cagr = comp["dif_cagr"].mean()
    mejora_sharpe = (con["sharpe"] - sin["sharpe"]).mean()
    n_mejora = int((comp["dif_cagr"] > 0).sum())
    n = len(comp)
    if mejora_cagr > 1.0 and n_mejora >= n * 0.75 and mejora_sharpe > 0:
        veredicto = (f"🟢 EL VOLUMEN APORTA: +{mejora_cagr:.1f} pp de CAGR medio, mejora en {n_mejora}/{n} "
                     f"configuraciones y Sharpe {mejora_sharpe:+.2f}. Candidato a incorporar (con peso {peso_volumen}).")
    elif mejora_cagr < -1.0 or n_mejora <= n * 0.25:
        veredicto = (f"🔴 EL VOLUMEN RESTA: {mejora_cagr:+.1f} pp de CAGR medio ({n_mejora}/{n} mejoran). "
                     f"Tu intuición no tiene firma estadística aquí — descartado, y con razón documentada.")
    else:
        veredicto = (f"🟡 NEUTRO: {mejora_cagr:+.1f} pp de CAGR medio, Sharpe {mejora_sharpe:+.2f} "
                     f"({n_mejora}/{n} mejoran). El volumen es casi REDUNDANTE con el momentum "
                     f"(justo lo previsto). No compensa la complejidad extra.")
    return comp, veredicto, {"cagr": mejora_cagr, "sharpe": mejora_sharpe, "peso": peso_volumen}

def imprimir_montecarlo(mc: dict):
    
    print(f"\n===== MONTE CARLO · {mc['meses']} meses · {mc['caminos']} caminos =====")
    print(f"Resultado a {mc['meses']} meses (percentiles):")
    print(f"  P5 {mc['p5']:+.1f}%   P25 {mc['p25']:+.1f}%   MEDIANA {mc['p50']:+.1f}%   "
          f"P75 {mc['p75']:+.1f}%   P95 {mc['p95']:+.1f}%")
    print(f"Prob. de acabar en pérdida:        {mc['prob_perdida']:.0f}%")
    print(f"Prob. de ir peor que el índice:    {mc['prob_peor_que_indice']:.0f}%")
    print(f"Drawdown dentro del periodo:       mediano {mc['dd_mediano']:.1f}% · malo (P95) {mc['dd_p95']:.1f}%")
    print("Lectura honesta: si el resultado real de tu test en vivo cae dentro de esta")
    print("distribución, el motor se comporta como el modelo — aunque pierda dinero.")
    print("=====================================================\n")
