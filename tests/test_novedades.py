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


class _Bloque:
    type = "text"
    text = '{"empresas": [{"ticker": "ALT", "resumen": "Nada nuevo.", "causa_probable": "no hay noticia", "confianza": "ninguna", "importante": false, "motivo_importante": ""}]}'


class _Resp:
    stop_reason = "end_turn"
    content = [_Bloque()]

    class usage:
        input_tokens = 10000
        output_tokens = 1000


class _Cliente:
    llamadas = 0

    class messages:
        @staticmethod
        def create(**kw):
            _Cliente.llamadas += 1
            assert kw["model"] == "claude-haiku-5-5"
            return _Resp()


def test_lector_ia_reutiliza_y_tope():
    from tradinglab.medio_plazo import lector_ia
    emp = {"ALT": dict(nombre="Altimmune", titulares=[], cambios=[])}
    r = lector_ia.leer(emp, None, {}, cliente=_Cliente)
    assert r["por_ticker"]["ALT"]["confianza"] == "ninguna" and r["coste_ultima_usd"] == 0.0015
    r2 = lector_ia.leer(emp, r, {}, cliente=_Cliente)
    assert r2.get("reutilizada") and _Cliente.llamadas == 1
    emp["ALT"]["cambios"] = ["algo nuevo"]
    mes = list(r["gasto_mes"])[0]
    r3 = lector_ia.leer(emp, {**r, "gasto_mes": {mes: 5}}, {"tope_mensual_usd": 3}, cliente=_Cliente)
    assert "Tope" in r3["aviso"] and _Cliente.llamadas == 1


def test_universo_suma_vigilancia_e_ideas(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(nv, "ruta", lambda *p: tmp_path.joinpath(*p))
    (tmp_path / "investigacion").mkdir()
    (tmp_path / "investigacion/watchlist.csv").write_text("ticker,empresa,sector\nAMSC,American Superconductor,Industrials\nALT,Altimmune,Healthcare\n")
    (tmp_path / "investigacion/ranking.json").write_text(json.dumps({"filas": [{"ticker": "REPX", "empresa": "Riley", "sector": "Energy"}]}))
    u = nv.universo(dict(empresas={"ALT": {"nombre": "Altimmune"}}, incluir_ranking_top=5))
    assert u["ALT"]["grupo"] == "cartera" and u["AMSC"]["grupo"] == "vigilancia" and u["REPX"]["referencia"] == "XLE"
