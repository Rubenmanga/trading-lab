from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Senal:
    """Una idea de operación que propone la estrategia (todavía NO es una orden)."""
    simbolo: str
    lado: str              # "compra" (apuestas a que sube) o "venta" (apuestas a que baja)
    entrada: float
    estrategia: str
    motivo: str = ""       # por qué la estrategia propone la operación
    stop: float = 0.0      # lo rellena el gestor de riesgo (1% por defecto)
    objetivo: float = 0.0  # lo rellena el gestor de riesgo (3R o 4R)
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResultadoCapa:
    capa: str
    pasa: bool
    motivo: str
    extra: dict = field(default_factory=dict)
