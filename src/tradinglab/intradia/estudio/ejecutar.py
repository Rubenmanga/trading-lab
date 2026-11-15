"""Paso 2: para cada día, baja las velas de 1 minuto (con premercado) SOLO de las candidatas y calcula
el estudio de top gainers y las operaciones ORB. Guarda dos CSV por tramo de fechas."""
from __future__ import annotations

import random
import re
from datetime import datetime, time

import pandas as pd
from zoneinfo import ZoneInfo

from . import simular
from .simular import Costes

NY = ZoneInfo("America/New_York")

MOTIVOS = [  # (motivo, palabras en titulares en inglés). Se aplica el primero que encaje.
    ("fusión o compra", r"acquir|merger|buyout|takeover|to be acquired|definitive agreement|tender offer|go(ing)? private"),
    ("FDA o ensayo", r"\bfda\b|trial|phase [123i]|topline|pdufa|approv|clinical|data (from|at)|breakthrough designation"),
    ("resultados", r"earnings|quarter|\bq[1-4]\b|revenue|\beps\b|results|guidance|outlook|sales (rose|grew|increase)"),
    ("ampliación de capital", r"offering|priced|registered direct|private placement|warrant|at-the-market|\batm\b"),
    ("contrato o acuerdo", r"contract|partner|collaborat|agreement|order|award|license|deal"),
    ("cripto/IA/moda", r"bitcoin|crypto|blockchain|\bai\b|artificial intelligence|quantum|drone|nuclear"),
]


def clasificar(titulares: list[str]) -> str:
    if not titulares:
        return "sin noticia"
    texto = " ".join(titulares).lower()
    for motivo, patron in MOTIVOS:
        if re.search(patron, texto):
            return motivo
    return "otra noticia"


def _ny(fecha: str, hh: int, mm: int = 0) -> datetime:
    y, m, d = map(int, fecha.split("-"))
    return datetime(y, m, d, hh, mm, tzinfo=NY)


def procesar(cliente, cands: pd.DataFrame, desde: str, hasta: str, cfg: dict,
             semilla: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    costes = Costes(**cfg["costes"])
    reglas = cfg["reglas_agente_a"]
    fechas_todas = sorted(cands["fecha"].unique())
    fechas = [f for f in fechas_todas if desde <= f <= hasta]
    rnd = random.Random(semilla)
    filas_g, filas_o = [], []
    for n, fecha in enumerate(fechas):
        dia = cands[cands["fecha"] == fecha]
        sims = sorted(dia["simbolo"].unique())
        partes = [cliente.velas(sims[i:i + 100], "1Min", _ny(fecha, 4), _ny(fecha, 16)) for i in range(0, len(sims), 100)]
        m = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
        if m.empty:
            continue
        por_sim = {s: simular.preparar(g) for s, g in m.groupby("simbolo")}
        en_juego = []
        for _, fila in dia.iterrows():
            mm = por_sim.get(fila["simbolo"])
            if mm is None:
                continue
            base = dict(fecha=fecha, simbolo=fila["simbolo"], cierre_ant=fila["cierre_ant"],
                        hueco=round(fila["hueco"], 4), sube_dia=round(fila["sube_dia"], 4),
                        vol_medio14=int(fila["vol_medio14"]), volumen_dia=int(fila["v"]))
            if fila["A"]:
                g = simular.rasgos_gainer(mm, float(fila["cierre_ant"]), reglas, costes)
                if g:
                    filas_g.append({**base, **g})
            if fila["B"]:
                ra = simular.rango_apertura(mm, cfg["orb"]["minutos"])
                if ra and fila["vol_medio14"] > 0:
                    en_juego.append((ra["v"] / fila["vol_medio14"], fila, mm, base))
        # Acciones en juego: las de más volumen relativo en los primeros 5 minutos
        en_juego.sort(key=lambda x: -x[0])
        for puesto, (rvol, fila, mm, base) in enumerate(en_juego[:cfg["orb"]["top"]], start=1):
            for nombre, var in cfg["orb"]["variantes"].items():
                if puesto > var.get("top", cfg["orb"]["top"]):
                    continue
                op = simular.orb(mm, float(fila["atr14"]), var, costes, cfg["orb"]["minutos"])
                if op:
                    filas_o.append({**base, "variante": nombre, "puesto": puesto, "rvol5": round(rvol, 4),
                                    "atr14": round(float(fila["atr14"]), 4), **op})
        if n % 20 == 0:
            print(f"  {fecha}: {len(filas_g)} filas gainers, {len(filas_o)} operaciones ORB, "
                  f"{cliente.llamadas} llamadas", flush=True)
    g = pd.DataFrame(filas_g)
    # Motivo de la subida: noticias de una muestra de las que suben >= +15 % (para no gastar llamadas)
    if len(g) and cfg["noticias"]["muestra_por_tramo"]:
        idx = [i for i in g.index if g.at[i, "sube_dia"] >= cfg["gainers"]["subida_min"] or g.at[i, "hueco"] >= 0.10]
        idx = rnd.sample(idx, min(len(idx), cfg["noticias"]["muestra_por_tramo"]))
        g["motivo"] = None
        g["titular"] = None
        for i in idx:
            f = g.at[i, "fecha"]
            k = fechas_todas.index(f)
            ant = fechas_todas[k - 1] if k > 0 else f
            try:
                nots = cliente.noticias(g.at[i, "simbolo"], _ny(ant, 16), _ny(f, 16))
            except Exception as e:  # noqa: BLE001 - una noticia que falla no para el estudio
                print("  noticias:", e)
                continue
            tit = [x.get("headline", "") for x in nots]
            g.at[i, "motivo"] = clasificar(tit)
            g.at[i, "titular"] = tit[-1][:160] if tit else ""
    return g, pd.DataFrame(filas_o)
