import yaml

from tradinglab.common.config import ruta
from tradinglab.common.db import DB
from tradinglab.intradia import backtest, datos_sinteticos
from tradinglab.intradia.brokers.simulado import BrokerSimulado
from tradinglab.intradia.estrategias import Ninguna
from tradinglab.intradia.modelos import ResultadoCapa, Senal
from tradinglab.intradia.motor import Motor


def cfg():
    return yaml.safe_load(open(ruta("config", "intradia.yaml"), encoding="utf-8"))


class IAQueFrena:
    def revisar(self, s, ctx):
        return ResultadoCapa("ia", False, "noticia mala", {"veredicto": "frena"})


def motor(modo):
    c = cfg()
    c["ia"]["modo"] = modo
    db = DB(":memory:")
    return Motor(c, Ninguna(), BrokerSimulado(10_000), db, IAQueFrena(), "test"), db


def test_modo_sombra_ejecuta_pero_anota_ia():
    m, db = motor("sombra")
    assert m.procesar_senal(Senal("SPY", "compra", 500.0, "t"), {"en_ventana_entradas": True})
    d = db.filas("SELECT * FROM decisiones")[0]
    assert d["resultado"] == "PASADA" and "la IA habría frenado" in d["motivo"]


def test_modo_veto_frena():
    m, db = motor("veto")
    assert m.procesar_senal(Senal("SPY", "compra", 500.0, "t"), {"en_ventana_entradas": True}) is None
    assert db.filas("SELECT * FROM decisiones")[0]["capa"] == "ia"


def test_fuera_de_horario_frena():
    m, db = motor("sombra")
    m.procesar_senal(Senal("SPY", "compra", 500.0, "t"), {"en_ventana_entradas": False})
    assert db.filas("SELECT capa FROM decisiones")[0]["capa"] == "reglas"


def test_backtest_cierra_todo_cada_dia():
    db = DB(":memory:")
    r = backtest.ejecutar(cfg(), datos_sinteticos.generar(["AAA", "BBB"], dias=10), db)
    assert r["operaciones"] > 0
    abiertas = db.filas("SELECT * FROM operaciones WHERE pnl IS NULL")
    assert abiertas == []
    for o in db.filas("SELECT * FROM operaciones"):  # ninguna operación pasa de un día a otro
        assert o["ts_apertura"][:10] == o["ts_cierre"][:10]
