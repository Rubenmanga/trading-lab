"""Conector MT5 para EUR/USD: RECHAZA CUENTAS REALES.

MetaTrader5 oficial requiere terminal MT5 abierto (normalmente Windows).
Las posiciones se protegen con SL/TP EN EL BROKER. El cierre por tiempo
requiere que este proceso permanezca en ejecución; no es una garantía si se cae.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .engine import Bar, PIP, Signal, market_entry_allowed

MAGIC = 26011703


class DemoMT5:
    def __init__(self, symbol: str = "EURUSD"):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise RuntimeError("Instala MetaTrader5 en Windows con terminal abierto") from exc
        if not symbol.upper().startswith("EURUSD"):
            raise ValueError("Agente C restringido exclusivamente a EURUSD")
        self.mt5 = mt5
        self.symbol = symbol
        if not mt5.initialize():
            raise RuntimeError(f"MT5 no conecta: {mt5.last_error()}")
        self.ensure_demo()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Símbolo no disponible: {symbol}")
        self.info = mt5.symbol_info(symbol)
        if self.info is None or not self.info.trade_contract_size:
            raise RuntimeError("Especificaciones de símbolo ausentes")

    def ensure_demo(self):
        account = self.mt5.account_info()
        if account is None or account.trade_mode != self.mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise PermissionError("BLOQUEADO: solo cuentas MetaTrader5 DEMO verificadas")
        if account.currency not in ("EUR", "USD"):
            raise PermissionError("Moneda de cuenta no admitida para dimensionamiento EURUSD")
        return account

    def close(self):
        self.mt5.shutdown()

    def history(self, count: int = 1000) -> list[Bar]:
        self.ensure_demo()
        rates = self.mt5.copy_rates_from_pos(self.symbol, self.mt5.TIMEFRAME_M5, 1, count)
        if rates is None:
            raise RuntimeError(f"Error histórico MT5: {self.mt5.last_error()}")
        rows = sorted(rates, key=lambda x: x["time"])
        # MT5 proporciona generalmente OHLC BID; convertir a precio medio
        # antes de simular fills bid/ask para evitar doble sesgo en el spread.
        return [
            Bar(datetime.fromtimestamp(int(row["time"]), tz=timezone.utc),
                *[float(row[k]) + float(row["spread"]) * self.info.point / 2
                  for k in ("open", "high", "low", "close")],
                float(row["spread"]) * self.info.point / PIP)
            for row in rows
        ]

    def bot_positions(self):
        self.ensure_demo()
        positions = self.mt5.positions_get(symbol=self.symbol)
        if positions is None:
            raise RuntimeError("No se pueden leer posiciones")
        return [p for p in positions if p.magic == MAGIC]

    def all_symbol_positions(self):
        self.ensure_demo()
        positions = self.mt5.positions_get(symbol=self.symbol)
        if positions is None:
            raise RuntimeError("No se pueden verificar posiciones")
        return positions

    def tick(self):
        tick = self.mt5.symbol_info_tick(self.symbol)
        if tick is None or tick.ask <= tick.bid or tick.bid <= 0:
            raise RuntimeError("Cotización MT5 inválida")
        if datetime.now(timezone.utc).timestamp() - tick.time > 20:
            raise RuntimeError("Cotización MT5 caducada >20 segundos")
        return tick

    def close_expired(self, *, max_minutes: int = 120) -> list[dict]:
        """Cierra las posiciones del bot en >120min, también tras reinicios."""
        self.ensure_demo()
        reports = []
        now = datetime.now(timezone.utc)
        for p in self.bot_positions():
            opened = datetime.fromtimestamp(int(p.time), timezone.utc)
            if now - opened >= timedelta(minutes=max_minutes):
                tick = self.tick()
                side = self.mt5.ORDER_TYPE_SELL if p.type == self.mt5.POSITION_TYPE_BUY else self.mt5.ORDER_TYPE_BUY
                price = tick.bid if side == self.mt5.ORDER_TYPE_SELL else tick.ask
                request = dict(action=self.mt5.TRADE_ACTION_DEAL,
                               symbol=self.symbol, position=p.ticket, volume=p.volume,
                               type=side, price=price, deviation=15,
                               magic=MAGIC, comment="FX-C-120min",
                               type_time=self.mt5.ORDER_TIME_GTC,
                               type_filling=self.mt5.ORDER_FILLING_IOC)
                result = self.mt5.order_send(request)
                done = bool(result and result.retcode == self.mt5.TRADE_RETCODE_DONE)
                reports.append({"ticket": p.ticket, "closed": done,
                                "retcode": getattr(result, "retcode", None)})
        return reports

    def daily_stats(self) -> tuple[int, float]:
        """Número de entradas + resultado monetario de salidas del agente, en día UTC."""
        self.ensure_demo()
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        deals = self.mt5.history_deals_get(start, now)
        if deals is None:
            raise RuntimeError("Historial MT5 no disponible: bloqueo preventivo")
        mine = [d for d in deals if d.magic == MAGIC and d.symbol == self.symbol]
        entries = sum(d.entry == self.mt5.DEAL_ENTRY_IN for d in mine)
        pnl = sum(float(d.profit) + float(d.commission) + float(d.swap) for d in mine)
        return entries, pnl

    def place_demo_order(self, signal: Signal, *, risk_fraction: float = 0.0025,
                         max_spread_pips: float = 1.2, max_entries_day: int = 4):
        """Apertura real EN DEMO, con stop y objetivo puestos en la petición."""
        acc = self.ensure_demo()  # volver a comprobar antes de cada orden
        if not (0 < risk_fraction <= 0.0025):
            raise PermissionError("Riesgo por operación excede 0,25%")
        now = datetime.now(timezone.utc)
        if not market_entry_allowed(now) or now - signal.at > timedelta(minutes=12):
            return {"sent": False, "reason": "horario o señal caducada"}
        if self.all_symbol_positions():
            return {"sent": False, "reason": "ya existe una posición EURUSD"}
        entries, net_pnl = self.daily_stats()
        if entries >= max_entries_day or net_pnl <= -0.01 * float(acc.equity):
            return {"sent": False, "reason": "máximo diario o freno de pérdidas"}
        tick = self.tick()
        spread = (tick.ask - tick.bid) / PIP
        if spread > min(max_spread_pips, signal.stop_pips / 4):
            return {"sent": False, "reason": f"spread excesivo: {spread:.2f} pips"}
        side = self.mt5.ORDER_TYPE_BUY if signal.side == "buy" else self.mt5.ORDER_TYPE_SELL
        direction = 1 if signal.side == "buy" else -1
        price = tick.ask if direction == 1 else tick.bid
        stop = round(price - direction * signal.stop_pips * PIP, self.info.digits)
        target = round(price + direction * signal.target_pips * PIP, self.info.digits)
        if signal.stop_pips * PIP < self.info.trade_stops_level * self.info.point:
            return {"sent": False, "reason": "stop menor que mínimo del bróker"}
        loss_one_lot = self.mt5.order_calc_profit(side, self.symbol, 1.0, price, stop)
        if loss_one_lot is None or loss_one_lot >= 0:
            return {"sent": False, "reason": "no se puede calcular riesgo en moneda de cuenta"}
        desired = risk_fraction * float(acc.equity) / abs(loss_one_lot)
        step = float(self.info.volume_step)
        size = math.floor((desired + 1e-10) / step) * step
        size = min(size, float(self.info.volume_max))
        if size < float(self.info.volume_min):
            return {"sent": False, "reason": "lote mínimo superaría el riesgo"}
        # EURUSD: cada lote representa 100k EUR. Limitar apalancamiento económico a 2x.
        notional = size * float(self.info.trade_contract_size)
        equity_eur = float(acc.equity) if acc.currency == "EUR" else float(acc.equity) / price
        if notional > 2 * equity_eur:
            return {"sent": False, "reason": "exposición >2x patrimonio"}
        margin = self.mt5.order_calc_margin(side, self.symbol, size, price)
        if margin is None or margin > 0.10 * float(acc.equity):
            return {"sent": False, "reason": "margen >10% o indeterminable"}
        request = dict(action=self.mt5.TRADE_ACTION_DEAL, symbol=self.symbol,
                       volume=round(size, 8), type=side, price=price, sl=stop, tp=target,
                       deviation=15, magic=MAGIC, comment="FX-C-DEMO",
                       type_time=self.mt5.ORDER_TIME_GTC,
                       type_filling=self.mt5.ORDER_FILLING_IOC)
        check = self.mt5.order_check(request)
        if check is None or check.retcode not in (0, self.mt5.TRADE_RETCODE_DONE):
            return {"sent": False, "reason": "order_check denegada",
                    "retcode": getattr(check, "retcode", None)}
        # Último seguro; no hay ningún camino permitido hacia cuentas LIVE.
        self.ensure_demo()
        result = self.mt5.order_send(request)
        return {"sent": bool(result and result.retcode == self.mt5.TRADE_RETCODE_DONE),
                "retcode": getattr(result, "retcode", None),
                "lots": round(size, 8), "stop": stop, "target": target}
