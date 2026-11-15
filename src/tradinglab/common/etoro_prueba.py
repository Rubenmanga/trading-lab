"""Prueba de SOLO LECTURA de la API de eToro (demo) frente a Alpaca. No envía órdenes.

Mide: si las claves conectan, qué tarda cada fuente, si los precios coinciden y si eToro
deja operar (largo/corto) los tickers indicados. Escribe un informe corto en Markdown.
Claves por variables de entorno (secretos de GitHub): ETORO_API_KEY, ETORO_USER_KEY. Nunca se imprimen.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

BASE = "https://public-api.etoro.com"
# Lista blanca: solo estas rutas. Nada de órdenes, nada de dinero real.
PERMITIDAS_GET = ("/api/v2/market-data/instruments", "/api/v1/market-data/instruments/")
PERMITIDAS_POST = ("/api/v2/trading/info/demo/eligibility",)


def _llamar(metodo: str, ruta: str, **kw):
    ok = ruta.startswith(PERMITIDAS_GET) if metodo == "GET" else ruta in PERMITIDAS_POST
    if not ok or "/demo/" not in ruta and metodo == "POST":
        raise SystemExit(f"Ruta no permitida en la prueba de solo lectura: {metodo} {ruta}")
    cab = {
        "x-api-key": os.environ["ETORO_API_KEY"].strip(),
        "x-user-key": os.environ["ETORO_USER_KEY"].strip(),
        "x-request-id": str(uuid.uuid4()),
    }
    t0 = time.perf_counter()
    r = requests.request(metodo, BASE + ruta, headers=cab, timeout=30, **kw)
    return r, (time.perf_counter() - t0) * 1000


def _alpaca_velas(simbolo: str, n: int = 30):
    cab = {"APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY", ""), "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY", "")}
    url = f"https://data.alpaca.markets/v2/stocks/{simbolo}/bars"
    t0 = time.perf_counter()
    r = requests.get(url, headers=cab, params={"timeframe": "1Min", "limit": n, "sort": "desc",
                     "feed": os.getenv("ALPACA_FEED", "iex")}, timeout=30)
    ms = (time.perf_counter() - t0) * 1000
    return (r.json().get("bars") or []) if r.ok else [], ms, r.status_code


def main(simbolos: list[str]) -> str:
    if os.getenv("ETORO_API_KEY") is None or os.getenv("ETORO_USER_KEY") is None:
        return "# Prueba eToro\n\nFaltan los secretos ETORO_API_KEY y ETORO_USER_KEY."
    out = [f"# Prueba eToro vs Alpaca (solo lectura, demo)\n\nHecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n",
           "| Ticker | eToro id | eToro ms | Alpaca ms | Último cierre eToro | Último cierre Alpaca | Dif. % | Corto (CFD/real) |",
           "|---|---|---|---|---|---|---|---|"]
    notas = []
    for s in simbolos:
        r, ms_i = _llamar("GET", "/api/v2/market-data/instruments", params={"symbols": s})
        if not r.ok:
            out.append(f"| {s} | error {r.status_code} | | | | | | |")
            notas.append(f"{s}: búsqueda de instrumento HTTP {r.status_code}")
            continue
        datos = r.json()
        lista = datos.get("instruments") or datos.get("items") or (datos if isinstance(datos, list) else [])
        inst = next((i for i in lista if str(i.get("symbol", "")).upper() == s.upper()), None)
        if not inst:
            out.append(f"| {s} | no está en eToro | | | | | | |")
            continue
        iid = inst["instrumentId"]
        r, ms_e = _llamar("GET", f"/api/v1/market-data/instruments/{iid}/history/candles/desc/OneMinute/30")
        c_e = None
        if r.ok:
            try:
                c_e = r.json()["candles"][0]["candles"][0]["close"]
            except Exception:
                notas.append(f"{s}: respuesta de velas eToro inesperada")
        else:
            notas.append(f"{s}: velas eToro HTTP {r.status_code}")
        barras, ms_a, st = _alpaca_velas(s)
        c_a = barras[0]["c"] if barras else None
        dif = f"{(c_e - c_a) / c_a * 100:+.2f}" if c_e and c_a else "n/d"
        corto = "n/d"
        re_, _ = _llamar("POST", "/api/v2/trading/info/demo/eligibility", json={"instrumentId": iid})
        if re_.ok:
            try:
                cfg = re_.json().get("leverageConfigs", [])
                tipos = sorted({f"{c.get('settlementType')}" for c in cfg if c.get("direction") == "short"})
                corto = "/".join(tipos) if tipos else "NO"
            except Exception:
                pass
        else:
            notas.append(f"{s}: elegibilidad HTTP {re_.status_code}")
        out.append(f"| {s} | {iid} | {ms_e:.0f} | {ms_a:.0f} | {c_e} | {c_a} | {dif} | {corto} |")
    if notas:
        out += ["", "Avisos:"] + [f"- {n}" for n in notas]
    out += ["", "Nota: la diferencia puede deberse a que Alpaca gratis usa una sola bolsa (IEX) y a que las velas",
            "no son del mismo minuto exacto. Es una primera foto, no una conclusión definitiva."]
    return "\n".join(out)


if __name__ == "__main__":
    lista = [x.strip().upper() for x in (sys.argv[1] if len(sys.argv) > 1 else "AAPL,AMSC,REPX,PGY,DCTH,ORIC").split(",") if x.strip()]
    texto = main(lista)
    destino = sys.argv[2] if len(sys.argv) > 2 else None
    if destino:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        open(destino, "w", encoding="utf-8").write(texto + "\n")
    print(texto)
