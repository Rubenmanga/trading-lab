"""Botón del pánico: cierra todas las posiciones y cancela órdenes en la cuenta demo de Alpaca."""
from ..common.alpaca_cliente import cliente_trading


def cerrar_todo() -> None:
    c = cliente_trading()
    n = len(c.get_all_positions())
    c.close_all_positions(cancel_orders=True)
    print(f"Enviada orden de cierre para {n} posiciones y canceladas las órdenes pendientes.")
