"""Datos inventados (paseo aleatorio) para probar el programa sin claves ni internet."""
from __future__ import annotations

import numpy as np
import pandas as pd


def generar(simbolos: list[str], dias: int = 20, minutos: int = 5, semilla: int = 7) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(semilla)
    fechas = pd.bdate_range(end=pd.Timestamp("2026-11-13"), periods=dias)
    salida = {}
    for i, s in enumerate(simbolos):
        precio, filas = 100.0 + 50 * i, []
        for f in fechas:
            inicio = pd.Timestamp(f.date()).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
            for k in range(0, 390, minutos):
                ts = inicio + pd.Timedelta(minutes=k)
                ret = rng.normal(0, 0.0018)
                o, c = precio, precio * (1 + ret)
                hi, lo = max(o, c) * (1 + abs(rng.normal(0, 0.0008))), min(o, c) * (1 - abs(rng.normal(0, 0.0008)))
                filas.append((ts.tz_convert("UTC"), o, hi, lo, c, int(rng.integers(5_000, 50_000))))
                precio = c
        salida[s] = pd.DataFrame(filas, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")
    return salida
