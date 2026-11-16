from datetime import date, timedelta

from tradinglab.medio_plazo import expediente as ex

HOY = date(2026, 11, 16)


def _sub():
    return {"cik": "1234", "filings": {"recent": {
        "form": ["8-K", "4", "4", "10-Q", "424B5", "8-K", "10-K"],
        "filingDate": ["2026-11-06", "2026-11-03", "2026-11-03", "2026-11-06", "2026-09-01", "2026-08-01", "2025-01-01"],
        "accessionNumber": ["0001-26-1", "0001-26-2", "0001-26-3", "0001-26-4", "0001-26-5", "0001-26-6", "0001-25-7"],
        "primaryDocument": ["a.htm", "b.xml", "c.xml", "d.htm", "e.htm", "f.htm", "g.htm"],
        "items": ["2.02,9.01", "", "", "", "", "7.01", ""],
    }}}


def _velas(n=60, salto_en=None):
    d0, out, p = HOY - timedelta(days=n), [], 10.0
    for k in range(n):
        p = p * (1.3 if k == salto_en else 1.0 + (0.005 if k % 2 else -0.005))
        out.append(dict(fecha=(d0 + timedelta(days=k)).isoformat(), cierre=p, volumen=1000.0 * (5 if k == salto_en else 1)))
    return out


def test_eventos_sec_tipos_fuente_y_form4_agrupado():
    ev = ex.eventos_sec(_sub(), HOY)
    tipos = {e["tipo"] for e in ev}
    assert {"resultados", "cuentas", "ampliacion", "8k", "directivos_form4"} <= tipos
    assert all(e["fuente_url"].startswith("https://www.sec.gov/") and e["fecha_fuente"] for e in ev)
    f4 = [e for e in ev if e["tipo"] == "directivos_form4"]
    assert len(f4) == 1 and f4[0]["resumen"].startswith("2 avisos")
    assert not any(e["fecha"] == "2025-01-01" for e in ev)  # más de 12 meses: fuera


def test_reacciones_y_eventos_recientes_sin_20d():
    v = _velas()
    r = ex.reacciones(v[30]["fecha"], v)
    assert r["precio_antes"] == round(v[29]["cierre"], 4)
    assert r["reaccion_1d"] == round((v[30]["cierre"] / v[29]["cierre"] - 1) * 100, 2)
    assert r["reaccion_20d"] is not None
    assert ex.reacciones(v[-3]["fecha"], v)["reaccion_20d"] is None


def test_movimiento_anomalo():
    m = ex.movimientos(_velas(salto_en=40), "ABC", HOY)
    assert len(m) == 1 and m[0]["tipo"] == "movimiento" and "Sube 30.0 %" in m[0]["resumen"]
    assert "yahoo" in m[0]["fuente_url"]


def test_solo_anade_nunca_borra(tmp_path):
    v = _velas()
    viejo = dict(fecha="2026-10-01", tipo="contrato", resumen="escrito a mano", fuente_url="https://x", fecha_fuente="2026-10-01")
    ex.escribir(tmp_path / "ABC" / "eventos.csv", [viejo])
    res = ex.ejecutar(tickers=["ABC"], carpeta=tmp_path, fuente_sec=lambda ts: {"ABC": _sub()},
                      fuente_velas=lambda t: v, hoy=HOY)
    filas = ex.leer(tmp_path / "ABC" / "eventos.csv")
    assert any(f["resumen"] == "escrito a mano" for f in filas)
    assert res["ABC"]["añadidas"] == len(filas) - 1
    # segunda pasada: no duplica
    res2 = ex.ejecutar(tickers=["ABC"], carpeta=tmp_path, fuente_sec=lambda ts: {"ABC": _sub()},
                       fuente_velas=lambda t: v, hoy=HOY)
    assert res2["ABC"]["añadidas"] == 0 and len(ex.leer(tmp_path / "ABC" / "eventos.csv")) == len(filas)
    assert (tmp_path / "ABC" / "tesis.md").exists()
    assert all(f["fuente_url"] for f in filas)


def test_seguidas_sin_materias_primas():
    cfg = {"lista_noticias": {"empresas": {"ALT": {}}, "materias_primas": {"XAU": {}}}}
    s = ex.seguidas(cfg)
    assert "XAU" not in s and s.get("ALT") == "cartera"
