from tradinglab.medio_plazo import marcador, propuestas as p

BIEN = """# Propuestas de hoy · 17/11/2026

Resumen corto.

| ticker | idea | precio | entrada | stop | objetivo | motivo |
|---|---|---|---|---|---|---|
| REPX | comprar_en_zona | 44.40 | 46 | 36 | 58 | En zona, potencial 31 % (hoy.md) |
| PGY | vigilar | 16.87 | 15 | 12.5 | 25 | Cae tras 13G; esperar |
| ORIC | evitar | 7.86 | 7 | 6.5 | 13 | Resultados hoy: binario |
"""


def test_valida_y_apunta(tmp_path):
    a = tmp_path / "2026-11-17.md"
    a.write_text(BIEN, encoding="utf-8")
    libro = tmp_path / "predicciones.csv"
    r = p.apuntar(a, libro)
    assert r["errores"] == [] and r["añadidas"] == 3
    filas = marcador.leer(libro)
    assert filas[0]["id"] == "PROP-2026-11-17-REPX" and filas[0]["stop_tesis"] == "36.0"
    assert filas[0]["fecha_revision"] == "2027-02-15"
    # otro día con la misma acción: no se repite en 30 días
    b = tmp_path / "2026-11-18.md"
    b.write_text(BIEN, encoding="utf-8")
    r2 = p.apuntar(b, libro)
    assert r2["añadidas"] == 0 and set(r2["repetidas"]) == {"REPX", "PGY", "ORIC"}


def test_rechaza_tabla_mala(tmp_path):
    a = tmp_path / "2026-11-17.md"
    a.write_text(BIEN.replace("| 46 | 36 |", "| 30 | 36 |").replace("| ORIC |", "| oric?? |"), encoding="utf-8")
    r = p.apuntar(a, tmp_path / "x.csv")
    assert r["añadidas"] == 0 and any("stop < entrada" in e for e in r["errores"])
    assert not (tmp_path / "x.csv").exists()


def test_pocas_ideas():
    _, err = p.validar(BIEN.split("| PGY")[0])
    assert any("de 3 a 5" in e for e in err)
