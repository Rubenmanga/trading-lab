"""Cuentas oficiales de la SEC (XBRL) y cuatro fórmulas clásicas de analistas.

Fuente: data.sec.gov/api/xbrl/companyfacts (gratis, sin clave; solo pide un User-Agent "Nombre email",
secreto SEC_USER_AGENT). Cada dato trae la fecha en que se PRESENTÓ (`filed`), así que `metricas(facts, fecha)`
usa solo lo que se sabía ese día: sirve igual para el ranking de hoy que para un backtest sin mirar al futuro.

Fórmulas (todas con cuentas anuales del 10-K; si falta un dato clave el resultado es None, nunca "bueno"):
  - Piotroski F-score (2000): 9 comprobaciones de salud, 0-9. Necesita al menos 7 comprobables.
  - Altman Z'' (1995, versión para cualquier sector): riesgo de quiebra. <1,1 peligro; >2,6 tranquilo.
  - Beneish M (1999, 8 variables): posible maquillaje contable. >-1,78 sospechoso.
  - Rentabilidad bruta sobre activos (Novy-Marx, 2013): beneficio bruto / activos totales.
"""
from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from .fuentes_publicas import ULTIMO_ERROR, _ua, mapa_cik

SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Concepto → nombres XBRL posibles (se usa el primero que tenga datos).
CONCEPTOS = {
    "ventas": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
               "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueGoodsNet"],
    "coste_ventas": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfServices"],
    "beneficio_bruto": ["GrossProfit"],
    "beneficio_neto": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "ebit": ["OperatingIncomeLoss"],
    "flujo_operativo": ["NetCashProvidedByUsedInOperatingActivities",
                        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "amortizacion": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
                     "DepreciationAmortizationAndAccretionNet", "Depreciation"],
    "gastos_generales": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
    "acciones": ["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
    # balance (fotos a fecha de cierre)
    "activos": ["Assets"],
    "activo_corriente": ["AssetsCurrent"],
    "pasivo_corriente": ["LiabilitiesCurrent"],
    "pasivo": ["Liabilities"],
    "patrimonio": ["StockholdersEquity",
                   "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "deuda_lp": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "beneficios_retenidos": ["RetainedEarningsAccumulatedDeficit"],
    "cobros_pendientes": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "inmovilizado": ["PropertyPlantAndEquipmentNet"],
}
BALANCE = {"activos", "activo_corriente", "pasivo_corriente", "pasivo", "patrimonio", "deuda_lp",
           "beneficios_retenidos", "cobros_pendientes", "inmovilizado"}
FORMULARIOS_ANUALES = ("10-K", "10-K/A", "10-KT", "20-F", "20-F/A", "40-F", "40-F/A")


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def serie_anual(facts: dict, concepto: str, fecha: date | None = None) -> dict[date, float]:
    """{fin de ejercicio: valor} con lo presentado en informes anuales hasta `fecha` (incluida).
    Si un ejercicio se corrigió más tarde, vale la última versión presentada antes de `fecha`."""
    fecha = fecha or date.today()
    gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    for nombre in CONCEPTOS[concepto]:
        unidades = (gaap.get(nombre) or {}).get("units") or {}
        filas = unidades.get("USD") or unidades.get("shares") or next(iter(unidades.values()), [])
        mejor: dict[date, tuple[date, float]] = {}
        for x in filas:
            if x.get("form") not in FORMULARIOS_ANUALES or not x.get("filed") or not x.get("end"):
                continue
            presentado = _d(x["filed"])
            if presentado > fecha:
                continue
            fin = _d(x["end"])
            if concepto not in BALANCE:
                if not x.get("start"):
                    continue
                dias = (fin - _d(x["start"])).days
                if not 340 <= dias <= 380:     # solo ejercicios completos (no trimestres)
                    continue
            prev = mejor.get(fin)
            if prev is None or presentado >= prev[0]:
                mejor[fin] = (presentado, float(x["val"]))
        if mejor:
            return {k: v[1] for k, v in mejor.items()}
    return {}


def _cerca(serie: dict[date, float], fin: date, holgura: int = 20) -> float | None:
    for k, v in serie.items():
        if abs((k - fin).days) <= holgura:
            return v
    return None


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def ejercicios(facts: dict, fecha: date | None = None) -> list[dict]:
    """Los 3 últimos ejercicios anuales conocidos a `fecha`, del más reciente al más antiguo."""
    series = {c: serie_anual(facts, c, fecha) for c in CONCEPTOS}
    fines = sorted(set(series["activos"]) | set(series["beneficio_neto"]), reverse=True)
    if not fines:
        return []
    salida, ultimo = [], None
    for fin in fines:
        if ultimo is not None and (ultimo - fin).days < 300:   # mismo ejercicio con fecha algo distinta
            continue
        e = {"fin": fin} | {c: _cerca(s, fin) for c, s in series.items()}
        if e["beneficio_bruto"] is None and e["ventas"] is not None and e["coste_ventas"] is not None:
            e["beneficio_bruto"] = e["ventas"] - e["coste_ventas"]
        if e["pasivo"] is None and e["activos"] is not None and e["patrimonio"] is not None:
            e["pasivo"] = e["activos"] - e["patrimonio"]
        salida.append(e)
        ultimo = fin
        if len(salida) == 3:
            break
    # El año anterior debe ser de verdad el anterior (no un hueco de 2+ años).
    limpio = salida[:1]
    for e in salida[1:]:
        if 330 <= (limpio[-1]["fin"] - e["fin"]).days <= 400:
            limpio.append(e)
        else:
            break
    return limpio


def piotroski(e0: dict, e1: dict | None, e2: dict | None = None) -> tuple[int | None, int, list[str]]:
    """(puntos, comprobaciones posibles, cuáles suman). Puntos None si se pueden comprobar menos de 7."""
    if not e1:
        return None, 0, []
    a0_ini = e1.get("activos")                       # activos al empezar el ejercicio
    a1_ini = (e2 or {}).get("activos") or e1.get("activos")
    roa0, roa1 = _div(e0.get("beneficio_neto"), a0_ini), _div(e1.get("beneficio_neto"), a1_ini)
    cfo0 = e0.get("flujo_operativo")
    pruebas = {
        "ROA positivo": None if roa0 is None else roa0 > 0,
        "Caja operativa positiva": None if cfo0 is None else cfo0 > 0,
        "ROA mejora": None if roa0 is None or roa1 is None else roa0 > roa1,
        "Caja operativa > beneficio": (None if cfo0 is None or a0_ini in (None, 0) or roa0 is None
                                       else cfo0 / a0_ini > roa0),
    }
    lev0, lev1 = _div(e0.get("deuda_lp") or 0, e0.get("activos")), _div(e1.get("deuda_lp") or 0, e1.get("activos"))
    if e0.get("deuda_lp") is None and e1.get("deuda_lp") is None:
        pruebas["Menos deuda"] = None                # sin dato de deuda: no se puede comprobar
    else:
        pruebas["Menos deuda"] = None if lev0 is None or lev1 is None else lev0 <= lev1
    cr0 = _div(e0.get("activo_corriente"), e0.get("pasivo_corriente"))
    cr1 = _div(e1.get("activo_corriente"), e1.get("pasivo_corriente"))
    pruebas["Más liquidez"] = None if cr0 is None or cr1 is None else cr0 > cr1
    s0, s1 = e0.get("acciones"), e1.get("acciones")
    pruebas["Sin acciones nuevas"] = None if s0 is None or s1 is None else s0 <= s1 * 1.005
    mb0, mb1 = _div(e0.get("beneficio_bruto"), e0.get("ventas")), _div(e1.get("beneficio_bruto"), e1.get("ventas"))
    pruebas["Margen bruto mejora"] = None if mb0 is None or mb1 is None else mb0 > mb1
    ro0, ro1 = _div(e0.get("ventas"), a0_ini), _div(e1.get("ventas"), a1_ini)
    pruebas["Rotación de activos mejora"] = None if ro0 is None or ro1 is None else ro0 > ro1
    posibles = [k for k, v in pruebas.items() if v is not None]
    si = [k for k, v in pruebas.items() if v]
    return (len(si) if len(posibles) >= 7 else None), len(posibles), si


def altman_z2(e0: dict) -> float | None:
    """Altman Z'' (no depende del precio ni del sector industrial)."""
    ta, tl = e0.get("activos"), e0.get("pasivo")
    ca, cl, re_, ebit, eq = (e0.get(k) for k in ("activo_corriente", "pasivo_corriente", "beneficios_retenidos",
                                                 "ebit", "patrimonio"))
    if None in (ta, ca, cl, re_, ebit, eq) or not ta or not tl:
        return None
    return 6.56 * (ca - cl) / ta + 3.26 * re_ / ta + 6.72 * ebit / ta + 1.05 * eq / tl


def beneish_m(e0: dict, e1: dict | None) -> float | None:
    """Beneish M de 8 variables. Las 3 secundarias (cobros, amortización, gastos generales) valen 1 (neutro) si
    faltan; las 5 principales son obligatorias. Sin ventas relevantes (<10 M$) no tiene sentido: None."""
    if not e1:
        return None
    v0, v1 = e0.get("ventas"), e1.get("ventas")
    if not v0 or not v1 or v0 < 1e7 or v1 < 1e7:
        return None
    ta0, ta1 = e0.get("activos"), e1.get("activos")
    gb0, gb1 = e0.get("beneficio_bruto"), e1.get("beneficio_bruto")
    ca0, ca1 = e0.get("activo_corriente"), e1.get("activo_corriente")
    ni0, cfo0 = e0.get("beneficio_neto"), e0.get("flujo_operativo")
    if None in (ta0, ta1, gb0, gb1, ca0, ca1, ni0, cfo0) or not ta0 or not ta1 or not gb0:
        return None
    ppe0, ppe1 = e0.get("inmovilizado") or 0, e1.get("inmovilizado") or 0

    def ratio(a, b):
        return a / b if a is not None and b not in (None, 0) else 1.0
    dsri = ratio(_div(e0.get("cobros_pendientes"), v0), _div(e1.get("cobros_pendientes"), v1))
    gmi = (gb1 / v1) / (gb0 / v0)
    aqi = ratio(1 - (ca0 + ppe0) / ta0, 1 - (ca1 + ppe1) / ta1)
    sgi = v0 / v1
    am0, am1 = e0.get("amortizacion"), e1.get("amortizacion")
    depi = ratio(_div(am1, am1 + ppe1) if am1 is not None else None,
                 _div(am0, am0 + ppe0) if am0 is not None else None)
    sgai = ratio(_div(e0.get("gastos_generales"), v0), _div(e1.get("gastos_generales"), v1))
    tata = (ni0 - cfo0) / ta0
    l0 = _div((e0.get("pasivo_corriente") or 0) + (e0.get("deuda_lp") or 0), ta0)
    l1 = _div((e1.get("pasivo_corriente") or 0) + (e1.get("deuda_lp") or 0), ta1)
    lvgi = ratio(l0, l1)
    return (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai
            + 4.679 * tata - 0.327 * lvgi)


def metricas(facts: dict, fecha: date | None = None) -> dict:
    """Todo lo que se sabía a `fecha` (por defecto hoy). Las claves llevan prefijo para el ranking."""
    fecha = fecha or date.today()
    ej = ejercicios(facts, fecha)
    if not ej:
        return {}
    e0, e1, e2 = ej[0], (ej[1] if len(ej) > 1 else None), (ej[2] if len(ej) > 2 else None)
    f, n, si = piotroski(e0, e1, e2)
    rb = _div(e0.get("beneficio_bruto"), e0.get("activos"))
    r = {
        "f_score": f, "f_score_comprobables": n, "f_score_aprobadas": si,
        "altman_z": altman_z2(e0), "beneish_m": beneish_m(e0, e1),
        "rent_bruta_activos": rb,
        "sec_ejercicio_fin": e0["fin"].isoformat(),
        "sec_cuentas_dias": (fecha - e0["fin"]).days,     # antigüedad del último 10-K conocido
    }
    if r["sec_cuentas_dias"] > 550:      # cuentas de hace más de año y medio: no valen para puntuar
        for k in ("f_score", "altman_z", "beneish_m", "rent_bruta_activos"):
            r[k] = None
    return r


# ------------------------------------------------------------------ descarga
def _get_gz(url: str, intentos: int = 3) -> dict | None:
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _ua(), "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            ULTIMO_ERROR["data.sec.gov"] = f"HTTP {e.code}"
            if e.code == 404:
                return None
            time.sleep(3 * (i + 1))
        except Exception as e:  # noqa: BLE001
            ULTIMO_ERROR["data.sec.gov"] = type(e).__name__
            time.sleep(2 * (i + 1))
    return None


def descargar(tickers: list[str], hilos: int = 4, pausa: float = 0.5, limite_seg: float = 900,
              ciks: dict[str, str] | None = None) -> dict[str, dict]:
    """Métricas de hoy para cada ticker. 4 hilos x 2/s = 8 peticiones/s (la SEC permite 10)."""
    ciks = ciks or mapa_cik()
    if not ciks:
        return {}
    fin = time.monotonic() + limite_seg
    hoy = date.today()

    def uno(t):
        if time.monotonic() > fin:
            return t, None
        cik = ciks.get(t.upper()) or ciks.get(t.upper().replace(".", "-"))
        if not cik:
            return t, None
        facts = _get_gz(SEC_FACTS.format(cik=cik))
        time.sleep(pausa)
        return t, (metricas(facts, hoy) if facts else None)
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        return {t: r for t, r in ex.map(uno, tickers) if r}


__all__ = ["serie_anual", "ejercicios", "piotroski", "altman_z2", "beneish_m", "metricas", "descargar"]
