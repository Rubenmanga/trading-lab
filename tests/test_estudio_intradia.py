"""Pruebas del estudio intradía (sin internet: datos inventados y un cliente falso)."""
from datetime import datetime, time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from zoneinfo import ZoneInfo

from tradinglab.intradia.estudio import ejecutar, informe, simular, universo
from tradinglab.intradia.estudio.simular import Costes

NY = ZoneInfo("America/New_York")
CFG = yaml.safe_load(open(Path(__file__).parents[1] / "config" / "estudio_intradia.yaml", encoding="utf-8"))
SIN_COSTES = Costes(0, 0)


def velas_dia(fecha="2025-03-03", precios=None, desde="9:30", vol=1000):
    """Velas de 1 min desde `desde` con los cierres dados (o=h=l=c salvo que se pase una tupla)."""
    h0, m0 = map(int, desde.split(":"))
    ini = datetime(*map(int, fecha.split("-")), h0, m0, tzinfo=NY)
    filas = []
    for i, p in enumerate(precios):
        o, h, l, c = p if isinstance(p, tuple) else (p, p, p, p)
        filas.append(dict(t=pd.Timestamp(ini) + pd.Timedelta(minutes=i), o=o, h=h, l=l, c=c, v=vol))
    return simular.preparar(pd.DataFrame(filas))


def test_objetivo_y_stop():
    b = velas_dia(precios=[100, 101, 102, 103.5])
    r = simular.gestionar(b, "compra", 100, 99, 103, time(12, 20), None, SIN_COSTES)
    assert r["motivo"] == "objetivo" and r["R"] == pytest.approx(3.0)
    # stop y objetivo en la misma vela: cuenta el stop (prudente)
    b = velas_dia(precios=[100, (100, 104, 98.5, 100)])
    r = simular.gestionar(b, "compra", 100, 99, 103, time(12, 20), None, SIN_COSTES)
    assert r["motivo"] == "stop" and r["R"] == pytest.approx(-1.0)


def test_hueco_por_debajo_del_stop_sale_a_la_apertura():
    b = velas_dia(precios=[100, (97, 97, 96, 96.5)])
    r = simular.gestionar(b, "compra", 100, 99, 103, time(12, 20), None, SIN_COSTES)
    assert r["salida"] == pytest.approx(97) and r["R"] == pytest.approx(-3.0)


def test_cierre_forzado_y_costes():
    b = velas_dia(precios=[100] * 5 + [101], desde="12:15")
    r = simular.gestionar(b, "compra", 100, 99, 103, time(12, 20), None, Costes(0.1, 0))
    assert r["motivo"] == "cierre forzado"
    assert r["R"] < 1.0  # el deslizamiento se come parte de la ganancia


def test_venta_en_corto():
    b = velas_dia(precios=[100, 99, 97.5, 96.9])
    r = simular.gestionar(b, "venta", 100, 101, 97, time(12, 20), None, SIN_COSTES)
    assert r["motivo"] == "objetivo" and r["R"] == pytest.approx(3.0)


def test_orb_compra_y_venta():
    verde = [(10, 10.1, 9.95, 10.05)] * 5 + [(10.05, 10.2, 10.05, 10.2)] + [10.3] * 10
    op = simular.orb(velas_dia(precios=verde), atr14=1.0, variante=CFG["orb"]["variantes"]["original"], costes=SIN_COSTES)
    assert op["lado"] == "compra" and op["entrada_bruta"] == pytest.approx(10.1) and op["hora_entrada"] == "09:35"
    roja = [(10, 10.05, 9.9, 9.95)] * 5 + [(9.95, 9.95, 9.8, 9.8)] + [9.7] * 10
    op = simular.orb(velas_dia(precios=roja), 1.0, CFG["orb"]["variantes"]["original"], SIN_COSTES)
    assert op["lado"] == "venta"
    assert simular.orb(velas_dia(precios=roja), 1.0, CFG["orb"]["variantes"]["original_solo_compras"], SIN_COSTES) is None


def test_orb_sin_ruptura():
    verde = [(10, 10.1, 9.95, 10.05)] * 5 + [10.0] * 20
    assert simular.orb(velas_dia(precios=verde), 1.0, CFG["orb"]["variantes"]["original"], SIN_COSTES) is None


def test_rasgos_gainer():
    pre = velas_dia(precios=[11.0] * 300, desde="4:00")
    reg = velas_dia(precios=list(np.linspace(12, 15, 390)), desde="9:30")
    m = pd.concat([pre, reg])
    d = simular.rasgos_gainer(m, 10.0, CFG["reglas_agente_a"], SIN_COSTES)
    assert d["pm_hueco_0900"] == pytest.approx(0.10)
    assert d["apertura"] == 12 and d["apertura_a_cierre"] == pytest.approx(0.25)
    assert d["reglasA_R"] > 0


def test_candidatas_sin_mirar_el_futuro():
    filas = []
    for s, (o, c) in {"GAN": (10.0, 13.0), "HUE": (11.0, 10.5), "NADA": (10.1, 10.0)}.items():
        for i in range(20):
            filas.append(dict(simbolo=s, t=pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(days=i),
                              o=10, h=10.2, l=9.8, c=10, v=2_000_000))
        filas.append(dict(simbolo=s, t=pd.Timestamp("2025-01-21", tz="UTC"), o=o, h=max(o, c), l=min(o, c), c=c, v=9e6))
    r = universo.rasgos_diarios(pd.DataFrame(filas))
    c = universo.candidatas(r, {**CFG, "orb": {**CFG["orb"], "atr_min": 0.1, "prefiltro_por_dia": 1}})
    ult = c[c["fecha"] == "2025-01-20"].set_index("simbolo")  # 21-ene 00:00 UTC = 20-ene en NY
    assert ult.loc["GAN", "A"] and ult.loc["HUE", "A"] and "NADA" not in ult.index
    assert ult["B"].sum() == 1 and ult.loc["HUE", "B"]  # el mayor hueco del día
    # el volumen medio usa solo días anteriores (no el del propio día)
    assert ult.loc["GAN", "vol_medio14"] == pytest.approx(2_000_000)


class ClienteFalso:
    llamadas = 0
    feed = "falso"

    def velas(self, simbolos, timeframe, desde, hasta):
        rng = np.random.default_rng(abs(hash((tuple(simbolos), str(desde)))) % 2**32)
        partes = []
        for s in simbolos:
            fecha = pd.Timestamp(desde).tz_convert(NY).strftime("%Y-%m-%d")
            p = 10 * np.exp(np.cumsum(rng.normal(0.0005, 0.004, 720)))
            pre = velas_dia(fecha, [(x, x * 1.001, x * 0.999, x) for x in p[:330]], "4:00")
            reg = velas_dia(fecha, [(x, x * 1.002, x * 0.998, x * 1.0005) for x in p[330:]], "9:30")
            partes.append(pd.concat([pre, reg]).assign(simbolo=s).reset_index(drop=True))
        return pd.concat(partes, ignore_index=True)

    def noticias(self, simbolo, desde, hasta):
        return [{"headline": "Company announces FDA approval"}]


def test_todo_el_proceso_con_datos_inventados(tmp_path):
    cands = pd.DataFrame([dict(fecha=f, simbolo=s, cierre_ant=9.0, hueco=0.12, sube_dia=0.2, vol_medio14=1e6, v=5e6,
                               atr14=0.6, A=True, B=True)
                          for f in ["2025-03-03", "2025-03-04"] for s in ["AAA", "BBB", "CCC"]])
    g, o = ejecutar.procesar(ClienteFalso(), cands, "2025-03-01", "2025-03-31", CFG)
    assert len(g) == 6 and (g["motivo"] == "FDA o ensayo").all()
    assert set(o["variante"]) <= set(CFG["orb"]["variantes"])
    g.to_csv(tmp_path / "gainers-2025.csv.gz", index=False)
    o.to_csv(tmp_path / "orb-2025.csv.gz", index=False)
    res = informe.generar(tmp_path, CFG)
    assert res["gainers"]["top_gainers"] == 6
    md = informe.guardar(res, tmp_path / "estrategias" / "backtest", "2025-03-05")
    texto = md.read_text(encoding="utf-8")
    assert texto.startswith("# Backtest intradía") and "ORB" in texto


def test_clasificar_titulares():
    assert ejecutar.clasificar([]) == "sin noticia"
    assert ejecutar.clasificar(["XYZ to be acquired by Big Pharma for $12 per share"]) == "fusión o compra"
    assert ejecutar.clasificar(["XYZ reports third quarter results"]) == "resultados"
    assert ejecutar.clasificar(["XYZ announces $5M registered direct offering"]) == "ampliación de capital"


def test_simbolos_raros_y_400():
    import requests
    vals = [dict(symbol="AAPL", exchange="NASDAQ"), dict(symbol="0029900E0", exchange="NASDAQ"),
            dict(symbol="BRK.B", exchange="NYSE"), dict(symbol="XYZ", exchange="OTC")]
    assert universo.simbolos_validos(vals) == ["AAPL"]

    class C:
        def velas(self, sims, *a):
            if "MALO" in sims:
                r = requests.Response()
                r.status_code = 400
                raise requests.HTTPError(response=r)
            return pd.DataFrame(dict(simbolo=sims))
    df = universo.velas_seguras(C(), ["A", "B", "MALO", "C"], "1Day", None, None)
    assert sorted(df["simbolo"]) == ["A", "B", "C"]


def test_ticker_na_no_es_un_vacio(tmp_path):
    pd.DataFrame(dict(fecha=["2025-01-02"], simbolo=["NA"], variante=["original"], R=[1.0])).to_csv(tmp_path / "x.csv", index=False)
    assert pd.read_csv(tmp_path / "x.csv", converters={"simbolo": str})["simbolo"][0] == "NA"
