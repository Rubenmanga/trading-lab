"""Cuenta sombra: broker simulado dentro del programa. No usa dinero ni conexión.
Sirve para backtests y para probar todo sin claves. Idea inspirada en el 'shadow account'
de HKUDS/Vibe-Trading (MIT); implementación propia.
"""
from __future__ import annotations

import itertools

from ..modelos import Senal
from .base import Broker


class BrokerSimulado(Broker):
    def __init__(self, capital: float, deslizamiento_pct: float = 0.0, comision_por_accion: float = 0.0):
        self._capital = self._inicio_dia = capital
        self.slip = deslizamiento_pct / 100
        self.comision = comision_por_accion
        self._ids = itertools.count(1)
        self.abiertas: dict[str, dict] = {}

    def capital(self):
        return self._capital

    def capital_inicio_dia(self):
        return self._inicio_dia

    def nuevo_dia(self):
        self._inicio_dia = self._capital

    def posiciones(self):
        return set(self.abiertas)

    def abrir(self, s: Senal, cantidad: int):
        precio = s.entrada * (1 + self.slip) if s.lado == "compra" else s.entrada * (1 - self.slip)
        oid = f"SIM-{next(self._ids)}"
        self.abiertas[s.simbolo] = dict(id=oid, lado=s.lado, cantidad=cantidad, entrada=precio,
                                        stop=s.stop, objetivo=s.objetivo)
        self._capital -= self.comision * cantidad
        return oid, round(precio, 4)

    def actualizar_stop(self, simbolo, stop):
        if simbolo in self.abiertas:
            self.abiertas[simbolo]["stop"] = stop

    def _cerrar(self, simbolo, precio, motivo):
        p = self.abiertas.pop(simbolo)
        signo = 1 if p["lado"] == "compra" else -1
        self._capital += signo * (precio - p["entrada"]) * p["cantidad"] - self.comision * p["cantidad"]
        return dict(simbolo=simbolo, salida=round(precio, 4), motivo=motivo)

    def procesar_vela(self, simbolo, vela):
        p = self.abiertas.get(simbolo)
        if not p:
            return []
        lo, hi, op = float(vela["low"]), float(vela["high"]), float(vela["open"])
        if p["lado"] == "compra":
            if lo <= p["stop"]:  # si en la misma vela toca stop y objetivo, suponemos lo peor
                precio = min(op, p["stop"]) * (1 - self.slip)
                return [self._cerrar(simbolo, precio, "stop")]
            if hi >= p["objetivo"]:
                return [self._cerrar(simbolo, max(op, p["objetivo"]), "objetivo")]
        else:
            if hi >= p["stop"]:
                precio = max(op, p["stop"]) * (1 + self.slip)
                return [self._cerrar(simbolo, precio, "stop")]
            if lo <= p["objetivo"]:
                return [self._cerrar(simbolo, min(op, p["objetivo"]), "objetivo")]
        return []

    def cerrar_todo(self, precios, motivo):
        return [self._cerrar(s, precios.get(s, self.abiertas[s]["entrada"]), motivo)
                for s in list(self.abiertas)]
