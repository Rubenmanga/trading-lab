"""Trailing stop: el stop 'persigue' al precio para proteger lo ganado."""
from __future__ import annotations


def nuevo_stop(lado: str, entrada: float, stop_inicial: float, stop_actual: float,
               mejor_precio: float, activar_en_R: float, distancia_pct: float) -> float:
    """Devuelve el stop actualizado (nunca lo empeora).

    1) Mientras la ganancia no llegue a `activar_en_R` veces el riesgo inicial, no se toca.
    2) Al llegar, el stop sube como mínimo a precio de entrada (ya no se pierde).
    3) Después sigue al mejor precio alcanzado a `distancia_pct` %.
    """
    riesgo = abs(entrada - stop_inicial)
    if riesgo <= 0:
        return stop_actual
    if lado == "compra":
        if mejor_precio - entrada < activar_en_R * riesgo:
            return stop_actual
        candidato = max(entrada, mejor_precio * (1 - distancia_pct / 100))
        return round(max(stop_actual, candidato), 2)
    if entrada - mejor_precio < activar_en_R * riesgo:
        return stop_actual
    candidato = min(entrada, mejor_precio * (1 + distancia_pct / 100))
    return round(min(stop_actual, candidato), 2)
