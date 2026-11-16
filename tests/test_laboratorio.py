"""Pruebas del laboratorio intradía (sin internet: velas inventadas)."""
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml
from zoneinfo import ZoneInfo

from tradinglab.intradia.estudio import simular
from tradinglab.intradia.estudio.simular import Costes
from tradinglab.intradia.laboratorio import estrategias as E
from tradinglab.intradia.laboratorio import informe, motor

NY = ZoneInfo("America/New_York")
CFG = yaml.safe_load(open(Path(__file__).parents[1] / "config" / "laboratorio_intradia.yaml", encoding="utf-8"))
RIESGO = {**CFG["riesgo"], "trailing": None}
CERO = Costes(0, 0)


def velas(precios, fecha="2025-03-03", vol=1000):
    ini = datetime(*map(int, fecha.split("-")), 9, 30, tzinfo=NY)
    filas = []
    for i, p in enumerate(precios):
        o, h, l, c = p if isinstance(p, tuple) else (p, p, p, p)
        filas.append(dict(t=pd.Timestamp(ini) + pd.Timedelta(minutes=i), o=o, h=h, l=l, c=c, v=vol))
    return simular.preparar(pd.DataFrame(filas))


def test_modo_demo():
    assert CFG["modo_cuenta"] == "demo"


def test_vwap_ponderado():
    r = E.con_vwap(velas([10, 20]))
    assert r["vwap"].iloc[-1] == pytest.approx(15)


def test_corto_hueco_entra_0935_y_cierra_1545():
    m = velas([150] * 5 + [150] + [140] * 400)
    op = E.corto_hueco(m, {"hueco": 0.6}, CFG["estrategias"]["corto_hueco"], RIESGO, CERO)
    assert op["hora_entrada"] == "09:35" and op["lado"] == "venta"
    assert op["motivo"] == "cierre forzado" and op["hora_salida"].startswith("15:45")
    assert op["R"] == pytest.approx((150 - 140) / (150 * 0.15), rel=1e-3)
    assert E.corto_hueco(m, {"hueco": 0.1}, CFG["estrategias"]["corto_hueco"], RIESGO, CERO) is None


def test_hueco_volumen_largo_rompe_rango_y_vwap():
    # 15 min planos en 100-101, luego rompe a 102 y sube a 106 -> objetivo 3R (3 %)
    rango = [(100, 101, 100, 100.5)] * 15
    m = velas(rango + [(100.5, 102, 100.5, 102), 102, 103, 104, 105, 107] + [107] * 10)
    ctx = {"hueco": 0.06, "rvol5": 0.5}
    op = E.hueco_volumen(m, ctx, CFG["estrategias"]["hueco_volumen"], RIESGO, CERO)
    assert op["lado"] == "compra" and op["hora_entrada"] == "09:46"
    assert op["motivo"] == "objetivo" and op["R"] == pytest.approx(3.0)
    assert op["R_alt"] == pytest.approx(4.0)   # con 4R también llegaba (107 > 102*1.04)
    assert E.hueco_volumen(m, {"hueco": 0.06, "rvol5": 0.01}, CFG["estrategias"]["hueco_volumen"], RIESGO, CERO) is None


def test_rebote_compra_al_recuperar_vwap():
    baja = [100 - i * 0.2 for i in range(20)]              # cae por debajo del VWAP
    sube = [96 + i * 0.5 for i in range(20)]               # y lo recupera
    m = velas(baja + sube + [106] * 5)
    op = E.rebote(m, {"hueco": -0.12}, CFG["estrategias"]["rebote"], RIESGO, CERO)
    assert op and op["lado"] == "compra"
    assert E.rebote(m, {"hueco": -0.02}, CFG["estrategias"]["rebote"], RIESGO, CERO) is None


def test_vwap_solo_a_favor_de_tendencia():
    sube = [100 + i * 0.1 for i in range(30)]              # 9:30-10:00 al alza
    vuelta = [(102.8, 102.9, 101.0, 102.5)] + [103 + i * 0.2 for i in range(20)]
    m = velas(sube + vuelta)
    op = E.vwap(m, {"en_juego": True, "puesto": 1}, CFG["estrategias"]["vwap"], RIESGO, CERO)
    assert op and op["lado"] == "compra" and op["hora_entrada"] == "10:01"
    assert E.vwap(m, {"en_juego": False, "puesto": 999}, CFG["estrategias"]["vwap"], RIESGO, CERO) is None


def test_azar_reproducible():
    m = velas([100 + (i % 7) * 0.1 for i in range(200)])
    ctx = {"azar_elegida": True, "fecha": "2025-03-03", "simbolo": "ABC"}
    a = E.azar(m, ctx, CFG["estrategias"]["azar"], RIESGO, CERO)
    b = E.azar(m, ctx, CFG["estrategias"]["azar"], RIESGO, CERO)
    assert a == b and a is not None


def test_universo_sin_mirar_el_futuro():
    dia = pd.DataFrame([
        dict(simbolo="SUBE", A=True, B=False, hueco=0.01),   # sube +15 % en el día pero no abrió con hueco: fuera
        dict(simbolo="HUECO", A=True, B=False, hueco=0.30),
        dict(simbolo="ORB", A=False, B=True, hueco=-0.05),
    ])
    assert sorted(motor.universo_dia(dia)["simbolo"]) == ["HUECO", "ORB"]


def test_operaciones_dia_e_informe(tmp_path):
    m1 = velas([(150, 151, 149, 150)] * 5 + [150] + [140] * 400)           # hueco enorme que se desinfla
    m2 = velas([(50, 50.5, 49.9, 50.4)] * 5 + [50.6, 51, 51.5, 52] + [52] * 400)
    dia = pd.DataFrame([
        dict(simbolo="GAP", A=True, B=False, hueco=0.6, cierre_ant=94, atr14=5, vol_medio14=1e5),
        dict(simbolo="ORB", A=False, B=True, hueco=0.05, cierre_ant=47.6, atr14=2, vol_medio14=1e5),
    ])
    ops = motor.operaciones_dia("2025-03-03", dia, {"GAP": m1, "ORB": m2}, CFG)
    est = {o["estrategia"] for o in ops}
    assert "corto_hueco" in est and "orb" in est
    df = pd.DataFrame(ops)
    res = informe.generar(df, df.iloc[0:0], CFG, "2025-03-04")
    assert res["estrategias"]["corto_hueco"]["pasado"]["n"] == 1
    assert res["estrategias"]["corto_hueco"]["pasado_como_bot"]["n"] == 1
    md = informe.guardar(res, tmp_path)
    assert "Laboratorio intradía" in md.read_text(encoding="utf-8")


def test_semaforo():
    L = CFG["listones"]
    assert informe.semaforo({"n": 150, "R_medio": 0.3, "ic95": [0.1, 0.5]}, L) == "verde"
    assert informe.semaforo({"n": 50, "R_medio": 0.3, "ic95": [-0.1, 0.7]}, L) == "amarillo"
    assert informe.semaforo({"n": 150, "R_medio": -0.1, "ic95": [-0.2, 0.0]}, L) == "rojo"


def test_filtro_a_favor_y_en_contra():
    from tradinglab.intradia.laboratorio import filtro
    sube = velas([100 + i * 0.1 for i in range(40)])
    a = filtro.evaluar(sube, "10:10", "compra", {"hueco": 0.05, "rvol5": 0.2}, sube)
    b = filtro.evaluar(sube, "10:10", "venta", {"hueco": 0.05, "rvol5": 0.2}, sube)
    assert a["nota"] > 60 and b["nota"] < 40
    # temprano (9:31) casi todo es neutro: no hay datos todavía
    assert 30 <= filtro.evaluar(sube, "09:31", "compra", {}, None)["nota"] <= 70


def test_informe_con_filtro(tmp_path):
    filas = [dict(fecha="2025-03-03", estrategia="orb", simbolo="A", lado="compra", hora_entrada="10:00", R=r, R_alt=r,
                  ret_pct=r, hueco=0.05, puesto=1, nota=n, filtro="11110000") for r, n in [(2, 80), (-1, 30), (3, 70), (-1, 40)]]
    df = pd.DataFrame(filas)
    res = informe.generar(df, df.iloc[0:0], CFG, "2025-03-04")
    assert res["estrategias"]["orb"]["pasado_filtrado"]["n"] == 2
    assert res["estrategias"]["orb"]["por_punto"]["1min"]["n_favor"] == 4
    assert "Filtro" in informe.markdown(res)


class BrokerFalso:
    def __init__(self):
        self.enviadas, self.movidos = [], []

    def reloj(self):
        return {"is_open": True}

    def ordenes(self, estado="all", desde=None):
        return []

    def posiciones(self):
        return []

    def cuenta(self):
        return {"equity": "100000", "last_equity": "100000"}

    def valor(self, s):
        return {"shortable": True, "easy_to_borrow": True}

    def orden_con_stop(self, *a):
        self.enviadas.append(a)
        return {}


def test_demo_envia_orden_con_stop(tmp_path, monkeypatch):
    from tradinglab.intradia.laboratorio import demo
    monkeypatch.setattr(demo, "carpeta", lambda: tmp_path / "reg")
    cfg = {**CFG, "filtro": {**CFG["filtro"], "aplicar_a": []}}
    # Hueco de +60 % que se desinfla: el corto del hueco da señal a las 9:35
    m = velas([(150, 151, 149, 150)] * 5 + [150] * 3)
    cands = pd.DataFrame([dict(fecha="2025-03-03", simbolo="GAP", A=True, B=False, hueco=0.6, cierre_ant=94, atr14=5,
                               vol_medio14=1e5, v=1e6)])
    (tmp_path / "cache").mkdir()
    cands.to_csv(tmp_path / "cache" / "candidatas-2025-03-03.csv.gz", index=False)
    monkeypatch.setattr(demo, "velas_hasta_ahora", lambda c, s, f, a: m.reset_index(drop=True).assign(simbolo="GAP"))
    b = BrokerFalso()
    ahora = datetime(2025, 3, 3, 9, 40, tzinfo=NY)
    filas = demo.pasada(cfg, {}, None, b, ahora=ahora, cache=tmp_path / "cache")
    assert len(b.enviadas) == 1
    sim, qty, lado, stop, obj, cid = b.enviadas[0]
    assert sim == "GAP" and lado == "venta" and stop > 150 and cid.startswith("lab-20250303-corto_hueco")
    assert qty * 150 * 0.15 <= 100000 * 0.005 + 1          # riesgo 0,5 %
    assert (tmp_path / "reg" / "registro.csv").exists() and filas[0]["accion"] == "abierta"
    # fuera de la ventana no hace nada
    assert demo.pasada(cfg, {}, None, b, ahora=datetime(2025, 3, 3, 14, 0, tzinfo=NY), cache=tmp_path / "cache") == []


def test_demo_tamano_y_niveles():
    from tradinglab.intradia.laboratorio import demo
    R = CFG["demo"]["riesgo"]
    assert demo.tamano(100000, 50, 1, R)[0] == 200            # 10 % máx. de la cuenta (sin eso serían 1000)
    assert demo.niveles(100, "venta", 1, 3) == (101.0, 97.0)


def test_directo_elegir_y_estado():
    from tradinglab.intradia.laboratorio import directo
    cands = pd.DataFrame([dict(fecha="2026-11-16", simbolo=f"S{i}", A=True, B=False, hueco=0.1 + i / 100) for i in range(40)])
    sims = directo.elegir(cands)
    assert len(sims) == 30 and sims[-1] == "QQQ" and sims[0] == "S39"
    e = directo.Estado()
    base = pd.DataFrame([dict(simbolo="X", t=pd.Timestamp("2026-11-16T14:30:00Z"), o=1, h=1, l=1, c=1, v=10)])
    e.poner_base(base)
    e.mensaje([{"T": "b", "S": "X", "t": "2026-11-16T14:31:00Z", "o": 1, "h": 2, "l": 1, "c": 2, "v": 5},
               {"T": "b", "S": "X", "t": "2026-11-16T14:30:00Z", "o": 9, "h": 9, "l": 9, "c": 9, "v": 9},   # ya está en la base: se ignora
               {"T": "t", "S": "X", "p": 2.5}], 1.0)
    m = e.por_sim()["X"]
    assert len(m) == 2 and float(m["c"].iloc[-1]) == 2 and e.ultimo["X"] == 2.5 and e.sucio


def test_directo_vela_de_entrada_sintetica():
    from tradinglab.intradia.laboratorio import directo
    e = directo.Estado()
    e.poner_base(pd.DataFrame([dict(simbolo="X", t=pd.Timestamp("2026-11-16T15:16:00Z"), o=1, h=1, l=1, c=1, v=10)]))
    e.mensaje([{"T": "b", "S": "X", "t": "2026-11-16T15:17:00Z", "o": 1, "h": 2, "l": 1, "c": 2, "v": 5},
               {"T": "t", "S": "X", "p": 2.2}], 1.0)
    # 15:18:01 UTC: la vela de las 15:17 acaba de cerrar -> se añade la de entrada (15:18) al precio último
    m = e.por_sim(datetime(2026, 11, 16, 10, 18, 1, tzinfo=NY))["X"]
    assert len(m) == 3 and float(m["c"].iloc[-1]) == 2.2 and m["hora"].iloc[-1].strftime("%H:%M") == "10:18"
    # si la última vela es vieja (sin operaciones ese minuto) no se inventa nada
    assert len(e.por_sim(datetime(2026, 11, 16, 10, 25, 1, tzinfo=NY))["X"]) == 2
