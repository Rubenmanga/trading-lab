"""¿Acierta el ranking? Comprobación honesta del buscador (idea de alphalens, Apache-2.0: medir si una nota
predice la rentabilidad futura).

Cada día (si el ranking está completo) se guarda una "foto" pequeña en investigacion/historico/AAAA-MM-DD.csv
con el puesto, la nota y el precio de TODAS las empresas puntuadas. Días o meses después se compara:
  - rentabilidad media de las 20 y 50 mejores de aquella foto, frente a la mediana de todas;
  - correlación de rangos (Spearman) entre nota y rentabilidad: >0 = las notas altas suben más.
Con pocas semanas de historia el resultado es puro ruido: el informe lo dice claramente.
"""
from __future__ import annotations

import csv
import os
from datetime import date
from statistics import mean, median

from ..common.config import ruta

PLAZOS = [(7, "1 semana"), (30, "1 mes"), (91, "3 meses"), (182, "6 meses"), (365, "12 meses")]


def carpeta() -> str:
    return str(ruta("investigacion", "historico"))


def guardar_foto(filas: list[dict], hoy: date | None = None, dir_: str | None = None) -> str | None:
    hoy = hoy or date.today()
    dir_ = dir_ or carpeta()
    os.makedirs(dir_, exist_ok=True)
    p = os.path.join(dir_, f"{hoy.isoformat()}.csv")
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["puesto", "ticker", "nota", "precio", "carril"])
        for f in filas:
            if f.get("precio"):
                w.writerow([f.get("puesto"), f["ticker"], f.get("nota"), round(float(f["precio"]), 4), f.get("carril")])
    return p


def leer_foto(p: str) -> list[dict]:
    with open(p, encoding="utf-8") as fh:
        return [dict(puesto=int(r["puesto"]), ticker=r["ticker"], nota=float(r["nota"]), precio=float(r["precio"]))
                for r in csv.DictReader(fh) if r.get("precio")]


def _rangos(v: list[float]) -> list[float]:
    orden = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and v[orden[j + 1]] == v[orden[i]]:
            j += 1
        for k in range(i, j + 1):
            r[orden[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 10:
        return None
    ra, rb = _rangos(a), _rangos(b)
    ma, mb = mean(ra), mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 3) if den else None


def comparar(foto: list[dict], precios_hoy: dict[str, float]) -> dict | None:
    """Rentabilidad desde la foto hasta hoy. Solo empresas que siguen teniendo precio hoy."""
    # La cohorte es la foto original: se fija por puesto ANTES de mirar quién sigue con precio.
    orig = sorted((f for f in foto if f["precio"] > 0), key=lambda f: f["puesto"])
    con = {f["ticker"] for f in orig if precios_hoy.get(f["ticker"])}
    if len(con) < 30:
        return None
    ret = lambda f: (precios_hoy[f["ticker"]] / f["precio"] - 1) * 100  # noqa: E731
    filas = [(f, ret(f)) for f in orig if f["ticker"] in con]
    rets = [r for _, r in filas]
    sin_precio = len(orig) - len(con)

    def top(n):
        r = [ret(f) for f in orig[:n] if f["ticker"] in con]
        return round(mean(r), 2) if r else None
    med = round(median(rets), 2)
    t20, t50 = top(20), top(50)
    ventaja = lambda t: round(t - med, 2) if t is not None else None  # noqa: E731
    return dict(empresas=len(filas), sin_precio=sin_precio, top20=t20, top50=t50, mediana_todas=med,
                ventaja_top20=ventaja(t20), ventaja_top50=ventaja(t50),
                aciertos_top20=sum(1 for f in orig[:20] if f["ticker"] in con and ret(f) > med),
                correlacion=spearman([f["nota"] for f, _ in filas], rets))


def validar(filas_hoy: list[dict], hoy: date | None = None, dir_: str | None = None) -> dict:
    hoy = hoy or date.today()
    dir_ = dir_ or carpeta()
    precios = {f["ticker"]: float(f["precio"]) for f in filas_hoy if f.get("precio")}
    fotos = []
    if os.path.isdir(dir_):
        for n in sorted(os.listdir(dir_)):
            try:
                fotos.append((date.fromisoformat(n[:10]), os.path.join(dir_, n)))
            except ValueError:
                continue
    out = dict(fotos=len(fotos), primera=fotos[0][0].isoformat() if fotos else None, plazos=[])
    for dias, nombre in PLAZOS:
        cand = [(d, p) for d, p in fotos if (hoy - d).days >= dias]
        if not cand:
            continue
        d, p = max(cand)   # la foto más reciente que tenga al menos ese plazo
        if (hoy - d).days > dias * 1.5 + 3:
            continue
        r = comparar(leer_foto(p), precios)
        if r:
            out["plazos"].append(dict(plazo=nombre, desde=d.isoformat(), dias=(hoy - d).days, **r))
    return out


def informe(v: dict) -> str:
    l = ["# ¿Acierta el ranking?", "",
         "_Comprobación automática del buscador de oportunidades. Se actualiza cada día._", ""]
    if not v["plazos"]:
        l += ["**Todavía no hay historia suficiente.** El sistema guarda una foto del ranking cada día "
              f"(fotos guardadas: {v['fotos']}). En una semana saldrá la primera comparación, y a partir de "
              "3-6 meses empezará a significar algo.", ""]
        return "\n".join(l)
    mejor = v["plazos"][-1]
    l += [f"- **Plazo más largo medido: {mejor['plazo']}** (desde la foto del {mejor['desde']}).",
          f"- Las 20 mejores de entonces: **{(mejor['top20'] or 0):+.1f} %** frente a {mejor['mediana_todas']:+.1f} % de la "
          f"empresa mediana (ventaja {(mejor['ventaja_top20'] or 0):+.1f} puntos).",
          f"- {mejor['aciertos_top20']} de las 20 lo hicieron mejor que la mediana.",
          f"- Empresas de la foto que ya no tienen precio (no cuentan en la media, pueden haber caído mucho): "
          f"**{mejor.get('sin_precio', 0)}**.",
          f"- Correlación nota-rentabilidad: {mejor['correlacion'] if mejor['correlacion'] is not None else '—'} "
          "(0 = la nota no predice nada; 0,05-0,10 ya es útil en bolsa).",
          "- **Ojo:** con menos de 3-6 meses de historia esto es casi todo azar. No cambies pesos por una semana mala.",
          "", "| Plazo | Desde | Empresas | Top 20 | Top 50 | Mediana | Ventaja top 20 | Aciertos top 20 | Correlación |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in v["plazos"]:
        l.append(f"| {p['plazo']} | {p['desde']} | {p['empresas']} | {(p['top20'] or 0):+.1f} % | {(p['top50'] or 0):+.1f} % | "
                 f"{p['mediana_todas']:+.1f} % | {(p['ventaja_top20'] or 0):+.1f} | {p['aciertos_top20']}/20 | "
                 f"{p['correlacion'] if p['correlacion'] is not None else '—'} |")
    l += ["", "Las empresas que ya no cotizan o salen del rango no se cuentan (puede inflar un poco el resultado)."]
    return "\n".join(l) + "\n"


def actualizar(res: dict) -> dict:
    """Guarda la foto de hoy (si el ranking está completo) y escribe investigacion/validacion.md."""
    filas = res["filas"]
    v = validar(filas)
    if not res.get("provisional"):
        guardar_foto(filas)
    with open(ruta("investigacion", "validacion.md"), "w", encoding="utf-8") as fh:
        fh.write(informe(v))
    return v
