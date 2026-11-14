"""Conexión con Alpaca. SOLO cuenta demo (paper): el código no permite otra cosa."""
from __future__ import annotations

import os

from .config import cargar_env


def _claves() -> tuple[str, str]:
    cargar_env()
    if os.getenv("ALPACA_PAPER", "true").strip().lower() != "true":
        raise SystemExit("ALPACA_PAPER debe ser 'true'. Este proyecto no se conecta a dinero real.")
    key, secret = os.getenv("ALPACA_API_KEY", "").strip(), os.getenv("ALPACA_SECRET_KEY", "").strip()
    if not key or not secret:
        raise SystemExit(
            "Faltan las claves de Alpaca. Copia .env.example como .env y pon tus claves de PAPER TRADING."
        )
    return key, secret


def cliente_trading():
    from alpaca.trading.client import TradingClient
    key, secret = _claves()
    cliente = TradingClient(key, secret, paper=True)  # paper=True fijo: nunca dinero real
    assert "paper" in str(getattr(cliente, "_base_url", "paper")), "Solo se permite la URL de paper"
    return cliente


def cliente_datos():
    from alpaca.data.historical import StockHistoricalDataClient
    key, secret = _claves()
    return StockHistoricalDataClient(key, secret)


def velas(simbolos: list[str], minutos: int, desde, hasta=None):
    """Descarga velas (gratis, feed IEX). Devuelve {simbolo: DataFrame(open,high,low,close,volume)}."""
    from alpaca.data.enums import DataFeed
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    req = StockBarsRequest(
        symbol_or_symbols=simbolos,
        timeframe=TimeFrame(minutos, TimeFrameUnit.Minute),
        start=desde, end=hasta, feed=DataFeed.IEX,
    )
    df = cliente_datos().get_stock_bars(req).df
    salida = {}
    for s in simbolos:
        if s in df.index.get_level_values(0):
            salida[s] = df.xs(s, level=0)[["open", "high", "low", "close", "volume"]]
    return salida
