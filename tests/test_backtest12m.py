"""Pruebas sin internet del backtest del agente B, con datos inventados."""
import csv
import gzip
import json
import random
from datetime import date

import pandas as pd

from tradinglab.backtest12m import datos, motor


def test_a_mensual_precio_real_con_contrasplit():
    # contrasplit 1 por 10 el 2020-02-03: Yahoo ya muestra 10 $ en enero, pero aquel día cotizaba a 1 $
    idx = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-28"])
    df = pd.DataFrame({"Close": [10.0, 10.0, 10.0, 12.0], "Adj Close": [10.0, 10.0, 10.0, 12.0],
                       "Volume": [100, 100, 100, 100], "Stock Splits": [0, 0, 0.1, 0]}, index=idx)
    m = {r["mes"]: r for r in datos.a_mensual(df, "AAA")}
    assert abs(m["2020-01"]["real"] - 1.0) < 1e-9 and abs(m["2020-02"]["real"] - 12.0) < 1e-9
    assert m["2020-02"]["adj"] == 12.0


def test_compactar_y_acciones_en():
    facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
        {"end": "2020-12-31", "val": 5, "form": "10-K", "filed": "2021-03-01", "accn": "x", "fy": 2020}]}},
        "Otra": {"units": {"USD": [{"end": "2020-12-31", "val": 1, "form": "10-K", "filed": "2021-03-01"}]}}},
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"end": "2021-02-15", "val": 100, "form": "10-K", "filed": "2021-03-01"},
            {"end": "2021-05-01", "val": 120, "form": "10-Q", "filed": "2021-05-10"}]}}}}}
    c = datos.compactar(facts)
    assert "Otra" not in c["facts"]["us-gaap"] and "accn" not in c["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]
    assert motor.acciones_en(c, date(2021, 4, 1)) == 100
    assert motor.acciones_en(c, date(2021, 6, 1)) == 120
    assert motor.acciones_en(c, date(2021, 2, 1)) is None          # aún no se había presentado
    assert motor.acciones_en(c, date(2023, 1, 1)) is None          # portada demasiado vieja


def test_meses():
    assert motor.mes_mas("2014-11", 3) == "2015-02" and motor.mes_mas("2015-01", -1) == "2014-12"
    assert motor.trimestres("2014-12") == ["2014-03", "2014-06", "2014-09", "2014-12"]


def _facts_empresa(r: random.Random):
    gaap, dei = {}, []
    base = r.uniform(80e6, 400e6)
    for a in range(2012, 2026):
        crec = 1 + r.uniform(-0.1, 0.3)
        base *= crec
        vals = {"Revenues": base, "CostOfRevenue": base * r.uniform(0.3, 0.7), "NetIncomeLoss": base * r.uniform(-0.1, 0.15),
                "OperatingIncomeLoss": base * r.uniform(-0.05, 0.2), "Assets": base * 1.5,
                "NetCashProvidedByUsedInOperatingActivities": base * r.uniform(-0.05, 0.2),
                "AssetsCurrent": base * 0.6, "LiabilitiesCurrent": base * 0.3, "Liabilities": base * 0.7,
                "StockholdersEquity": base * 0.8, "RetainedEarningsAccumulatedDeficit": base * 0.1,
                "WeightedAverageNumberOfDilutedSharesOutstanding": 50e6, "CashAndCashEquivalentsAtCarryingValue": base * 0.2}
        for n, v in vals.items():
            x = {"end": f"{a}-12-31", "val": v, "form": "10-K", "filed": f"{a + 1}-03-01"}
            if n not in ("Assets", "AssetsCurrent", "LiabilitiesCurrent", "Liabilities", "StockholdersEquity",
                         "RetainedEarningsAccumulatedDeficit", "CashAndCashEquivalentsAtCarryingValue"):
                x["start"] = f"{a}-01-01"
            u = "shares" if "Shares" in n else "USD"
            gaap.setdefault(n, {"units": {u: []}})["units"][u].append(x)
        for mes in ("03-01", "05-10", "08-10", "11-10"):
            dei.append({"end": f"{a + 1}-{mes}", "val": 50e6, "form": "10-Q", "filed": f"{a + 1}-{mes}"})
    return {"us-gaap": gaap, "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": dei}}}}


def test_ejecutar_de_punta_a_punta(tmp_path):
    r = random.Random(7)
    d = tmp_path / "datos"
    d.mkdir()
    meses = [motor.mes_mas("2013-01", k) for k in range(0, 12 * 13)]       # hasta 2025-12
    with open(d / "tickers.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cik", "ticker", "nombre", "bolsa"])
        for i in range(90):
            w.writerow([str(i).zfill(10), f"T{i}", f"Empresa {i}", "Nasdaq"])
    with gzip.open(d / "cuentas.jsonl.gz", "wt") as fh:
        for i in range(90):
            fh.write(json.dumps({"cik": str(i).zfill(10), "facts": _facts_empresa(r)}) + "\n")
    with gzip.open(d / "precios-1.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "mes", "adj", "real", "dolares_dia"])
        for t in [f"T{i}" for i in range(90)] + ["IWM"]:
            p = r.uniform(8, 30)
            for m in meses:
                p *= 1 + r.gauss(0.01, 0.08)
                w.writerow([t, m, round(p, 4), round(p, 4), 5e6])
    with gzip.open(d / "supervivencia.json.gz", "wt") as fh:
        json.dump({"1": {"anios": {"2015": 2e8}, "cotiza_hoy": False},
                   "2": {"anios": {"2015": 2e8, "2016": 2e8, "2017": 2e8}, "cotiza_hoy": True}}, fh)
    res = motor.ejecutar(str(d), str(tmp_path / "salida"))
    assert res["cartera"]["nota"]["trimestres"] >= 10
    assert set(res["cartera"]) >= {"nota", "calidad", "momentum", "f_score"}
    assert res["doce_meses"]["correlacion"]["nota"]["n"] >= 10
    assert res["pelotazos"]["casos"] > 0
    assert res["supervivencia"]["por_anio"]["2015"]["desaparecen_pct"] == 50.0
    informe = next((tmp_path / "salida").glob("INFORME-*.md")).read_text()
    assert "Resumen en 5 líneas" in informe and "Límites" in informe
