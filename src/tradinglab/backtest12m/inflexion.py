"""Detector de «punto de inflexión» (Paso 8): ¿en qué empresa acaba de CAMBIAR algo a mejor?

Seis señales, todas con lo que se SABÍA aquel día (cuentas trimestrales 10-Q/10-K de la SEC y compras de
directivos del Form 4, por fecha de presentación):
  1. aceleración: las ventas crecen (frente al mismo trimestre del año anterior) más deprisa que el trimestre previo;
  2. margen bruto mejor que hace un año;
  3. gastos generales crecen menos que las ventas;
  4. caja: el negocio genera caja en el trimestre, o tiene caja para 18+ meses al ritmo de gasto actual;
  5. poca dilución: acciones +10 % o menos en un año;
  6. directivos: 2 o más compran con su dinero en el mercado en 30 días (Form 4, código P).

La prueba (decidida ANTES de mirar, revisión del 16-nov-2026): en cada trimestre se toma el 10 % con más señales
(desempate: la aceleración). Medida: qué % multiplica x3 en 3 años. Listón: 12 % o más y al menos el doble de la
base del mismo periodo. Se elige la variante con 2014-2020 y se COMPRUEBA en 2021 en adelante (datos no vistos).
"""
from __future__ import annotations

import csv
import gzip
import os
from datetime import date, timedelta

from ..medio_plazo import sec_cuentas as sc

FORMS = set(sc.FORMULARIOS_ANUALES) | {"10-Q", "10-Q/A"}
FLUJOS = ("ventas", "beneficio_bruto", "coste_ventas", "gastos_generales", "ebit", "flujo_operativo")
SENALES = ["aceleracion", "margen", "gastos", "caja", "dilucion", "directivos"]
VARIANTES = {   # pesos de cada señal; se elige con 2014-2020
    "seis_senales": {s: 1 for s in SENALES},
    "solo_cuentas": {s: 1 for s in SENALES if s != "directivos"},
    "ventas_y_margen_doble": {s: (2 if s in ("aceleracion", "margen") else 1) for s in SENALES},
}
CORTE_ENTRENO = "2020-12"
LISTON_PCT = 12.0


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


# ------------------------------------------------------------------ cuentas trimestrales
def preparar(facts: dict) -> dict:
    """Filas de cada concepto, una vez por empresa: {concepto: [(presentado, inicio|None, fin, valor)]}.
    Une los nombres alternativos de cada concepto (las empresas cambian de etiqueta con los años)."""
    gaap = (facts.get("facts") or facts).get("us-gaap") or {}
    out: dict[str, list] = {}
    for c in FLUJOS + ("caja", "inversiones_cp"):
        filas, vistas = [], set()
        for nombre in sc.CONCEPTOS[c]:
            u = (gaap.get(nombre) or {}).get("units") or {}
            nuevas = []
            for x in u.get("USD") or []:
                if x.get("form") not in FORMS or not x.get("filed") or not x.get("end"):
                    continue
                k = (x.get("start"), x["end"])
                if k in vistas:
                    continue
                nuevas.append((_d(x["filed"]), _d(x["start"]) if x.get("start") else None, _d(x["end"]), float(x["val"])))
            vistas |= {(None if f[1] is None else f[1].isoformat(), f[2].isoformat()) for f in nuevas}
            filas += nuevas
        out[c] = filas
    return out


def trimestral(filas: list, fecha: date) -> dict[date, float]:
    """{fin de trimestre: valor de 3 meses} con lo presentado hasta `fecha`. Los acumulados (6, 9, 12 meses) se
    restan: así salen el 4.º trimestre y los flujos de caja (que la SEC solo da acumulados)."""
    per: dict[tuple, tuple] = {}
    for pres, ini, fin, v in filas:
        if pres > fecha or ini is None:
            continue
        k = (ini, fin)
        if k not in per or pres >= per[k][0]:
            per[k] = (pres, v)
    q: dict[date, float] = {}
    for (ini, fin), (_, v) in per.items():
        if 80 <= (fin - ini).days <= 100:
            q[fin] = v
    por_ini: dict[date, list] = {}
    for (ini, fin), (_, v) in per.items():
        por_ini.setdefault(ini, []).append((fin, v))
    for (ini, fin), (_, v) in per.items():
        n = round((fin - ini).days / 91.3)
        if fin in q or not 2 <= n <= 4 or abs((fin - ini).days - 91.3 * n) > 20:
            continue
        for f2, v2 in por_ini[ini]:
            if round((f2 - ini).days / 91.3) == n - 1 and 80 <= (fin - f2).days <= 100:
                q[fin] = v - v2
                break
    return q


def _hace(q: dict[date, float], fin: date, dias: int) -> float | None:
    for k, v in q.items():
        if abs((fin - k).days - dias) <= 20:
            return v
    return None


def _crec(a, b):
    return a / b - 1 if a is not None and b is not None and b > 0 else None


def compras_directivos(compras: list, fecha: date, ventana: int = 90, junta: int = 30) -> int:
    """Máximo de directivos DISTINTOS que compraron en 30 días, con Form 4 presentados en los 90 días previos."""
    vis = sorted((op, dueno) for pres, op, dueno in compras if fecha - timedelta(days=ventana) < pres <= fecha)
    mejor = 0
    for i, (d0, _) in enumerate(vis):
        mejor = max(mejor, len({du for d, du in vis[i:] if (d - d0).days <= junta}))
    return mejor


def senales(prep: dict, fecha: date, acciones_hoy: float | None, acciones_hace_1a: float | None,
            compras: list | None = None) -> dict:
    q = {c: trimestral(prep[c], fecha) for c in FLUJOS}
    ven = q["ventas"]
    r: dict = {s: False for s in SENALES} | {"acel_pp": None, "datos_trimestrales": False}
    if acciones_hoy and acciones_hace_1a:
        r["dilucion"] = acciones_hoy / acciones_hace_1a - 1 <= 0.10
    r["directivos"] = compras_directivos(compras or [], fecha) >= 2
    if not ven:
        return r
    f0 = max(ven)
    if (fecha - f0).days > 200:
        return r
    r["datos_trimestrales"] = True
    f1 = next((k for k in ven if 80 <= (f0 - k).days <= 100), None)
    g0 = _crec(ven[f0], _hace(ven, f0, 365))
    g1 = _crec(ven[f1], _hace(ven, f1, 365)) if f1 else None
    if g0 is not None and g1 is not None:
        r["acel_pp"] = round((g0 - g1) * 100, 1)
        r["aceleracion"] = g0 > 0 and g0 > g1

    def bruto(fin):
        b = q["beneficio_bruto"].get(fin)
        if b is None and q["coste_ventas"].get(fin) is not None and ven.get(fin) is not None:
            b = ven[fin] - q["coste_ventas"][fin]
        return b
    fa = next((k for k in ven if abs((f0 - k).days - 365) <= 20), None)
    if fa and ven.get(fa):
        b0, ba = bruto(f0), bruto(fa)
        if b0 is not None and ba is not None and ven[f0]:
            r["margen"] = b0 / ven[f0] > ba / ven[fa]
        gg = q["gastos_generales"]
        if gg.get(f0) is not None and _hace(gg, f0, 365) and g0 is not None:
            c = _crec(gg[f0], _hace(gg, f0, 365))
            r["gastos"] = c is not None and c < g0
        elif q["ebit"].get(f0) is not None and q["ebit"].get(fa) is not None and g0 is not None:
            c = _crec(ven[f0] - q["ebit"][f0], ven[fa] - q["ebit"][fa])
            r["gastos"] = c is not None and c < g0
    cfo = q["flujo_operativo"].get(f0)
    if cfo is not None:
        if cfo > 0:
            r["caja"] = True
        else:
            bal = [(fin, v) for pres, ini, fin, v in prep["caja"] if pres <= fecha and ini is None]
            inv = {fin: v for pres, ini, fin, v in prep["inversiones_cp"] if pres <= fecha and ini is None}
            if bal:
                fin, caja = max(bal)
                r["caja"] = caja + inv.get(fin, 0) >= -cfo * 6        # 6 trimestres = 18 meses
    return r


def puntos(f: dict, pesos: dict) -> tuple:
    s = f.get("inflexion") or {}
    return (sum(p for k, p in pesos.items() if s.get(k)), s.get("acel_pp") if s.get("acel_pp") is not None else -1e9)


# ------------------------------------------------------------------ directivos (Form 4 de la SEC)
def cargar_directivos(carpeta: str) -> dict[str, list]:
    p = os.path.join(carpeta, "directivos.csv.gz")
    out: dict[str, list] = {}
    if not os.path.exists(p):
        return out
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out.setdefault(r["cik"], []).append((_d(r["presentado"]), _d(r["fecha_op"]), r["dueno"]))
            except ValueError:
                continue
    return out


# ------------------------------------------------------------------ estudio
def estudio(cohortes: dict, pre: dict, ultimo: str, x: float = 3.0, meses: int = 36) -> dict:
    from .motor import mes_mas, ret_futuro

    def medir(desde: str | None, hasta: str | None, pesos: dict | None) -> dict:
        tot = hits = d_tot = d_hits = d_hund = 0
        rets, d_rets = [], []
        for m, filas in sorted(cohortes.items()):
            if mes_mas(m, meses) > ultimo or (desde and m < desde) or (hasta and m > hasta):
                continue
            con = [f for f in filas if (f.get("inflexion") or {}).get("datos_trimestrales")]
            if not con:
                continue
            dec = set()
            if pesos:
                orden = sorted(con, key=lambda f: puntos(f, pesos), reverse=True)
                dec = {f["ticker"] for f in orden[:max(1, len(orden) // 10)]}
            for f in con:
                r, _ = ret_futuro(pre[f["ticker"]], m, meses)
                if r is None:
                    continue
                tot += 1
                hits += r + 1 >= x
                rets.append(r)
                if f["ticker"] in dec:
                    d_tot += 1
                    d_hits += r + 1 >= x
                    d_hund += r <= -0.5
                    d_rets.append(r)
        med = lambda v: round(100 * sorted(v)[len(v) // 2], 1) if v else None  # noqa: E731
        return {"casos": tot, "base_pct": round(100 * hits / tot, 2) if tot else None,
                "decil_casos": d_tot, "decil_pct": round(100 * d_hits / d_tot, 2) if d_tot else None,
                "decil_hunden_pct": round(100 * d_hund / d_tot, 1) if d_tot else None,
                "mediana_todas_pct": med(rets), "mediana_decil_pct": med(d_rets)}

    entreno = {v: medir(None, CORTE_ENTRENO, p) for v, p in VARIANTES.items()}
    elegida = max(entreno, key=lambda v: entreno[v]["decil_pct"] or -1)
    prueba = {v: medir(mes_mas(CORTE_ENTRENO, 1), None, p) for v, p in VARIANTES.items()}
    pr = prueba[elegida]
    pasa = bool(pr["decil_pct"] is not None and pr["base_pct"] and pr["decil_pct"] >= LISTON_PCT
                and pr["decil_pct"] >= 2 * pr["base_pct"])
    # ¿qué señal, sola, se asocia más a los x3? (todo el periodo, informativo)
    por_senal = {}
    for s in SENALES:
        si = no = si_h = no_h = 0
        for m, filas in cohortes.items():
            if mes_mas(m, meses) > ultimo:
                continue
            for f in filas:
                inf = f.get("inflexion") or {}
                if not inf.get("datos_trimestrales"):
                    continue
                r, _ = ret_futuro(pre[f["ticker"]], m, meses)
                if r is None:
                    continue
                if inf.get(s):
                    si += 1
                    si_h += r + 1 >= x
                else:
                    no += 1
                    no_h += r + 1 >= x
        por_senal[s] = {"con_senal_pct": round(100 * si_h / si, 2) if si else None, "casos_con": si,
                        "sin_senal_pct": round(100 * no_h / no, 2) if no else None}
    return {"x": x, "meses": meses, "liston_pct": LISTON_PCT, "corte_entreno": CORTE_ENTRENO,
            "entreno": entreno, "elegida": elegida, "prueba": prueba, "pasa": pasa, "por_senal": por_senal}


NOMBRES = {"aceleracion": "Ventas que aceleran", "margen": "Margen bruto mejor que hace un año",
           "gastos": "Gastos que crecen menos que las ventas", "caja": "Genera caja o tiene para 18+ meses",
           "dilucion": "Poca dilución (acciones +10 % o menos en un año)",
           "directivos": "2+ directivos comprando en 30 días"}


def informe(res: dict, ruta: str, meta: dict) -> str:
    e = res["elegida"]
    tr, pr = res["entreno"][e], res["prueba"][e]
    f = lambda v: "—" if v is None else f"{v:.1f} %"  # noqa: E731
    veredicto = ("**PASA el listón**: en años que el detector no había visto, encontró al menos el doble de x3 que la media."
                 if res["pasa"] else
                 "**NO PASA el listón**: en los años de comprobación no encontró el doble de x3 que la media. "
                 "No se usa para elegir acciones; queda solo como dato informativo.")
    L = ["# Detector de punto de inflexión: ¿encuentra las x3?\n", "**Resumen en 5 líneas**\n",
         f"1. Veredicto: {veredicto}",
         f"2. Comprobación ({res['corte_entreno'][:4]}+1 en adelante): del 10 % con más señales, **{f(pr['decil_pct'])}** "
         f"multiplicó x3 en 3 años; la media de todas fue {f(pr['base_pct'])}. Listón: {res['liston_pct']:.0f} % y el doble de la media.",
         f"3. Ajuste (2014-{res['corte_entreno'][:4]}): {f(tr['decil_pct'])} frente a {f(tr['base_pct'])} de media "
         f"(variante elegida: «{e.replace('_', ' ')}»).",
         f"4. Riesgo: del 10 % elegido, {f(pr['decil_hunden_pct'])} perdió la mitad o más. Mediana a 3 años: "
         f"{f(pr['mediana_decil_pct'])} (todas: {f(pr['mediana_todas_pct'])}).",
         "5. Aun cuando funcione, la mayoría de las elegidas NO triplica: se juega con una cesta de 10-15 posiciones pequeñas.\n",
         "## Qué mira el detector (6 señales, con datos oficiales de la SEC de aquel día)\n"]
    L += [f"- {NOMBRES[s]}" for s in SENALES]
    L += ["\n«x3» = la acción vale 3 veces más (o más) a los 3 años, con dividendos. «Base» = % de x3 entre TODAS las "
          "small caps de ese trimestre. «Decil» = el 10 % con más señales.\n",
          "## Resultado por variante\n", "| Variante | Ajuste 2014-2020 | Comprobación 2021+ | Base comprobación |",
          "|---|---|---|---|"]
    for v in VARIANTES:
        L.append(f"| {v.replace('_', ' ')}{' (elegida)' if v == e else ''} | {f(res['entreno'][v]['decil_pct'])} | "
                 f"{f(res['prueba'][v]['decil_pct'])} | {f(res['prueba'][v]['base_pct'])} |")
    L += ["\n## Cada señal por separado (todo el periodo, solo informativo)\n",
          "| Señal | % de x3 con la señal | sin la señal | casos con señal |", "|---|---|---|---|"]
    for s, d in res["por_senal"].items():
        L.append(f"| {NOMBRES[s]} | {f(d['con_senal_pct'])} | {f(d['sin_senal_pct'])} | {d['casos_con']} |")
    L += [f"\nCasos: {tr['casos']} (ajuste) y {pr['casos']} (comprobación); cada caso es una empresa en un trimestre. "
          f"Datos hasta {meta.get('ultimo_mes')}.\n",
          "## Límites\n",
          "- Solo empresas que cotizan hoy (las que quebraron no están): las tasas de x3 salen algo infladas, para "
          "todas por igual.",
          "- La comprobación solo llega a trimestres con 3 años ya cumplidos (hasta ~3 años antes de hoy): pocos años.",
          "- Una misma empresa cuenta en varios trimestres seguidos.",
          "- Pasado no es futuro. Esto es un filtro para estudiar, no una orden de compra.\n",
          "Fuentes: SEC companyfacts (10-Q/10-K por fecha de presentación), SEC Insider Transactions Data Sets "
          "(Form 4), precios de Yahoo. Código: `src/tradinglab/backtest12m/inflexion.py`."]
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return ruta
