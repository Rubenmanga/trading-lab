"""CLI del agente C: python -m tradinglab.fx {doctor,export,backtest,news,run}.

Por defecto: no envía órdenes. Requiere flag explícito y cuenta demo validada.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .engine import STRATEGIES, backtest, candidates, load_csv
from .news import load_news, update_news

STATE = Path("data/fx-demo")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _print(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _broker(args):
    from .mt5_demo import DemoMT5
    return DemoMT5(args.symbol)


def doctor(args):
    broker = _broker(args)
    try:
        acc = broker.ensure_demo()
        tick = broker.tick()
        _print({"status": "OK", "account": "DEMO", "server": acc.server,
                "symbol": args.symbol, "balance_currency": acc.currency,
                "ask": tick.ask, "bid": tick.bid,
                "spread_pips": round((tick.ask-tick.bid)/0.0001, 2),
                "terminal_required": True})
    finally:
        broker.close()


def export(args):
    broker = _broker(args)
    try:
        rows = broker.history(args.count)
        if len(rows) < 220:
            raise RuntimeError("El terminal MT5 no entregó suficientes barras")
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["timestamp", "open", "high", "low", "close", "spread_pips"])
            for b in rows:
                writer.writerow([b.timestamp.isoformat(), b.open, b.high,
                                 b.low, b.close, round(b.spread_pips, 4)])
        _print({"bars_exported": len(rows), "path": str(dest),
                "source": "MT5 broker demo, precios mid estimados y spread histórico indicado"})
    finally:
        broker.close()


def study(args):
    bars = load_csv(args.csv)
    if len(bars) < 1000:
        raise ValueError("Necesitamos al menos 1000 velas M5 reales para un test exploratorio")
    if any((y.timestamp-x.timestamp) < timedelta(minutes=5)
           for x, y in zip(bars, bars[1:])):
        raise ValueError("Se esperan barras de M5, no M1/ticks ni timestamps duplicados")
    split = int(len(bars)*0.7)
    summary = {"input": args.csv, "bars": len(bars),
               "period": [bars[0].timestamp.isoformat(), bars[-1].timestamp.isoformat()],
               "train_fraction": 0.7, "results": {}}
    for name in STRATEGIES:
        kwargs = dict(strategy=name, slippage_pips=args.slippage,
                      commission_pips_roundtrip=args.commission)
        ins = backtest(bars[:split], **kwargs)
        oos = backtest(bars[max(0, split-240):], **kwargs)
        # El periodo OOS incluye hasta 240 velas solo para calentamiento.
        cutoff = bars[split].timestamp.isoformat()
        oos_trades = [t for t in oos["trades"] if t["start"] >= cutoff]
        from .engine import summarize_trades
        oos_summary = summarize_trades(name, oos_trades)
        summary["results"][name] = {
            "in_sample": {k:v for k,v in ins.items() if k != "trades"},
            "out_of_sample": {k:v for k,v in oos_summary.items() if k != "trades"},
        }
    _write_json(Path(args.output), summary)
    _print({"written": args.output, "bars": len(bars),
            "out_of_sample": {k:v["out_of_sample"] for k,v in summary["results"].items()}})


def news(args):
    _print(update_news(args.output).__dict__)


def runtime(args):
    broker = _broker(args)
    state = Path(args.state)
    news_path = state / "news.json"
    log_path = state / "journal.jsonl"
    enabled = tuple(dict.fromkeys(args.strategies))
    if args.place_demo_orders and not enabled:
        raise ValueError("Para habilitar órdenes demo especifica --strategies NAME")
    if args.place_demo_orders and not args.confirm_demo:
        raise ValueError("Requiere --confirm-demo para enviar órdenes al bróker de PRUEBAS")
    last_bar = None
    last_news = None
    try:
        while True:
            now = datetime.now(timezone.utc)
            # Gestionar posiciones incluso si noticias/API están caídas.
            # Ante fallo de cierre: NO abrir; insistir cada 5 segundos y registrar incidencia.
            try:
                closed = broker.close_expired()
                for item in closed:
                    _record(log_path, {"utc": now.isoformat(), "event": "close_expired", **item})
                if any(not event["closed"] for event in closed):
                    _record(log_path, {"utc": now.isoformat(), "event": "CLOSE_FAILURE", "action": "RETRY"})
                    if args.once:
                        raise RuntimeError("Una orden de cierre demo fue rechazada")
                    time.sleep(5)
                    continue
            except Exception as exc:
                _record(log_path, {"utc": now.isoformat(), "event": "CLOSE_ERROR",
                                   "error_type": type(exc).__name__, "action": "RETRY"})
                if args.once:
                    raise
                time.sleep(5)
                continue
            if last_news is None or (now-last_news).total_seconds() >= 600:
                decision = update_news(news_path, now=now)
                last_news = now
                _record(log_path, {"utc": now.isoformat(), "event": "news",
                                   "allow": decision.allow_entries, "reason": decision.reason})
            bars = broker.history(260)
            if len(bars) >= 220 and bars[-1].timestamp != last_bar:
                last_bar = bars[-1].timestamp
                proposals = [s for s in candidates(bars) if s.strategy in enabled]
                gate = load_news(news_path, now=now)
                # Señales simultáneas opuestas son conflicto, no invitación a duplicar órdenes.
                unambiguous = len({s.side for s in proposals}) <= 1
                for sig in proposals:
                    event = {"utc": now.isoformat(), "event": "signal",
                             "strategy": sig.strategy, "side": sig.side,
                             "stop_pips": sig.stop_pips, "tp_pips": sig.target_pips,
                             "news_allowed": gate.allow_entries}
                    if args.place_demo_orders and gate.allow_entries and unambiguous:
                        # Máximo 1 entrada por barra: primera estrategia priorizada por --strategies.
                        if sig.strategy == next((name for name in enabled if name in
                                                {s.strategy for s in proposals}), None):
                            event["execution"] = broker.place_demo_order(sig)
                    else:
                        event["execution"] = "SHADOW_ONLY"
                    _record(log_path, event)
            if args.once:
                _print({"mode": "DEMO" if args.place_demo_orders else "SHADOW",
                        "state": str(state), "symbols": args.symbol,
                        "strategies": enabled, "active_positions": len(broker.bot_positions())})
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print("Interrumpido. Verifica posiciones abiertas en MT5; los SL/TP permanecen activos.")
    finally:
        broker.close()


def _record(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(data, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Agente C, Forex EUR/USD. SOLO DEMO")
    command = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "export", "run"):
        cmd = command.add_parser(name)
        cmd.add_argument("--symbol", default="EURUSD")
    export_cmd = command.choices["export"]
    export_cmd.add_argument("--count", type=int, default=50000)
    export_cmd.add_argument("--output", default="data/fx-demo/eurusd_m5.csv")
    back_cmd = command.add_parser("backtest")
    back_cmd.add_argument("csv")
    back_cmd.add_argument("--output", default="investigacion/fx/backtest.json")
    back_cmd.add_argument("--slippage", type=float, default=0.15)
    back_cmd.add_argument("--commission", type=float, default=0.25,
                          help="Comisión adicional por ida y vuelta expresada en pips")
    news_cmd = command.add_parser("news")
    news_cmd.add_argument("--output", default="data/fx-demo/news.json")
    run_cmd = command.choices["run"]
    run_cmd.add_argument("--state", default=str(STATE))
    run_cmd.add_argument("--strategies", nargs="*", choices=STRATEGIES, default=[])
    run_cmd.add_argument("--place-demo-orders", action="store_true")
    run_cmd.add_argument("--confirm-demo", action="store_true")
    run_cmd.add_argument("--once", action="store_true")
    args = parser.parse_args()
    {"doctor": doctor, "export": export, "backtest": study,
     "news": news, "run": runtime}[args.command](args)


if __name__ == "__main__":
    main()
