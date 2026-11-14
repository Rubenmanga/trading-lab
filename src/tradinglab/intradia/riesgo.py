"""Gestor de riesgo. Código normal, SIN IA: es la red de seguridad y siempre manda.

Ideas adaptadas de tradermonty/claude-trading-skills (MIT): position-sizer y drawdown-circuit-breaker.
"""
from __future__ import annotations

import math

from .modelos import Senal


class GestorRiesgo:
    def __init__(self, cfg: dict):
        self.stop_pct = cfg["stop_loss_pct"]
        self.rr = cfg["ratio_beneficio_riesgo"]
        self.rr_min = cfg.get("ratio_minimo", self.rr)
        self.riesgo_pct = cfg["riesgo_por_operacion_pct"]
        self.max_expo_pct = cfg.get("max_exposicion_por_operacion_pct", 100)
        self.corte_dia = cfg["corte_perdida_diaria_pct"]
        self.max_ops = cfg["max_operaciones_dia"]
        self.max_abiertas = cfg.get("max_posiciones_abiertas", 99)

    def poner_stop_y_objetivo(self, s: Senal) -> Senal:
        """Stop a un X% (1% por defecto) y objetivo a R veces esa distancia (3:1 o 4:1)."""
        d = s.entrada * self.stop_pct / 100
        if s.lado == "compra":
            s.stop, s.objetivo = s.entrada - d, s.entrada + d * self.rr
        else:
            s.stop, s.objetivo = s.entrada + d, s.entrada - d * self.rr
        s.stop, s.objetivo = round(s.stop, 2), round(s.objetivo, 2)
        return s

    @staticmethod
    def ratio(s: Senal) -> float:
        return abs(s.objetivo - s.entrada) / max(abs(s.entrada - s.stop), 1e-9)

    def puede_operar(self, capital_inicio_dia: float, capital_ahora: float,
                     ops_hoy: int, abiertas: int) -> tuple[bool, str]:
        perdida = (capital_inicio_dia - capital_ahora) / capital_inicio_dia * 100
        if perdida >= self.corte_dia:
            return False, f"Corte diario: el día pierde {perdida:.2f}% (límite {self.corte_dia}%)"
        if ops_hoy >= self.max_ops:
            return False, f"Ya hay {ops_hoy} operaciones hoy (máximo {self.max_ops})"
        if abiertas >= self.max_abiertas:
            return False, f"Ya hay {abiertas} posiciones abiertas (máximo {self.max_abiertas})"
        return True, "ok"

    def tamano(self, capital: float, s: Senal) -> int:
        """Nº de acciones para que, si salta el stop, pierdas solo riesgo_pct del capital.
        Además, nunca se mueve más de max_exposicion_pct del capital en una operación."""
        distancia = abs(s.entrada - s.stop)
        if distancia <= 0 or s.entrada <= 0:
            return 0
        por_riesgo = capital * self.riesgo_pct / 100 / distancia
        por_exposicion = capital * self.max_expo_pct / 100 / s.entrada
        return max(0, math.floor(min(por_riesgo, por_exposicion)))
