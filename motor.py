# -*- coding: utf-8 -*-
"""Motor del laboratorio — port FIEL del backtest del Gemelo Digital (Apps Script).

Arquitectura en dos fases (idéntica al Gemelo):
  1) construir_frames (fase CARA, una vez): indicadores y scores por fecha.
     No depende de los parámetros de salida -> la rejilla los varía sin recalcular.
  2) replay (fase BARATA): simula la cartera sobre los frames con una config dada.

Principio de paridad: cada fórmula replica la del Codigo.gs (mismos pesos, mismas
ventanas, misma varianza poblacional ddof=0, mismo trinquete del trailing, mismo
freno de caída con reanclaje, misma prohibición de recomprar el día de la venta).
"""
import numpy as np
import pandas as pd
from statistics import median


def clamp(x, a, b):
    return max(a, min(b, x))


# ---------------------------------------------------------------- indicadores
def indicadores(serie: pd.Series, cfg: dict) -> pd.DataFrame:
    """Réplica de computeMetrics sobre la serie PROPIA del valor (sin rellenar huecos).

    - vol: desviación típica POBLACIONAL (ddof=0) de los retornos de 63 días, anualizada.
    - pos52w: posición en el rango de las últimas 252 sesiones propias (hasta 252).
    - atr: proxy cierre-a-cierre = media de |Δcierre| de ATR_PERIODO sesiones.
    """
    c = serie.dropna().astype(float)
    df = pd.DataFrame(index=c.index)
    df["precio"] = c
    df["ma50"] = c.rolling(50).mean()
    df["ma200"] = c.rolling(200).mean()
    df["mom1m"] = (c / c.shift(21) - 1) * 100
    df["mom3m"] = (c / c.shift(63) - 1) * 100
    df["mom6m"] = (c / c.shift(126) - 1) * 100
    r = c.pct_change()
    df["vol"] = r.rolling(63).std(ddof=0) * np.sqrt(252) * 100
    hi = c.rolling(252, min_periods=1).max()
    lo = c.rolling(252, min_periods=1).min()
    rango = (hi - lo)
    df["pos52w"] = np.where(rango > 0, (c - lo) / rango, 0.5)
    df["atr"] = c.diff().abs().rolling(int(cfg["ATR_PERIODO"])).mean()
    # mom faltante (serie corta): el Gemelo devuelve 0 en ret() si no hay histórico
    for col in ("mom1m", "mom3m", "mom6m"):
        df[col] = df[col].fillna(0.0)
    # nº de observaciones propias acumuladas (para exigir >200 como el Gemelo: ptr>=200)
    df["nobs"] = np.arange(1, len(df) + 1)
    return df


def _score_componentes(md: pd.DataFrame, rs: pd.Series, rot: pd.Series, cfg: dict,
                       sent=None, a_score=None, q_score=None, vol_ratio=None) -> pd.Series:
    """Réplica exacta de scoreStock del Gemelo. Sin overlays = modo backtest (sent neutral 50).
    Con overlays (motor COMPLETO): sent -2..+2 -> 0..100 (su peso SIEMPRE cuenta);
    analistas/fundamental 0..100 y si faltan su peso se EXCLUYE (no penaliza).
    vol_ratio (experimental): volumen reciente / medio; su peso W_VOLUMEN solo cuenta si >0."""
    blended = 0.5 * md["mom1m"] + 0.35 * md["mom3m"] + 0.15 * md["mom6m"]
    mom = (50 + blended * 2.0).clip(0, 100)
    trend = (
        ((md["precio"] > md["ma50"]) & md["ma50"].notna()).astype(float) * 50
        + ((md["ma50"] > md["ma200"]) & md["ma50"].notna() & md["ma200"].notna()).astype(float) * 50
    )
    pos = (md["pos52w"] * 100).clip(0, 100)
    sent_score = 50.0 if sent is None else float(min(100, max(0, 50 + sent * 25)))
    fuerza = (50 + rs * 2.0).clip(0, 100)
    wf = cfg["W_FUERZA"]
    wr = cfg["W_ROTACION"] if cfg["USAR_ROTACION"] else 0.0
    wa = cfg.get("W_ANALISTAS", 0) if a_score is not None else 0.0
    wq = cfg.get("W_FUNDAMENTAL", 0) if q_score is not None else 0.0
    wv = cfg.get("W_VOLUMEN", 0) if (vol_ratio is not None and cfg.get("W_VOLUMEN", 0) > 0) else 0.0
    # confirmación por volumen: ratio 1 -> 50 (neutro); 2 -> 100 (doble actividad); 0.5 -> 25
    vol_score = (50 + (vol_ratio - 1.0) * 50).clip(0, 100) if wv else None
    wsum = (cfg["W_MOMENTUM"] + cfg["W_TENDENCIA"] + cfg["W_POS52W"] + cfg["W_SENTIMIENTO"]
            + wf + wr + wa + wq + wv)
    return (
        mom * cfg["W_MOMENTUM"] + trend * cfg["W_TENDENCIA"] + pos * cfg["W_POS52W"]
        + sent_score * cfg["W_SENTIMIENTO"] + fuerza * wf + rot * wr
        + (a_score or 0) * wa + (q_score or 0) * wq
        + (vol_score if vol_score is not None else 0) * wv
    ) / wsum


# ------------------------------------------------------------------- frames
def construir_frames(cierres: pd.DataFrame, sectores: dict, cfg: dict, overlays: dict = None,
                     volumenes: pd.DataFrame = None) -> dict:
    """Fase cara: precios y scores en cada fecha de decisión (cada REBALANCEO_DIAS)."""
    bench = cierres[cfg["BENCHMARK"]].dropna().astype(float)
    if len(bench) < 210:
        raise ValueError("Benchmark con histórico insuficiente (<210 sesiones).")
    paso = int(cfg["REBALANCEO_DIAS"])
    fechas = bench.index[200::paso]

    bench_ma200 = bench.rolling(200).mean()
    bench_mom3m = ((bench / bench.shift(63) - 1) * 100).reindex(fechas)
    risk_on = (bench > bench_ma200).reindex(fechas).to_numpy()
    bench_f = bench.reindex(fechas).to_numpy()
    r_b = bench.pct_change()
    volB = (r_b.rolling(20).std(ddof=0) * np.sqrt(252) * 100).reindex(fechas).fillna(0).to_numpy()

    tk_ok, P, V, A, RS_cols, MDs = [], [], [], [], [], []
    for tk in cierres.columns:
        if tk == cfg["BENCHMARK"] or tk not in sectores:
            continue
        serie = cierres[tk].dropna()
        if len(serie) <= 210:  # mismo umbral que el Gemelo para entrar en la simulación
            continue
        md = indicadores(serie, cfg)
        alin = md.reindex(fechas, method="ffill")           # semántica ptr: último dato <= fecha
        valido = alin["nobs"] > 200                          # ptr>=200 en el Gemelo
        P.append(alin["precio"].to_numpy())
        V.append(np.where(valido, alin["vol"].to_numpy(), np.nan))
        A.append(np.where(valido, alin["atr"].to_numpy(), np.nan))
        RS_cols.append(np.where(valido, alin["mom3m"].to_numpy() - bench_mom3m.to_numpy(), np.nan))
        MDs.append((alin, valido))
        tk_ok.append(tk)

    n_f, n_t = len(fechas), len(tk_ok)
    RS = np.array(RS_cols).T if n_t else np.zeros((n_f, 0))
    sec_arr = np.array([sectores[t] for t in tk_ok])

    # Rotación sectorial por frame (media de RS por sector -> ranking -> 40..100)
    ROT = np.full((n_f, n_t), 50.0)
    sec_unicos = sorted(set(sec_arr))
    masc = {s: (sec_arr == s) for s in sec_unicos}
    for f in range(n_f):
        medias = []
        for s in sec_unicos:
            v = RS[f, masc[s]]
            v = v[~np.isnan(v)]
            if len(v):
                medias.append((s, v.mean()))
        medias.sort(key=lambda x: -x[1])
        L = len(medias)
        ss = {}
        for idx, (s, _) in enumerate(medias):
            r01 = 1 - idx / (L - 1) if L > 1 else 1.0
            base = 60 if idx < cfg["ROTACION_TOP"] else 40
            ss[s] = clamp(base + r01 * 40, 0, 100)
        for j in range(n_t):
            ROT[f, j] = ss.get(sec_arr[j], 50.0)

    SC = np.full((n_f, n_t), np.nan)
    for j, (alin, valido) in enumerate(MDs):
        rs_j = pd.Series(RS[:, j], index=fechas)
        rot_j = pd.Series(ROT[:, j], index=fechas)
        ov = (overlays or {}).get(tk_ok[j], {})
        vr = None
        if volumenes is not None and cfg.get("W_VOLUMEN", 0) > 0 and tk_ok[j] in volumenes.columns:
            v = volumenes[tk_ok[j]].reindex(cierres.index).astype(float)
            ratio = v.rolling(10).mean() / v.rolling(60).mean()          # actividad reciente vs media
            vr = ratio.reindex(fechas, method="ffill").fillna(1.0).clip(0.2, 4.0)
        s = _score_componentes(alin, rs_j, rot_j, cfg,
                               sent=ov.get("sent"), a_score=ov.get("analyst"), q_score=ov.get("fund"),
                               vol_ratio=vr)
        SC[:, j] = np.where(valido, s.to_numpy(), np.nan)

    return {
        "fechas": fechas, "tickers": tk_ok, "sector": sec_arr,
        "precio": np.array(P).T if n_t else np.zeros((n_f, 0)),
        "score": SC, "vol": np.array(V).T if n_t else SC, "atr": np.array(A).T if n_t else SC,
        "risk_on": risk_on, "bench": bench_f, "volB": volB, "bench0": float(bench_f[0]),
    }


# -------------------------------------------------------------------- replay
def replay(cfg: dict, F: dict, estado: dict = None, bloqueados=None) -> dict:
    """Fase barata: simula la cartera. Réplica línea a línea de _btReplay (Codigo.gs).

    `estado` (opcional, modo VIVO): {"liquido": float, "pos": {tk: {u, pm, pmax}}}.
    Si se pasa, la simulación arranca desde ese estado (un paso del bot en papel)
    y devuelve también el estado final y el registro de operaciones con motivo.
    `bloqueados` (opcional, modo VIVO): tickers en cooldown tras una venta reciente
    (no elegibles para comprar), la misma protección anti-churn del Gemelo.
    """
    bloqueados = bloqueados or set()
    tks, sec = F["tickers"], F["sector"]
    idx = {t: j for j, t in enumerate(tks)}
    cash = float(estado["liquido"]) if estado else float(cfg["LIQUIDO_INICIAL"])
    pos = {t: dict(p) for t, p in estado["pos"].items()} if estado else {}
    registro = []
    cerrados = ganados = en_mercado = 0
    curva_m, curva_b = [], []
    peak = max(cash, cash + sum(p["u"] * p["pm"] for p in pos.values()))
    slip0 = cfg["SLIPPAGE_PCT"] / 100.0

    for f in range(len(F["fechas"])):
        px = F["precio"][f]; sc = F["score"][f]; at = F["atr"][f]; vl = F["vol"][f]

        def precio(tk, pm):
            v = px[idx[tk]]
            return pm if np.isnan(v) else float(v)

        mtm = sum(p["u"] * precio(t, p["pm"]) for t, p in pos.items())
        equity = cash + mtm
        if equity > peak:
            peak = equity
        risk_on = bool(F["risk_on"][f]) if cfg["FILTRO_REGIMEN"] else True
        # freno de caída con reanclaje al recuperarse el régimen (fix del ciclo de la muerte)
        if risk_on and equity < peak * (1 + cfg["MAX_DRAWDOWN_PCT"] / 100):
            peak = equity
        en_dd = equity < peak * (1 + cfg["MAX_DRAWDOWN_PCT"] / 100)

        # --- salidas (trailing ATR + stop + objetivo + score) ---
        vendidos = set()
        for tk in list(pos.keys()):
            j = idx[tk]
            if np.isnan(sc[j]):
                continue
            p = pos[tk]
            d_px, d_atr, d_sc = float(px[j]), float(at[j]) if not np.isnan(at[j]) else 0.0, float(sc[j])
            p["pmax"] = max(p["pmax"] or p["pm"], d_px)          # trinquete: el máximo solo sube
            pnl_pct = (d_px / p["pm"] - 1) * 100
            trail = cfg["USAR_TRAILING"] and d_atr > 0 and d_px <= p["pmax"] - cfg["TRAILING_ATR"] * d_atr
            motivo = ("Trailing stop" if trail else
                      "Stop-loss" if pnl_pct <= cfg["STOP_LOSS_PCT"] else
                      "Objetivo alcanzado" if pnl_pct >= cfg["TAKE_PROFIT_PCT"] else
                      "Score bajo umbral" if d_sc < cfg["UMBRAL_VENTA"] else None)
            if motivo:
                slip = slip0 * (2.5 if sec[j] == "Cripto" else 1.0)
                cash += p["u"] * d_px * (1 - slip) - cfg["COMISION"]
                cerrados += 1
                if d_px - p["pm"] > 0:
                    ganados += 1
                registro.append({"t": str(F["fechas"][f])[:10], "tk": tk, "accion": "VENTA",
                                 "u": p["u"], "px": d_px, "pnl_pct": round(pnl_pct, 2), "motivo": motivo})
                del pos[tk]
                vendidos.add(tk)                                  # fidelidad: no recomprar el mismo día

        # --- objetivo de volatilidad (por defecto OFF, paridad completa) ---
        vol_factor = 1.0
        if cfg["USAR_VOL_TARGET"]:
            vB = float(F["volB"][f])
            vol_factor = clamp(cfg["VOL_OBJETIVO_PCT"] / vB, 0.25, 1.0) if vB > 0 else 1.0
            inv_act = sum(p["u"] * precio(t, p["pm"]) for t, p in pos.items())
            max_inv = vol_factor * equity
            if inv_act > max_inv * 1.05:
                frac = 1 - max_inv / inv_act
                for tk in list(pos.keys()):
                    j = idx[tk]; prc = px[j]
                    if not (prc > 0):
                        continue
                    slip = slip0 * (2.5 if sec[j] == "Cripto" else 1.0)
                    vende = pos[tk]["u"] * frac
                    cash += vende * prc * (1 - slip)
                    pos[tk]["u"] -= vende
                    if pos[tk]["u"] * prc < 5:
                        cash += pos[tk]["u"] * prc * (1 - slip)
                        del pos[tk]

        # --- entradas ---
        libres = cfg["MAX_POSICIONES"] - len(pos)
        solo_cripto = (not risk_on) and (not en_dd)
        if libres > 0 and not en_dd:
            por_sec = {}
            for t in pos:
                s = sec[idx[t]]
                por_sec[s] = por_sec.get(s, 0) + 1
            cand = [t for t in tks
                    if t not in pos and t not in vendidos and t not in bloqueados
                    and not np.isnan(sc[idx[t]]) and sc[idx[t]] >= cfg["UMBRAL_COMPRA"]
                    and (not solo_cripto or sec[idx[t]] == "Cripto")]
            cand.sort(key=lambda t: -sc[idx[t]])
            sel = []
            for t in cand:
                if len(sel) >= libres:
                    break
                s = sec[idx[t]]
                if por_sec.get(s, 0) >= cfg["MAX_POR_SECTOR"]:
                    continue
                por_sec[s] = por_sec.get(s, 0) + 1
                sel.append(t)
            cap_eur = equity * cfg["CAP_POSICION_PCT"] / 100
            caja = max(0.0, cash - equity * cfg["BUFFER_LIQUIDEZ_PCT"] / 100)
            if cfg["USAR_VOL_TARGET"]:
                inv2 = sum(p["u"] * precio(t, p["pm"]) for t, p in pos.items())
                caja = min(caja, max(0.0, vol_factor * equity - inv2))
            base = caja / len(sel) if sel else 0.0
            mv = median([(vl[idx[t]] if not np.isnan(vl[idx[t]]) else 25.0) or 25.0 for t in sel]) if sel else 25.0
            for t in sel:
                j = idx[t]
                d_px = float(px[j]); d_vol = float(vl[j]) if not np.isnan(vl[j]) else mv
                if not (d_px > 0):
                    continue
                size = min(base * (mv / (d_vol or mv)), cap_eur, caja)
                inv = size - cfg["COMISION"]
                if inv < 5:
                    continue
                frac_ok = sec[j] == "Cripto" or inv < d_px
                u = round(inv / d_px * 1e6) / 1e6 if frac_ok else np.floor(inv / d_px)
                if not (u > 0):
                    continue
                slip = slip0 * (2.5 if sec[j] == "Cripto" else 1.0)
                costo = u * d_px * (1 + slip) + cfg["COMISION"]
                cash -= costo
                caja -= costo
                pos[t] = {"u": float(u), "pm": d_px, "pmax": d_px}
                registro.append({"t": str(F["fechas"][f])[:10], "tk": t, "accion": "COMPRA",
                                 "u": float(u), "px": d_px, "pnl_pct": 0.0,
                                 "motivo": "Score " + str(round(float(sc[j])))})

        mtm2 = sum(p["u"] * precio(t, p["pm"]) for t, p in pos.items())
        if pos:
            en_mercado += 1
        curva_m.append(cash + mtm2)
        curva_b.append(cfg["LIQUIDO_INICIAL"] * float(F["bench"][f]) / F["bench0"])

    curva = pd.DataFrame({"motor": curva_m, "bench": curva_b}, index=F["fechas"])
    return {"curva": curva, "cerrados": cerrados, "ganados": ganados,
            "pct_mercado": 100.0 * en_mercado / max(len(curva), 1),
            "registro": registro, "liquido": cash, "pos": pos}
