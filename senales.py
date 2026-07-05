# -*- coding: utf-8 -*-
"""Señales externas para el motor COMPLETO: analistas + fundamentales + sentimiento IA.

Filosofía de robustez (la misma del Gemelo):
- Caché persistente commiteada al repo: fundamentales ~1 vez/día, sentimiento cada 12 h.
- Degradación elegante: si una señal falta, su peso se EXCLUYE del score (no penaliza).
- La clave de Gemini viene del entorno (GitHub Secrets), nunca del código.
"""
import json
import os
import time
import urllib.request
from datetime import datetime

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_FUND = os.path.join(RAIZ, "fundamentales.json")
RUTA_SENT = os.path.join(RAIZ, "sentimiento.json")


def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _guardar(ruta, obj):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _clamp(x, a, b):
    return max(a, min(b, x))


# ------------------------------------------------ fundamentales + analistas
def _scores_fund(f):
    """Réplica exacta de _scoresFund del Gemelo (Codigo.gs)."""
    if not f:
        return None, None
    aS = None
    if f.get("rating") is not None:
        aS = _clamp((5 - f["rating"]) / 4 * 100, 0, 100)
        if f.get("objetivo") and f.get("precio"):
            up = (f["objetivo"] / f["precio"] - 1) * 100
            aS = 0.7 * aS + 0.3 * _clamp(50 + up * 1.67, 0, 100)
    elif f.get("objetivo") and f.get("precio"):
        up2 = (f["objetivo"] / f["precio"] - 1) * 100
        aS = _clamp(50 + up2 * 1.67, 0, 100)
    parts = []
    if f.get("roe") is not None:
        parts.append(_clamp(40 + f["roe"] * 200, 0, 100))
    if f.get("margen") is not None:
        parts.append(_clamp(40 + f["margen"] * 250, 0, 100))
    if f.get("per") is not None and f["per"] > 0:
        parts.append(_clamp(100 - (f["per"] - 10) * 2.5, 10, 100))
    if f.get("deuda") is not None:
        parts.append(_clamp(100 - f["deuda"] * 0.4, 10, 100))
    fS = sum(parts) / len(parts) if parts else None
    return aS, fS


def fundamentales(tickers, horas_cache=20):
    """Devuelve {tk: {"analyst": 0..100|None, "fund": 0..100|None}} con caché diaria."""
    cache = _leer(RUTA_FUND) or {}
    edad_h = (time.time() - cache.get("_ts", 0)) / 3600
    if cache.get("datos") and edad_h < horas_cache:
        print(f"Fundamentales desde caché ({edad_h:.1f} h; se renuevan a las {horas_cache} h).")
        return cache["datos"]
    print(f"Descargando fundamentales/analistas de {len(tickers)} valores (1 vez/día)…")
    import yfinance as yf
    datos, ok = {}, 0
    for tk in tickers:
        try:
            info = yf.Ticker(tk).info or {}
            f = {"rating": info.get("recommendationMean"),
                 "objetivo": info.get("targetMeanPrice"),
                 "precio": info.get("currentPrice") or info.get("regularMarketPrice"),
                 "per": info.get("trailingPE") or info.get("forwardPE"),
                 "roe": info.get("returnOnEquity"),
                 "margen": info.get("profitMargins"),
                 "deuda": info.get("debtToEquity")}
            aS, fS = _scores_fund(f)
            datos[tk] = {"analyst": aS, "fund": fS}
            if aS is not None or fS is not None:
                ok += 1
        except Exception:
            datos[tk] = {"analyst": None, "fund": None}
        time.sleep(0.12)
    print(f"  {ok}/{len(tickers)} con datos (el resto: peso excluido, no penaliza).")
    if ok:
        _guardar(RUTA_FUND, {"_ts": time.time(), "datos": datos})
        return datos
    viejo = (cache or {}).get("datos")
    if viejo:
        print("  ⚠ Descarga vacía: se conserva la caché anterior.")
        return viejo
    return datos


# --------------------------------------------------------- sentimiento (IA)
def sentimiento(sectores, tickers_nombres, horas_cache=12):
    """Devuelve {"sectores": {sector: -2..2}, "acciones": {tk: -2..2}} o None si no hay clave.

    Usa Gemini (gratis) con la clave en la variable de entorno GEMINI_API_KEY
    (en GitHub: Settings → Secrets → Actions). Caché de 12 h commiteada al repo.
    """
    clave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not clave:
        return None
    cache = _leer(RUTA_SENT) or {}
    edad_h = (time.time() - cache.get("_ts", 0)) / 3600
    if cache.get("datos") and edad_h < horas_cache:
        print(f"Sentimiento IA desde caché ({edad_h:.1f} h).")
        return cache["datos"]
    print("Consultando sentimiento IA (Gemini)…")
    prompt = ("Eres analista de mercados. Según tu conocimiento del contexto macro, geopolítico y "
              "sectorial reciente, valora el sentimiento a 1-3 meses (entero -2 a +2; 0 = neutral).\n"
              "SECTORES: " + ", ".join(sectores) + "\n"
              "ACCIONES: " + "; ".join(f"{t} ({n})" for t, n in tickers_nombres) + "\n"
              'Devuelve SOLO JSON: {"sectores":[{"k":"<sector>","s":<-2..2>}],'
              '"acciones":[{"k":"<ticker exacto>","s":<-2..2>}]}')
    cuerpo = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 32768,
                             "responseMimeType": "application/json",
                             "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
    url = ("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash"
           ":generateContent?key=" + clave)
    try:
        req = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.loads(r.read().decode())
        txt = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"])
        txt = txt[txt.index("{"): txt.rindex("}") + 1]
        obj = json.loads(txt)
        datos = {"sectores": {o["k"]: _clamp(round(float(o.get("s", 0))), -2, 2)
                              for o in obj.get("sectores", [])},
                 "acciones": {o["k"]: _clamp(round(float(o.get("s", 0))), -2, 2)
                              for o in obj.get("acciones", [])}}
        _guardar(RUTA_SENT, {"_ts": time.time(), "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                             "datos": datos})
        print(f"  Sentimiento: {len(datos['sectores'])} sectores, {len(datos['acciones'])} acciones.")
        return datos
    except Exception as err:
        print(f"  ⚠ Gemini falló ({err}); se usa la caché previa si existe.")
        return (cache or {}).get("datos")
