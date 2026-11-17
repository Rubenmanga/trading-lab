"""Contratos del investigador IA: datos de hoy, descubrimiento, riesgos y suspensión."""
import csv
import json
from datetime import date, timedelta

import pytest

from tradinglab.medio_plazo import investigador_fuentes as f
from tradinglab.medio_plazo import investigador_ia as ia

HOY = date(2026, 11, 17)


def noticia(ticker, tipo="titular RSS", fecha="2026-11-17", primaria=False, url="https://example.com/noticia"):
    return f.fuente(ticker, fecha, tipo, url, "Se publica un documento", primaria)


def empresa(ticker, nota=70, empresa="Example Biotechnology"):
    return {"ticker": ticker, "empresa": empresa, "precio": 8.0, "nota": nota,
            "sector": "Healthcare", "factores": {}, "banderas": [], "extra": {
                "noticias": [{"fecha": "2026-11-17", "titulo": ticker + " anuncia novedades",
                              "url": "https://example.com/" + ticker}]},
            "sec_documentos": []}


def test_radar_descubre_empresas_que_no_estan_en_watchlist():
    r = {"actualizado": "2026-11-17T05:30:00Z",
         "filas": [empresa("NEWA"), empresa("NEWB"), empresa("OLD")]}
    out = f.candidatos(r, [{"ticker": "OLD"}], {}, [], HOY)
    assert {x["ticker"] for x in out} == {"NEWA", "NEWB", "OLD"}
    assert next(x for x in out if x["ticker"] == "NEWA")["nueva"] is True
    assert next(x for x in out if x["ticker"] == "OLD")["nueva"] is False


def test_evitar_dormido_rechaza_titulares_y_13g():
    antes = {"estado": "evitar", "desde": "2026-11-15", "vistas": ["abc"]}
    secundaria = noticia("OLD", fecha="2026-11-17")
    sec13g = noticia("OLD", tipo="SEC listado", fecha="2026-11-17", primaria=True)
    assert not f.reactivable(antes, [secundaria, sec13g], HOY)


def test_evitar_se_reactiva_tras_documento_material_nuevo():
    antes = {"estado": "evitar", "desde": "2026-11-15", "vistas": ["abc"]}
    act = noticia("OLD", tipo="SEC 8-K", fecha="2026-11-17", primaria=True)
    assert f.reactivable(antes, [act], HOY)
    assert not f.reactivable({**antes, "vistas": [act["id"]]}, [act], HOY)
    assert not f.reactivable(antes, [noticia("OLD", "SEC 8-K", fecha="2026-11-13", primaria=True)], HOY)


def test_validacion_no_aprueba_compra_inventada_o_sin_escenarios():
    e = empresa("NEWX")
    r = {"actualizado": "2026-11-17T05:30:00Z", "filas": [e]}
    candidatos = f.candidatos(r, [], {}, [], HOY)
    src = candidatos[0]["fuentes"][0]
    respuesta = {"resumen": "Algo", "analisis": [
        {"ticker": "NEWX", "estado": "comprar_en_zona", "tesis": "Posible oportunidad",
         "fuentes": [src["id"]], "riesgos": "Puede caer"}]}
    analisis, errores = ia.evaluar_respuesta(respuesta, candidatos, [], {}, HOY)
    assert not errores
    assert analisis[0]["estado"] == "vigilar"


def test_validacion_rechaza_citas_que_no_existen():
    r = {"actualizado": "2026-11-17", "filas": [empresa("NEWA")]}
    c = f.candidatos(r, [], {}, [], HOY)
    with pytest.raises(ValueError, match="evidencia"):
        ia.evaluar_respuesta({"analisis": [{"ticker": "NEWA", "fuentes": ["inventada"]}]}, c, [], {}, HOY)


def test_memoria_guarda_evitar_sin_borrar_anteriores():
    a = {"ticker": "NEWA", "estado": "evitar", "razon_estado": "Posible ampliación",
         "fuentes": [noticia("NEWA", fecha="2026-11-17")]}
    r = ia.actualizar_estado({"OLD": {"estado": "vigilar"}}, [a], HOY)
    assert r["OLD"]["estado"] == "vigilar"
    assert r["NEWA"]["estado"] == "evitar"
    assert r["NEWA"]["vistas"] == [a["fuentes"][0]["id"]]


def test_sin_api_key_falla_y_no_escribe(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        ia.ejecutar(HOY, tmp_path)
    assert not list(tmp_path.rglob("*.md"))


def test_ejecucion_ia_mock_crea_reporte_del_dia_y_memoria(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-clave-no-real")
    inv = tmp_path / "investigacion"
    inv.mkdir()
    (inv / "hoy.md").write_text("# Carpeta del día · 17/11/2026\n", encoding="utf-8")
    (inv / "ranking.json").write_text(json.dumps({
        "actualizado": "2026-11-17T05:30:00+00:00",
        "filas": [empresa("NEWA"), empresa("NEWB"), empresa("NEWC")]}), encoding="utf-8")
    (inv / "estado.json").write_text(json.dumps({"actualizado": "2026-11-17T05:30:00+00:00"}),
                                     encoding="utf-8")
    (inv / "entradas.json").write_text("{}", encoding="utf-8")
    (inv / "watchlist.csv").write_text("ticker,stop_tesis,precio_objetivo_12m\n", encoding="utf-8")

    def model(prompt, key):
        assert "NEWA" in prompt and key == "test-clave-no-real"
        c = f.candidatos({"actualizado": "2026-11-17", "filas": [empresa("NEWA")]}, [], {}, [], HOY)
        return {"resumen": "Nuevas empresas hoy", "analisis": [{
            "ticker": "NEWA", "estado": "evitar", "razon_estado": "Resultados inciertos",
            "tesis": "Novedad de hoy", "fuentes": [c[0]["fuentes"][0]["id"]],
            "riesgos": "Riesgo de pérdida del capital", "catalizador": "Pendiente"}]}

    r = ia.ejecutar(HOY, tmp_path, modelo_llamar=model,
                   rss_llamar=lambda _: ([], []), sec_llamar=lambda _, __: ({}, []))
    assert r["estado"] == "publicado" and r["nuevas"] == 1
    s = (inv / "investigador" / "2026-11-17.md").read_text(encoding="utf-8")
    assert "NEWA" in s and "Riesgo de pérdida" in s
    m = json.loads((inv / "investigador" / "estado_ia.json").read_text())
    assert m["NEWA"]["estado"] == "evitar"
    r2 = ia.ejecutar(HOY, tmp_path, modelo_llamar=lambda *_: (_ for _ in ()).throw(AssertionError()))
    assert r2["estado"] == "ya_publicado"


def test_fecha_fresca_sin_simular_mercado():
    assert f.dia_valido("2026-11-17T05:31:22+00:00", HOY, 2)
    assert not f.dia_valido("2026-11-09", HOY, 2)
    assert not f.dia_valido("2026-11-20", HOY, 2)
