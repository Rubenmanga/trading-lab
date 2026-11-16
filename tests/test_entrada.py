import json

from tradinglab.medio_plazo import entrada as en

TESIS = """# AAA · tesis

## Por qué interesa
algo

## Escenarios y precio de entrada
| escenario | probabilidad | precio en 12 meses | qué tiene que pasar |
|---|---|---|---|
| malo | 25 % | 11 $ | x |
| normal | 45 % | 24 $ | y |
| bueno | 30 % | 32 $ | z |

## Notas
no tocar
"""


def _prep(tmp_path, tesis=TESIS, t="AAA"):
    d = tmp_path / "expedientes" / t
    d.mkdir(parents=True)
    (d / "tesis.md").write_text(tesis, encoding="utf-8")
    return d / "tesis.md"


def test_calculo_fijo():
    r = en.calcular({"malo": {"prob": 25, "precio": 11}, "normal": {"prob": 45, "precio": 24},
                     "bueno": {"prob": 30, "precio": 32}})
    assert r["valor_esperado"] == 23.15
    assert r["regla_3a1"] == 14.25 and r["regla_margen"] == 19.68
    assert r["entrada"] == 14.25 and r["manda"] == "3 a 1" and not r["binaria"]


def test_errores_y_binaria():
    assert "error" in en.calcular({"malo": {"prob": 50, "precio": 1}, "normal": {"prob": 50, "precio": 2}})
    assert "suman" in en.calcular({"malo": {"prob": 50, "precio": 1}, "normal": {"prob": 50, "precio": 2},
                                   "bueno": {"prob": 50, "precio": 3}})["error"]
    r = en.calcular({"malo": {"prob": 0.4, "precio": 1}, "normal": {"prob": 0.4, "precio": 10},
                     "bueno": {"prob": 0.2, "precio": 20}})
    assert r["binaria"] and r["entrada"] is None


def test_mismo_precio_siempre_y_no_pisa_lo_demas(tmp_path):
    tes = _prep(tmp_path)
    r1 = en.ejecutar(["AAA"], tmp_path)["AAA"]
    texto1 = tes.read_text(encoding="utf-8")
    r2 = en.ejecutar(["AAA"], tmp_path)["AAA"]
    assert r1 == r2 and r1["entrada"] == 14.25
    assert tes.read_text(encoding="utf-8") == texto1          # segunda pasada: nada cambia
    assert texto1.count(en.INI) == 1 and "## Notas\nno tocar" in texto1 and "≤ 14,25 $" in texto1
    assert json.loads((tmp_path / "entradas.json").read_text())["AAA"]["entrada"] == 14.25


def test_siembra_desde_informe_y_binaria_declarada(tmp_path):
    tes = _prep(tmp_path, "# BBB · tesis\n\n## Escenarios y precio de entrada\n_(pendiente)_\n", "BBB")
    (tmp_path / "analisis").mkdir()
    (tmp_path / "analisis" / "BBB-2026-11-14.md").write_text(
        "| Escenario | Probabilidad | Precio a 12 meses | Por qué |\n|---|---|---|---|\n"
        "| Bueno | 30 % | 95-100 $ | a |\n| Base | 45 % | 60-65 $ | b |\n| Malo | 25 % | 25-30 $ | c |\n",
        encoding="utf-8")
    r = en.ejecutar(["BBB"], tmp_path)["BBB"]
    assert r["entrada"] == 36.25 and "BBB-2026-11-14.md" in r["origen"]
    texto = tes.read_text(encoding="utf-8")
    assert "_(pendiente)_" not in texto and "| malo | 25 % | 27,50 $ | c |" in texto
    tes.write_text(texto.replace("Tipo: normal", "Tipo: binaria"), encoding="utf-8")
    assert en.ejecutar(["BBB"], tmp_path)["BBB"]["entrada"] is None
    assert "todo o nada" in tes.read_text(encoding="utf-8")


def test_tabla_vacia_no_inventa(tmp_path):
    tes = _prep(tmp_path, "# CCC · tesis\n\n## Escenarios y precio de entrada\n_(pendiente)_\n", "CCC")
    assert en.ejecutar(["CCC"], tmp_path) == {}
    assert "| malo | | | |" in tes.read_text(encoding="utf-8")
