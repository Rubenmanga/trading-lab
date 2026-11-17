"""Convierte dos CSV bid/ask de Dukascopy (M5) a barras de precio medio y spread observado.

Uso: python -m tradinglab.fx.dukascopy bid.csv ask.csv output.csv

Dukascopy CLI: timestamp Unix milisegundos en UTC, OHLC bid o ask.
No interpolamos barras ni inventamos spreads que falten.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from .engine import Bar, PIP


def load_side(path: str | Path) -> dict[int, dict[str, float]]:
    data = {}
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        fields = {"timestamp", "open", "high", "low", "close"}
        if not reader.fieldnames or not fields.issubset(reader.fieldnames):
            raise ValueError(f"CSV Dukascopy incorrecto: {path}")
        for row in reader:
            timestamp = int(row["timestamp"])
            if timestamp in data or timestamp <= 0 or timestamp % 300_000:
                raise ValueError("Timestamp duplicado/inválido/no alineado a M5")
            data[timestamp] = {field: float(row[field]) for field in fields - {"timestamp"}}
    return data


def merge(bid_csv: str, ask_csv: str, target: str) -> dict:
    bids, asks = load_side(bid_csv), load_side(ask_csv)
    timestamps = sorted(bids.keys() & asks.keys())
    if not timestamps or len(timestamps) < 300:
        raise ValueError("No hay suficientes barras bid/ask solapadas")
    unmatched = (len(bids.keys() ^ asks.keys()) / max(len(bids), len(asks)))
    if unmatched > 0.02:
        raise ValueError(f"Demasiadas barras desparejadas: {unmatched:.1%}")
    dest = Path(target)
    dest.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    max_spread = 0.0
    with dest.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["timestamp", "open", "high", "low", "close", "spread_pips"])
        for ts in timestamps:
            bid, ask = bids[ts], asks[ts]
            if any(ask[k] < bid[k] for k in ("open", "high", "low", "close")):
                raise ValueError(f"Bid superior a ask: {ts}")
            # Para OHLC estimar el centro de las velas; para spread el peor
            # diferencial de los extremos observados, aproximación conservadora.
            mids = {k: (bid[k]+ask[k])/2 for k in ("open", "high", "low", "close")}
            spread = max((ask[k]-bid[k])/PIP for k in mids)
            if not 0 <= spread < 100:
                raise ValueError("Spread fuera de límites")
            bar = Bar(datetime.fromtimestamp(ts/1000, timezone.utc),
                      mids["open"], max(mids["high"], mids["open"], mids["close"]),
                      min(mids["low"], mids["open"], mids["close"]), mids["close"], spread)
            writer.writerow([bar.timestamp.isoformat(), bar.open, bar.high,
                             bar.low, bar.close, round(spread, 4)])
            count += 1
            max_spread = max(max_spread, spread)
    return {"written": target, "bars": count, "unmatched_ratio": unmatched,
            "max_spread_pips": round(max_spread, 3),
            "note": "M5 bid/ask; spread máximo entre OHLC, no microestructura exacta de ticks"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bid")
    parser.add_argument("ask")
    parser.add_argument("target")
    args = parser.parse_args()
    print(merge(args.bid, args.ask, args.target))


if __name__ == "__main__":
    main()
