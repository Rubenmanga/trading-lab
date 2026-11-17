import json
from datetime import date

from tradinglab.medio_plazo import carpeta_dia as cd


def _prep(tmp_path):
    (tmp_path / "estado.json").write_text(json.dumps({
        "actualizado": "2026-11-16T22:40:00+00:00",
        "alertas": [{"ticker": "AAA", "tipo": "ZONA DE ENTRADA", "mensaje": "AAA en zona"},
                    {"ticker": "AAA", "tipo": "ZONA DE ENTRADA", "mensaje": "repetido"},
                    {"ticker": "BBB", "tipo": "SIN IMPORTANCIA", "mensaje": "no sale"}],
        "precios": [{"ticker": "AAA", "precio": 9.5}, {"ticker": "BBB", "precio": 30}]}))
    (tmp_path / "watchlist.csv").write_text(
        "ticker,veredicto,zona_entrada_max,precio_objetivo_12m,stop_tesis,proximo_catalizador,fecha_catalizador\n"
        "AAA,comprar_en_zona,10,15,8,Resultados,2026-11-20\n"
        "BBB,vigilar,20,40,15,FDA,2027-03-01\n", encoding="utf-8")
    (tmp_path / "ranking.json").write_text(json.dumps({"actualizado": "2026-11-16T22:00:00+00:00", "filas": [
        {"puesto": 1, "ticker": "NUE", "nota": 80, "carril": "GARP", "proximos_resultados": "2026-11-25"},
        {"puesto": 2, "ticker": "BBB", "nota": 70, "carril": "x", "proximos_resultados": "2026-11-25"}]}))
    (tmp_path / "historico").mkdir()
    (tmp_path / "historico" / "2026-11-13.csv").write_text("puesto,ticker,nota,precio,carril\n1,BBB,70,30,x\n")
    exp = tmp_path / "expedientes" / "AAA"
    exp.mkdir(parents=True)
    (exp / "eventos.csv").write_text(
        "fecha,tipo,resumen,fuente_url,fecha_fuente,precio_antes,reaccion_1d,reaccion_5d,reaccion_20d\n"
        "2026-11-15,cuentas,Cuentas (10-Q),u,2026-11-15,9,3.1,,\n"
        "2026-10-01,cuentas,Viejo,u,2026-10-01,9,,,\n", encoding="utf-8")


def test_carpeta_dia(tmp_path):
    _prep(tmp_path)
    txt = cd.construir(date(2026, 11, 16), tmp_path, {"AAA": "cartera", "BBB": "vigilancia"})
    assert "AAA en zona" in txt and "repetido" not in txt and "no sale" not in txt
    assert "Cuentas (10-Q) (1 día: 3.1 %)" in txt and "Viejo" not in txt
    assert "**AAA** a 9.50 $ ≤ zona 10" in txt and "**BBB** a 30" not in txt
    assert "20/11 **AAA** · Resultados" in txt and "25/11 **BBB** · presenta resultados" in txt and "FDA" not in txt
    assert "#1 **NUE**" in txt and "#2 **BBB**" not in txt
    assert len(txt.splitlines()) < 45   # cabe en una pantalla del móvil


def test_sin_datos_no_falla(tmp_path):
    txt = cd.construir(date(2026, 11, 16), tmp_path, {})
    assert txt.count("- Nada.") == 5


def test_recorta():
    assert cd._recorta([f"- {i}" for i in range(9)])[-1] == "- … y 3 más"


def test_avisa_si_los_precios_son_viejos(tmp_path):
    """Auditoría 17-nov (D3): con precios de hace más de un día de bolsa, la carpeta lo dice y no confirma zonas."""
    _prep(tmp_path)
    fresco = cd.construir(date(2026, 11, 17), tmp_path, tickers={"AAA": "a"})
    assert "PRECIOS VIEJOS" not in fresco
    viejo = cd.construir(date(2026, 11, 19), tmp_path, tickers={"AAA": "a"})
    assert "PRECIOS VIEJOS" in viejo and "SIN CONFIRMAR" in viejo
    assert cd.dias_bolsa_de_retraso("2026-11-13T22:00:00+00:00", date(2026, 11, 16)) == 1   # viernes -> lunes
    assert cd.dias_bolsa_de_retraso("", date(2026, 11, 16)) is None
