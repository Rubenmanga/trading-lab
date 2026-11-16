"""Pruebas sin internet del detector de inflexión (Paso 8)."""
import zipfile
from datetime import date

from tradinglab.backtest12m import datos, inflexion as inf


def _fila(ini, fin, val, filed, form="10-Q"):
    return {"start": ini, "end": fin, "val": val, "form": form, "filed": filed}


def _facts():
    # ventas trimestrales 2022: 100, 100, 100, 100 (Q4 sale de restar el año menos 9 meses)
    # 2023: 110 (+10 %), 130 (+30 %): las ventas ACELERAN.
    v = [_fila("2022-01-01", "2022-03-31", 100, "2022-05-10"), _fila("2022-04-01", "2022-06-30", 100, "2022-08-10"), _fila("2022-01-01", "2022-06-30", 200, "2022-08-10"),
         _fila("2022-01-01", "2022-09-30", 300, "2022-11-10"), _fila("2022-01-01", "2022-12-31", 400, "2023-03-01", "10-K"),
         _fila("2023-01-01", "2023-03-31", 110, "2023-05-10"), _fila("2023-04-01", "2023-06-30", 130, "2023-08-10")]
    bruto = [_fila("2022-04-01", "2022-06-30", 40, "2022-08-10"), _fila("2023-04-01", "2023-06-30", 65, "2023-08-10")]
    gg = [_fila("2022-04-01", "2022-06-30", 30, "2022-08-10"), _fila("2023-04-01", "2023-06-30", 31, "2023-08-10")]
    cfo = [_fila("2023-01-01", "2023-03-31", -5, "2023-05-10"), _fila("2023-01-01", "2023-06-30", -15, "2023-08-10")]
    caja = [{"end": "2023-06-30", "val": 100, "form": "10-Q", "filed": "2023-08-10"}]
    return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": v}}, "GrossProfit": {"units": {"USD": bruto}},
                                  "SellingGeneralAndAdministrativeExpense": {"units": {"USD": gg}},
                                  "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": cfo}},
                                  "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": caja}}}}}


def test_trimestral_resta_acumulados():
    prep = inf.preparar(_facts())
    q = inf.trimestral(prep["ventas"], date(2023, 9, 1))
    assert q[date(2022, 9, 30)] == 100 and q[date(2022, 12, 31)] == 100 and q[date(2023, 6, 30)] == 130
    assert date(2023, 6, 30) not in inf.trimestral(prep["ventas"], date(2023, 8, 1))     # aún no presentado
    assert inf.trimestral(prep["flujo_operativo"], date(2023, 9, 1))[date(2023, 6, 30)] == -10


def test_senales():
    prep = inf.preparar(_facts())
    s = inf.senales(prep, date(2023, 9, 30), 105, 100, [(date(2023, 9, 1), date(2023, 8, 28), "a"),
                                                         (date(2023, 9, 5), date(2023, 9, 2), "b")])
    assert s["datos_trimestrales"] and s["aceleracion"] and s["acel_pp"] == 20.0
    assert s["margen"] and s["gastos"] and s["dilucion"] and s["directivos"]
    assert s["caja"]                                  # quema 10 por trimestre y tiene 100 (> 6 trimestres)
    s2 = inf.senales(prep, date(2023, 9, 30), 150, 100, [])
    assert not s2["dilucion"] and not s2["directivos"]


def test_compras_directivos_ventana():
    c = [(date(2023, 1, 5), date(2023, 1, 2), "a"), (date(2023, 3, 10), date(2023, 3, 8), "b")]
    assert inf.compras_directivos(c, date(2023, 3, 31)) == 1        # separadas más de 30 días
    c.append((date(2023, 3, 20), date(2023, 3, 18), "c"))
    assert inf.compras_directivos(c, date(2023, 3, 31)) == 2
    assert inf.compras_directivos(c, date(2023, 3, 15)) == 1        # la de "c" aún no se conocía


def test_directivos_de_zip(tmp_path):
    zp = tmp_path / "f.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("2023q1/SUBMISSION.tsv", "ACCESSION_NUMBER\tFILING_DATE\tDOCUMENT_TYPE\tISSUERCIK\n"
                   "1\t05-JAN-2023\t4\t123\n2\t06-JAN-2023\t4\t123\n")
        z.writestr("2023q1/NONDERIV_TRANS.tsv", "ACCESSION_NUMBER\tTRANS_DATE\tTRANS_CODE\n"
                   "1\t03-JAN-2023\tP\n2\t04-JAN-2023\tS\n")
        z.writestr("2023q1/REPORTINGOWNER.tsv", "ACCESSION_NUMBER\tRPTOWNERCIK\n1\t999\n2\t888\n")
    assert datos.directivos_de_zip(str(zp)) == [{"cik": "0000000123", "presentado": "2023-01-05",
                                                 "fecha_op": "2023-01-03", "dueno": "999"}]


def test_compactar_guarda_trimestres():
    c = datos.compactar(_facts())
    assert len(c["facts"]["us-gaap"]["Revenues"]["units"]["USD"]) == 7


def test_estudio_y_informe(tmp_path):
    pre, coh = {}, {}
    for k, m in enumerate(["2016-03", "2016-06", "2022-03", "2022-06"]):
        filas = []
        for i in range(20):
            t = f"T{i}"
            pre.setdefault(t, {})[m] = (10.0, 10.0, 1e6)
            a, b = int(m[:4]) + 3, m[5:]
            pre[t][f"{a}-{b}"] = (40.0 if i < 2 else 11.0, 0, 0)        # T0 y T1 hacen x4
            filas.append({"ticker": t, "inflexion": {"datos_trimestrales": True, "aceleracion": i < 2,
                                                     "margen": i < 2, "acel_pp": float(i)}})
        coh[m] = filas
    r = inf.estudio(coh, pre, "2026-10")
    assert r["prueba"][r["elegida"]]["decil_pct"] == 100.0 and r["prueba"][r["elegida"]]["base_pct"] == 10.0
    assert r["pasa"]
    texto = open(inf.informe(r, str(tmp_path / "INFORME-INFLEXION-x.md"), {"ultimo_mes": "2026-10"})).read()
    assert "PASA" in texto and "Límites" in texto and "Resumen en 5 líneas" in texto
