"""Broker Alpaca en cuenta DEMO (paper). Precios reales, dinero ficticio.

Cada entrada se envía como orden 'bracket': compra/venta a mercado + objetivo (límite) + stop.
Así, aunque el programa se cuelgue, el stop y el objetivo ya están en Alpaca.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ...common.alpaca_cliente import cliente_trading
from ..modelos import Senal
from .base import Broker


class BrokerAlpacaPaper(Broker):
    def __init__(self):
        self.c = cliente_trading()

    def capital(self):
        return float(self.c.get_account().equity)

    def capital_inicio_dia(self):
        return float(self.c.get_account().last_equity)  # capital al cierre de ayer

    def mercado_abierto(self) -> bool:
        return bool(self.c.get_clock().is_open)

    def posiciones(self):
        return {p.symbol for p in self.c.get_all_positions()}

    def abrir(self, s: Senal, cantidad: int):
        from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest, StopLossRequest, TakeProfitRequest

        orden = self.c.submit_order(MarketOrderRequest(
            symbol=s.simbolo, qty=cantidad,
            side=OrderSide.BUY if s.lado == "compra" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY, order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=round(s.objetivo, 2)),
            stop_loss=StopLossRequest(stop_price=round(s.stop, 2)),
        ))
        return str(orden.id), s.entrada  # el precio real de entrada se corrige al sincronizar

    def _pata_stop(self, simbolo):
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        for o in self.c.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[simbolo], nested=True)):
            for orden in [o, *(o.legs or [])]:
                if "stop" in str(orden.order_type).lower() and orden.stop_price is not None:
                    return orden
        return None

    def actualizar_stop(self, simbolo, stop):
        from alpaca.trading.requests import ReplaceOrderRequest

        pata = self._pata_stop(simbolo)
        if pata is not None:
            self.c.replace_order_by_id(pata.id, ReplaceOrderRequest(stop_price=round(stop, 2)))

    def sincronizar(self, abiertas):
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        vivas = self.posiciones()
        cierres = []
        for simbolo, op in abiertas.items():
            if simbolo in vivas:
                continue
            desde = datetime.now(timezone.utc) - timedelta(hours=12)
            ordenes = self.c.get_orders(GetOrdersRequest(status=QueryOrderStatus.CLOSED, symbols=[simbolo],
                                                         after=desde, nested=True))
            salida, motivo = op["entrada"], "cerrada en broker"
            for o in ordenes:
                for orden in [o, *(o.legs or [])]:
                    if orden.filled_avg_price and str(orden.id) != op.get("broker_id"):
                        salida = float(orden.filled_avg_price)
                        motivo = "stop" if "stop" in str(orden.order_type).lower() else "objetivo"
                        break
            cierres.append(dict(simbolo=simbolo, salida=salida, motivo=motivo))
        return cierres

    def cerrar_todo(self, precios, motivo):
        abiertas = self.posiciones()
        self.c.close_all_positions(cancel_orders=True)
        return [dict(simbolo=s, salida=precios.get(s, 0.0), motivo=motivo) for s in abiertas]
