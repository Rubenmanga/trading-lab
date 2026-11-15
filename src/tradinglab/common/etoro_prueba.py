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
from datetime import datetime, timedelta, timezone

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


def _buscar_lista(datos):
    """Devuelve la primera lista de diccionarios que encuentre en la respuesta."""
    if isinstance(datos, list):
        return [d for d in datos if isinstance(d, dict)]
    if isinstance(datos, dict):
        for v in datos.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        for v in datos.values():
            if isinstance(v, dict):
                lista = _buscar_lista(v)
                if lista:
                    return lista
    return []


def _simbolo(inst: dict) -> str:
    for k in ("symbol", "symbolFull", "internalSymbolFull", "ticker"):
        if inst.get(k):
            return str(inst[k]).upper().split(".")[0]
    return ""


def _forma(datos) -> str:
    """Solo nombres de campos (sin valores) para depurar sin exponer nada."""
    if isinstance(datos, dict):
        partes = []
        for k, v in list(datos.items())[:8]:
            if isinstance(v, list):
                sub = list(v[0].keys())[:12] if v and isinstance(v[0], dict) else []
                partes.append(f"{k}[{len(v)}]{sub}")
            else:
                partes.append(k)
        return ", ".join(partes)
    if isinstance(datos, list):
        return f"lista[{len(datos)}]"
    return type(datos).__name__


def _alpaca_velas(simbolo: str, n: int = 30):
    cab = {"APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY", ""), "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY", "")}
    url = f"https://data.alpaca.markets/v2/stocks/{simbolo}/bars"
    t0 = time.perf_counter()
    desde = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = requests.get(url, headers=cab, params={"timeframe": "1Min", "limit": n, "sort": "desc", "start": desde,
                     "feed": os.getenv("ALPACA_FEED", "iex")}, timeout=30)
    ms = (time.perf_counter() - t0) * 1000
    return (r.json().get("bars") or []) if r.ok else [], ms, r.status_code


def main(simbolos: list[str]) -> str:
    if os.getenv("ETORO_API_KEY") is None or os.getenv("ETORO_USER_KEY") is None:
        return "# Prueba eToro\n\nFaltan los secretos ETORO_API_KEY y ETORO_USER_KEY."
    out = [f"# Prueba eToro vs Alpaca (solo lectura, demo)\n\nHecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n",
           "| Ticker | eToro id | eToro ms | Alpaca ms | Último cierre eToro | Último cierre Alpaca | Dif. % | Corto | Trailing | Stop mín. % |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    notas = []
    for s in simbolos:
        r, ms_i = _llamar("GET", "/api/v2/market-data/instruments", params={"symbols": s})
        if not r.ok:
            out.append(f"| {s} | error {r.status_code} | | | | | | |")
            notas.append(f"{s}: búsqueda de instrumento HTTP {r.status_code}")
            continue
        datos = r.json()
        lista = _buscar_lista(datos)
        inst = next((i for i in lista if _simbolo(i) == s.upper()), None) or (lista[0] if len(lista) == 1 else None)
        if not inst:
            out.append(f"| {s} | no encontrado | | | | | | |")
            notas.append(f"{s}: forma de la respuesta: {_forma(datos)}")
            continue
        iid = inst.get("instrumentId") or inst.get("instrumentID") or inst.get("id")
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
        corto = trailing = sl_min = "n/d"
        re_, _ = _llamar("POST", "/api/v2/trading/info/demo/eligibility",
                         json={"instrumentIds": [int(iid)], "currency": "USD"})
        if re_.ok:
            try:
                eleg = (re_.json().get("eligibilities") or [{}])[0]
                cfg = eleg.get("leverageConfigs") or []
                cortos = [c for c in cfg if str(c.get("direction", "")).lower() == "short"]
                tipos = sorted({str(c.get("settlementType")) for c in cortos})
                corto = "/".join(tipos) if tipos else "NO"
                trailing = "sí" if eleg.get("allowTrailingStopLoss") else "no"
                mins = [c.get("minStopLossPercentage") for c in cfg if c.get("minStopLossPercentage") is not None]
                sl_min = str(min(mins)) if mins else "n/d"
            except Exception:
                notas.append(f"{s}: elegibilidad con forma inesperada: {_forma(re_.json())}")
        else:
            notas.append(f"{s}: elegibilidad HTTP {re_.status_code}")
        if c_a is None:
            notas.append(f"{s}: Alpaca sin velas (HTTP {st})")
        out.append(f"| {s} | {iid} | {ms_e:.0f} | {ms_a:.0f} | {c_e} | {c_a} | {dif} | {corto} | {trailing} | {sl_min} |")
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
