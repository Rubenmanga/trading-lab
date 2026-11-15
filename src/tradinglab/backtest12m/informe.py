"""Informe en Markdown (para el móvil) del backtest del agente B."""
from __future__ import annotations

NOMBRES = {"nota": "Nota completa del ranking", "nota_50": "Nota: las 50 mejores", "nota_100": "Nota: las 100 mejores", "calidad": "Solo calidad", "crecimiento": "Solo crecimiento",
           "valoracion": "Solo valoración (barata)", "momentum": "Solo momentum (tendencia)",
           "solidez": "Solo solidez (balance)", "f_score": "Piotroski F alto (y barata para desempatar)"}


def _p(v, dec=1, signo=True):
    if v is None:
        return "—"
    return f"{v:+.{dec}f} %" if signo else f"{v:.{dec}f} %"


def escribir(res: dict, ruta: str) -> str:
    c = res["cartera"]
    n = c["nota"]
    ic = res["doce_meses"]["correlacion"]
    pel = res["pelotazos"]
    sup = res.get("supervivencia") or {}
    tasa_sup = sup.get("media_anual_pct")
    exceso = n["estrategia"]["anual_pct"] - n["universo"]["anual_pct"]
    exceso_iwm = n["estrategia"]["anual_pct"] - n["iwm"]["anual_pct"]
    mejor = max((k for k in c if not k.startswith("nota")), key=lambda k: c[k]["estrategia"]["anual_pct"])
    veredicto = ("**sí aporta**" if exceso > 2 and (ic.get("nota", {}).get("pct_positivas") or 0) >= 60
                 else "**aporta poco o nada**" if exceso < 1 else "**aporta algo, pero poco seguro**")
    L = []
    L.append("# Backtest del agente B (small caps a 12 meses)\n")
    L.append("**Resumen en 5 líneas**\n")
    L.append(f"1. Desde {res['meta']['fechas'][0]} hasta {res['meta']['ultimo_mes']}, comprar cada trimestre las 20 "
             f"mejores según la nota habría dado **{_p(n['estrategia']['anual_pct'])} al año** (con costes).")
    L.append(f"2. Todas las small caps del mismo universo: {_p(n['universo']['anual_pct'])} al año; IWM (índice de "
             f"small caps): {_p(n['iwm']['anual_pct'])}. Diferencia frente al universo: {_p(exceso)} al año → la nota {veredicto}.")
    L.append(f"3. Peor caída de la estrategia: {_p(n['estrategia']['max_caida_pct'], 0)} (IWM: "
             f"{_p(n['iwm']['max_caida_pct'], 0)}). El factor que mejor funcionó solo: {NOMBRES[mejor].lower()}.")
    L.append(f"4. Pelotazos (x{pel['x']:.0f} en {pel['meses'] // 12} años): {_p(pel['tasa_pct'], 1, False)} de las "
             f"small caps; entre el 10 % con mejor nota, {_p(pel['tasa_decil_top_pct'], 1, False)}.")
    L.append("5. Ojo: solo se prueba la parte de cuentas y precios (≈70 % de la nota). Falta la de analistas, y "
             "las empresas que quebraron o dejaron la bolsa no están (ver «Límites»). Pasado ≠ futuro.\n")

    L.append("## Carteras (20 empresas, cambio cada trimestre, 0,5 % de coste por operación)\n")
    L.append("| Estrategia | Al año | Total | Peor caída | Trimestres que gana al universo |")
    L.append("|---|---|---|---|---|")
    for k, v in c.items():
        L.append(f"| {NOMBRES[k]} | {_p(v['estrategia']['anual_pct'])} | {_p(v['estrategia']['total_pct'], 0)} | "
                 f"{_p(v['estrategia']['max_caida_pct'], 0)} | {_p(v['pct_trimestres_gana_universo'], 0, False)} |")
    L.append(f"| _Universo (todas, a partes iguales)_ | {_p(n['universo']['anual_pct'])} | "
             f"{_p(n['universo']['total_pct'], 0)} | {_p(n['universo']['max_caida_pct'], 0)} | — |")
    L.append(f"| _IWM (Russell 2000)_ | {_p(n['iwm']['anual_pct'])} | {_p(n['iwm']['total_pct'], 0)} | "
             f"{_p(n['iwm']['max_caida_pct'], 0)} | — |\n")
    L.append("La comparación justa es con el **universo**: tiene los mismos datos y el mismo sesgo. Ganar a IWM "
             "es más fácil de lo que parece, porque IWM sí incluye las empresas que quebraron.\n")

    L.append("## ¿La nota predice los 12 meses siguientes?\n")
    L.append("Correlación de rangos (de -1 a +1) entre la nota y lo que subió cada empresa en los 12 meses siguientes. "
             "En bolsa, 0,03-0,05 ya es útil; por encima de 0,10 es muy raro.\n")
    L.append("| Qué | Correlación media | % de trimestres positiva |")
    L.append("|---|---|---|")
    for k, v in ic.items():
        L.append(f"| {NOMBRES.get(k, k)} | {v['media']:+.3f} | {v['pct_positivas']:.0f} % |")
    qs = res["doce_meses"].get("quintiles") or []
    if qs:
        L.append("\n**Por quintiles de nota** (5 grupos del mismo tamaño; 1 = el 20 % con mejor nota). "
                 "Rentabilidad a 12 meses frente a la media del universo:\n")
        L.append("| Quintil | Frente al universo | % de trimestres que gana |")
        L.append("|---|---|---|")
        for q in qs:
            L.append(f"| {q['quintil']} | {_p(q['exceso_12m_pct'])} | {q['pct_cohortes_gana']:.0f} % |")
        L.append("\nOjo: las empresas que quebraron (que faltan) habrían caído sobre todo en los quintiles malos, así que "
                 "la diferencia real entre el 1 y el 5 probablemente es **mayor** que la que se ve aquí.")
    co = res["doce_meses"]["cohortes"]
    if co:
        L.append("\n| Fecha | Top 20 a 12 m | Top 50 | Universo | IWM |")
        L.append("|---|---|---|---|---|")
        for f in co[::2]:
            L.append(f"| {f['fecha']} | {_p(f['top20_pct'], 0)} | {_p(f['top50_pct'], 0)} | "
                     f"{_p(f['universo_pct'], 0)} | {_p(f['iwm_pct'], 0)} |")

    L.append(f"\n## Pelotazos: multiplicar por {pel['x']:.0f} en {pel['meses'] // 12} años\n")
    L.append(f"De {pel['casos']} casos (empresa × trimestre), {pel['pelotazos']} lo lograron "
             f"({_p(pel['tasa_pct'], 1, False)}), de {pel['empresas_distintas']} empresas distintas. "
             f"Entre el 10 % con mejor nota: {_p(pel['tasa_decil_top_pct'], 1, False)}.\n")
    L.append("¿Cómo eran **antes** de subir? (mediana del percentil de cada factor; 50 = normal)\n")
    L.append("| Factor | Pelotazos | Resto |")
    L.append("|---|---|---|")
    for k, v in pel["perfil"].items():
        a, b = v["mediana_pelotazos"], v["mediana_resto"]
        L.append(f"| {NOMBRES.get(k, k).replace('Solo ', '')} | {'—' if a is None else f'{a:.0f}'} | "
                 f"{'—' if b is None else f'{b:.0f}'} |")
    if pel["ejemplos"]:
        L.append("\nEjemplos (su mejor subida): " + ", ".join(
            f"{e['ticker']} x{e['multiplica']} desde {e['desde']} (puesto {e['puesto']}/{e['de']})" for e in pel["ejemplos"]))

    L.append("\n## Límites (léelos antes de fiarte)\n")
    L.append("- **Supervivencia:** solo están las empresas que siguen cotizando hoy, porque Yahoo no tiene el precio "
             "de las que desaparecieron. " + (
                 f"Cada año dejó de presentar cuentas un {tasa_sup:.1f} % de las empresas de tamaño parecido "
                 "(muchas porque las compraron, a menudo con prima, y otras por quiebra). Peor caso: si todas fueran "
                 f"pérdida total y te tocaran en la misma proporción, resta ~{tasa_sup:.0f} puntos al año a la "
                 "estrategia **y también al universo**." if tasa_sup is not None else ""))
    L.append("- **Analistas, directivos y catalizadores** no tienen historia gratis: en el backtest quedan sin dato "
             "para todas por igual. Desde el 15-nov-2026 guardamos una foto diaria para poder probarlos dentro de unos meses.")
    L.append("- **PER**: el ranking usa el PER futuro (con previsiones); aquí se usa el pasado.")
    L.append("- **Sector**: sin sector histórico, la calidad y la valoración se comparan con todas las empresas, no solo con las de su sector.")
    L.append("- **Sin mirar al futuro:** cada cuenta se usa desde el día en que se presentó a la SEC y cada precio desde su mes.")
    L.append("- Unos pocos años buenos pueden explicar todo el resultado. **Rentabilidades pasadas no garantizan las futuras**; "
             "el siguiente paso es la cartera de práctica en demo.")
    txt = "\n".join(L) + "\n"
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(txt)
    return txt
