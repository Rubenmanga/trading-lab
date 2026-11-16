from pathlib import Path

from tradinglab.medio_plazo.regla_fuentes import dias_bolsa, nivel_fuente, revisar, main
from datetime import date

BUENA = """# ABC
## Resumen
...
## Tabla de fuentes
| dato | valor | fuente | fecha |
|---|---|---|---|
| precio | 4,10 $ | investigacion/ranking.json | 2026-11-20 |
| caja | 50 M$ | [10-Q](https://www.sec.gov/Archives/edgar/data/1/x.htm) | 2026-11-10 |
| objetivo analistas | 8 $ | https://stockanalysis.com/stocks/abc/forecast/ (intermediaria) | 2026-11-20 |
"""


def _r(nombre="ABC-2026-11-23.md"):
    return Path("investigacion/analisis") / nombre


def test_informe_bueno_pasa():
    # 20-nov viernes → 23-nov lunes: 1 día de bolsa
    assert revisar(_r(), BUENA) == []


def test_sin_tabla_no_pasa():
    assert "falta la sección" in revisar(_r(), "# ABC\n## Fuentes\n- https://sec.gov\n")[0]


def test_precio_viejo_no_pasa():
    f = revisar(_r("ABC-2026-11-26.md"), BUENA)
    assert any("días de bolsa" in x for x in f)


def test_precio_o_caja_de_intermediaria_no_pasa():
    t = BUENA.replace("investigacion/ranking.json", "https://www.marketbeat.com/stocks/NASDAQ/ABC/")
    assert any("intermediaria" in x for x in revisar(_r(), t))


def test_sin_fuente_oficial_ni_fecha():
    t = BUENA.replace("[10-Q](https://www.sec.gov/Archives/edgar/data/1/x.htm)", "https://finviz.com/x")
    f = revisar(_r(), t)
    assert any("ninguna fuente oficial" in x for x in f) and any("caja" in x for x in f)
    t2 = BUENA.replace("| 2026-11-10 |", "| nov |")
    assert any("sin fecha" in x for x in revisar(_r(), t2))


def test_nivel_mentido_y_sin_precio():
    t = ("## Tabla de fuentes\n| dato | valor | fuente | fecha | nivel |\n|---|---|---|---|---|\n"
         "| ventas | 1 | https://www.tipranks.com/x | 2026-11-20 | 1 |\n")
    f = revisar(_r(), t)
    assert any("dice nivel 1" in x for x in f) and any("falta la fila «precio»" in x for x in f)


def test_informes_antiguos_y_otros_nombres_no_se_revisan():
    assert revisar(_r("TE-2026-11-16.md"), "nada") == []
    assert revisar(_r("notas.md"), "nada") == []


def test_niveles_y_dias():
    assert nivel_fuente("https://www.sec.gov/x") == 1
    assert nivel_fuente("https://ir.empresa.com/news") == 1
    assert nivel_fuente("https://finance.yahoo.com/quote/ABC") == 2
    assert nivel_fuente("https://www.nasdaq.com/articles/x") == 3
    assert nivel_fuente("sin enlace") is None
    assert dias_bolsa(date(2026, 11, 20), date(2026, 11, 23)) == 1


def test_main_con_informes_del_repo_pasa():
    assert main([]) == 0
