"""Motor del laboratorio: para cada día elige las acciones, baja sus velas de 1 minuto y pasa TODAS las
estrategias. Lo mismo sirve para el pasado (muchos días) y para la cuenta sombra (solo hoy)."""
from __future__ import annotations

import random
from datetime import datetime

import pandas as pd
from zoneinfo import ZoneInfo

from ..estudio import simular
from ..estudio.simular import Costes
from ..estudio.universo import velas_seguras
from . import estrategias, filtro

INDICE = "QQQ"  # el Nasdaq 100: sirve al filtro para saber si el mercado acompaña

NY = ZoneInfo("America/New_York")


def _ny(fecha: str, hh: int, mm: int = 0) -> datetime:
    y, m, d = map(int, fecha.split("-"))
    return datetime(y, m, d, hh, mm, tzinfo=NY)


def universo_dia(dia: pd.DataFrame) -> pd.DataFrame:
    """De las candidatas del estudio se quedan solo las que se eligen con datos de ANTES de entrar:
    las B (precio, volumen medio, ATR y hueco) y las A que abren con hueco >= +8 % (no las que «suben
    +15 % en el día», porque eso solo se sabe al cierre)."""
    return dia[dia["B"].astype(bool) | (dia["A"].astype(bool) & (dia["hueco"] >= 0.08))]


def operaciones_dia(fecha: str, dia: pd.DataFrame, por_sim: dict[str, pd.DataFrame], cfg: dict) -> list[dict]:
    """Todas las operaciones de todas las estrategias en un día. `por_sim`: velas ya preparadas."""
    costes, riesgo, ests = Costes(**cfg["costes"]), cfg["riesgo"], cfg["estrategias"]
    ctxs = []
    for _, f in universo_dia(dia).iterrows():
        m = por_sim.get(f["simbolo"])
        if m is None:
            continue
        ra = simular.rango_apertura(m, 5)
        vm = float(f.get("vol_medio14") or 0)
        ctxs.append(dict(fecha=fecha, simbolo=f["simbolo"], hueco=float(f["hueco"]), cierre_ant=float(f["cierre_ant"]),
                         atr14=float(f.get("atr14") or 0), vol_medio14=vm, B=bool(f["B"]),
                         resultados=bool(f.get("resultados", False)), con_cik=bool(f.get("con_cik", False)),
                         rvol5=(ra["v"] / vm) if (ra and vm > 0) else 0.0, en_juego=False, puesto=999))
    # Acciones en juego: de las B, las de más volumen relativo en los 5 primeros minutos
    juego = sorted([c for c in ctxs if c["B"] and c["rvol5"] > 0], key=lambda c: -c["rvol5"])[:cfg["en_juego"]["top"]]
    for p, c in enumerate(juego, start=1):
        c.update(en_juego=True, puesto=p)
    if ests.get("azar", {}).get("activa"):
        for c in random.Random(fecha).sample(juego, min(len(juego), ests["azar"]["por_dia"])):
            c["azar_elegida"] = True
    # Corto del hueco: puesto por tamaño del hueco (el bot solo abre las 3 primeras)
    huecos = sorted([c for c in ctxs if c["hueco"] >= ests.get("corto_hueco", {}).get("hueco_min", 9)], key=lambda c: -c["hueco"])
    for p, c in enumerate(huecos, start=1):
        c["puesto_hueco"] = p
    ops = []
    indice = por_sim.get(INDICE)
    for nombre, fn in estrategias.TODAS.items():
        e = ests.get(nombre) or {}
        if not e.get("activa"):
            continue
        for c in ctxs:
            try:
                op = fn(por_sim[c["simbolo"]], c, e, riesgo, costes)
            except Exception as ex:  # noqa: BLE001 - una acción rara no para el laboratorio
                print(f"  aviso {fecha} {c['simbolo']} {nombre}: {ex}")
                continue
            if op:
                op.update(filtro.evaluar(por_sim[c["simbolo"]], op["hora_entrada"], op["lado"], c, indice))
                extra = {"puesto": c["puesto_hueco"]} if nombre == "corto_hueco" else {"puesto": c["puesto"]}
                ops.append(dict(fecha=fecha, estrategia=nombre, simbolo=c["simbolo"], hueco=round(c["hueco"], 4),
                                rvol5=round(c["rvol5"], 4), **extra, **op))
    return ops


def procesar(cliente, cands: pd.DataFrame, desde: str, hasta: str, cfg: dict) -> pd.DataFrame:
    """Recorre los días entre `desde` y `hasta` (las candidatas vienen de `lab estudio universo`)."""
    fechas = sorted(f for f in cands["fecha"].unique() if desde <= f <= hasta)
    ops = []
    for n, fecha in enumerate(fechas):
        dia = cands[cands["fecha"] == fecha]
        sims = sorted(set(universo_dia(dia)["simbolo"]) | {INDICE})
        partes = [velas_seguras(cliente, sims[i:i + 100], "1Min", _ny(fecha, 9, 30), _ny(fecha, 16))
                  for i in range(0, len(sims), 100)]
        partes = [p for p in partes if len(p)]
        if not partes:
            continue
        m = pd.concat(partes, ignore_index=True)
        por_sim = {s: simular.preparar(g) for s, g in m.groupby("simbolo")}
        ops += operaciones_dia(fecha, dia, por_sim, cfg)
        if n % 20 == 0:
            print(f"  {fecha}: {len(ops)} operaciones · {cliente.llamadas} llamadas", flush=True)
    return pd.DataFrame(ops)
