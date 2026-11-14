from __future__ import annotations

from ..modelos import Senal


class Broker:
    """Lo que necesita el agente de cualquier broker (simulado o Alpaca demo)."""

    def capital(self) -> float: ...
    def capital_inicio_dia(self) -> float: ...
    def posiciones(self) -> set[str]: ...                      # símbolos con posición abierta
    def abrir(self, s: Senal, cantidad: int) -> tuple[str, float]: ...  # (id, precio de entrada)
    def actualizar_stop(self, simbolo: str, stop: float) -> None: ...

    def procesar_vela(self, simbolo: str, vela) -> list[dict]:
        """Solo simulado: comprueba si la vela toca stop u objetivo. Devuelve cierres."""
        return []

    def sincronizar(self, abiertas: dict[str, dict]) -> list[dict]:
        """Solo Alpaca: detecta posiciones que el broker ya ha cerrado (stop/objetivo)."""
        return []

    def cerrar_todo(self, precios: dict[str, float], motivo: str) -> list[dict]: ...
    def nuevo_dia(self) -> None: ...
