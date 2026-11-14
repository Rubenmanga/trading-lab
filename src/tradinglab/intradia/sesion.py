"""Sesión en vivo: se lanza con el PC encendido durante la ventana de trading.

- Antes de 'inicio' espera.
- Entre 'inicio' y 'fin_entradas' busca entradas.
- Hasta 'cierre_forzado' solo gestiona lo abierto (stop, objetivo, trailing).
- En 'cierre_forzado' cierra TODO y termina. Si pulsas Ctrl+C, también cierra todo.
"""
from __future__ import annotations

import time as _time
from datetime import timedelta

from ..common.alpaca_cliente import velas
from ..common.db import DB
from ..common.horario import Horario
from . import estrategias, revisor_ia
from .brokers.simulado import BrokerSimulado
from .motor import Motor


def _broker(cfg):
    if cfg["broker"] == "alpaca":
        from .brokers.alpaca_paper import BrokerAlpacaPaper
        return BrokerAlpacaPaper()
    costes = cfg.get("costes", {})
    return BrokerSimulado(cfg["riesgo"]["capital_simulado"], costes.get("deslizamiento_pct", 0),
                          costes.get("comision_por_accion", 0))


def ejecutar(cfg: dict) -> None:
    hor = Horario(cfg["horario"])
    broker = _broker(cfg)
    if hasattr(broker, "mercado_abierto") and not broker.mercado_abierto():
        print("La bolsa de EE. UU. está cerrada ahora mismo (o es festivo). No hago nada.")
        return
    motor = Motor(cfg, estrategias.crear(cfg["estrategia"]), broker, DB(), revisor_ia.crear(cfg["ia"]),
                  origen=f"sesion-{cfg['broker']}")
    tf = int(cfg["temporalidad_min"])
    ultima: dict[str, object] = {}
    print(f"Sesión iniciada. Broker: {cfg['broker']}. Estrategia: {cfg['estrategia']['nombre']}. "
          f"IA: {cfg['ia']['revisor']} ({cfg['ia']['modo']}).")
    print(f"Entradas de {hor.en_madrid(hor.inicio)} a {hor.en_madrid(hor.fin_entradas)} (hora de Madrid), "
          f"cierre forzado a las {hor.en_madrid(hor.cierre)}.")
    precios: dict[str, float] = {}
    try:
        while True:
            ahora = hor.ahora()
            if hor.hay_que_cerrar(ahora):
                motor.cerrar_todo(precios, "cierre forzado fin de sesión")
                print("Hora de cierre: todo cerrado. Fin de la sesión.")
                return
            if hor.local(ahora) < hor.inicio:
                _time.sleep(30)
                continue
            datos = velas(cfg["simbolos"], tf, desde=ahora - timedelta(hours=8))
            for simbolo, df in datos.items():
                cerradas = df[df.index + timedelta(minutes=tf) <= ahora]  # solo velas ya terminadas
                if cerradas.empty:
                    continue
                precios[simbolo] = float(df["close"].iloc[-1])
                ts = cerradas.index[-1]
                if ultima.get(simbolo) == ts:
                    continue
                ultima[simbolo] = ts
                motor.nueva_vela(simbolo, cerradas, {"ts": ts, "en_ventana_entradas": hor.en_ventana_entradas(ahora),
                                                     "precio_actual": precios[simbolo]})
            motor.sincronizar()
            _time.sleep(cfg["horario"].get("revisar_cada_seg", 60))
    except KeyboardInterrupt:
        motor.cerrar_todo(precios, "parada manual (Ctrl+C)")
        print("\nParada manual: he cerrado todas las posiciones.")
