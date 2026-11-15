"""Pruebas sin internet de las fuentes públicas, el sentimiento y la validación del ranking."""
from datetime import date

from tradinglab.medio_plazo import fuentes_publicas as fp
from tradinglab.medio_plazo import oportunidades as op
from tradinglab.medio_plazo import sentimiento, validacion

HOY = date(2026, 11, 15)


def test_resumen_sec_cuenta_formularios():
    sub = {"cik": "1796280", "filings": {"recent": {
        "form": ["424B5", "S-3", "SCHEDULE 13G", "SC 13D", "4", "4", "8-K", "NT 10-Q", "SC 13G/A", "S-3"],
        "filingDate": ["2026-10-20", "2026-09-01", "2026-08-01", "2026-07-01", "2026-11-01", "2026-06-01",
                       "2026-11-10", "2026-03-01", "2026-10-01", "2025-01-01"],
        "accessionNumber": ["0001-26-000001"] * 10, "primaryDocument": ["d.htm"] * 10}}}
    r = fp.resumen_sec(sub, HOY)
    assert r["sec_colocacion_90d"] == 1 and r["sec_registro_180d"] == 1   # el S-3 de 2025 es antiguo
    assert r["sec_13g_180d"] == 1 and r["sec_13d_180d"] == 1               # la enmienda 13G/A no cuenta
    assert r["sec_grandes_inversores_180d"] == 2
    assert r["sec_form4_90d"] == 1 and r["sec_8k_30d"] == 1 and r["sec_retraso_365d"] == 1
    assert r["sec_documentos"][0]["url"].startswith("https://www.sec.gov/Archives/edgar/data/1796280/000126000001/")


def test_resumen_sec_vacio():
    assert fp.resumen_sec({}, HOY)["sec_registro_180d"] == 0


def _estudio(nct, sponsor, fases, fecha, estado="RECRUITING"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": "Estudio " + nct},
        "statusModule": {"overallStatus": estado, "primaryCompletionDateStruct": {"date": fecha}},
        "designModule": {"phases": fases},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": sponsor}}}}


def test_resumen_ensayos_filtra_fase_fecha_y_patrocinador():
    est = [_estudio("A", "ORIC Pharmaceuticals", ["PHASE3"], "2027-03"),          # cuenta
           _estudio("B", "ORIC Pharmaceuticals, Inc.", ["PHASE1"], "2027-01-10"),  # fase 1: no
           _estudio("C", "ORIC Pharmaceuticals", ["PHASE2"], "2029-01-01"),        # muy lejos: no
           _estudio("D", "Oricorp Hospital", ["PHASE3"], "2027-01-01"),            # otro patrocinador
           _estudio("E", "ORIC Pharmaceuticals", ["PHASE1", "PHASE2"], "2026-12-01")]
    r = fp.resumen_ensayos(est, "ORIC Pharmaceuticals, Inc.", HOY)
    assert r["ensayos_clave_12m"] == 2 and [e["nct"] for e in r["ensayos"]] == ["E", "A"]
    assert r["ensayos_activos"] == 4


def test_nombre_simple():
    assert fp.nombre_simple("Oric Pharmaceuticals, Inc.") == "oric pharmaceuticals"
    assert fp.nombre_simple("Delcath Systems Corp.") == "delcath systems"


def test_fred_y_semaforo():
    txt = "observation_date,BAMLH0A0HYM2\n2026-08-01,3.0\n2026-09-01,.\n2026-11-13,4.2\n"
    s = fp.leer_csv_fred(txt)
    assert s[-1] == (date(2026, 11, 13), 4.2) and len(s) == 2
    m = fp.semaforo_macro({"BAMLH0A0HYM2": s, "T10Y2Y": [(date(2026, 11, 13), 0.5)],
                           "NFCI": [(date(2026, 11, 7), -0.4)]}, dict(precio=97, ma200=100))
    hy = next(i for i in m["indicadores"] if i["clave"] == "BAMLH0A0HYM2")
    assert hy["estado"] == "rojo"            # ámbar por nivel, y sube >0,75 en 3 meses → rojo
    assert m["estado"] == "ambar"            # 1 rojo + 1 ámbar (IWM a -3 %)
    assert fp.semaforo_macro({})["estado"] is None


def test_sentimiento():
    s = sentimiento.sentimiento(["Acme beats estimates and raises guidance", "Acme announces $50M public offering",
                                 "Rosen Law Firm reminds investors of class action against Acme"])
    assert "ampliación de capital" in s["sent_alarmas"]
    assert "investigación o demanda" not in s["sent_alarmas"]   # anuncio de bufete = ruido
    assert s["sent_positivos"] == 1 and s["sent_negativos"] == 1
    assert sentimiento.sentimiento([])["sent_nota"] is None
    f = [dict(ticker="X", banderas=[], extra={"noticias": [{"titulo": "X receives complete response letter from FDA"}]})]
    assert sentimiento.aplicar(f) == 1 and f[0]["extra"]["sent_nota"] < 0 and f[0]["banderas"]


def test_banderas_y_senales_nuevas():
    from tests.test_oportunidades import _fila
    filas = [_fila("A", sec_colocacion_90d=1, sec_13d_180d=1, sec_grandes_inversores_180d=1),
             _fila("B", sector="Healthcare", ensayos_clave_12m=2, sec_retraso_365d=1),
             _fila("C", cortos_flotante=0.2, cortos_cambio_1m_pct=40)] + [_fila(f"Z{i}") for i in range(5)]
    r = {f["ticker"]: f for f in op.puntuar(filas, hoy=HOY)}
    assert any("424B" in b for b in r["A"]["banderas"]) and any("13D" in s for s in r["A"]["senales"])
    assert any("ensayos de fase 2/3" in s for s in r["B"]["senales"]) and any("tarde" in b for b in r["B"]["banderas"])
    assert any("cortas suben" in b for b in r["C"]["banderas"])


def test_validacion(tmp_path):
    filas = [dict(puesto=i + 1, ticker=f"T{i}", nota=100 - i, precio=10.0, carril="x") for i in range(60)]
    validacion.guardar_foto(filas, date(2026, 10, 1), str(tmp_path))
    hoy = [dict(ticker=f"T{i}", precio=10.0 * (1.3 if i < 20 else 1.0)) for i in range(60)]   # las 20 mejores suben
    v = validacion.validar(hoy, date(2026, 11, 15), str(tmp_path))
    p = v["plazos"][-1]
    assert p["plazo"] == "1 mes" and p["top20"] == 30.0 and p["ventaja_top20"] == 30.0 and p["correlacion"] > 0.5
    assert "Las 20 mejores" in validacion.informe(v)
    assert "Todavía no hay historia" in validacion.informe(dict(fotos=0, plazos=[]))
