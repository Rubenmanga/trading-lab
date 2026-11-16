from datetime import date, timedelta

from tradinglab.medio_plazo import marcador as m

HOY = date(2026, 12, 31)


def _velas(precios, d0=date(2026, 11, 13)):
    out = []
    for k, p in enumerate(precios):
        d = (d0 + timedelta(days=k)).isoformat()
        out.append(dict(fecha=d, apertura=p, maximo=p * 1.01, minimo=p * 0.99, cierre=p))
    return out


def _pred(**kw):
    base = dict(id="X-2026-11-14", fecha="2026-11-14", ticker="X", veredicto="comprar_en_zona", conviccion="3",
                precio="10", zona_entrada_max="9", objetivo="20", stop_tesis="5", fecha_revision="2027-11-14")
    return {**base, **kw}


IDX = _velas([100] * 2 + [100 + k for k in range(1, 40)])  # el índice sube


def test_compra_que_bate_al_indice_es_acierto():
    r = m.puntuar(_pred(), _velas([10, 10] + [10 * (1 + 0.02 * k) for k in range(1, 40)]), IDX, HOY)
    assert r["resultado"] == "acierto" and r["exceso_pct"] > 0 and r["estado"] == "abierta"


def test_vigilar_que_baja_es_acierto_y_stop_cierra():
    v = _velas([10, 10, 9, 8, 4, 4, 4, 4])
    r = m.puntuar(_pred(veredicto="vigilar"), v, IDX, HOY)
    assert r["motivo"] == "stop" and r["resultado"] == "acierto" and r["estado"] == "cerrada" and r["toco_zona"]
    r2 = m.puntuar(_pred(), v, IDX, HOY)
    assert r2["resultado"] == "fallo"


def test_objetivo_y_pronto():
    r = m.puntuar(_pred(), _velas([10, 10, 21, 21]), IDX, HOY)
    assert r["motivo"] == "objetivo" and r["resultado"] == "acierto" and r["precio_final"] >= 20
    r = m.puntuar(_pred(), _velas([10, 10, 10.5]), IDX, HOY)
    assert r["resultado"] == "pronto"


def test_libro_solo_anade(tmp_path):
    libro = tmp_path / "p.csv"
    w = [dict(ticker="A", fecha_analisis="2026-11-14", veredicto="vigilar", precio_analisis="5")]
    assert m.sincronizar(w, libro) == 1
    w[0]["veredicto"] = "comprar"  # un cambio posterior en watchlist NO reescribe la predicción
    assert m.sincronizar(w + [dict(ticker="A", fecha_analisis="2026-12-01")], libro) == 1
    filas = m.leer(libro)
    assert [f["id"] for f in filas] == ["A-2026-11-14", "A-2026-12-01"] and filas[0]["veredicto"] == "vigilar"


def test_resumen_honesto_con_poca_muestra(tmp_path):
    libro = tmp_path / "p.csv"
    libro.write_text(",".join(m.COLUMNAS) + "\n" + "X-2026-11-14,2026-11-14,X,,comprar,2,,10,,,,2027-11-14,\n", encoding="utf-8")
    import tradinglab.medio_plazo.watchlist as wl
    viejo = wl.leer
    wl.leer = lambda *a, **k: []
    try:
        r = m.ejecutar(HOY, lambda t: IDX if t == "IWM" else _velas([10, 10] + [11] * 30), libro, tmp_path / "out")
    finally:
        wl.leer = viejo
    assert r["puntuadas"] == 1 and "muy poco" in r["muestra"]
    assert (tmp_path / "out" / "marcador.json").exists() and "Resumen (5 líneas)" in (tmp_path / "out" / "marcador.md").read_text(encoding="utf-8")
