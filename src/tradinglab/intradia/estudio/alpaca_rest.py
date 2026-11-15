"""Cliente mínimo de la API de DATOS de Alpaca (solo lectura), con freno para no pasar el límite gratis.

Plan gratis: 200 llamadas/min y datos SIP (todas las bolsas) siempre que tengan más de 15 min.
Usamos llamadas REST directas para controlar el ritmo y los reintentos.
"""
from __future__ import annotations

import os
import time
from datetime import datetime

import pandas as pd
import requests

from ...common.alpaca_cliente import _claves

DATOS = "https://data.alpaca.markets"
TRADING_PAPER = "https://paper-api.alpaca.markets"  # solo para la lista de valores; nunca dinero real


class Alpaca:
    def __init__(self, por_minuto: int | None = None, sesion: requests.Session | None = None):
        key, secret = _claves()
        self.h = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self.pausa = 60.0 / (por_minuto or int(os.getenv("ALPACA_LLAMADAS_MIN", "180")))
        self.s = sesion or requests.Session()
        self._ultima = 0.0
        self.llamadas = 0
        self.feed = os.getenv("ALPACA_FEED", "sip")

    def _get(self, url: str, params: dict) -> dict:
        for intento in range(6):
            espera = self._ultima + self.pausa - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            self._ultima = time.monotonic()
            self.llamadas += 1
            try:
                r = self.s.get(url, headers=self.h, params=params, timeout=60)
            except requests.RequestException:
                time.sleep(5 * (intento + 1))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(10 * (intento + 1))
                continue
            if r.status_code == 403 and params.get("feed") == "sip":
                # Si la cuenta no permite SIP, seguimos con IEX (menos volumen, pero gratis siempre)
                print("Aviso: SIP no permitido, uso feed IEX")
                self.feed = params["feed"] = "iex"
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"Alpaca no responde tras varios intentos: {url}")

    def valores(self) -> list[dict]:
        """Acciones de EE. UU. activas E inactivas (para no olvidar las que dejaron de cotizar)."""
        out = []
        for estado in ("active", "inactive"):
            j = self._get(f"{TRADING_PAPER}/v2/assets", {"status": estado, "asset_class": "us_equity"})
            out += j if isinstance(j, list) else []
        return out

    def velas(self, simbolos: list[str], timeframe: str, desde: datetime, hasta: datetime) -> pd.DataFrame:
        """Velas de varios símbolos -> DataFrame largo (simbolo, t, o, h, l, c, v). Ajustadas por splits."""
        filas, token = [], None
        while True:
            p = {"symbols": ",".join(simbolos), "timeframe": timeframe, "start": _iso(desde), "end": _iso(hasta),
                 "limit": 10000, "adjustment": "split", "feed": self.feed, "sort": "asc"}
            if token:
                p["page_token"] = token
            j = self._get(f"{DATOS}/v2/stocks/bars", p)
            for s, barras in (j.get("bars") or {}).items():
                for b in barras:
                    filas.append((s, b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]))
            token = j.get("next_page_token")
            if not token:
                break
        df = pd.DataFrame(filas, columns=["simbolo", "t", "o", "h", "l", "c", "v"])
        if len(df):
            df["t"] = pd.to_datetime(df["t"], utc=True)
        return df

    def noticias(self, simbolo: str, desde: datetime, hasta: datetime, limite: int = 20) -> list[dict]:
        j = self._get(f"{DATOS}/v1beta1/news", {"symbols": simbolo, "start": _iso(desde), "end": _iso(hasta),
                                                "limit": limite, "sort": "desc"})
        return j.get("news") or []


def _iso(d: datetime) -> str:
    return pd.Timestamp(d).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ") if pd.Timestamp(d).tzinfo \
        else pd.Timestamp(d).strftime("%Y-%m-%dT%H:%M:%SZ")
