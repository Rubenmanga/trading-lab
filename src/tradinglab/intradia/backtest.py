"""Backtest: probar la estrategia con datos del pasado, con las MISMAS reglas de riesgo,
el mismo horario y el cierre forzado diario. Incluye deslizamiento para no engañarnos.

La IA no se puede probar con datos del pasado (ya 'sabe' lo que pasó), así que aquí va desactivada.
"""
from __future__ import annotations

import pandas as pd

from ..common.db import DB, ahora
from ..common.horario import Horario
from . import estrategias
from .brokers.simulado import BrokerSimulado
from .motor import Motor
from .revisor_ia import RevisorNinguno


def ejecutar(cfg: dict, datos: dict[str, pd.DataFrame], db: DB, etiqueta: str = "backtest") -> dict:
    cfg = {**cfg, "ia": {**cfg["ia"], "modo": "sombra"}}
    hor = Horario(cfg["horario"])
    costes = cfg.get("costes", {})
    broker = BrokerSimulado(cfg["riesgo"]["capital_simulado"], costes.get("deslizamiento_pct", 0),
                            costes.get("comision_por_accion", 0))
    origen = f"{etiqueta}:{ahora()}"
    motor = Motor(cfg, estrategias.crear(cfg["estrategia"]), broker, db, RevisorNinguno(), origen)

    todas = sorted(set().union(*[set(df.index) for df in datos.values()]))
    dia_actual, cerrado_hoy = None, False
    curva = [broker.capital()]
    for ts in todas:
        dia = ts.astimezone(hor.zona).date()
        if dia != dia_actual:
            dia_actual, cerrado_hoy = dia, False
            motor.nuevo_dia()
        if cerrado_hoy:
            continue
        if hor.hay_que_cerrar(ts):
            precios = {s: float(df.loc[:ts, "open"].iloc[-1]) for s, df in datos.items() if len(df.loc[:ts])}
            motor.cerrar_todo(precios, "cierre forzado fin de sesión", ts)
            cerrado_hoy = True
            curva.append(broker.capital())
            continue
        for simbolo, df in datos.items():
            if ts not in df.index:
                continue
            hasta = df.loc[:ts]
            motor.nueva_vela(simbolo, hasta.tail(300), {"ts": ts, "en_ventana_entradas": hor.en_ventana_entradas(ts)})
        curva.append(broker.capital())
    if motor.abiertas:
        motor.cerrar_todo({s: float(df["close"].iloc[-1]) for s, df in datos.items()}, "fin de datos")
        curva.append(broker.capital())

    ops = db.filas("SELECT * FROM operaciones WHERE origen=? AND pnl IS NOT NULL", (origen,))
    resumen = resumir(ops, curva, cfg["riesgo"]["capital_simulado"])
    resumen.update(estrategia=cfg["estrategia"]["nombre"], origen=origen)
    db.insertar("backtests", ts=ahora(), estrategia=resumen["estrategia"], simbolos=",".join(datos),
                desde=str(todas[0]) if todas else "", hasta=str(todas[-1]) if todas else "",
                n_operaciones=resumen["operaciones"], aciertos_pct=resumen["aciertos_pct"],
                profit_factor=resumen["profit_factor"], pnl=resumen["pnl"],
                max_drawdown_pct=resumen["max_drawdown_pct"], detalle=resumen)
    return resumen


def resumir(ops: list[dict], curva: list[float], capital: float) -> dict:
    pnls = [o["pnl"] for o in ops]
    ganadas = [p for p in pnls if p > 0]
    perdidas = [-p for p in pnls if p < 0]
    pico, max_dd = curva[0] if curva else capital, 0.0
    for v in curva:
        pico = max(pico, v)
        max_dd = max(max_dd, (pico - v) / pico * 100)
    motivos: dict[str, int] = {}
    for o in ops:
        motivos[o["motivo_salida"]] = motivos.get(o["motivo_salida"], 0) + 1
    return dict(
        operaciones=len(pnls),
        aciertos_pct=round(100 * len(ganadas) / len(pnls), 1) if pnls else 0.0,
        profit_factor=round(sum(ganadas) / sum(perdidas), 2) if perdidas else (float("inf") if ganadas else 0.0),
        pnl=round(sum(pnls), 2),
        rentabilidad_pct=round(100 * sum(pnls) / capital, 2),
        r_medio=round(sum(o["r_multiple"] for o in ops) / len(ops), 2) if ops else 0.0,
        max_drawdown_pct=round(max_dd, 2),
        salidas=motivos,
    )
