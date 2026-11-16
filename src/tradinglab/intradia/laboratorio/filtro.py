"""Filtro «¿entrar o no?»: mira VARIAS temporalidades e indicadores justo antes de entrar y da una nota
de 0 a 100. Cuanto más alta, más cosas empujan a favor de la operación.

Solo usa velas ANTERIORES a la entrada (nada del futuro). Cada punto vale 1 si está a favor, 0 si está en
contra y 0,5 si aún no hay datos suficientes (muy temprano en la sesión):

  1 min   · media rápida (EMA 9) por encima de la lenta (EMA 21)        -> el último rato empuja a favor
  5 min   · el cierre de 5 min sube respecto a hace 3 velas de 5 min      -> la media hora empuja a favor
  15 min  · el precio está por encima de la apertura del día              -> el día va a favor
  diario  · el hueco de apertura va en la misma dirección                 -> la noticia/ayer empuja a favor
  VWAP    · el precio está del lado bueno del precio medio del día
  RSI     · no está «agotado» (RSI 14 de 1 min < 80 para comprar, > 20 para vender en corto)
  mercado · el Nasdaq (QQQ) está del lado bueno de su VWAP
  volumen · en los 5 primeros minutos negoció al menos el 10 % de un día normal

Para un corto todo se lee al revés (por debajo de la media, día bajista...).
"""
from __future__ import annotations

import pandas as pd

from ..estudio import simular

NOMBRES = ["1min", "5min", "15min", "diario", "vwap", "rsi", "mercado", "volumen"]


def _ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False).mean()


def rsi(c: pd.Series, n: int = 14) -> float | None:
    if len(c) <= n:
        return None
    d = c.diff()
    sube = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    baja = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    if baja == 0:
        return 100.0
    return float(100 - 100 / (1 + sube / baja))


def _vwap(r: pd.DataFrame) -> float:
    tip = (r["h"] + r["l"] + r["c"]) / 3
    v = r["v"].clip(lower=0)
    return float((tip * v).sum() / v.sum()) if v.sum() > 0 else float(r["c"].iloc[-1])


def puntos(antes: pd.DataFrame, lado: str, ctx: dict, indice: pd.DataFrame | None = None) -> dict:
    """`antes`: velas de la sesión regular ANTERIORES a la entrada. Devuelve cada punto (0, 0,5 o 1)."""
    s = 1 if lado == "compra" else -1
    p = dict.fromkeys(NOMBRES, 0.5)
    if antes is None or len(antes) == 0:
        return p
    c = antes["c"].astype(float)
    ult = float(c.iloc[-1])
    if len(c) >= 21:
        p["1min"] = float(s * (_ema(c, 9).iloc[-1] - _ema(c, 21).iloc[-1]) > 0)
    c5 = c.resample("5min").last().dropna()
    if len(c5) >= 4:
        p["5min"] = float(s * (c5.iloc[-1] - c5.iloc[-4]) > 0)
    if len(antes) >= 15:
        p["15min"] = float(s * (ult - float(antes["o"].iloc[0])) > 0)
    if ctx.get("hueco") is not None:
        p["diario"] = float(s * ctx["hueco"] > 0)
    p["vwap"] = float(s * (ult - _vwap(antes)) > 0)
    x = rsi(c)
    if x is not None:
        p["rsi"] = float(x < 80) if s > 0 else float(x > 20)
    if indice is not None and len(indice):
        p["mercado"] = float(s * (float(indice["c"].iloc[-1]) - _vwap(indice)) > 0)
    if ctx.get("rvol5") is not None:
        p["volumen"] = float(ctx["rvol5"] >= 0.10)
    return p


def nota(p: dict) -> float:
    return round(100 * sum(p.values()) / len(p), 1)


def evaluar(m: pd.DataFrame, hora_entrada: str, lado: str, ctx: dict, indice: pd.DataFrame | None = None) -> dict:
    """Nota del filtro para una entrada a la hora `hora_entrada` (HH:MM, NY)."""
    hh = simular.T(hora_entrada)
    r = simular.regular(m)
    antes = r[r["hora"] < hh]
    idx = None
    if indice is not None:
        ri = simular.regular(indice)
        idx = ri[ri["hora"] < hh]
    p = puntos(antes, lado, ctx, idx)
    return dict(nota=nota(p), filtro="".join("1" if v == 1 else ("0" if v == 0 else "·") for v in p.values()))
