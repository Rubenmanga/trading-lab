"""Escáner de la apertura: ¿qué acciones abren hoy con un hueco enorme? (datos gratis de Alpaca)

1) Foto de TODAS las acciones con el feed IEX (gratis y en tiempo real): precio de hoy contra el cierre de ayer.
2) A las que parecen haber saltado mucho se les mira el cierre de ayer y el volumen medio con datos SIP
   (todas las bolsas; gratis porque son de días anteriores) para no fiarse solo de IEX.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from ..estudio.alpaca_rest import DATOS, TRADING_PAPER, Alpaca
from ..estudio.universo import BOLSAS, TICKER


def mercado_abre_hoy(alpaca: Alpaca, hoy: str) -> bool:
    j = alpaca._get(f"{TRADING_PAPER}/v2/clock", {})
    return bool(j.get("is_open")) or str(j.get("next_open", ""))[:10] == hoy


def simbolos_activos(alpaca: Alpaca) -> list[str]:
    out = []
    for a in alpaca.valores():
        if a.get("status") != "active" or not a.get("tradable", True):
            continue
        s = str(a.get("symbol", ""))
        if TICKER.match(s) and (not BOLSAS or a.get("exchange") in BOLSAS):
            out.append(s)
    return sorted(set(out))


def foto_iex(alpaca: Alpaca, simbolos: list[str], trozo: int = 500) -> list[dict]:
    filas = []
    for i in range(0, len(simbolos), trozo):
        j = alpaca._get(f"{DATOS}/v2/stocks/snapshots", {"symbols": ",".join(simbolos[i:i + trozo]), "feed": "iex"})
        for s, x in (j or {}).items():
            if not isinstance(x, dict):
                continue
            prev = (x.get("prevDailyBar") or {}).get("c")
            dia = x.get("dailyBar") or {}
            ult = (x.get("latestTrade") or {}).get("p")
            filas.append(dict(simbolo=s, cierre_ant_iex=prev, apertura_iex=dia.get("o"), ultimo_iex=ult,
                              fecha_dia=str(dia.get("t", ""))[:10]))
    return filas


def candidatos(alpaca: Alpaca, cfg: dict, ahora_ny: datetime, simbolos: list[str] | None = None) -> list[dict]:
    hoy = ahora_ny.strftime("%Y-%m-%d")
    sims = simbolos or simbolos_activos(alpaca)
    foto = [f for f in foto_iex(alpaca, sims) if f["cierre_ant_iex"] and (simbolos or f["fecha_dia"] == hoy)]
    umbral = cfg["hueco_min"] * 0.6   # filtro amplio: luego se confirma con SIP
    pre = [f for f in foto if max(f["apertura_iex"] or 0, f["ultimo_iex"] or 0) / f["cierre_ant_iex"] - 1 >= umbral]
    if simbolos:   # modo ensayo con símbolos elegidos a mano: se miran aunque no tengan hueco
        pre = foto
    if not pre:
        return []
    desde = ahora_ny - timedelta(days=40)
    hasta = ahora_ny.replace(hour=0, minute=0, second=0, microsecond=0)
    d = alpaca.velas([f["simbolo"] for f in pre], "1Day", desde, hasta)
    out = []
    for f in pre:
        b = d[d["simbolo"] == f["simbolo"]] if len(d) else pd.DataFrame()
        if b.empty:
            continue
        b = b.sort_values("t")
        b = b[pd.to_datetime(b["t"]).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d") < hoy]
        if b.empty:
            continue
        cierre_ant = float(b["c"].iloc[-1])
        ult14 = b.tail(14)
        dolares = float((ult14["v"] * ult14["c"]).mean())
        apertura = f["apertura_iex"] or f["ultimo_iex"]
        hueco = apertura / cierre_ant - 1 if cierre_ant > 0 else 0
        c = dict(simbolo=f["simbolo"], cierre_ant=cierre_ant, apertura=apertura, ultimo=f["ultimo_iex"],
                 hueco=round(hueco, 4), dolares_dia=round(dolares))
        if simbolos or (hueco >= cfg["hueco_min"] and apertura >= cfg["precio_min"] and dolares >= cfg["dolares_dia_min"]):
            out.append(c)
    return sorted(out, key=lambda c: -c["hueco"])
