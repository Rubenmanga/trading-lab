"""Agente C FX: cinco hipótesis reproducibles, simulación con costes bid/ask.

Nunca ejecuta órdenes. Señales generadas SOLO con velas cerradas.
Los parámetros son hipótesis a contrastar, no estrategias rentables acreditadas.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

PIP = 0.0001
NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")
STRATEGIES = (
    "ema_pullback", "donchian_breakout", "bollinger_reversion",
    "rsi2_rebound", "squeeze_breakout",
)


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    spread_pips: float

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp UTC obligatorio")
        if not 0 < self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("OHLC no válido")
        if not 0 < self.spread_pips < 100:
            raise ValueError("Spread inválido")


@dataclass(frozen=True)
class Signal:
    strategy: str
    side: str
    stop_pips: float
    target_pips: float
    at: datetime

    def __post_init__(self) -> None:
        if self.strategy not in STRATEGIES or self.side not in ("buy", "sell"):
            raise ValueError("Señal desconocida")
        if not 0 < self.stop_pips <= 40 or not 0 < self.target_pips <= 100:
            raise ValueError("Distancia de SL/TP fuera de límites")


def market_entry_allowed(ts: datetime, *, minutes_to_exit: int = 120) -> bool:
    """No operar en cierre semanal ni rollover NY, independientemente del DST."""
    if ts.tzinfo is None:
        return False
    local = ts.astimezone(NY)
    if local.weekday() == 5:
        return False
    if local.weekday() == 6 and (local.hour, local.minute) < (18, 15):
        return False
    minutes = local.hour * 60 + local.minute
    # Salir antes del rollover de las 16:45 NY incluso si salta el time stop.
    return not (16 * 60 + 45 - minutes_to_exit - 10 <= minutes < 18 * 60 + 15)



def session_for(ts: datetime) -> str:
    """Clasificación sin desfase de hora estacional London/NY."""
    london = ts.astimezone(LONDON)
    new_york = ts.astimezone(NY)
    london_open = 8 <= london.hour < 17
    ny_open = 8 <= new_york.hour < 17
    if london_open and ny_open:
        return "Londres_NY_solape"
    if london_open:
        return "Londres"
    if ny_open:
        return "Nueva_York"
    return "Asia_o_baja_actividad"


def ema(values: list[float], span: int) -> float:
    if len(values) < span:
        raise ValueError("Faltan datos EMA")
    result = mean(values[:span])
    alpha = 2 / (span + 1)
    for value in values[span:]:
        result = alpha * value + (1 - alpha) * result
    return result


def atr(bars: list[Bar], window: int = 14) -> float:
    if len(bars) < window + 1:
        raise ValueError("Faltan datos ATR")
    return mean(max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
                for prev, b in zip(bars[-window-1:-1], bars[-window:]))


def rsi(values: list[float], window: int = 14) -> float:
    changes = [v - prev for prev, v in zip(values[-window:], values[-window-1:-1])]
    ups = sum(max(0, x) for x in changes)
    downs = sum(max(0, -x) for x in changes)
    if not (ups + downs):
        return 50.0
    return 100.0 * ups / (ups + downs)


def _make(strategy: str, side: str, atr_value: float, rr: float, ts: datetime) -> Signal:
    stop = min(30.0, max(4.0, atr_value / PIP * 1.25))
    return Signal(strategy, side, round(stop, 3), round(stop * rr, 3), ts)


def candidates(bars: list[Bar], *, strategy: str | None = None) -> list[Signal]:
    """Cinco sistemas sin dependencia de una hora de entrada concreta.
    Solo acepta velas de M5 COMPLETAS, con la última barra cerrada.
    """
    if len(bars) < 220:
        return []
    bars = bars[-240:]
    if any(a.timestamp >= b.timestamp for a, b in zip(bars[:-1], bars[1:])):
        raise ValueError("Barras desordenadas/duplicadas")
    closes = [b.close for b in bars]
    now, prev = bars[-1], bars[-2]
    if not market_entry_allowed(now.timestamp + timedelta(minutes=5)):
        return []
    volatility = atr(bars)
    if not 2 * PIP <= volatility <= 35 * PIP:
        return []
    out: list[Signal] = []
    e20, e50, e200 = ema(closes, 20), ema(closes, 50), ema(closes, 200)
    prev20 = ema(closes[:-1], 20)

    if strategy in (None, "ema_pullback"):
            # 1. Retroceso a EMA20 a favor de EMA50; evita entrada en el cruce de medias.
        if e20 > e50 and prev.close <= prev20 and now.close > e20 and now.close > prev.close:
            out.append(_make("ema_pullback", "buy", volatility, 1.5, now.timestamp))
        if e20 < e50 and prev.close >= prev20 and now.close < e20 and now.close < prev.close:
            out.append(_make("ema_pullback", "sell", volatility, 1.5, now.timestamp))

    if strategy in (None, "donchian_breakout"):
            # 2. Donchian de 24 velas + filtro de volatilidad, sin mirar la vela actual.
        if atr(bars, 14) > 0.85 * atr(bars, 60):
            high24 = max(b.high for b in bars[-25:-1])
            low24 = min(b.low for b in bars[-25:-1])
            if now.close > high24 and prev.close <= high24:
                out.append(_make("donchian_breakout", "buy", volatility, 1.8, now.timestamp))
            if now.close < low24 and prev.close >= low24:
                out.append(_make("donchian_breakout", "sell", volatility, 1.8, now.timestamp))

    if strategy in (None, "bollinger_reversion"):
            # 3. Regresión a la media en rango: z-score + RSI14 + eficiencia de trayectoria.
        sample = closes[-20:]
        std = pstdev(sample)
        path = sum(abs(x-y) for x,y in zip(closes[-21:-1], closes[-20:]))
        efficiency = abs(closes[-1] - closes[-21]) / path if path else 1
        z = (now.close - mean(sample)) / std if std > 0 else 0
        if efficiency < 0.37 and z < -1.8 and rsi(closes, 14) < 35:
            out.append(_make("bollinger_reversion", "buy", volatility, 1.25, now.timestamp))
        if efficiency < 0.37 and z > 1.8 and rsi(closes, 14) > 65:
            out.append(_make("bollinger_reversion", "sell", volatility, 1.25, now.timestamp))

    if strategy in (None, "rsi2_rebound"):
            # 4. Reversión RSI(2) en tendencia EMA200; no confundir con momentum intradía acreditado.
        two = rsi(closes, 2)
        if now.close > e200 and two < 8 and now.close < prev.close:
            out.append(_make("rsi2_rebound", "buy", volatility, 1.3, now.timestamp))
        if now.close < e200 and two > 92 and now.close > prev.close:
            out.append(_make("rsi2_rebound", "sell", volatility, 1.3, now.timestamp))

    if strategy in (None, "squeeze_breakout"):
            # 5. Ruptura tras compresión de Bollinger20, comparada con 100 barras previas.
        widths = []
        for i in range(20, len(closes)):
            block = closes[i-20:i]
            widths.append(4 * pstdev(block) / mean(block))
        previous_width = widths[-2]
        baseline = sorted(widths[-101:-2])
        squeeze_threshold = baseline[int(len(baseline) * 0.2)]
        if previous_width < squeeze_threshold:
            high20 = max(b.high for b in bars[-21:-1])
            low20 = min(b.low for b in bars[-21:-1])
            if now.close > high20 and now.close > prev.close:
                out.append(_make("squeeze_breakout", "buy", volatility, 1.8, now.timestamp))
            if now.close < low20 and now.close < prev.close:
                out.append(_make("squeeze_breakout", "sell", volatility, 1.8, now.timestamp))
    return out


def load_csv(path: str | Path) -> list[Bar]:
    """CSV en UTC: timestamp,open,high,low,close,spread_pips.
    Spread real obligatorio. Sin ello no hay backtest defendible.
    """
    bars = []
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"timestamp", "open", "high", "low", "close", "spread_pips"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"Faltan columnas: {required}")
        for row in reader:
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("CSV requiere timestamp con zona UTC explícita")
            bars.append(Bar(stamp.astimezone(timezone.utc), *(float(row[k]) for k in
                         ("open", "high", "low", "close", "spread_pips"))))
    for a, b in zip(bars[:-1], bars[1:]):
        if a.timestamp >= b.timestamp:
            raise ValueError("CSV temporalmente desordenado")
    return bars


def backtest(bars: list[Bar], *, strategy: str, slippage_pips: float = 0.15,
             commission_pips_roundtrip: float = 0.25, spread_max_pips: float = 1.2) -> dict:
    """Simulador conservador sobre M5: señal al cierre, entrada en siguiente apertura.
    Pérdida si SL y TP ocurren en la misma vela. Una posición simultánea.
    Exige M5 histórico real, no datos sintéticos; incluye medio spread por extremo.
    """
    if strategy not in STRATEGIES:
        raise ValueError("Estrategia no existe")
    if slippage_pips < 0 or commission_pips_roundtrip < 0:
        raise ValueError("Costes inválidos")
    trades = []
    i = 220
    while i < len(bars) - 1:
        signal = next((s for s in candidates(bars[max(0, i-239):i+1], strategy=strategy) if s.strategy == strategy), None)
        b = bars[i + 1]
        if (signal is None or b.timestamp - bars[i].timestamp > timedelta(minutes=5)
                or b.spread_pips > spread_max_pips or
                b.spread_pips > signal.stop_pips / 4 or
                not market_entry_allowed(b.timestamp)):
            i += 1
            continue
        direction = 1 if signal.side == "buy" else -1
        entry = b.open + direction * (b.spread_pips / 2 + slippage_pips) * PIP
        stop = entry - direction * signal.stop_pips * PIP
        target = entry + direction * signal.target_pips * PIP
        exitprice, reason, j = None, None, None
        for j in range(i+1, len(bars)):
            candle = bars[j]
            # Los huecos >5m invalidan cualquier fill presupuestado.
            if j > i + 1 and candle.timestamp - bars[j-1].timestamp > timedelta(minutes=5):
                exitprice = candle.open - direction * (candle.spread_pips / 2 + slippage_pips) * PIP
                reason = "gap"
                break
            if candle.timestamp - b.timestamp >= timedelta(minutes=120):
                exitprice = candle.open - direction * (candle.spread_pips / 2 + slippage_pips) * PIP
                reason = "120min"
                break
            half = candle.spread_pips * PIP / 2
            adverse = (candle.low - half) if direction == 1 else (candle.high + half)
            favorable = (candle.high - half) if direction == 1 else (candle.low + half)
            touches_stop = adverse <= stop if direction == 1 else adverse >= stop
            touches_target = favorable >= target if direction == 1 else favorable <= target
            if touches_stop:
                exitprice = min(stop, candle.open-half) if direction == 1 else max(stop, candle.open+half)
                exitprice -= direction * slippage_pips * PIP
                reason = "stop"
                break
            if touches_target:
                exitprice = target - direction * slippage_pips * PIP
                reason = "target"
                break
        if exitprice is None or j is None:
            break
        net_pips = direction * (exitprice - entry) / PIP - commission_pips_roundtrip
        trades.append({
            "strategy": strategy, "side": signal.side, "start": b.timestamp.isoformat(),
            "end": bars[j].timestamp.isoformat(), "reason": reason,
            "R": round(net_pips / signal.stop_pips, 5), "pips_net": round(net_pips, 3),
            "utc_hour": b.timestamp.hour, "session": session_for(b.timestamp),
        })
        i = j + 1  # sin reentrar en la vela usada para salir
    rets = [t["R"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r < 0]
    equity, peak, dd = 0.0, 0.0, 0.0
    for r in rets:
        equity += r
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    slices = {}
    for label in ("Londres_NY_solape", "Londres", "Nueva_York", "Asia_o_baja_actividad"):
        vals = [t["R"] for t in trades if t["session"] == label]
        slices[label] = {"operations": len(vals), "expectancy_R": round(mean(vals), 4) if vals else None}
    return {
        "strategy": strategy, "source": "CSV histórico REAL del bróker; spread por vela",
        "operations": len(trades), "win_rate": round(len(wins) / len(rets), 4) if rets else None,
        "expectancy_R": round(mean(rets), 4) if rets else None,
        "profit_factor": round(sum(wins) / -sum(losses), 4) if losses else None,
        "max_drawdown_R": round(dd, 4), "session_slices": slices, "trades": trades,
        "disclaimer": "Hipótesis sin validación OOS ni prueba de ejecución real; gastos estimados.",
    }


def summarize_trades(strategy: str, trades: list[dict]) -> dict:
    """Recalcula estadísticas sobre cualquier partición cronológica real."""
    rets = [float(t["R"]) for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r < 0]
    equity, peak, dd = 0.0, 0.0, 0.0
    for r in rets:
        equity += r
        peak = max(peak, equity)
        dd = max(dd, peak-equity)
    slices = {}
    for label in ("Londres_NY_solape", "Londres", "Nueva_York", "Asia_o_baja_actividad"):
        vals = [float(t["R"]) for t in trades if t.get("session",
                session_for(datetime.fromisoformat(t["start"]))) == label]
        slices[label] = {"operations": len(vals),
                         "expectancy_R": round(mean(vals), 4) if vals else None}
    return {"strategy": strategy, "operations": len(trades),
            "win_rate": round(len(wins)/len(rets), 4) if rets else None,
            "expectancy_R": round(mean(rets), 4) if rets else None,
            "profit_factor": round(sum(wins)/-sum(losses), 4) if losses else None,
            "max_drawdown_R": round(dd, 4), "session_slices": slices,
            "trades": trades}
