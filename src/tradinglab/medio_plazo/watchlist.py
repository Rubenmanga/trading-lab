"""Lista de vigilancia: las empresas ya analizadas, con su zona de entrada y su tesis.
Vive en investigacion/watchlist.csv (se sube a GitHub, así la ves desde el móvil)."""
from __future__ import annotations

import csv

from ..common.config import ruta

COLUMNAS = ["ticker", "empresa", "sector", "fecha_analisis", "veredicto", "conviccion",
            "precio_analisis", "zona_entrada_max", "precio_objetivo_12m", "stop_tesis",
            "proximo_catalizador", "fecha_catalizador", "informe"]
VEREDICTOS = {"comprar_en_zona", "vigilar", "descartar"}


def leer(path=None) -> list[dict]:
    path = path or ruta("investigacion", "watchlist.csv")
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except FileNotFoundError:
        return []


def escribir(filas: list[dict], path=None) -> None:
    path = path or ruta("investigacion", "watchlist.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
