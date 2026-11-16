"""Datos del backtest del agente B (se ejecuta en GitHub Actions, gratis).

1) Cuentas: el archivo masivo de la SEC `companyfacts.zip` (todas las empresas que han presentado cuentas
   en XBRL, también las que ya no cotizan). Se reduce a los conceptos que usa `sec_cuentas` y a las
   acciones en circulación (portada de cada 10-K/10-Q), con su fecha de presentación.
   De paso se guarda un resumen de TODAS las empresas (años con 10-K y activos) para medir cuántas
   desaparecen de la bolsa cada año (sesgo de supervivencia).
2) Precios: Yahoo (yfinance), diario con splits, reducido a fin de mes:
   precio ajustado (con dividendos), precio "de verdad" de aquel día (sin ajustar por splits posteriores,
   para calcular la capitalización real) y volumen medio diario en dólares.

Uso:  python -m tradinglab.backtest12m.datos sec --salida datos_bt
      python -m tradinglab.backtest12m.datos precios --parte 1 --de 4 --salida datos_bt
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
import urllib.request
import zipfile

from ..medio_plazo.fuentes_publicas import _ua
from ..medio_plazo.sec_cuentas import CONCEPTOS, FORMULARIOS_ANUALES

SEC_BULK = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
SEC_TICKERS_BOLSA = "https://www.sec.gov/files/company_tickers_exchange.json"
BOLSAS = {"Nasdaq", "NYSE"}            # sin OTC (chicharros fuera de bolsa)
ACCIONES_DEI = ["EntityCommonStockSharesOutstanding"]
ACCIONES_GAAP = ["CommonStockSharesOutstanding"]
DESDE = "2012-01-01"


def _bajar(url: str, destino: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _ua()})
    with urllib.request.urlopen(req, timeout=600) as r, open(destino, "wb") as fh:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            fh.write(b)
    return destino


def tickers_sec() -> list[dict]:
    """[{cik, ticker, nombre, bolsa}] de las empresas que cotizan HOY en Nasdaq/NYSE (una fila por CIK)."""
    req = urllib.request.Request(SEC_TICKERS_BOLSA, headers={"User-Agent": _ua()})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    campos, vistos, out = d["fields"], set(), []
    for fila in d["data"]:
        x = dict(zip(campos, fila))
        if x.get("exchange") not in BOLSAS or not x.get("ticker") or x["cik"] in vistos:
            continue
        vistos.add(x["cik"])
        out.append({"cik": str(x["cik"]).zfill(10), "ticker": x["ticker"].upper().replace(".", "-"),
                    "nombre": x.get("name"), "bolsa": x["exchange"]})
    return out


def compactar(facts: dict) -> dict:
    """Se queda con los conceptos que usa el backtest y con lo mínimo de cada dato (misma forma que la API)."""
    gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    dei = (facts.get("facts") or {}).get("dei") or {}
    nombres = {n for lista in CONCEPTOS.values() for n in lista}
    out: dict = {"us-gaap": {}, "dei": {}}
    for n in nombres | set(ACCIONES_GAAP):
        if n not in gaap:
            continue
        unidades = {}
        for u, filas in (gaap[n].get("units") or {}).items():
            keep = [{k: x[k] for k in ("start", "end", "val", "form", "filed") if k in x} for x in filas
                    if (x.get("form") in FORMULARIOS_ANUALES or n in ACCIONES_GAAP) and x.get("filed")]
            if keep:
                unidades[u] = keep
        if unidades:
            out["us-gaap"][n] = {"units": unidades}
    for n in ACCIONES_DEI:
        filas = ((dei.get(n) or {}).get("units") or {}).get("shares") or []
        keep = [{"end": x["end"], "val": x["val"], "form": x.get("form"), "filed": x["filed"]}
                for x in filas if x.get("filed") and x.get("end")]
        if keep:
            out["dei"][n] = {"units": {"shares": keep}}
    return {"facts": out}


def resumen_supervivencia(facts: dict) -> dict:
    """{año: activos} de cada 10-K presentado (para medir cuántas empresas dejan de presentar cuentas)."""
    act = (((facts.get("facts") or {}).get("us-gaap") or {}).get("Assets") or {}).get("units", {}).get("USD", [])
    anios: dict[str, float] = {}
    for x in act:
        if x.get("form") in ("10-K", "10-K/A") and x.get("filed"):
            a = x["filed"][:4]
            anios[a] = max(anios.get(a, 0.0), float(x["val"]))
    return anios


def sec(salida: str, zip_local: str | None = None) -> dict:
    os.makedirs(salida, exist_ok=True)
    lista = tickers_sec()
    with open(os.path.join(salida, "tickers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cik", "ticker", "nombre", "bolsa"])
        w.writeheader()
        w.writerows(lista)
    actuales = {x["cik"] for x in lista}
    zp = zip_local or os.path.join(salida, "companyfacts.zip")
    if not os.path.exists(zp):
        t0 = time.monotonic()
        _bajar(SEC_BULK, zp)
        print(f"companyfacts.zip: {os.path.getsize(zp) / 1e6:.0f} MB en {time.monotonic() - t0:.0f} s")
    n_act = n_tot = 0
    superv: dict[str, dict] = {}
    with zipfile.ZipFile(zp) as z, gzip.open(os.path.join(salida, "cuentas.jsonl.gz"), "wt", encoding="utf-8") as out:
        for nombre in z.namelist():
            if not nombre.endswith(".json"):
                continue
            cik = nombre.replace("CIK", "").replace(".json", "").zfill(10)
            try:
                facts = json.loads(z.read(nombre))
            except ValueError:
                continue
            n_tot += 1
            anios = resumen_supervivencia(facts)
            if anios:
                superv[cik] = {"anios": anios, "cotiza_hoy": cik in actuales}
            if cik in actuales:
                out.write(json.dumps({"cik": cik, "facts": compactar(facts)["facts"]}, separators=(",", ":")) + "\n")
                n_act += 1
    with gzip.open(os.path.join(salida, "supervivencia.json.gz"), "wt", encoding="utf-8") as fh:
        json.dump(superv, fh)
    if not zip_local:
        os.remove(zp)
    r = {"empresas_zip": n_tot, "empresas_cotizan_hoy": len(lista), "cuentas_guardadas": n_act}
    print(r)
    return r


# ------------------------------------------------------------------ precios
def a_mensual(df, ticker: str) -> list[dict]:
    """De un DataFrame diario de yfinance (Close, Adj Close, Volume, Stock Splits) a filas de fin de mes."""
    import pandas as pd
    if df is None or df.empty or "Close" not in df:
        return []
    df = df.dropna(subset=["Close"])
    if df.empty:
        return []
    splits = df["Stock Splits"].fillna(0) if "Stock Splits" in df else pd.Series(0.0, index=df.index)
    ratio = splits.where(splits > 0, 1.0)
    # factor de splits POSTERIORES a cada día: precio real de aquel día = Close (ajustado por splits) * factor
    posteriores = ratio[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    real = df["Close"] * posteriores
    adj = df["Adj Close"] if "Adj Close" in df else df["Close"]
    dolares = df["Close"] * df["Volume"].fillna(0)
    meses = df.index.to_period("M")
    out = []
    for m, idx in pd.Series(range(len(df)), index=meses).groupby(level=0):
        i_fin = idx.iloc[-1]
        out.append({"ticker": ticker, "mes": str(m), "adj": round(float(adj.iloc[i_fin]), 6),
                    "real": round(float(real.iloc[i_fin]), 6),
                    "dolares_dia": round(float(dolares.iloc[idx.values].mean()), 0)})
    return out


def precios(salida: str, parte: int = 1, de: int = 1, lote: int = 80, extra: tuple = ("IWM", "IJR")) -> dict:
    import yfinance as yf
    os.makedirs(salida, exist_ok=True)
    if not os.path.exists(os.path.join(salida, "tickers.csv")):
        with open(os.path.join(salida, "tickers.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["cik", "ticker", "nombre", "bolsa"])
            w.writeheader()
            w.writerows(tickers_sec())
    with open(os.path.join(salida, "tickers.csv"), encoding="utf-8") as fh:
        todos = [r["ticker"] for r in csv.DictReader(fh)]
    mios = todos[parte - 1::de] + (list(extra) if parte == 1 else [])
    p = os.path.join(salida, f"precios-{parte}.csv.gz")
    hechos = set()
    if os.path.exists(p):                                  # continuar si se cortó
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            hechos = {r["ticker"] for r in csv.DictReader(fh)}
    pend = [t for t in mios if t not in hechos]
    modo = "at" if hechos else "wt"
    n_ok = 0
    with gzip.open(p, modo, encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ticker", "mes", "adj", "real", "dolares_dia"])
        if not hechos:
            w.writeheader()
        for i in range(0, len(pend), lote):
            grupo = pend[i:i + lote]
            for intento in range(3):
                try:
                    df = yf.download(grupo, start=DESDE, interval="1d", auto_adjust=False, actions=True,
                                     group_by="ticker", threads=True, progress=False)
                    break
                except Exception as e:  # noqa: BLE001
                    print("Yahoo:", type(e).__name__, "reintento", intento + 1, file=sys.stderr)
                    time.sleep(20 * (intento + 1))
            else:
                continue
            for t in grupo:
                try:
                    sub = df[t]
                except KeyError:
                    if len(grupo) > 1:
                        continue
                    sub = df
                filas = a_mensual(sub, t)
                if filas:
                    w.writerows(filas)
                    n_ok += 1
            fh.flush()
            time.sleep(2)
    r = {"parte": parte, "tickers": len(mios), "con_precio": n_ok + len(hechos)}
    print(r)
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("que", choices=["sec", "precios"])
    ap.add_argument("--salida", default="datos_bt")
    ap.add_argument("--parte", type=int, default=1)
    ap.add_argument("--de", type=int, default=1)
    ap.add_argument("--zip")
    a = ap.parse_args(argv)
    if a.que == "sec":
        sec(a.salida, a.zip)
    else:
        precios(a.salida, a.parte, a.de)


if __name__ == "__main__":
    main()
