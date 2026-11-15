"""Paso 1: velas DIARIAS de todas las acciones de EE. UU. (activas y deslistadas) y selección de candidatas.

No guardamos las ~25 millones de velas: de cada día solo nos quedamos con las acciones que interesan:
  A) estudio de top gainers: suben >= +15 % en el día o abren con un hueco >= +8 %, precio >= 1 $.
  B) ORB: precio >= 5 $, volumen medio >= 1 M acciones, ATR >= 0,5 $ y las 40 con más hueco (arriba o abajo).
Todo lo que se usa para elegir B se conoce a las 9:30 (cierre de ayer, medias de días anteriores y el
precio de apertura), así que no hay trampa de "mirar el futuro".
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

BOLSAS = {"NYSE", "NASDAQ", "AMEX", "ARCA", "BATS", "NYSEARCA"}
TICKER = re.compile(r"^[A-Z]{1,5}$")  # las inactivas traen códigos raros (CUSIP, derechos...): fuera


def simbolos_validos(valores: list[dict]) -> list[str]:
    out = set()
    for a in valores:
        s = str(a.get("symbol", ""))
        if a.get("exchange") not in BOLSAS or not TICKER.match(s):
            continue
        out.add(s)
    return sorted(out)


def rasgos_diarios(df: pd.DataFrame) -> pd.DataFrame:
    """De velas diarias (simbolo, t, o, h, l, c, v) calcula lo que se sabe cada mañana y lo que pasó."""
    if df.empty:
        return df
    df = df.sort_values(["simbolo", "t"]).copy()
    df["fecha"] = df["t"].dt.tz_convert("America/New_York").dt.date.astype(str)
    g = df.groupby("simbolo", sort=False)
    df["cierre_ant"] = g["c"].shift(1)
    tr = np.maximum(df["h"] - df["l"], np.maximum((df["h"] - df["cierre_ant"]).abs(), (df["l"] - df["cierre_ant"]).abs()))
    df["tr"] = tr
    g = df.groupby("simbolo", sort=False)
    df["vol_medio14"] = g["v"].transform(lambda x: x.shift(1).rolling(14, min_periods=10).mean())
    df["atr14"] = g["tr"].transform(lambda x: x.shift(1).rolling(14, min_periods=10).mean())
    df["hueco"] = df["o"] / df["cierre_ant"] - 1
    df["sube_dia"] = df["c"] / df["cierre_ant"] - 1
    return df.dropna(subset=["cierre_ant"]).drop(columns=["tr", "t"])


def candidatas(r: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Marca las filas A (gainers) y B (ORB). Devuelve solo las que son A o B."""
    if r.empty:
        return r.assign(A=False, B=False)
    ca, cb = cfg["gainers"], cfg["orb"]
    liquida = (r["vol_medio14"] * r["cierre_ant"]) >= ca["min_dolares_dia"]
    A = (r["cierre_ant"] >= ca["precio_min"]) & liquida & (
        (r["sube_dia"] >= ca["subida_min"]) | (r["hueco"] >= ca["hueco_apertura_min"]))
    base_b = (r["cierre_ant"] >= cb["precio_min"]) & (r["vol_medio14"] >= cb["vol_medio_min"]) & (r["atr14"] >= cb["atr_min"])
    rb = r[base_b].assign(_abs=r.loc[base_b, "hueco"].abs())
    top = rb.sort_values("_abs", ascending=False).groupby("fecha").head(cb["prefiltro_por_dia"]).index
    B = pd.Series(False, index=r.index)
    B.loc[top] = True
    out = r.assign(A=A, B=B)
    return out[out["A"] | out["B"]].reset_index(drop=True)


def velas_seguras(cliente, sims: list[str], timeframe: str, ini, fin) -> pd.DataFrame:
    """Como cliente.velas, pero si Alpaca rechaza la lista (400: algún símbolo no válido),
    la parte en dos hasta aislar y saltar el símbolo malo."""
    import requests
    try:
        return cliente.velas(sims, timeframe, ini, fin)
    except requests.HTTPError as e:
        if e.response is None or e.response.status_code != 400:
            raise
        if len(sims) == 1:
            print(f"  aviso: Alpaca no acepta el símbolo {sims[0]}, se salta")
            return pd.DataFrame()
        mitad = len(sims) // 2
        partes = [velas_seguras(cliente, sims[:mitad], timeframe, ini, fin),
                  velas_seguras(cliente, sims[mitad:], timeframe, ini, fin)]
        return pd.concat([p for p in partes if len(p)], ignore_index=True) if any(len(p) for p in partes) else pd.DataFrame()


def descargar(cliente, desde: str, hasta: str, cfg: dict, max_simbolos: int | None = None,
              trozo: int = 100) -> pd.DataFrame:
    """Baja las velas diarias por trozos de símbolos y se queda solo con las candidatas."""
    sims = simbolos_validos(cliente.valores())
    if max_simbolos:
        sims = sims[:max_simbolos]
    ini = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc) - timedelta(days=40)
    fin = min(datetime.fromisoformat(hasta).replace(tzinfo=timezone.utc) + timedelta(days=1),
              datetime.now(timezone.utc) - timedelta(minutes=20))
    partes = []
    for i in range(0, len(sims), trozo):
        df = velas_seguras(cliente, sims[i:i + trozo], "1Day", ini, fin)
        c = candidatas(rasgos_diarios(df), cfg)
        partes.append(c[(c["fecha"] >= desde) & (c["fecha"] <= hasta)])
        if (i // trozo) % 10 == 0:
            print(f"  diario: {i + trozo}/{len(sims)} símbolos · {sum(len(p) for p in partes)} candidatas · "
                  f"{cliente.llamadas} llamadas", flush=True)
    out = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    # El top 40 de B se decide entre TODAS las acciones del día: se recalcula con todo junto
    if len(out):
        out = candidatas(out.drop(columns=["A", "B"]), cfg)
    return out
