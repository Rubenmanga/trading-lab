import csv
import json
from datetime import date

from tradinglab.intradia.corto_hueco import marcador
from tradinglab.intradia.corto_hueco.sesion import CAMPOS

DEC = {"fecha": "2027-02-15", "ops_min": 40, "R_min": 0.1}


def _fila(dia, sim, accion, **x):
    return {"fecha_hora_ny": f"{dia} 09:35:00", "simbolo": sim, "accion": accion, "motivo": "", **x}


def test_empareja_cierres_y_stops():
    filas = [_fila("2026-11-17", "AAA", "abierta", precio="10", hueco="0.6"),
             _fila("2026-11-17", "BBB", "abierta", precio="5"),
             _fila("2026-11-17", "AAA", "cerrada", resultado_pct="3"),
             _fila("2026-11-17", "BBB", "ya cerrada"),
             _fila("2026-11-18", "CCC", "abierta")]
    ops = marcador.operaciones_bot(filas, 15)
    assert [o["R"] for o in ops] == [0.2, -1.0, None]
    assert ops[1]["estado"] == "stop (supuesto)"


def test_veredicto():
    assert marcador.veredicto(3, 0.5, date(2026, 12, 1), DEC)["estado"] == "pronto"
    assert marcador.veredicto(25, 0.3, date(2026, 12, 1), DEC)["estado"] == "faltan operaciones"
    assert marcador.veredicto(45, 0.05, date(2027, 1, 1), DEC)["estado"] == "por debajo"
    assert marcador.veredicto(45, 0.2, date(2027, 1, 1), DEC)["estado"] == "en camino"
    assert marcador.veredicto(30, 0.5, date(2027, 2, 15), DEC)["estado"] == "apagar"
    assert marcador.veredicto(40, 0.1, date(2027, 2, 16), DEC)["estado"] == "seguir"


def test_calcular_y_guardar(tmp_path):
    (tmp_path / "corto-hueco").mkdir()
    with open(tmp_path / "corto-hueco" / "registro.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        w.writerow(_fila("2026-11-17", "AAA", "abierta"))
        w.writerow(_fila("2026-11-17", "AAA", "cerrada", resultado_pct="-6"))
    (tmp_path / "laboratorio" / "demo").mkdir(parents=True)
    (tmp_path / "laboratorio" / "resumen.json").write_text(json.dumps({
        "periodo_pasado": ["2026-01-05", "2026-01-16"],
        "estrategias": {"corto_hueco": {"nombre": "Corto", "pasado": {"R_medio": 0.1}, "pasado_como_bot": {"n": 10, "R_medio": 0.24}}}}))
    (tmp_path / "laboratorio" / "demo" / "registro.csv").write_text("estrategia,accion,R\ncorto_hueco,cerrada,0.5\norb,descartada,\n")
    m = marcador.calcular({"stop_pct": 15, "decision": DEC}, hoy=date(2026, 11, 20), base=tmp_path)
    assert m["bot"]["n"] == 1 and m["bot"]["R_medio"] == -0.4
    assert m["backtest"]["ops_por_dia_bolsa"] == 1.0  # 10 ops en 10 días de bolsa
    assert m["alpaca"] == {"corto_hueco": {**m["alpaca"]["corto_hueco"], "n": 1, "backtest_R": 0.1}}
    assert m["decision"]["estado"] == "pronto"
    assert json.loads(marcador.guardar(m, tmp_path).read_text())["bot"]["n"] == 1
