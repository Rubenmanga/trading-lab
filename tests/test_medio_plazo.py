from datetime import date

import yaml

from tradinglab.common.config import ruta
from tradinglab.medio_plazo import alertas


def test_alertas():
    cfg = yaml.safe_load(open(ruta("config", "medio_plazo.yaml"), encoding="utf-8"))
    filas = [
        dict(ticker="AAA", veredicto="comprar_en_zona", zona_entrada_max="10", precio_objetivo_12m="20",
             stop_tesis="7", fecha_catalizador="2026-11-20", proximo_catalizador="Resultados Q3",
             fecha_analisis="2026-11-01"),
        dict(ticker="BBB", veredicto="vigilar", zona_entrada_max="5", stop_tesis="4", fecha_analisis="2026-08-01"),
        dict(ticker="CCC", veredicto="descartar"),
    ]
    precios = {"AAA": 9.5, "BBB": 3.9}
    tipos = {(a["ticker"], a["tipo"]) for a in alertas.revisar(cfg, filas, precios.get, hoy=date(2026, 11, 14))}
    assert tipos == {("AAA", "ZONA DE ENTRADA"), ("AAA", "CATALIZADOR CERCA"),
                     ("BBB", "TESIS EN PELIGRO"), ("BBB", "REVISAR ANÁLISIS")}


def test_cribado_filtra_y_prioriza(monkeypatch):
    import yfinance

    from tradinglab.medio_plazo import cribado

    quotes = [dict(symbol="AAA", shortName="A", regularMarketPrice=10, marketCap=5e8),
              dict(symbol="BBB", shortName="B", regularMarketPrice=10, marketCap=6e8),
              dict(symbol="CCC", shortName="C", regularMarketPrice=10, marketCap=7e8),
              dict(symbol="DDD", shortName="D", regularMarketPrice=10, marketCap=8e8)]
    monkeypatch.setattr(yfinance, "screen", lambda *a, **k: {"quotes": quotes})
    detalle = {"AAA": dict(sector="Technology", analistas=5, objetivo_medio=20),
               "BBB": dict(sector="Industrials", analistas=8, objetivo_medio=14),
               "CCC": dict(sector="Healthcare", analistas=1, objetivo_medio=30),   # pocos analistas
               "DDD": dict(sector="Energy", analistas=6, objetivo_medio=11)}       # poco potencial
    cfg = yaml.safe_load(open(ruta("config", "medio_plazo.yaml"), encoding="utf-8"))
    cfg["cribado"]["sectores_prioritarios"] = ["Industrials"]
    r = cribado.cribar(cfg, descargar=lambda t: dict(detalle[t]))
    assert [f["ticker"] for f in r] == ["BBB", "AAA"]


def test_cribado_descarta_extremos_y_limita_sector(monkeypatch):
    import yfinance

    from tradinglab.medio_plazo import cribado

    quotes = [dict(symbol=s, shortName=s, regularMarketPrice=10, marketCap=5e8) for s in ["H1", "H2", "H3", "X", "V"]]
    monkeypatch.setattr(yfinance, "screen", lambda *a, **k: {"quotes": quotes})
    detalle = {"H1": dict(sector="Healthcare", analistas=5, objetivo_medio=20, recomendacion="buy"),
               "H2": dict(sector="Healthcare", analistas=5, objetivo_medio=19, recomendacion="strong_buy"),
               "H3": dict(sector="Healthcare", analistas=5, objetivo_medio=18, recomendacion="buy"),
               "X": dict(sector="Technology", analistas=5, objetivo_medio=60, recomendacion="buy"),   # +500%: sospechoso
               "V": dict(sector="Energy", analistas=5, objetivo_medio=16, recomendacion="hold")}      # consenso "mantener"
    cfg = yaml.safe_load(open(ruta("config", "medio_plazo.yaml"), encoding="utf-8"))
    cfg["cribado"]["max_por_sector"] = 2
    r = cribado.cribar(cfg, descargar=lambda t: dict(detalle[t]))
    assert [f["ticker"] for f in r] == ["H1", "H2"]


def test_estado_calcula_distancias():
    filas = [dict(ticker="AAA", zona_entrada_max="10", precio_objetivo_12m="15", stop_tesis="8"),
             dict(ticker="ZZZ", zona_entrada_max="10")]
    e = alertas.estado(filas, {"AAA": 12.0}.get)
    assert e[0]["distancia_zona_pct"] == 20.0 and e[0]["potencial_pct"] == 25.0 and e[0]["distancia_stop_pct"] == 50.0
    assert e[1]["precio"] is None and e[1]["potencial_pct"] is None
