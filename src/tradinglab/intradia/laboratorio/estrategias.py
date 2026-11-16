"""Las estrategias del laboratorio intradía. Cada una mira UNA acción en UN día (velas de 1 minuto,
hora de Nueva York, ya pasadas por `simular.preparar`) y devuelve 0 o 1 operaciones.

Reglas para no hacernos trampas:
- La señal se ve al CIERRE de una vela y se entra a la APERTURA de la siguiente (salvo el ORB, que entra
  justo en la ruptura, como en el estudio original).
- Para elegir la acción solo se usa lo que se sabe al entrar (hueco de apertura, volumen de los primeros
  minutos, medias de días anteriores). Nunca el cierre del día.
- Las salidas (stop, objetivo, trailing, cierre forzado) y los costes son los de `estudio.simular.gestionar`.
"""
from __future__ import annotations

import random

import pandas as pd

from ..estudio import simular
from ..estudio.simular import T, Costes


def con_vwap(r: pd.DataFrame) -> pd.DataFrame:
    """Añade el VWAP: precio medio del día ponderado por volumen, desde las 9:30."""
    r = r.copy()
    tipico = (r["h"] + r["l"] + r["c"]) / 3
    vol = r["v"].clip(lower=0)
    acum = vol.cumsum().replace(0, float("nan"))
    r["vwap"] = ((tipico * vol).cumsum() / acum).fillna(r["c"])
    return r


def _entrar(r: pd.DataFrame, i: int, lado: str, riesgo: dict, costes: Costes, stop_pct: float | None = None,
            con_objetivo: bool = True) -> dict | None:
    """Entra a la apertura de la vela i y sigue la operación hasta salir. Apunta también qué habría
    pasado con el objetivo alternativo (4R)."""
    if i >= len(r):
        return None
    entrada = float(r["o"].iloc[i])
    if entrada <= 0:
        return None
    pct = stop_pct if stop_pct is not None else riesgo["stop_pct"]
    dist = entrada * pct / 100
    stop = entrada - dist if lado == "compra" else entrada + dist
    resto = r.iloc[i:]
    cierre = T(riesgo["cierre"])
    trailing = riesgo.get("trailing") if con_objetivo else None
    signo = 1 if lado == "compra" else -1
    obj = entrada + signo * dist * riesgo["rr"] if con_objetivo else None
    res = simular.gestionar(resto, lado, entrada, stop, obj, cierre, trailing, costes)
    if con_objetivo and riesgo.get("rr_alternativo"):
        alt = simular.gestionar(resto, lado, entrada, stop, entrada + signo * dist * riesgo["rr_alternativo"],
                                cierre, trailing, costes)
        res["R_alt"] = alt["R"]
    else:
        res["R_alt"] = res["R"]
    res.update(hora_entrada=r["hora"].iloc[i].strftime("%H:%M"), entrada_bruta=round(entrada, 4),
               riesgo_pct=round(pct, 3))
    return res


def _primera(senal: pd.Series, r: pd.DataFrame, fin: str) -> int | None:
    """Posición de la vela SIGUIENTE a la primera señal, si cae antes de `fin`."""
    pos = [k for k, s in enumerate(senal.to_numpy()) if s]
    for k in pos:
        if k + 1 < len(r) and r["hora"].iloc[k + 1] < T(fin):
            return k + 1
        return None
    return None


# ---------------------------------------------------------------- 1) ORB
def orb(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    if not ctx.get("en_juego") or ctx["puesto"] > cfg.get("top", 10):
        return None
    var = dict(stop="pct", stop_pct=riesgo["stop_pct"], rr=riesgo["rr"], trailing=riesgo.get("trailing"),
               fin_entradas=cfg["fin_entradas"], cierre=riesgo["cierre"], cortos=True)
    res = simular.orb(m, ctx.get("atr14") or 0, var, costes, cfg.get("minutos", 5))
    if res and riesgo.get("rr_alternativo"):
        alt = simular.orb(m, ctx.get("atr14") or 0, {**var, "rr": riesgo["rr_alternativo"]}, costes, cfg.get("minutos", 5))
        res["R_alt"] = alt["R"] if alt else res["R"]
    return res


# ---------------------------------------------------------------- 2) Hueco con volumen
def hueco_volumen(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    h = ctx.get("hueco") or 0
    if abs(h) < cfg["hueco_min"] or (ctx.get("rvol5") or 0) < cfg["rvol5_min"]:
        return None
    r = con_vwap(simular.regular(m))
    fin_rango = simular.tras_apertura(cfg["minutos_rango"])
    rango, tras = r[r["hora"] < fin_rango], r[r["hora"] >= fin_rango]
    if len(rango) < 3 or len(tras) < 2:
        return None
    off = len(rango)
    if h > 0:   # sigue subiendo: rompe el máximo de los 15 min y está por encima del VWAP
        lado, senal = "compra", (tras["c"] > rango["h"].max()) & (tras["c"] > tras["vwap"])
    else:       # sigue bajando: rompe el mínimo y está por debajo del VWAP
        lado, senal = "venta", (tras["c"] < rango["l"].min()) & (tras["c"] < tras["vwap"])
    i = _primera(senal, tras, cfg["fin_entradas"])
    return _entrar(r, off + i, lado, riesgo, costes) if i is not None else None


# ---------------------------------------------------------------- 3) Retroceso al VWAP
def vwap(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    if not ctx.get("en_juego") or ctx["puesto"] > cfg.get("top", 20):
        return None
    r = con_vwap(simular.regular(m))
    antes, tras = r[r["hora"] < T(cfg["desde"])], r[r["hora"] >= T(cfg["desde"])]
    if len(antes) < 10 or len(tras) < 2:
        return None
    ult, apertura = antes.iloc[-1], float(r["o"].iloc[0])
    if ult["c"] > ult["vwap"] and ult["c"] > apertura:          # tendencia al alza en la primera media hora
        lado, senal = "compra", (tras["l"] <= tras["vwap"]) & (tras["c"] > tras["vwap"])
    elif ult["c"] < ult["vwap"] and ult["c"] < apertura:        # tendencia a la baja
        lado, senal = "venta", (tras["h"] >= tras["vwap"]) & (tras["c"] < tras["vwap"])
    else:
        return None
    i = _primera(senal, tras, cfg["fin_entradas"])
    return _entrar(r, len(antes) + i, lado, riesgo, costes) if i is not None else None


# ---------------------------------------------------------------- 4) Corto del hueco
def corto_hueco(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    if (ctx.get("hueco") or 0) < cfg["hueco_min"]:
        return None
    r = simular.regular(m)
    idx = [k for k, h in enumerate(r["hora"]) if h >= T(cfg["entrada"])]
    if not idx:
        return None
    return _entrar(r, idx[0], "venta", riesgo, costes, stop_pct=cfg["stop_pct"],
                   con_objetivo=not cfg.get("sin_objetivo", True))


# ---------------------------------------------------------------- 5) Rebote tras caída
def rebote(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    if (ctx.get("hueco") or 0) > cfg["hueco_max"]:
        return None
    r = con_vwap(simular.regular(m))
    antes, tras = r[r["hora"] < T(cfg["desde"])], r[r["hora"] >= T(cfg["desde"])]
    if len(antes) < 5 or len(tras) < 2:
        return None
    debajo = (tras["c"] < tras["vwap"]).shift(1, fill_value=bool(antes["c"].iloc[-1] < antes["vwap"].iloc[-1]))
    senal = debajo & (tras["c"] > tras["vwap"])   # cruza hacia arriba el VWAP
    i = _primera(senal, tras, cfg["fin_entradas"])
    return _entrar(r, len(antes) + i, "compra", riesgo, costes) if i is not None else None


# ---------------------------------------------------------------- 6) Azar (control)
def azar(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    """Solo para comparar: si una estrategia no gana a esta, su «ventaja» es suerte."""
    if not ctx.get("azar_elegida"):
        return None
    r = simular.regular(m)
    pos = [k for k, h in enumerate(r["hora"]) if T(cfg["desde"]) <= h < T(cfg["fin_entradas"])]
    if not pos:
        return None
    rnd = random.Random(f"{ctx.get('fecha')}-{ctx.get('simbolo')}")
    return _entrar(r, rnd.choice(pos), rnd.choice(["compra", "venta"]), riesgo, costes)


# ---------------------------------------------------------------- 7) Hueco al alza + trailing hasta el cierre
def hueco_trailing(m: pd.DataFrame, ctx: dict, cfg: dict, riesgo: dict, costes: Costes) -> dict | None:
    """Idea de Ruben (16-nov): si una acción abre con hueco al alza tras buenos resultados, comprarla y
    dejarla correr. SIN objetivo fijo: solo stop inicial y trailing; si el trailing sigue subiendo al
    final del día, se aguanta hasta el cierre (15:59 NY).
    - `solo_resultados`: solo si hubo 8-K de resultados entre la tarde anterior y las 9:30 (SEC).
    - `confirmar`: en vez de entrar a las 9:35, entra a la hora `entrada` solo si el precio está por encima
      de la apertura y del VWAP (la subida «aguanta»)."""
    if (ctx.get("hueco") or 0) < cfg["hueco_min"]:
        return None
    if cfg.get("solo_resultados") and not ctx.get("resultados"):
        return None
    r = con_vwap(simular.regular(m))
    idx = [k for k, h in enumerate(r["hora"]) if h >= T(cfg["entrada"])]
    if not idx or idx[0] == 0:
        return None
    i = idx[0]
    if cfg.get("confirmar"):
        prev = r.iloc[i - 1]
        if not (prev["c"] > float(r["o"].iloc[0]) and prev["c"] > prev["vwap"]):
            return None
    entrada = float(r["o"].iloc[i])
    if entrada <= 0:
        return None
    d = float(cfg["distancia_pct"])
    trailing = {"activo": True, "activar_en_R": cfg.get("activar_en_R", 1.0), "distancia_pct": d}
    res = simular.gestionar(r.iloc[i:], "compra", entrada, entrada * (1 - d / 100), None,
                            T(cfg.get("cierre", "15:59")), trailing, costes)
    res.update(R_alt=res["R"], hora_entrada=r["hora"].iloc[i].strftime("%H:%M"), entrada_bruta=round(entrada, 4),
               riesgo_pct=round(d, 3), resultados=bool(ctx.get("resultados")), con_cik=bool(ctx.get("con_cik")))
    return res


TODAS = {"orb": orb, "hueco_volumen": hueco_volumen, "vwap": vwap, "corto_hueco": corto_hueco,
         "rebote": rebote, "azar": azar,
         # Variantes de la idea «hueco por resultados + trailing hasta el cierre» (misma función, otros ajustes)
         "resultados_t3": hueco_trailing, "resultados_t5": hueco_trailing, "resultados_t8": hueco_trailing,
         "resultados_confirma_t5": hueco_trailing, "hueco_trailing_t5": hueco_trailing}
