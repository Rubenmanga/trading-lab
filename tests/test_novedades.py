from tradinglab.medio_plazo import novedades as nv

U = dict(umbral_movimiento_pct=8, umbral_sigmas=2.5, umbral_minimo_pct=3, umbral_volumen=2.5, mercado="SPY")


def _velas(cierres, vol=1e6, ultimo_vol=None):
    v = [dict(fecha=f"2026-10-{1 + i:02d}" if i < 28 else f"2026-11-{i - 27:02d}", cierre=c, volumen=vol) for i, c in enumerate(cierres)]
    if ultimo_vol:
        v[-1]["volumen"] = ultimo_vol
    return v


def test_clasificar():
    assert "resultados" in nv.clasificar("Altimmune reports third quarter 2026 financial results")["causas"]
    assert nv.clasificar("Company prices public offering of shares")["importante"]
    assert nv.clasificar("Rosen Law Firm reminds investors of lawsuit")["ruido"]


def test_movimiento_grande_y_normal():
    base = [10 + (0.1 if i % 2 else -0.1) for i in range(30)]
    m = nv.movimiento(_velas(base + [12.0], ultimo_vol=5e6))
    assert nv.es_grande(m, U) and m["volumen_rel"] == 5.0
    assert not nv.es_grande(nv.movimiento(_velas(base + [10.05])), U)


def test_sin_noticia_no_inventa():
    base = [10 + (0.1 if i % 2 else -0.1) for i in range(30)]
    m = nv.movimiento(_velas(base + [11.0]))
    txt = nv.explicar(m, [], None, None, U)
    assert "No se inventa" in txt


def test_con_noticia_y_primer_dia():
    base = [10 + (0.1 if i % 2 else -0.1) for i in range(30)]
    v = _velas(base + [11.5])
    fecha = v[-1]["fecha"]
    d = dict(velas=v, finnhub={"noticias": [dict(fecha=fecha, titulo="Red Cat wins Army contract order", fuente="x", url="")]},
             alpaca=[], sec=None, ensayos=None)
    e = nv.analizar("RCAT", dict(nombre="Red Cat"), d, {}, U, None, None)
    assert "Causa probable" in e["porque"] and "contrato" in e["porque"]
    assert e["cambios"]
    # segundo día con los mismos titulares: ya no son nuevos
    e2 = nv.analizar("RCAT", dict(nombre="Red Cat"), d, {"vistos": e["vistos"]}, U, None, None)
    assert not any(n["nueva"] for n in e2["titulares"])


def test_ejecutar_con_fuentes_falsas(tmp_path, monkeypatch):
    monkeypatch.setattr(nv, "ruta", lambda *p: tmp_path.joinpath(*p))
    base = [10.0] * 30
    cfg = dict(lista_noticias=dict(empresas=dict(ALT=dict(nombre="Altimmune", sector="salud", referencia="XBI")),
                                   materias_primas=dict(XAU=dict(nombre="Oro", yahoo="GC=F"))))
    fu = dict(velas=lambda t, p="3mo": _velas(base), finnhub=lambda t, h: {}, alpaca=lambda t: [],
              sec=lambda ts: {}, ensayos=lambda e: {})
    res = nv.ejecutar(cfg, fuentes=fu)
    assert "ALT" in res["empresas"] and "XAU" in res["materias_primas"]
    assert (tmp_path / "investigacion/seguimiento/lista.md").exists()
    assert "Sin cambios" in res["empresas"]["ALT"]["resumen"]
