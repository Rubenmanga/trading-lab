"""Resultados del laboratorio: compara las estrategias en el pasado y en la cuenta sombra.

Medida principal: **R medio por operación** tras costes. R = lo que se arriesga en una operación
(la distancia al stop). +0,2 R de media = por cada 100 € arriesgados se ganan 20 € de media.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from ..estudio.universo import leer_csv

EXPLICA = {
    "orb": "Compra si rompe el máximo de los 5 primeros minutos (vela verde) o vende en corto si rompe el mínimo (vela roja). Solo las 10 acciones con más volumen al abrir.",
    "hueco_volumen": "Acciones que abren con hueco de ±4 % y mucho volumen (suele haber noticia o resultados). Entra a favor del hueco si rompe el rango de los 15 primeros minutos y está del lado bueno del VWAP.",
    "vwap": "Si en la primera media hora va claramente al alza (o a la baja), espera a que el precio vuelva al VWAP (precio medio del día) y entra a favor de la tendencia.",
    "corto_hueco": "Vende en corto a las 9:35 las que abren +25 % o más; stop 15 %, sin objetivo, cierra a las 15:45. «Como el bot» = hueco ≥ +50 % y las 3 primeras del día.",
    "rebote": "Acciones que abren un 8 % o más abajo: compra cuando el precio vuelve a subir por encima del VWAP.",
    "azar": "CONTROL: 4 acciones en juego al azar, lado y hora al azar, mismas reglas de riesgo. Una estrategia que no le gane no aporta nada.",
}


def estadisticas(o: pd.DataFrame, listones: dict, col: str = "R") -> dict:
    if o.empty:
        return dict(n=0, semaforo="gris")
    R = o[col].astype(float)
    n, media = len(R), float(R.mean())
    sd = float(R.std(ddof=1)) if n > 1 else 0.0
    ic = 1.96 * sd / math.sqrt(n) if n > 1 else float("nan")
    gan, per = R[R > 0].sum(), -R[R < 0].sum()
    curva = R.cumsum()
    caida = float((curva - curva.cummax()).min()) if n else 0.0
    racha = mx = 0
    for x in R:
        racha = racha + 1 if x < 0 else 0
        mx = max(mx, racha)
    anios = o.assign(anio=o["fecha"].str[:4]).groupby("anio")[col].agg(["count", "mean"])
    d = dict(n=n, R_medio=round(media, 3), ic95=[round(media - ic, 3), round(media + ic, 3)] if n > 1 else None,
             R_alt_medio=round(float(o["R_alt"].mean()), 3) if "R_alt" in o else None,
             aciertos_pct=round(100 * float((R > 0).mean()), 1), pf=round(gan / per, 2) if per > 0 else None,
             R_total=round(float(R.sum()), 1), peor_caida_R=round(caida, 1), peor_racha=mx,
             largos=int((o["lado"] == "compra").sum()), cortos=int((o["lado"] == "venta").sum()),
             dias=int(o["fecha"].nunique()), ops_dia=round(n / max(1, o["fecha"].nunique()), 2),
             por_anio={a: dict(n=int(f["count"]), R=round(float(f["mean"]), 3)) for a, f in anios.iterrows()},
             anios_positivos=int((anios["mean"] > 0).sum()), anios=int(len(anios)))
    d["semaforo"] = semaforo(d, listones)
    return d


def semaforo(d: dict, L: dict) -> str:
    """verde = aprueba · amarillo = prometedora o faltan operaciones · rojo = pierde · gris = sin datos."""
    if not d.get("n"):
        return "gris"
    lo = (d.get("ic95") or [float("nan")])[0]
    if d["n"] >= L["ops_minimas"] and d["R_medio"] >= L["R_medio_min"] and lo > 0:
        return "verde"
    if d["n"] >= 30 and d["R_medio"] < 0 and (d.get("ic95") or [0, 0])[1] < 0:
        return "rojo"
    if d["n"] >= L["ops_minimas"] and d["R_medio"] <= 0:
        return "rojo"
    return "amarillo"


TRAMOS = [(0, 50, "< 50"), (50, 62.5, "50-62"), (62.5, 75, "62-75"), (75, 101, "≥ 75")]


def por_nota(o: pd.DataFrame) -> list[dict]:
    if o.empty or "nota" not in o:
        return []
    out = []
    for lo, hi, nom in TRAMOS:
        g = o[(o["nota"] >= lo) & (o["nota"] < hi)]
        out.append(dict(tramo=nom, n=int(len(g)), R=round(float(g["R"].mean()), 3) if len(g) else None))
    return out


def por_punto(o: pd.DataFrame) -> dict:
    """Para cada indicador del filtro: R medio cuando estaba a favor (1) y en contra (0)."""
    from .filtro import NOMBRES
    if o.empty or "filtro" not in o:
        return {}
    f = o["filtro"].astype(str).str.pad(len(NOMBRES), fillchar="·")
    out = {}
    for k, nom in enumerate(NOMBRES):
        letra = f.str[k]
        a, e = o[letra == "1"]["R"], o[letra == "0"]["R"]
        out[nom] = dict(a_favor=round(float(a.mean()), 3) if len(a) else None, n_favor=int(len(a)),
                        en_contra=round(float(e.mean()), 3) if len(e) else None, n_contra=int(len(e)))
    return out


def curva_mensual(o: pd.DataFrame) -> list[dict]:
    if o.empty:
        return []
    m = o.assign(mes=o["fecha"].str[:7]).groupby("mes")["R"].sum().cumsum()
    return [{"f": k, "R": round(float(v), 1)} for k, v in m.items()]


def curva_diaria(o: pd.DataFrame) -> list[dict]:
    if o.empty:
        return []
    m = o.groupby("fecha")["R"].sum().cumsum()
    return [{"f": k, "R": round(float(v), 2)} for k, v in m.items()]


def leer_ops(carpeta: Path, patron: str) -> pd.DataFrame:
    partes = [leer_csv(f) for f in sorted(Path(carpeta).glob(patron)) if f.stat().st_size > 30]
    partes = [p for p in partes if len(p)]
    return pd.concat(partes, ignore_index=True).sort_values(["fecha", "hora_entrada"]) if partes else pd.DataFrame()


def generar(back: pd.DataFrame, sombra: pd.DataFrame, cfg: dict, hoy: str) -> dict:
    L = cfg["listones"]
    res = dict(actualizado=hoy, listones=L, riesgo=cfg["riesgo"], filtro=cfg.get("filtro") or {}, estrategias={})
    for clave, e in cfg["estrategias"].items():
        b = back[back["estrategia"] == clave] if len(back) else back
        s = sombra[sombra["estrategia"] == clave] if len(sombra) else sombra
        d = dict(nombre=e.get("nombre", clave), explica=EXPLICA.get(clave, ""), activa=bool(e.get("activa")),
                 pasado=estadisticas(b, L), sombra=estadisticas(s, L),
                 curva_pasado=curva_mensual(b), curva_sombra=curva_diaria(s))
        F = cfg.get("filtro") or {}
        if "nota" in getattr(b, "columns", []):
            d["por_nota"] = por_nota(b)
            d["por_punto"] = por_punto(b)
            d["pasado_filtrado"] = estadisticas(b[b["nota"] >= F.get("umbral", 62.5)], L)
        if "nota" in getattr(s, "columns", []):
            d["sombra_filtrada"] = estadisticas(s[s["nota"] >= F.get("umbral", 62.5)], L)
        d["filtro_aplica"] = clave in (F.get("aplicar_a") or [])
        if clave == "corto_hueco" and len(b):
            bot = b[(b["hueco"] >= 0.5) & (b["puesto"] <= 3)]
            d["pasado_como_bot"] = estadisticas(bot, L)
            d["pasado_como_bot"]["ret_pct_medio"] = round(float(bot["ret_pct"].mean()), 2) if len(bot) else None
        res["estrategias"][clave] = d
    # Ventaja frente al azar (en R medio) para saber si es algo más que suerte
    for nombre in ("pasado", "sombra"):
        base = res["estrategias"].get("azar", {}).get(nombre, {}).get("R_medio")
        for d in res["estrategias"].values():
            if base is not None and d[nombre].get("n"):
                d[nombre]["vs_azar"] = round(d[nombre]["R_medio"] - base, 3)
    res["periodo_pasado"] = [str(back["fecha"].min()), str(back["fecha"].max())] if len(back) else None
    res["dias_sombra"] = int(sombra["fecha"].nunique()) if len(sombra) else 0
    res["ultimas_sombra"] = [] if sombra.empty else json.loads(
        sombra.sort_values(["fecha", "hora_entrada"]).tail(60)[
            ["fecha", "estrategia", "simbolo", "lado", "hora_entrada", "entrada", "salida", "motivo", "hora_salida",
             "R", "ret_pct", "hueco"]].to_json(orient="records"))
    return res


SEM = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴", "gris": "⚪"}


def _f(x, dec=2, signo=True):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return (f"{x:+.{dec}f}" if signo else f"{x:.{dec}f}").replace(".", ",")


def markdown(res: dict) -> str:
    E, L = res["estrategias"], res["listones"]
    orden = sorted(E, key=lambda k: -(E[k]["pasado"].get("R_medio") or -9))
    mejor = orden[0] if orden else None
    verdes = [E[k]["nombre"] for k in E if E[k]["pasado"].get("semaforo") == "verde"]
    p = res.get("periodo_pasado") or ["—", "—"]
    lin = [f"# Laboratorio intradía · {res['actualizado']}", "",
           "**Resumen**", "",
           f"1. Se prueban {len(E)} estrategias a la vez con las mismas reglas de riesgo (stop {_f(res['riesgo']['stop_pct'], 0, False)} %, objetivo {_f(res['riesgo']['rr'], 0, False)}R, trailing, todo cerrado a las {res['riesgo']['cierre']} NY), con costes.",
           f"2. Pasado: {p[0]} a {p[1]}. Mejor por R medio: **{E[mejor]['nombre'] if mejor else '—'}** ({_f(E[mejor]['pasado'].get('R_medio')) if mejor else '—'} R).",
           f"3. Aprueban el listón (≥ {L['ops_minimas']} operaciones, ≥ {_f(L['R_medio_min'])} R de media y margen de error por encima de 0): **{', '.join(verdes) or 'ninguna'}**.",
           f"4. Cuenta sombra: {res['dias_sombra']} días apuntados desde el 16-nov-2026. Hacen falta ~{L['ops_minimas']} operaciones por estrategia para una primera lectura.",
           "5. Todo es papel: no se envía ninguna orden. R = lo que se arriesga en una operación.", "",
           "## Pasado (backtest)", "",
           "| | Estrategia | Ops | Ops/día | R medio | Margen (95 %) | Con 4R | Aciertos | PF | Peor caída | Años + | Vs azar |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in orden:
        d = E[k]["pasado"]
        if not d.get("n"):
            lin.append(f"| {SEM['gris']} | {E[k]['nombre']} | 0 | | | | | | | | | |")
            continue
        ic = d.get("ic95") or [None, None]
        lin.append(f"| {SEM[d['semaforo']]} | {E[k]['nombre']} | {d['n']} | {_f(d['ops_dia'], 1, False)} | {_f(d['R_medio'])} | "
                   f"{_f(ic[0])} a {_f(ic[1])} | {_f(d.get('R_alt_medio'))} | {_f(d['aciertos_pct'], 0, False)} % | "
                   f"{_f(d.get('pf'), 2, False)} | {_f(d['peor_caida_R'], 0)} R | {d['anios_positivos']}/{d['anios']} | {_f(d.get('vs_azar'))} |")
    cb = E.get("corto_hueco", {}).get("pasado_como_bot")
    if cb and cb.get("n"):
        lin += ["", f"Corto del hueco **como el bot de eToro** (hueco ≥ +50 %, 3 al día): {cb['n']} operaciones, "
                    f"{_f(cb['R_medio'])} R de media ({_f(cb.get('ret_pct_medio'))} % por operación), aciertos {_f(cb['aciertos_pct'], 0, False)} %."]
    if any(E[k].get("por_nota") for k in E):
        u = res.get("filtro", {}).get("umbral", 62.5)
        lin += ["", f"## Filtro «¿entrar o no?» (nota ≥ {_f(u, 1, False)} de 100)", "",
                "Nota = cuántos de 8 indicadores (tendencia en 1, 5 y 15 min, hueco del día, VWAP, RSI, Nasdaq y volumen) estaban a favor justo antes de entrar.", "",
                "| Estrategia | Sin filtro | Con filtro | Nota < 50 | 50-62 | 62-75 | ≥ 75 |", "|---|---|---|---|---|---|---|"]
        for k in orden:
            d, pf = E[k]["pasado"], E[k].get("pasado_filtrado") or {}
            tr = {t["tramo"]: t for t in E[k].get("por_nota") or []}
            celda = lambda t: f"{_f(t['R'])} ({t['n']})" if t and t.get("n") else "—"  # noqa: E731
            lin.append(f"| {E[k]['nombre']} | {_f(d.get('R_medio'))} ({d.get('n', 0)}) | {_f(pf.get('R_medio'))} ({pf.get('n', 0)}) | "
                       + " | ".join(celda(tr.get(n)) for _, _, n in TRAMOS) + " |")
        pp = {}
        for k in E:
            if E[k].get("filtro_aplica"):
                for nom, v in (E[k].get("por_punto") or {}).items():
                    pp.setdefault(nom, []).append(v)
        if pp:
            lin += ["", "Qué indicador ayuda (estrategias con filtro): R medio cuando estaba **a favor** frente a **en contra**.", "",
                    "| Indicador | A favor | En contra | Diferencia |", "|---|---|---|---|"]
            for nom, vs in pp.items():
                nf, nc = sum(v["n_favor"] for v in vs), sum(v["n_contra"] for v in vs)
                af = sum((v["a_favor"] or 0) * v["n_favor"] for v in vs) / nf if nf else None
                ec = sum((v["en_contra"] or 0) * v["n_contra"] for v in vs) / nc if nc else None
                lin.append(f"| {nom} | {_f(af)} ({nf}) | {_f(ec)} ({nc}) | {_f(af - ec) if af is not None and ec is not None else '—'} |")
    lin += ["", "## Cuenta sombra (desde el 16-nov-2026)", "",
            "| | Estrategia | Ops | R medio | Aciertos | R total | Vs azar |", "|---|---|---|---|---|---|---|"]
    for k in orden:
        d = E[k]["sombra"]
        lin.append(f"| {SEM[d.get('semaforo', 'gris')]} | {E[k]['nombre']} | {d.get('n', 0)} | {_f(d.get('R_medio'))} | "
                   f"{_f(d.get('aciertos_pct'), 0, False) + ' %' if d.get('n') else '—'} | {_f(d.get('R_total'), 1)} | {_f(d.get('vs_azar'))} |")
    lin += ["", "## Qué hace cada estrategia", ""] + [f"- **{E[k]['nombre']}**: {E[k]['explica']}" for k in E]
    lin += ["", "## Cómo leerlo", "",
            "- **R medio**: lo que gana o pierde de media cada operación, en unidades de riesgo. Tras costes.",
            "- **Margen (95 %)**: con estas operaciones, el R medio «de verdad» está casi seguro entre esos dos números. Si el de la izquierda es mayor que 0, no parece suerte.",
            "- **PF** (factor de beneficio): lo ganado entre lo perdido. Por encima de 1,3 es bueno.",
            "- **Peor caída**: la mayor racha de pérdidas acumulada, en R. Con 0,5 % de riesgo por operación, −20 R = −10 % de la cuenta.",
            "- **Vs azar**: cuánto mejora a la estrategia de control. Si es ~0, la estrategia no aporta.",
            "- Semáforo: 🟢 aprueba · 🟡 prometedora o faltan operaciones · 🔴 pierde · ⚪ sin datos.",
            "- Límites: las velas son de 1 minuto (no vemos el orden exacto dentro del minuto: se supone lo peor); no sabemos qué acciones se podían vender en corto ese día; el pasado no garantiza el futuro."]
    return "\n".join(lin) + "\n"


def guardar(res: dict, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = carpeta / "INFORME.md"
    md.write_text(markdown(res), encoding="utf-8")
    return md
