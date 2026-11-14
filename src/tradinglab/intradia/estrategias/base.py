from __future__ import annotations

import pandas as pd

from ..modelos import Senal


class Estrategia:
    """Una estrategia mira las velas de un valor y decide si propone una operación.

    No pone stop ni objetivo: eso lo hace el gestor de riesgo (1% y 3R/4R).
    `velas` es un DataFrame con columnas open, high, low, close, volume, ordenado en el tiempo;
    la última fila es la vela que acaba de cerrar.
    """
    nombre = "base"
    velas_minimas = 30

    def senal(self, simbolo: str, velas: pd.DataFrame) -> Senal | None:
        raise NotImplementedError
