from .base import Estrategia


class Ninguna(Estrategia):
    """No propone nada. Es la opción segura mientras no haya estrategia validada."""
    nombre = "ninguna"

    def senal(self, simbolo, velas):
        return None
