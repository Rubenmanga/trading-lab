"""Base de datos local (SQLite): guarda cada decisión, operación, alerta y backtest con su motivo."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import ruta

ESQUEMA = """
CREATE TABLE IF NOT EXISTS decisiones(
    id INTEGER PRIMARY KEY, ts TEXT, origen TEXT, simbolo TEXT, lado TEXT, estrategia TEXT,
    entrada REAL, stop REAL, objetivo REAL, resultado TEXT, capa TEXT, motivo TEXT,
    ia_modo TEXT, ia_veredicto TEXT, ia_motivo TEXT, detalle TEXT);
CREATE TABLE IF NOT EXISTS operaciones(
    id INTEGER PRIMARY KEY, decision_id INTEGER, origen TEXT, broker_id TEXT,
    simbolo TEXT, lado TEXT, cantidad REAL, entrada REAL, stop_inicial REAL, stop_actual REAL,
    objetivo REAL, ts_apertura TEXT, ts_cierre TEXT, salida REAL, motivo_salida TEXT,
    pnl REAL, r_multiple REAL);
CREATE TABLE IF NOT EXISTS alertas(
    id INTEGER PRIMARY KEY, ts TEXT, ticker TEXT, tipo TEXT, mensaje TEXT);
CREATE TABLE IF NOT EXISTS backtests(
    id INTEGER PRIMARY KEY, ts TEXT, estrategia TEXT, simbolos TEXT, desde TEXT, hasta TEXT,
    n_operaciones INTEGER, aciertos_pct REAL, profit_factor REAL, pnl REAL,
    max_drawdown_pct REAL, detalle TEXT);
"""


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DB:
    def __init__(self, path: str | Path | None = None):
        path = Path(path) if path else ruta("data", "lab.db")
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def insertar(self, tabla: str, **campos) -> int:
        for k, v in campos.items():
            if isinstance(v, (dict, list)):
                campos[k] = json.dumps(v, default=str, ensure_ascii=False)
        cols = ",".join(campos)
        marcas = ",".join("?" * len(campos))
        cur = self.con.execute(f"INSERT INTO {tabla}({cols}) VALUES({marcas})", tuple(campos.values()))
        self.con.commit()
        return cur.lastrowid

    def actualizar(self, tabla: str, id_: int, **campos) -> None:
        sets = ",".join(f"{k}=?" for k in campos)
        self.con.execute(f"UPDATE {tabla} SET {sets} WHERE id=?", (*campos.values(), id_))
        self.con.commit()

    def filas(self, sql: str, params: tuple = ()) -> list[dict]:
        return [dict(r) for r in self.con.execute(sql, params)]
