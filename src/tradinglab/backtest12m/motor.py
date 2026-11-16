"""Backtest del método del agente B (ranking de small caps) desde 2014 hasta hoy.

Cada fin de trimestre (marzo, junio, septiembre, diciembre):
  1. Universo de AQUEL día: empresas de Nasdaq/NYSE con capitalización real de 300 M$ a 2.000 M$
     (precio sin ajustar por splits posteriores × acciones de la última portada presentada a la SEC),
     precio ≥ 3 $ y al menos 1 M$ negociado al día. Igual que el buscador de hoy.
  2. Métricas con lo que se SABÍA ese día: cuentas anuales presentadas a la SEC hasta esa fecha
     (sec_cuentas, sin mirar al futuro) y precios hasta ese mes.
  3. Nota con el MISMO código del ranking (oportunidades.puntuar). Los factores sin historia gratis
     (revisiones de analistas, directivos, catalizadores) quedan sin dato para todas por igual.
  4. Cartera: las 20 mejores a partes iguales durante 3 meses, con 0,5 % de coste por compra y por venta.
Referencias: IWM (Russell 2000, con dividendos) y la media de TODO el universo del backtest (misma muestra,
mismo sesgo: es la comparación más justa).
"""
from __future__ import annotations

import csv
import gzip
import json
import os
from calendar import monthrange
from datetime import date
from statistics import mean, median

from ..medio_plazo import oportunidades as op
from ..medio_plazo import sec_cuentas as sc

CAP_MIN, CAP_MAX, PRECIO_MIN, DOLARES_MIN = 300e6, 2000e6, 3.0, 1e6
TOP, COSTE = 20, 0.005
INICIO = (2014, 3)
FACTORES_PROBADOS = ["calidad", "crecimiento", "valoracion", "momentum", "solidez"]


# ------------------------------------------------------------------ utilidades de meses
def mes_mas(m: str, n: int) -> str:
    a, b = int(m[:4]), int(m[5:7]) - 1 + n
    return f"{a + b // 12:04d}-{b % 12 + 1:02d}"


def fin_de_mes(m: str) -> date:
    a, b = int(m[:4]), int(m[5:7])
    return date(a, b, monthrange(a, b)[1])


def trimestres(ultimo: str) -> list[str]:
    out, m = [], f"{INICIO[0]:04d}-{INICIO[1]:02d}"
    while m <= ultimo:
        out.append(m)
        m = mes_mas(m, 3)
    return out


# ------------------------------------------------------------------ carga
def cargar_precios(carpeta: str) -> dict[str, dict[str, tuple]]:
    pre: dict[str, dict[str, tuple]] = {}
    for n in sorted(os.listdir(carpeta)):
        if n.startswith("precios-") and n.endswith(".csv.gz"):
            with gzip.open(os.path.join(carpeta, n), "rt", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    pre.setdefault(r["ticker"], {})[r["mes"]] = (float(r["adj"]), float(r["real"]),
                                                                  float(r["dolares_dia"] or 0))
    return pre


def acciones_en(facts: dict, fecha: date, max_dias: int = 400) -> float | None:
    """Acciones en circulación de la última portada (10-K/10-Q) presentada hasta `fecha`."""
    f = facts.get("facts") or facts
    filas = ((((f.get("dei") or {}).get("EntityCommonStockSharesOutstanding") or {}).get("units") or {})
             .get("shares") or [])
    if not filas:
        filas = ((((f.get("us-gaap") or {}).get("CommonStockSharesOutstanding") or {}).get("units") or {})
                 .get("shares") or [])
    mejor = None
    for x in filas:
        pres = date.fromisoformat(x["filed"][:10])
        if pres <= fecha and (mejor is None or (x["filed"], x["end"]) > (mejor["filed"], mejor["end"])):
            mejor = x
    if not mejor or (fecha - date.fromisoformat(mejor["filed"][:10])).days > max_dias or not mejor["val"]:
        return None
    return float(mejor["val"])


def _ret(serie: dict, m0: str, m1: str) -> float | None:
    a, b = serie.get(m0), serie.get(m1)
    return b[0] / a[0] - 1 if a and b and a[0] > 0 else None


def ret_futuro(serie: dict, m: str, meses: int) -> tuple[float | None, bool]:
    """Rentabilidad de m a m+meses. Si deja de cotizar antes, se usa su último precio (y se marca)."""
    p0 = serie.get(m)
    if not p0 or p0[0] <= 0:
        return None, False
    for k in range(meses, 0, -1):
        p = serie.get(mes_mas(m, k))
        if p:
            return p[0] / p0[0] - 1, k < meses
    return None, False


def rasgos_precio(serie: dict, m: str, iwm: dict) -> dict:
    hist = [serie.get(mes_mas(m, -k)) for k in range(0, 12)]
    adj = [h[0] for h in hist if h]
    r = {"ret_12m_1m": _ret(serie, mes_mas(m, -12), mes_mas(m, -1)), "ret_6m": _ret(serie, mes_mas(m, -6), m)}
    ri = _ret(iwm, mes_mas(m, -6), m)
    r["fuerza_relativa_6m"] = r["ret_6m"] - ri if r["ret_6m"] is not None and ri is not None else None
    if len(adj) >= 10:
        r["sobre_ma200_pct"] = (adj[0] / mean(adj[:10]) - 1) * 100
        r["dist_max52_pct"] = (adj[0] / max(adj) - 1) * 100
        pico, caida = adj[-1], 0.0
        for v in reversed(adj):
            pico = max(pico, v)
            caida = min(caida, v / pico - 1)
        r["max_caida_1a_pct"] = caida * 100
    return r


def rasgos_cuentas(facts: dict, fecha: date, cap: float) -> dict | None:
    ej = sc.ejercicios(facts, fecha)
    if not ej:
        return None
    m = sc.metricas(facts, fecha, ej)
    if m.get("sec_cuentas_dias", 9999) > 550:
        return None
    e0, e1 = ej[0], (ej[1] if len(ej) > 1 else {})
    d = sc._div
    v0, ni, cfo = e0.get("ventas"), e0.get("beneficio_neto"), e0.get("flujo_operativo")
    caja = (e0.get("caja") or 0) + (e0.get("inversiones_cp") or 0) if e0.get("caja") is not None else None
    deuda = e0.get("deuda_lp")
    fcf = cfo - (e0.get("capex") or 0) if cfo is not None else None
    ebitda = e0["ebit"] + (e0.get("amortizacion") or 0) if e0.get("ebit") is not None else None
    ev = cap + (deuda or 0) - (caja or 0)
    s0, s1 = e0.get("acciones"), e1.get("acciones")
    r = {k: m.get(k) for k in ("f_score", "altman_z", "beneish_m", "rent_bruta_activos")}
    r.update({
        "margen_bruto": d(e0.get("beneficio_bruto"), v0), "margen_operativo": d(e0.get("ebit"), v0),
        "roe": d(ni, e0.get("patrimonio")) if (e0.get("patrimonio") or 0) > 0 else None,
        "roa": d(ni, e0.get("activos")),
        "rent_fcf_pct": fcf / cap * 100 if fcf is not None else None,
        "crec_ventas": d(v0, e1.get("ventas")) - 1 if d(v0, e1.get("ventas")) is not None else None,
        "per_futuro": cap / ni if ni and ni > 0 else None,      # PER pasado (no hay previsiones antiguas gratis)
        "ev_ventas": ev / v0 if v0 and v0 > 0 else None,
        "ev_ebitda": ev / ebitda if ebitda and ebitda > 0 else None,
        "caja": caja, "deuda": deuda, "fcf_4t": fcf,
        "dilucion_1a_pct": (s0 / s1 - 1) * 100 if s0 and s1 else None,
        "deuda_neta_ebitda": ((deuda or 0) - (caja or 0)) / ebitda if ebitda and ebitda > 0 else None,
        "fcf_trim_positivos": None,
    })
    return r


def construir_cohortes(carpeta: str) -> tuple[dict[str, list[dict]], dict, dict]:
    pre = cargar_precios(carpeta)
    iwm = pre.get("IWM", {})
    ultimo = max(iwm) if iwm else max(m for s in pre.values() for m in s)
    fechas = trimestres(ultimo)
    with open(os.path.join(carpeta, "tickers.csv"), encoding="utf-8") as fh:
        tick = {r["cik"]: r["ticker"] for r in csv.DictReader(fh)}
    cohortes: dict[str, list[dict]] = {m: [] for m in fechas}
    with gzip.open(os.path.join(carpeta, "cuentas.jsonl.gz"), "rt", encoding="utf-8") as fh:
        for linea in fh:
            x = json.loads(linea)
            t = tick.get(x["cik"])
            serie = pre.get(t)
            if not t or not serie:
                continue
            facts = {"facts": x["facts"]}
            for m in fechas:
                p = serie.get(m)
                if not p or p[1] < PRECIO_MIN or p[2] < DOLARES_MIN:
                    continue
                fecha = fin_de_mes(m)
                acc = acciones_en(facts, fecha)
                if not acc:
                    continue
                cap = p[1] * acc
                if not CAP_MIN <= cap <= CAP_MAX:
                    continue
                cu = rasgos_cuentas(facts, fecha, cap)
                if cu is None:
                    continue
                f = {"ticker": t, "precio": p[1], "capitalizacion": cap, "sector": None, "analistas": 10} | cu
                f |= rasgos_precio(serie, m, iwm)
                cohortes[m].append(f)
    return cohortes, pre, {"ultimo_mes": ultimo, "fechas": fechas}


# ------------------------------------------------------------------ evaluación
def _spearman(a: list[float], b: list[float]) -> float | None:
    from ..medio_plazo.validacion import spearman
    return spearman(a, b)


def _cagr(total: float, anios: float) -> float:
    return (1 + total) ** (1 / anios) - 1 if anios > 0 and total > -1 else -1.0


def _max_caida(curva: list[float]) -> float:
    pico, peor = curva[0], 0.0
    for v in curva:
        pico = max(pico, v)
        peor = min(peor, v / pico - 1)
    return peor


def simular(cohortes: dict, pre: dict, clave, top: int = TOP, ultimo: str | None = None) -> dict:
    """Cartera trimestral con las `top` mejores según clave(fila) (mayor = mejor)."""
    iwm = pre.get("IWM", {})
    curva, curva_u, curva_i = [1.0], [1.0], [1.0]
    anterior: set = set()
    trimestres_ok = gana_u = gana_i = 0
    for m, filas in sorted(cohortes.items()):
        fin = mes_mas(m, 3)
        if ultimo and fin > ultimo:
            break
        validas = [f for f in filas if clave(f) is not None]
        if len(validas) < top * 3 or not iwm.get(fin) or not iwm.get(m):
            continue
        elegidas = sorted(validas, key=clave, reverse=True)[:top]
        rs = [ret_futuro(pre[f["ticker"]], m, 3)[0] for f in elegidas]
        rs = [r for r in rs if r is not None]
        ru = [r for r in (ret_futuro(pre[f["ticker"]], m, 3)[0] for f in filas) if r is not None]
        nuevas = {f["ticker"] for f in elegidas}
        rotacion = len(nuevas - anterior) / top
        anterior = nuevas
        r = mean(rs) - rotacion * 2 * COSTE
        ri = _ret(iwm, m, fin)
        curva.append(curva[-1] * (1 + r))
        curva_u.append(curva_u[-1] * (1 + mean(ru)))
        curva_i.append(curva_i[-1] * (1 + ri))
        trimestres_ok += 1
        gana_u += r > mean(ru)
        gana_i += r > ri
    anios = trimestres_ok / 4
    out = {"trimestres": trimestres_ok, "anios": anios}
    for nombre, c in (("estrategia", curva), ("universo", curva_u), ("iwm", curva_i)):
        out[nombre] = {"total_pct": (c[-1] - 1) * 100, "anual_pct": _cagr(c[-1] - 1, anios) * 100,
                       "max_caida_pct": _max_caida(c) * 100}
    out["pct_trimestres_gana_universo"] = 100 * gana_u / trimestres_ok if trimestres_ok else None
    out["pct_trimestres_gana_iwm"] = 100 * gana_i / trimestres_ok if trimestres_ok else None
    return out


def auditar_cobertura_cartera(cohortes: dict, pre: dict, ultimo: str, top: int = TOP) -> dict:
    """Mide cuántos precios FINALES faltan en la cartera simulada, sin imputar retornos.

    Este indicador NO detecta los tickers excluidos de la fuente histórica:
    una cobertura del 100 % NO demuestra ausencia de sesgo de supervivencia.
    """
    iwm = pre.get("IWM", {})
    periodos = posiciones = sin_fin = con_precio_anterior = 0
    for m, filas in sorted(cohortes.items()):
        fin = mes_mas(m, 3)
        if fin > ultimo or m not in iwm or fin not in iwm:
            continue
        validas = [f for f in filas if f.get("nota") is not None]
        if len(validas) < top * 3:
            continue
        periodos += 1
        for f in sorted(validas, key=lambda x: x["nota"], reverse=True)[:top]:
            posiciones += 1
            serie = pre.get(f["ticker"], {})
            if fin not in serie:
                sin_fin += 1
                if any(mes_mas(m, k) in serie for k in (1, 2)):
                    con_precio_anterior += 1
    return {
        "trimestres_examinados": periodos,
        "posiciones_examinadas": posiciones,
        "sin_precio_fin_trimestre": sin_fin,
        "con_ultimo_precio_intermedio": con_precio_anterior,
        "pct_fin_incompleto": round(100 * sin_fin / posiciones, 2) if posiciones else None,
        "validacion_financiera": "NO VALIDADA: faltan universo historico completo, delistings y OOS",
    }


def estudio_12m(cohortes: dict, pre: dict, ultimo: str) -> dict:
    """Para cada cohorte con 12 meses de futuro: rentabilidad media de las 20/50 mejores frente al universo,
    y correlación de rangos (Spearman) entre nota/factor y rentabilidad a 12 meses."""
    filas_out, ic = [], {k: [] for k in ["nota"] + FACTORES_PROBADOS}
    quint: list[list[float]] = [[] for _ in range(5)]     # quintiles de nota: rentabilidad frente al universo
    for m, filas in sorted(cohortes.items()):
        if mes_mas(m, 12) > ultimo or len(filas) < 60:
            continue
        rets = [ret_futuro(pre[f["ticker"]], m, 12)[0] for f in filas]
        par = [(f, r) for f, r in zip(filas, rets) if r is not None]
        orden = sorted(par, key=lambda x: x[0]["nota"], reverse=True)
        u = [r for _, r in par]
        q = max(1, len(orden) // 5)
        for i in range(5):
            quint[i].append(mean(r for _, r in orden[i * q:(i + 1) * q if i < 4 else None]) - mean(u))
        filas_out.append({"fecha": m, "empresas": len(par), "top20_pct": mean(r for _, r in orden[:20]) * 100,
                          "top50_pct": mean(r for _, r in orden[:50]) * 100, "universo_pct": mean(u) * 100,
                          "mediana_pct": median(u) * 100, "iwm_pct": (_ret(pre.get("IWM", {}), m, mes_mas(m, 12)) or 0) * 100})
        for k in ic:
            pares = [((f["nota"] if k == "nota" else f["factores"].get(k)), r) for f, r in par]
            pares = [(a, b) for a, b in pares if a is not None]
            if len(pares) >= 30:
                s = _spearman([a for a, _ in pares], [b for _, b in pares])
                if s is not None:
                    ic[k].append(s)
    resumen = {k: {"media": mean(v), "pct_positivas": 100 * sum(x > 0 for x in v) / len(v), "n": len(v)}
               for k, v in ic.items() if v}
    quintiles = [{"quintil": i + 1, "exceso_12m_pct": mean(v) * 100,
                  "pct_cohortes_gana": 100 * sum(x > 0 for x in v) / len(v)} for i, v in enumerate(quint) if v]
    return {"cohortes": filas_out, "correlacion": resumen, "quintiles": quintiles}


def estudio_pelotazos(cohortes: dict, pre: dict, ultimo: str, x: float = 3.0, meses: int = 36) -> dict:
    """¿Cuántas small caps multiplicaron por x en `meses`? ¿Las detectaba la nota? ¿Cómo eran antes?"""
    total = hits = top_tot = top_hits = 0
    perfil_si: dict[str, list] = {k: [] for k in FACTORES_PROBADOS + ["nota"]}
    perfil_no: dict[str, list] = {k: [] for k in FACTORES_PROBADOS + ["nota"]}
    ejemplos = []
    for m, filas in sorted(cohortes.items()):
        if mes_mas(m, meses) > ultimo:
            continue
        orden = sorted(filas, key=lambda f: f["nota"], reverse=True)
        decil = {f["ticker"] for f in orden[:max(1, len(orden) // 10)]}
        for f in filas:
            r, _ = ret_futuro(pre[f["ticker"]], m, meses)
            if r is None:
                continue
            total += 1
            es = r + 1 >= x
            hits += es
            if f["ticker"] in decil:
                top_tot += 1
                top_hits += es
            dest = perfil_si if es else perfil_no
            dest["nota"].append(f["nota"])
            for k in FACTORES_PROBADOS:
                if f["factores"].get(k) is not None:
                    dest[k].append(f["factores"][k])
            if es:
                ejemplos.append({"ticker": f["ticker"], "desde": m, "multiplica": round(r + 1, 1),
                                 "nota": f["nota"], "puesto": orden.index(f) + 1, "de": len(orden)})
    # una fila por empresa (su mejor subida) para no repetir la misma 8 trimestres
    mejor: dict[str, dict] = {}
    for e in ejemplos:
        if e["ticker"] not in mejor or e["multiplica"] > mejor[e["ticker"]]["multiplica"]:
            mejor[e["ticker"]] = e
    return {
        "x": x, "meses": meses, "casos": total, "pelotazos": hits,
        "tasa_pct": 100 * hits / total if total else None,
        "tasa_decil_top_pct": 100 * top_hits / top_tot if top_tot else None,
        "empresas_distintas": len(mejor),
        "perfil": {k: {"mediana_pelotazos": median(perfil_si[k]) if perfil_si[k] else None,
                       "mediana_resto": median(perfil_no[k]) if perfil_no[k] else None} for k in perfil_si},
        "ejemplos": sorted(mejor.values(), key=lambda e: -e["multiplica"])[:15],
    }


def supervivencia(carpeta: str, activos_min: float = 1e8, activos_max: float = 5e9) -> dict:
    """% de empresas (por tamaño de activos, aproximación a small cap) que dejan de presentar cuentas cada año."""
    p = os.path.join(carpeta, "supervivencia.json.gz")
    if not os.path.exists(p):
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        d = json.load(fh)
    por_anio = {}
    for a in range(2014, 2025):
        sa = str(a)
        grupo = [v for v in d.values() if activos_min <= v["anios"].get(sa, 0) <= activos_max]
        if not grupo:
            continue
        desap = [v for v in grupo if not v["cotiza_hoy"]
                 and not any(int(y) in (a + 1, a + 2) for y in v["anios"])]
        por_anio[sa] = {"empresas": len(grupo), "desaparecen_pct": 100 * len(desap) / len(grupo)}
    tasas = [v["desaparecen_pct"] for v in por_anio.values()]
    return {"por_anio": por_anio, "media_anual_pct": mean(tasas) if tasas else None}


def ejecutar(carpeta: str, salida: str) -> dict:
    cohortes, pre, meta = construir_cohortes(carpeta)
    for filas in cohortes.values():
        if filas:
            op.puntuar(filas)
    ultimo = meta["ultimo_mes"]
    res = {"meta": meta | {"empresas_por_trimestre": {m: len(f) for m, f in cohortes.items()},
                           "auditoria_cobertura": auditar_cobertura_cartera(cohortes, pre, ultimo)}}
    res["cartera"] = {"nota": simular(cohortes, pre, lambda f: f["nota"], ultimo=ultimo),
                      "nota_50": simular(cohortes, pre, lambda f: f["nota"], top=50, ultimo=ultimo),
                      "nota_100": simular(cohortes, pre, lambda f: f["nota"], top=100, ultimo=ultimo)}
    for k in FACTORES_PROBADOS:
        res["cartera"][k] = simular(cohortes, pre, lambda f, k=k: f["factores"].get(k), ultimo=ultimo)
    res["cartera"]["f_score"] = simular(cohortes, pre, lambda f: (f["f_score"] + f["factores"]["valoracion"] / 1000)
                                        if f.get("f_score") is not None and f["factores"].get("valoracion") is not None
                                        else None, ultimo=ultimo)
    res["doce_meses"] = estudio_12m(cohortes, pre, ultimo)
    res["pelotazos"] = estudio_pelotazos(cohortes, pre, ultimo)
    res["supervivencia"] = supervivencia(carpeta)
    os.makedirs(salida, exist_ok=True)
    with open(os.path.join(salida, "resultados.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    from .informe import escribir
    escribir(res, os.path.join(salida, f"INFORME-{date.today().isoformat()}.md"))
    return res


if __name__ == "__main__":
    import sys
    ejecutar(sys.argv[1] if len(sys.argv) > 1 else "datos_bt",
             sys.argv[2] if len(sys.argv) > 2 else os.path.join("investigacion", "backtest-12m"))
