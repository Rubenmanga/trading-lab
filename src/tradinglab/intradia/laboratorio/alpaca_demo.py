"""Órdenes en la cuenta DEMO (paper) de Alpaca, por REST. La URL de paper está fija: nunca dinero real."""
from __future__ import annotations

import time

import requests

from ...common.alpaca_cliente import _claves  # exige ALPACA_PAPER=true

PAPER = "https://paper-api.alpaca.markets"


class AlpacaDemo:
    def __init__(self, sesion: requests.Session | None = None):
        key, secret = _claves()
        self.h = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self.s = sesion or requests.Session()
        assert PAPER.startswith("https://paper-api."), "Solo se permite la cuenta demo"

    def _pedir(self, metodo: str, ruta: str, **kw):
        for intento in range(4):
            r = self.s.request(metodo, PAPER + ruta, headers=self.h, timeout=30, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(3 * (intento + 1))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Alpaca {r.status_code}: {r.text[:300]}")
            return r.json() if r.text else {}
        raise RuntimeError(f"Alpaca no responde: {ruta}")

    def cuenta(self) -> dict:
        return self._pedir("GET", "/v2/account")

    def reloj(self) -> dict:
        return self._pedir("GET", "/v2/clock")

    def valor(self, simbolo: str) -> dict:
        return self._pedir("GET", f"/v2/assets/{simbolo}")

    def posiciones(self) -> list[dict]:
        return self._pedir("GET", "/v2/positions")

    def ordenes(self, estado: str = "all", desde: str | None = None) -> list[dict]:
        p = {"status": estado, "nested": "true", "limit": 500, "direction": "asc"}
        if desde:
            p["after"] = desde
        return self._pedir("GET", "/v2/orders", params=p)

    def orden_con_stop(self, simbolo: str, qty: int, lado: str, stop: float, objetivo: float, id_cliente: str) -> dict:
        """Orden a mercado con stop y objetivo ya puestos en Alpaca (bracket): funcionan aunque el bot no mire."""
        return self._pedir("POST", "/v2/orders", json={
            "symbol": simbolo, "qty": str(qty), "side": "buy" if lado == "compra" else "sell", "type": "market",
            "time_in_force": "day", "order_class": "bracket", "client_order_id": id_cliente[:48],
            "take_profit": {"limit_price": f"{objetivo:.2f}"}, "stop_loss": {"stop_price": f"{stop:.2f}"}})

    def mover_stop(self, id_orden: str, stop: float) -> dict:
        return self._pedir("PATCH", f"/v2/orders/{id_orden}", json={"stop_price": f"{stop:.2f}"})

    def cancelar(self, id_orden: str):
        return self._pedir("DELETE", f"/v2/orders/{id_orden}")

    def cerrar_posicion(self, simbolo: str) -> dict:
        return self._pedir("DELETE", f"/v2/positions/{simbolo}")
