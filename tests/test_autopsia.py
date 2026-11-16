import json
from datetime import date, timedelta

from tradinglab.medio_plazo import autopsia as au

CAB = ",".join(au.COLUMNAS)


def _velas(n=30, desde="2026-10-01", precio=10.0, salto_en=None, salto=0.0):
    d0 = date.fromisoformat(desde)
    out, p = [], precio
    for i in range(n):
        f = (d0 + timedelta(days=i)).isoformat()
        if f == salto_en:
            p = p * (1 + salto)
        out.append({"fecha": f, "cierre": p})
    return out


def test_base_tras_cierre_es_el_mismo_dia():
    v = _velas(40, salto_en="2026-10-26", salto=-0.2)  # resultados el 25 tras el cierre: cae al día siguiente
    m = au.medir({"fecha": "2026-10-25", "hora": "tras_cierre"}, v)
    assert m["precio_antes"] == 10.0 and m["r1"] == -20.0 and m["previa_20d"] == 0.0
    m2 = au.medir({"fecha": "2026-10-26", "hora": "antes_apertura"}, v)
    assert m2["precio_antes"] == 10.0 and m2["r1"] == -20.0


def test_desenlace_y_prediccion_con_stop_roto(tmp_path):
    (tmp_path / "autopsias").mkdir()
    (tmp_path / "autopsias" / "autopsias.csv").write_text(
        CAB + "\nZZZ,2026-10-25,tras_cierre,T3 2026,40,12,-0.20,-0.26,retira,texto,-18.5,https://sec.gov/x,web,Lección: x\n",
        encoding="utf-8")
    (tmp_path / "predicciones.csv").write_text(
        "id,fecha,ticker,veredicto,precio,stop_tesis,objetivo,zona_entrada_max\n"
        "ZZZ-1,2026-10-01,ZZZ,vigilar,10,9,15,\nZZZ-2,2026-11-30,ZZZ,comprar,5,4,8,\n", encoding="utf-8")
    exp = tmp_path / "expedientes" / "ZZZ"
    exp.mkdir(parents=True)
    (exp / "eventos.csv").write_text("fecha,tipo,resumen,fuente_url\n2026-10-25,resultados,R,u\n2026-10-20,resultados,R2,u2\n", encoding="utf-8")
    v = _velas(40, salto_en="2026-10-26", salto=-0.2)
    auts = au.ejecutar(fuente_velas=lambda t: v, base=tmp_path, hoy=date(2026, 11, 1))
    a = auts[0]
    assert a["resultado"] == "falla" and a["frase"] == "falla y cae" and a["reaccion_medida"] == "1 sesión"
    assert a["prediccion"]["id"] == "ZZZ-1" and a["prediccion"]["stop_roto"] is True
    j = json.loads((tmp_path / "autopsias" / "autopsias.json").read_text(encoding="utf-8"))
    assert [p["fecha"] for p in j["pendientes"]] == ["2026-10-20"]
    md = (exp / "autopsias.md").read_text(encoding="utf-8")
    assert "ROTO" in md and "la retira" in md
    assert "Pendientes" in (tmp_path / "autopsias" / "resumen.md").read_text(encoding="utf-8")


def test_sin_precios_usa_horario_extendido():
    fila = dict(zip(au.COLUMNAS, ["ZZZ", "2026-11-16", "tras_cierre", "T3", "1.6", "1.0", "-0.07", "-0.04",
                                  "retrasa", "", "-10", "u", "w", "l"]))
    a = au.autopsia(fila, [], [])
    assert a["resultado"] == "mixto" and a["reaccion"] == -10.0 and a["reaccion_medida"] == "horario extendido"
