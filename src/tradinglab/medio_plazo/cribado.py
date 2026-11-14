"""Cribado: primera criba de small caps de EE. UU. de TODOS los sectores.

Criterio de partida: empresas pequeñas, con suficientes analistas siguiéndolas y con un precio
objetivo medio bastante por encima del precio actual. Es solo un filtro grueso: el análisis de
verdad lo hace la skill `analizar-empresa-12m`.
"""
from __future__ import annotations

import csv

from ..common.config import ruta

COLUMNAS = ["ticker", "empresa", "sector", "industria", "precio", "capitalizacion_musd",
            "analistas", "recomendacion", "objetivo_medio", "potencial_pct", "prioritario"]


def _consulta(c: dict):
    from yfinance import EquityQuery as Q
    return Q("and", [
        Q("eq", ["region", "us"]),
        Q("btwn", ["intradaymarketcap", c["capitalizacion_min_usd"], c["capitalizacion_max_usd"]]),
        Q("gt", ["avgdailyvol3m", c["volumen_medio_min"]]),
        Q("gt", ["intradayprice", c["precio_min_usd"]]),
    ])


def cribar(cfg: dict, descargar=None) -> list[dict]:
    import yfinance as yf

    c = cfg["cribado"]
    prioritarios = {s.lower() for s in c.get("sectores_prioritarios") or []}
    quotes = []
    for offset in range(0, 1000, 250):  # Yahoo devuelve como máximo 250 por página
        r = yf.screen(_consulta(c), offset=offset, size=250, sortField="intradaymarketcap", sortAsc=False)
        lote = r.get("quotes", [])
        quotes += lote
        if len(lote) < 250:
            break
    filas = []
    for q in quotes:
        p, n = q.get("regularMarketPrice"), q.get("numberOfAnalystOpinions")
        if not p:
            continue
        filas.append(dict(ticker=q.get("symbol"), empresa=q.get("shortName") or q.get("longName"),
                          precio=p, capitalizacion_musd=round((q.get("marketCap") or 0) / 1e6), analistas=n))
    # El objetivo de analistas y el sector no siempre vienen en el cribado: se completan uno a uno.
    descargar = descargar or _detalle
    resultado = []
    for f in filas:
        f.update(descargar(f["ticker"]))
        if (f.get("analistas") or 0) < c["analistas_min"] or not f.get("objetivo_medio"):
            continue
        f["potencial_pct"] = round((f["objetivo_medio"] / f["precio"] - 1) * 100, 1)
        if f["potencial_pct"] < c["potencial_min_pct"] or f["potencial_pct"] > c.get("potencial_max_pct", 1e9):
            continue
        recs = c.get("recomendaciones")
        if recs and f.get("recomendacion") and f["recomendacion"] not in recs:
            continue
        f["prioritario"] = "sí" if (f.get("sector") or "").lower() in prioritarios else ""
        resultado.append(f)
    resultado.sort(key=lambda f: (f["prioritario"] != "sí", -f["potencial_pct"]))
    por_sector, final = {}, []
    for f in resultado:
        s = f.get("sector") or "?"
        if por_sector.get(s, 0) >= c.get("max_por_sector", 10**6):
            continue
        por_sector[s] = por_sector.get(s, 0) + 1
        final.append(f)
    return final[: c["max_resultados"]]


def _detalle(ticker: str) -> dict:
    import yfinance as yf
    try:
        i = yf.Ticker(ticker).info or {}
    except Exception:  # noqa: BLE001
        return {}
    return dict(sector=i.get("sector"), industria=i.get("industry"), analistas=i.get("numberOfAnalystOpinions"),
                recomendacion=i.get("recommendationKey"), objetivo_medio=i.get("targetMeanPrice"))


def guardar(filas: list[dict], path=None) -> str:
    path = path or ruta("investigacion", "candidatos.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    return str(path)
