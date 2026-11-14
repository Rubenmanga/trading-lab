"""Capa 1: reglas fijas, instantáneas y sin IA."""
from __future__ import annotations

from .modelos import ResultadoCapa, Senal


def revisar(s: Senal, ratio: float, ratio_min: float, ctx: dict) -> ResultadoCapa:
    if not ctx.get("en_ventana_entradas", True):
        return ResultadoCapa("reglas", False, "Fuera del horario de entradas")
    if ctx.get("ya_hay_posicion"):
        return ResultadoCapa("reglas", False, f"Ya hay una posición abierta en {s.simbolo}")
    if ratio + 1e-9 < ratio_min:
        return ResultadoCapa("reglas", False, f"Beneficio/riesgo {ratio:.1f} menor que {ratio_min}")
    if s.entrada <= 0:
        return ResultadoCapa("reglas", False, "Precio de entrada no válido")
    return ResultadoCapa("reglas", True, "Pasa las reglas básicas")
