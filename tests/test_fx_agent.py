"""Contrato crítico del tercer agente: sin lookahead, sin LIVE, noticias fail closed."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as Obj

import pytest

from tradinglab.fx.engine import (
    Bar, STRATEGIES, backtest, candidates, load_csv, market_entry_allowed, summarize_trades,
)
from tradinglab.fx.mt5_demo import DemoMT5
from tradinglab.fx.news import load_news, update_news


def bars_oscillating(n=260):
    from math import sin
    t = datetime(2026, 11, 18, 7, tzinfo=timezone.utc)
    result = []
    for i in range(n):
        # Datos SINTÉTICOS SOLO para validar programa, nunca rentabilidad.
        mid = 1.10 + 0.00055 * sin(i * 0.4) + 0.000002 * i
        result.append(Bar(t + timedelta(minutes=5*i),
                          mid, mid+0.0001, mid-0.0001, mid, 0.9))
    return result


def test_five_strategies_named():
    assert len(STRATEGIES) == 5
    b = bars_oscillating()
    assert all(s.strategy in STRATEGIES and s.side in ("buy","sell")
               for s in candidates(b))


def test_backtest_nonnegative_operations_and_costs():
    b = bars_oscillating(700)
    output = backtest(b, strategy="ema_pullback")
    assert output["operations"] == len(output["trades"])
    for trade in output["trades"]:
        assert trade["start"] < trade["end"] or trade["reason"] in ("stop", "target")
        assert trade["strategy"] == "ema_pullback"
    stats = summarize_trades("ema_pullback", output["trades"])
    assert stats["operations"] == output["operations"]


def test_reject_bad_data(tmp_path):
    path = tmp_path / "fx.csv"
    path.write_text("timestamp,open,high,low,close\n2026-11-18T00:00:00Z,1,2,0.5,1\n")
    with pytest.raises(ValueError, match="Faltan"):
        load_csv(path)
    with pytest.raises(ValueError):
        Bar(datetime(2026, 11, 18), 1.0, 1.01, .99, 1.0, 1)


def test_no_entries_near_rollover_or_weekend():
    assert not market_entry_allowed(datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc))
    assert not market_entry_allowed(datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc))
    assert market_entry_allowed(datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc))


def test_mt5_live_account_is_denied():
    broker = object.__new__(DemoMT5)
    broker.mt5 = Obj(account_info=lambda: Obj(trade_mode=2, currency="EUR"),
                     ACCOUNT_TRADE_MODE_DEMO=0)
    with pytest.raises(PermissionError, match="cuentas MetaTrader5 DEMO"):
        broker.ensure_demo()


def test_mt5_demo_account_accepted():
    broker = object.__new__(DemoMT5)
    broker.mt5 = Obj(account_info=lambda: Obj(trade_mode=0, currency="EUR"),
                     ACCOUNT_TRADE_MODE_DEMO=0)
    assert broker.ensure_demo().trade_mode == 0


def test_news_fail_closed_on_unavailable_sources(tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("No network")
    monkeypatch.setattr("tradinglab.fx.news._get", blocked)
    path = tmp_path / "news.json"
    decision = update_news(path)
    assert not decision.allow_entries
    assert decision.reason.startswith("FAIL_CLOSED")
    assert not load_news(path).allow_entries


def test_news_valid_only_when_fresh_and_all_sources(tmp_path):
    import json
    now = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    path = tmp_path / "news.json"
    path.write_text(json.dumps({"checked_at": now.isoformat(), "allow_entries": True,
      "block_until": (now+timedelta(minutes=10)).isoformat(),
      "reason": "LOW", "headlines": [], "sources": ["BCE", "FED", "BLS"]}))
    assert load_news(path, now=now).allow_entries
    assert not load_news(path, now=now+timedelta(minutes=25)).allow_entries


def test_convert_bid_ask_realistic_spread(tmp_path):
    """Contrato de formato del proveedor; números sintéticos, jamás retorno."""
    import csv
    from tradinglab.fx.dukascopy import merge
    first = datetime(2026, 11, 18, 0, tzinfo=timezone.utc)
    bid = tmp_path / "bid.csv"
    ask = tmp_path / "ask.csv"
    for path, shift in ((bid, 0.0), (ask, 0.00009)):
        with path.open("w", newline="", encoding="utf-8") as file:
            w = csv.writer(file)
            w.writerow(["timestamp", "open", "high", "low", "close"])
            for i in range(305):
                ts = first + timedelta(minutes=5*i)
                mid = 1.1 + 0.00002*i + shift
                w.writerow([int(ts.timestamp()*1000), mid, mid+.00011,
                            mid-.00011, mid])
    dest = tmp_path / "mid.csv"
    result = merge(str(bid), str(ask), str(dest))
    rows = load_csv(dest)
    assert result["bars"] == len(rows) == 305
    assert rows[0].spread_pips == pytest.approx(0.9)
    assert rows[0].open == pytest.approx(1.100045)


def test_reject_zero_spread():
    with pytest.raises(ValueError, match="Spread"):
        Bar(datetime(2026, 11, 18, tzinfo=timezone.utc), 1.1, 1.101, 1.099, 1.1, 0)


def test_only_eurusd_is_valid_symbol():
    class FakeMT5:
        def initialize(self):
            return True
    # El bloqueo se comprueba en __init__ antes de intentar conectar con MT5.
    # No importar librería MetaTrader5 real para esta prueba en Linux.
    import sys
    from unittest.mock import patch
    with patch.dict(sys.modules, {"MetaTrader5": FakeMT5()}):
        with pytest.raises(ValueError, match="EURUSD"):
            DemoMT5(symbol="GBPUSD")
