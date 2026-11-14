"""ESTRATEGIA DE EJEMPLO, solo para comprobar que la tubería funciona.
NO está validada y NO se espera que gane dinero.

Regla: cuando la media rápida cruza por encima de la lenta -> propone compra;
cuando cruza por debajo -> propone venta.
"""
from __future__ import annotations

from ..modelos import Senal
from .base import Estrategia


class CruceMedias(Estrategia):
    nombre = "ejemplo_cruce_medias"

    def __init__(self, media_rapida: int = 9, media_lenta: int = 21):
        self.r, self.l = media_rapida, media_lenta
        self.velas_minimas = media_lenta + 2

    def senal(self, simbolo, velas):
        if len(velas) < self.velas_minimas:
            return None
        c = velas["close"]
        rap, len_ = c.ewm(span=self.r).mean(), c.ewm(span=self.l).mean()
        antes, ahora = rap.iloc[-2] - len_.iloc[-2], rap.iloc[-1] - len_.iloc[-1]
        precio = float(c.iloc[-1])
        if antes <= 0 < ahora:
            return Senal(simbolo, "compra", precio, self.nombre,
                         f"Media {self.r} cruza por encima de la media {self.l}")
        if antes >= 0 > ahora:
            return Senal(simbolo, "venta", precio, self.nombre,
                         f"Media {self.r} cruza por debajo de la media {self.l}")
        return None
