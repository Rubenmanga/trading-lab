"""Pruebas sin internet de las cuentas de la SEC (XBRL) y las fórmulas Piotroski, Altman Z'' y Beneish M."""
import gzip
import csv
from datetime import date

from tradinglab.medio_plazo import oportunidades as op
from tradinglab.medio_plazo import sec_cuentas as sc
from tradinglab.medio_plazo import validacion

# Tres ejercicios (2023-2025) de una empresa que mejora. Cada 10-K se presenta en marzo del año siguiente.
ANIOS = {
    2023: dict(ventas=100e6, coste_ventas=60e6, beneficio_neto=-5e6, ebit=-3e6, flujo_operativo=2e6, activos=200e6,
               activo_corriente=80e6, pasivo_corriente=40e6, pasivo=100e6, patrimonio=100e6, deuda_lp=50e6,
               beneficios_retenidos=-20e6, acciones=50e6, cobros_pendientes=20e6, inmovilizado=50e6),
    2024: dict(ventas=120e6, coste_ventas=70e6, beneficio_neto=2e6, ebit=5e6, flujo_operativo=8e6, activos=210e6,
               activo_corriente=90e6, pasivo_corriente=40e6, pasivo=100e6, patrimonio=110e6, deuda_lp=45e6,
               beneficios_retenidos=-18e6, acciones=50e6, cobros_pendientes=22e6, inmovilizado=52e6),
    2025: dict(ventas=150e6, coste_ventas=80e6, beneficio_neto=10e6, ebit=14e6, flujo_operativo=18e6, activos=220e6,
               activo_corriente=100e6, pasivo_corriente=38e6, pasivo=95e6, patrimonio=125e6, deuda_lp=40e6,
               beneficios_retenidos=-8e6, acciones=49e6, cobros_pendientes=24e6, inmovilizado=55e6),
}
NOMBRE = {"ventas": "Revenues", "coste_ventas": "CostOfRevenue", "beneficio_neto": "NetIncomeLoss",
          "ebit": "OperatingIncomeLoss", "flujo_operativo": "NetCashProvidedByUsedInOperatingActivities",
          "activos": "Assets", "activo_corriente": "AssetsCurrent", "pasivo_corriente": "LiabilitiesCurrent",
          "pasivo": "Liabilities", "patrimonio": "StockholdersEquity", "deuda_lp": "LongTermDebtNoncurrent",
          "beneficios_retenidos": "RetainedEarningsAccumulatedDeficit",
          "acciones": "WeightedAverageNumberOfDilutedSharesOutstanding",
          "cobros_pendientes": "AccountsReceivableNetCurrent", "inmovilizado": "PropertyPlantAndEquipmentNet"}


def _facts(anios=ANIOS):
    gaap = {}
    for a, d in anios.items():
        for k, v in d.items():
            x = {"end": f"{a}-12-31", "val": v, "form": "10-K", "filed": f"{a + 1}-03-01", "fy": a, "fp": "FY"}
            if k not in sc.BALANCE:
                x["start"] = f"{a}-01-01"
            unidad = "shares" if k == "acciones" else "USD"
            gaap.setdefault(NOMBRE[k], {"units": {unidad: []}})["units"][unidad].append(x)
    # un trimestre que no debe contar como año
    gaap.setdefault("Revenues", {"units": {"USD": []}})["units"]["USD"].append({"start": "2026-04-01", "end": "2026-06-30", "val": 40e6,
                                             "form": "10-Q", "filed": "2026-08-01"})
    return {"facts": {"us-gaap": gaap}}


def test_serie_anual_sin_mirar_al_futuro():
    f = _facts()
    assert set(sc.serie_anual(f, "ventas", date(2026, 11, 15))) == {date(2023, 12, 31), date(2024, 12, 31),
                                                                    date(2025, 12, 31)}
    # en enero de 2026 el 10-K de 2025 aún no existía
    assert date(2025, 12, 31) not in sc.serie_anual(f, "ventas", date(2026, 1, 15))


def test_correccion_posterior_solo_cuenta_desde_que_se_presenta():
    f = _facts()
    f["facts"]["us-gaap"]["Revenues"]["units"]["USD"].append(
        {"start": "2025-01-01", "end": "2025-12-31", "val": 140e6, "form": "10-K/A", "filed": "2026-09-01"})
    assert sc.serie_anual(f, "ventas", date(2026, 6, 1))[date(2025, 12, 31)] == 150e6
    assert sc.serie_anual(f, "ventas", date(2026, 11, 1))[date(2025, 12, 31)] == 140e6


def test_metricas_empresa_que_mejora():
    m = sc.metricas(_facts(), date(2026, 11, 15))
    assert m["sec_ejercicio_fin"] == "2025-12-31"
    assert m["f_score"] >= 8 and m["f_score_comprobables"] == 9
    assert m["altman_z"] > 2.6                     # zona tranquila
    assert m["beneish_m"] is not None and m["beneish_m"] < -1.78
    assert abs(m["rent_bruta_activos"] - 70e6 / 220e6) < 1e-9


def test_dato_desconocido_no_cuenta_como_bueno():
    solo = {a: {k: v for k, v in d.items() if k in ("beneficio_neto", "activos")} for a, d in ANIOS.items()}
    m = sc.metricas(_facts(solo), date(2026, 11, 15))
    assert m["f_score"] is None and m["f_score_comprobables"] < 7
    assert m["altman_z"] is None and m["beneish_m"] is None


def test_cuentas_viejas_no_puntuan():
    m = sc.metricas(_facts(), date(2027, 9, 1))     # último 10-K de hace 20 meses
    assert m["f_score"] is None and m["altman_z"] is None


def test_banderas_formulas():
    b = [t for t, _ in op.banderas({"altman_z": 0.5, "beneish_m": -1.0, "f_score": 1, "analistas": 5})]
    assert any("Altman" in t for t in b) and any("Beneish" in t for t in b) and any("Piotroski" in t for t in b)
    banco = [t for t, _ in op.banderas({"altman_z": 0.5, "beneish_m": -1.0, "sector": "Financial Services",
                                         "analistas": 5})]
    assert not any("Altman" in t or "Beneish" in t for t in banco)


def test_foto_analistas(tmp_path):
    p = validacion.guardar_foto_analistas([{"ticker": "AAA", "precio": 10.123456, "objetivo_medio": 15.0,
                                            "analistas": 6}, {"ticker": "BBB"}], date(2026, 11, 15), str(tmp_path))
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    assert p.endswith("2026-11-15.csv.gz") and [r["ticker"] for r in filas] == ["AAA", "BBB"]
    assert filas[0]["precio"] == "10.1235" and filas[1]["objetivo_medio"] == ""
