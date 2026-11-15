"""Simulación con velas de 1 minuto de UNA acción en UN día (hora de Nueva York).

Supuestos prudentes (para no engañarnos):
- Si en la misma vela se tocan el stop y el objetivo, contamos que saltó el stop.
- Si el precio abre por debajo del stop (hueco), salimos al precio de apertura de esa vela, no al stop.
- Cada entrada y cada salida a mercado/stop pagan deslizamiento (un % del precio) y un coste por acción.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd

from ..trailing import nuevo_stop

T = lambda s: time(*map(int, s.split(":")))  # noqa: E731


def tras_apertura(minutos: int) -> time:
    """Hora NY a los `minutos` de abrir (9:30 + minutos)."""
    total = 9 * 60 + 30 + minutos
    return time(total // 60, total % 60)


@dataclass
class Costes:
    desliz_pct: float = 0.05      # por lado
    por_accion: float = 0.0035    # $ por acción y lado (como en el estudio original)

    def peor(self, precio: float, lado: str, entrando: bool) -> float:
        """Precio real tras deslizamiento: comprar más caro, vender más barato."""
        sube = (lado == "compra") == entrando
        return precio * (1 + self.desliz_pct / 100) if sube else precio * (1 - self.desliz_pct / 100)


def preparar(m: pd.DataFrame) -> pd.DataFrame:
    """Índice en hora de NY y columna 'hora' (datetime.time)."""
    m = m.copy()
    m.index = pd.DatetimeIndex(m["t"]).tz_convert("America/New_York") if "t" in m else m.index.tz_convert("America/New_York")
    m["hora"] = [x.time() for x in m.index]
    return m


def gestionar(barras: pd.DataFrame, lado: str, entrada_bruta: float, stop: float, objetivo: float | None,
              cierre: time, trailing: dict | None, costes: Costes, entrada_a_mitad: bool = False) -> dict:
    """Sigue la operación vela a vela desde la vela de entrada (incluida) hasta salir.

    `entrada_a_mitad`: la entrada fue dentro de la primera vela (una ruptura), no en su apertura. Entonces
    lo que pasó en esa vela ANTES de entrar no cuenta. Se supone el camino típico de una vela:
    verde = apertura -> mínimo -> máximo -> cierre; roja = apertura -> máximo -> mínimo -> cierre."""
    stop_ini, stop_act = stop, stop
    mejor = entrada_bruta
    entrada = costes.peor(entrada_bruta, lado, True)
    salida_bruta, motivo, hora = None, "", None
    largo = lado == "compra"
    O, H, L, HORA = barras["o"].tolist(), barras["h"].tolist(), barras["l"].tolist(), barras["hora"].tolist()
    C = barras["c"].tolist()
    for i in range(len(O)):
        o, h, l, hh = O[i], H[i], L[i], HORA[i]
        if i == 0 and entrada_a_mitad:
            # Tras entrar en una ruptura, primero se llega al extremo a favor y luego al cierre de la vela
            if largo:
                l = C[0] if C[0] >= o else l
            else:
                h = C[0] if C[0] <= o else h
            if objetivo is not None and (h >= objetivo if largo else l <= objetivo):
                salida_bruta, motivo, hora = objetivo, "objetivo", hh
                break
        if hh >= cierre:
            salida_bruta, motivo, hora = o, "cierre forzado", hh
            break
        toca_stop = l <= stop_act if largo else h >= stop_act
        if toca_stop:
            hueco = (o < stop_act) if largo else (o > stop_act)
            salida_bruta = o if (hueco and i > 0) else stop_act
            motivo = "stop" if stop_act == stop_ini else ("trailing" if (stop_act - entrada_bruta) * (1 if largo else -1) > 0 else "stop movido")
            hora = hh
            break
        if objetivo is not None and (h >= objetivo if largo else l <= objetivo):
            salida_bruta, motivo, hora = objetivo, "objetivo", hh
            break
        mejor = max(mejor, h) if largo else min(mejor, l)
        if trailing and trailing.get("activo"):
            stop_act = nuevo_stop(lado, entrada_bruta, stop_ini, stop_act, mejor,
                                  trailing["activar_en_R"], trailing["distancia_pct"])
    if salida_bruta is None:  # se acabaron las velas (día corto): última vela
        salida_bruta, motivo, hora = barras["c"].iloc[-1], "fin del día", barras["hora"].iloc[-1]
    salida = salida_bruta if motivo == "objetivo" else costes.peor(salida_bruta, lado, False)
    signo = 1 if largo else -1
    pnl_accion = signo * (salida - entrada) - 2 * costes.por_accion
    riesgo = abs(entrada_bruta - stop_ini)
    bruto = signo * (salida_bruta - entrada_bruta)
    return dict(lado=lado, entrada=round(entrada, 4), salida=round(salida, 4), stop_inicial=round(stop_ini, 4),
                motivo=motivo, hora_salida=str(hora), R=round(pnl_accion / riesgo, 3) if riesgo else 0.0,
                R_sin_costes=round(bruto / riesgo, 3) if riesgo else 0.0,
                ret_pct=round(100 * pnl_accion / entrada_bruta, 3))


def regular(m: pd.DataFrame) -> pd.DataFrame:
    return m[(m["hora"] >= T("9:30")) & (m["hora"] < T("16:00"))]


# ---------------------------------------------------------------- estudio de top gainers
def rasgos_gainer(m: pd.DataFrame, cierre_ant: float, reglas: dict, costes: Costes) -> dict | None:
    """Qué se veía antes de abrir y qué pasó después, para una acción en un día."""
    r = regular(m)
    if len(r) < 30 or cierre_ant <= 0:
        return None
    pre = m[(m["hora"] >= T("4:00")) & (m["hora"] < T("9:00"))]
    apertura, cierre = float(r["o"].iloc[0]), float(r["c"].iloc[-1])
    hmax = r["h"].idxmax()
    d = dict(
        pm_precio_0900=round(float(pre["c"].iloc[-1]), 4) if len(pre) else None,
        pm_volumen_0900=int(pre["v"].sum()) if len(pre) else 0,
        apertura=apertura, cierre=cierre, maximo=float(r["h"].max()), minimo=float(r["l"].min()),
        hora_maximo=hmax.strftime("%H:%M"),
        vol_primeros5=int(r[r["hora"] < T("9:35")]["v"].sum()),
    )
    d["pm_hueco_0900"] = round(d["pm_precio_0900"] / cierre_ant - 1, 4) if d["pm_precio_0900"] else None
    d["apertura_a_cierre"] = round(cierre / apertura - 1, 4)
    d["max_desde_apertura"] = round(d["maximo"] / apertura - 1, 4)
    d["min_desde_apertura"] = round(d["minimo"] / apertura - 1, 4)
    tras = r[r["hora"] >= T("9:35")]
    if len(tras) < 5:
        return d
    p0935 = float(tras["o"].iloc[0])
    d["precio_0935"] = p0935
    d["c0935_a_cierre"] = round(cierre / p0935 - 1, 4)
    a1220 = tras[tras["hora"] < T(reglas["cierre_forzado"])]
    d["c0935_a_1220"] = round(float(a1220["c"].iloc[-1]) / p0935 - 1, 4) if len(a1220) else None
    # Reglas del agente A: compra a las 9:35, stop 1 %, objetivo 3R, trailing y cierre forzado
    stop = p0935 * (1 - reglas["stop_pct"] / 100)
    obj = p0935 + (p0935 - stop) * reglas["rr"]
    res = gestionar(tras, "compra", p0935, stop, obj, T(reglas["cierre_forzado"]), reglas["trailing"], costes)
    d["reglasA_R"], d["reglasA_salida"], d["reglasA_ret_pct"] = res["R"], res["motivo"], res["ret_pct"]
    # Idea «corto del hueco»: vender en corto a las 9:35 si abrió con hueco >= 10 %, stop ancho, sin objetivo,
    # cerrar antes del cierre. Solo es una simulación para saber si compensa (no se opera nada).
    if apertura / cierre_ant - 1 >= 0.10:
        for pct in (10, 15, 25, 35):
            r = gestionar(tras, "venta", p0935, p0935 * (1 + pct / 100), None, T("15:55"), None, costes)
            d[f"corto{pct}_ret_pct"], d[f"corto{pct}_salida"] = r["ret_pct"], r["motivo"]
    return d


# ---------------------------------------------------------------- ORB «acciones en juego»
def rango_apertura(m: pd.DataFrame, minutos: int = 5) -> dict | None:
    r = regular(m)
    fin = tras_apertura(minutos)
    v = r[r["hora"] < fin]
    if len(v) < 2:
        return None
    return dict(o=float(v["o"].iloc[0]), h=float(v["h"].max()), l=float(v["l"].min()), c=float(v["c"].iloc[-1]),
                v=int(v["v"].sum()))


def orb(m: pd.DataFrame, atr14: float, variante: dict, costes: Costes, minutos: int = 5) -> dict | None:
    """Ruptura del rango de los primeros 5 min. Vela verde -> solo compra si rompe el máximo;
    vela roja -> solo venta si rompe el mínimo. Devuelve la operación o None si no hay entrada."""
    ra = rango_apertura(m, minutos)
    if not ra or ra["c"] == ra["o"]:
        return None
    lado = "compra" if ra["c"] > ra["o"] else "venta"
    if lado == "venta" and not variante.get("cortos", True):
        return None
    r = regular(m)
    tras = r[(r["hora"] >= tras_apertura(minutos)) & (r["hora"] < T(variante["fin_entradas"]))]
    nivel = ra["h"] if lado == "compra" else ra["l"]
    rompe = (tras["h"] >= nivel) if lado == "compra" else (tras["l"] <= nivel)
    for ts in tras.index[rompe.to_numpy()][:1]:  # solo la primera vela que rompe
        b = tras.loc[ts]
        entrada = max(nivel, b["o"]) if lado == "compra" else min(nivel, b["o"])
        if variante["stop"] == "atr":
            dist = variante["stop_atr"] * atr14
        else:
            dist = entrada * variante["stop_pct"] / 100
        stop = entrada - dist if lado == "compra" else entrada + dist
        obj = None
        if variante.get("rr"):
            obj = entrada + dist * variante["rr"] if lado == "compra" else entrada - dist * variante["rr"]
        resto = r[r.index >= ts]
        a_mitad = (b["o"] < nivel) if lado == "compra" else (b["o"] > nivel)
        res = gestionar(resto, lado, entrada, stop, obj, T(variante["cierre"]), variante.get("trailing"), costes,
                        entrada_a_mitad=a_mitad)
        res.update(hora_entrada=b["hora"].strftime("%H:%M"), entrada_bruta=round(entrada, 4),
                   riesgo_pct=round(100 * dist / entrada, 3))
        return res
    return None
