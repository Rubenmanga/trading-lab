from tradinglab.radar import resultados as rr


def _velas(n=400, precio=10.0, salto=None):
    """Velas diarias con fechas ficticias y un salto en el día `salto` (índice)."""
    out = []
    for i in range(n):
        c = precio * (1 + 0.001 * (i % 3))
        if salto and i >= salto[0]:
            c *= 1 + salto[1]
        y, d = 2019 + i // 360, i % 360
        out.append(dict(fecha=f"{y}-{1 + d // 30:02d}-{1 + d % 30:02d}", apertura=c, cierre=c, volumen=1e6))
    return out


def test_momento():
    assert rr.momento(8) == "antes" and rr.momento(16) == "despues" and rr.momento(12) is None and rr.momento(None) is None


def test_evento_despues_del_cierre_reacciona_el_dia_siguiente():
    v = _velas(salto=(301, 0.20))
    f = v[300]["fecha"]                 # resultados tras el cierre del día 300 -> reacciona el 301
    ev = rr.construir_evento(v, f, 17, 12.0, [])
    assert ev and ev["reaccion"] > 15 and ev["supero"] and not ev["trampa"]


def test_trampa_supera_y_cae():
    v = _velas(salto=(301, -0.10))
    ev = rr.construir_evento(v, v[300]["fecha"], 17, 5.0, [])
    assert ev["trampa"] and ev["reaccion"] < -5


def test_sin_horas_o_pocas_velas_no_hay_evento():
    v = _velas()
    assert rr.construir_evento(v, v[300]["fecha"], 12, 5.0, []) is None
    assert rr.construir_evento(v[:50], v[40]["fecha"], 17, 5.0, []) is None
    assert rr.construir_evento(v, v[300]["fecha"], 17, None, []) is None


def test_previos_y_analisis():
    v = _velas()
    evs = []
    for k in (260, 280, 300, 320, 340):
        e = rr.construir_evento(v, v[k]["fecha"], 17, 3.0, evs)
        assert e
        evs.append(e)
    assert evs[-1]["previas_superadas"] == 4 and evs[0]["previas_superadas"] is None
    res = rr.analizar(evs * 100)
    base = res["reglas"]["TODAS (referencia)"]
    assert base["reaccion"]["n"] == 500
    assert rr.veredicto(base, base) in ("no se nota", "pocos casos")
    assert "Radar de resultados" in rr.informe(res)


def test_informe_incluye_cortes_nuevos():
    v = _velas()
    evs = []
    for k in (260, 280, 300, 320, 340):
        evs.append(rr.construir_evento(v, v[k]["fecha"], 17, 3.0, evs))
    res = rr.analizar(evs * 100)
    assert "Todas las presentaciones (referencia)" in res["deriva_base"] and "Superó por poco (0 a 5 %)" in res["por_sorpresa"]
    assert "Según cuánto superó" in rr.informe(res)
