# -*- coding: utf-8 -*-
"""Descarga de histórico (Yahoo vía yfinance) con caché local en CSV.

La caché hace los experimentos REPRODUCIBLES: descargas una vez y todos los
análisis (backtest, rejilla, Monte Carlo, walk-forward) usan el mismo dataset.
"""
import os
import pandas as pd

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_datos")


def _ruta(anos: int) -> str:
    return os.path.join(CARPETA, f"cierres_{anos}y.csv")


def descargar(tickers, benchmark: str, anos: int = 5, forzar: bool = False) -> pd.DataFrame:
    """Descarga cierres AJUSTADOS (dividendos/splits) — mismo criterio que el Gemelo (adjclose).
    También guarda el VOLUMEN en paralelo (volumen_Ny.csv) para el experimento de volumen."""
    import yfinance as yf  # import perezoso: los tests no necesitan red
    os.makedirs(CARPETA, exist_ok=True)
    if os.path.exists(_ruta(anos)) and not forzar:
        print(f"Caché encontrada ({_ruta(anos)}). Usa --forzar para re-descargar.")
        return cargar(anos)
    todos = list(dict.fromkeys(list(tickers) + [benchmark]))
    print(f"Descargando {len(todos)} símbolos, {anos} años (Yahoo)…")
    bruto = yf.download(todos, period=f"{anos}y", interval="1d",
                        auto_adjust=True, progress=True)
    df = bruto["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(name=todos[0])
    df = df.dropna(how="all")
    df.to_csv(_ruta(anos))
    print(f"Guardado: {_ruta(anos)}  ({df.shape[0]} sesiones × {df.shape[1]} símbolos)")
    try:                                          # volumen (para el factor experimental; si falla, no pasa nada)
        vol = bruto["Volume"]
        if isinstance(vol, pd.Series):
            vol = vol.to_frame(name=todos[0])
        vol.dropna(how="all").to_csv(os.path.join(CARPETA, f"volumen_{anos}y.csv"))
        print(f"Guardado volumen: volumen_{anos}y.csv")
    except Exception as e:
        print(f"⚠ No se pudo guardar el volumen ({e}); el experimento de volumen no estará disponible.")
    vacios = [t for t in todos if t not in df.columns or df[t].dropna().empty]
    if vacios:
        print("⚠ Sin datos (revisa tickers):", ", ".join(vacios))
    return df


def cargar_volumen(anos: int = 5):
    """Carga el volumen cacheado (o None si no existe)."""
    ruta = os.path.join(CARPETA, f"volumen_{anos}y.csv")
    if not os.path.exists(ruta):
        return None
    return pd.read_csv(ruta, index_col=0, parse_dates=True)


def cargar(anos: int = 5) -> pd.DataFrame:
    if not os.path.exists(_ruta(anos)):
        raise FileNotFoundError(
            f"No hay caché para {anos} años. Ejecuta antes:  python main.py descargar --anos {anos}")
    return pd.read_csv(_ruta(anos), index_col=0, parse_dates=True)
