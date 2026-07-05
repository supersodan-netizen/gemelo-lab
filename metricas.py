# -*- coding: utf-8 -*-
"""Métricas de riesgo y rendimiento — réplica de _riesgo/maxDD del Gemelo (rf=0, ddof=0)."""
import numpy as np
import pandas as pd


def riesgo(serie: pd.Series, ppy: float) -> dict:
    r = serie.pct_change().dropna().to_numpy()
    if not len(r):
        return {"vol": 0.0, "sharpe": 0.0, "sortino": 0.0}
    mean, sd = r.mean(), r.std(ddof=0)
    down = r[r < 0]
    dsd = np.sqrt((down ** 2).mean()) if len(down) else 0.0
    return {
        "vol": sd * np.sqrt(ppy) * 100,
        "sharpe": (mean / sd) * np.sqrt(ppy) if sd > 0 else 0.0,
        "sortino": (mean / dsd) * np.sqrt(ppy) if dsd > 0 else (np.inf if mean > 0 else 0.0),
    }


def max_dd(serie: pd.Series) -> float:
    v = serie.to_numpy()
    peak = np.maximum.accumulate(v)
    dd = np.where(peak > 0, (peak - v) / peak * 100, 0.0)
    return float(dd.max()) if len(dd) else 0.0


def cagr(final: float, inicial: float, anos: float) -> float:
    return ((final / inicial) ** (1 / anos) - 1) * 100 if inicial > 0 and anos > 0 else 0.0


def por_anio(curva: pd.DataFrame) -> pd.DataFrame:
    """Rentabilidad por año natural de motor y benchmark (misma lógica que la hoja POR AÑO)."""
    filas = []
    prev = None
    for anio, g in curva.groupby(curva.index.year):
        base = prev if prev is not None else g.iloc[0]
        m = (g["motor"].iloc[-1] / base["motor"] - 1) * 100
        b = (g["bench"].iloc[-1] / base["bench"] - 1) * 100
        filas.append({"año": int(anio), "motor_%": round(m, 1), "bench_%": round(b, 1), "dif_pp": round(m - b, 1)})
        prev = g.iloc[-1]
    return pd.DataFrame(filas).set_index("año")


def resumen(curva: pd.DataFrame, cerrados: int, ganados: int, pct_mercado: float,
            anos: float, paso: int, inicial: float) -> dict:
    ppy = 252 / paso
    rm, rb = riesgo(curva["motor"], ppy), riesgo(curva["bench"], ppy)
    fin_m, fin_b = float(curva["motor"].iloc[-1]), float(curva["bench"].iloc[-1])
    split = int(len(curva) * 0.6)
    oos_m = oos_b = None
    if len(curva) - split > 5 and curva["motor"].iloc[split] > 0:
        oos_m = (fin_m / curva["motor"].iloc[split] - 1) * 100
        oos_b = (fin_b / curva["bench"].iloc[split] - 1) * 100
    return {
        "ret_total_m": (fin_m / inicial - 1) * 100, "ret_total_b": (fin_b / inicial - 1) * 100,
        "cagr_m": cagr(fin_m, inicial, anos), "cagr_b": cagr(fin_b, inicial, anos),
        "dd_m": max_dd(curva["motor"]), "dd_b": max_dd(curva["bench"]),
        "vol_m": rm["vol"], "vol_b": rb["vol"], "sharpe_m": rm["sharpe"], "sharpe_b": rb["sharpe"],
        "sortino_m": rm["sortino"], "sortino_b": rb["sortino"],
        "win_rate": 100.0 * ganados / cerrados if cerrados else 0.0, "ops": cerrados,
        "pct_mercado": pct_mercado, "oos_m": oos_m, "oos_b": oos_b,
        "final_m": fin_m, "final_b": fin_b,
    }


def imprimir(R: dict, por_a: pd.DataFrame):
    f = lambda x: f"{x:,.1f}".replace(",", ".")
    print("\n================= RESULTADO =================")
    print(f"{'Métrica':<28}{'Motor':>12}{'Índice':>12}")
    print(f"{'Rentabilidad total %':<28}{f(R['ret_total_m']):>12}{f(R['ret_total_b']):>12}")
    print(f"{'CAGR %':<28}{f(R['cagr_m']):>12}{f(R['cagr_b']):>12}")
    print(f"{'Caída máxima %':<28}{f(-R['dd_m']):>12}{f(-R['dd_b']):>12}")
    print(f"{'Volatilidad anual %':<28}{f(R['vol_m']):>12}{f(R['vol_b']):>12}")
    print(f"{'Sharpe':<28}{R['sharpe_m']:>12.2f}{R['sharpe_b']:>12.2f}")
    print(f"{'Sortino':<28}{R['sortino_m']:>12.2f}{R['sortino_b']:>12.2f}")
    print(f"{'% aciertos':<28}{R['win_rate']:>11.1f}%{'—':>12}")
    print(f"{'Operaciones cerradas':<28}{R['ops']:>12}{'—':>12}")
    print(f"{'% tiempo invertido':<28}{R['pct_mercado']:>11.1f}%{'100.0%':>12}")
    if R["oos_m"] is not None:
        print(f"{'Fuera de muestra (40%) %':<28}{f(R['oos_m']):>12}{f(R['oos_b']):>12}")
    print("\nPOR AÑO:")
    print(por_a.to_string())
    print("=============================================\n")
