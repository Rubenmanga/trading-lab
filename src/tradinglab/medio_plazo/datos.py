"""Datos gratuitos de empresas (Yahoo Finance a través de la librería yfinance).

Ojo: yfinance es gratis pero no oficial; a veces falla o falta algún dato. Las skills de Claude
completan y contrastan con búsquedas web (informes de resultados, notas de prensa, SEC).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone


def _num(x):
    try:
        x = float(x)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def precio(ticker: str) -> float | None:
    """Último precio. Prueba Yahoo (yfinance) y, si falla, Stooq (también gratis)."""
    try:
        import yfinance as yf
        p = _num(yf.Ticker(ticker).fast_info["last_price"])
        if p:
            return p
    except Exception:  # noqa: BLE001
        pass
    return precio_stooq(ticker)


def precio_stooq(ticker: str) -> float | None:
    import csv
    import io
    import urllib.request
    url = f"https://stooq.com/q/l/?s={ticker.lower()}.us&f=sd2t2ohlcv&h&e=csv"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
            fila = next(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))
        return _num(fila.get("Close"))
    except Exception:  # noqa: BLE001
        return None


def ficha(ticker: str) -> dict:
    """Todo lo que se puede sacar gratis de una empresa, en un diccionario."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    i = t.info or {}
    p = _num(i.get("currentPrice") or i.get("regularMarketPrice"))
    obj = _num(i.get("targetMeanPrice"))
    f = {
        "ticker": ticker.upper(),
        "empresa": i.get("longName") or i.get("shortName"),
        "sector": i.get("sector"), "industria": i.get("industry"), "pais": i.get("country"),
        "descripcion": (i.get("longBusinessSummary") or "")[:1200],
        "precio": p,
        "capitalizacion_usd": _num(i.get("marketCap")),
        "rango_52s": [_num(i.get("fiftyTwoWeekLow")), _num(i.get("fiftyTwoWeekHigh"))],
        "analistas": {
            "numero": i.get("numberOfAnalystOpinions"),
            "recomendacion": i.get("recommendationKey"),
            "objetivo_medio": obj, "objetivo_alto": _num(i.get("targetHighPrice")),
            "objetivo_bajo": _num(i.get("targetLowPrice")),
            "potencial_pct": round((obj / p - 1) * 100, 1) if obj and p else None,
        },
        "valoracion": {
            "per_futuro": _num(i.get("forwardPE")), "precio_ventas": _num(i.get("priceToSalesTrailing12Months")),
            "ev_ebitda": _num(i.get("enterpriseToEbitda")), "precio_valor_contable": _num(i.get("priceToBook")),
        },
        "crecimiento": {
            "ventas_interanual": _num(i.get("revenueGrowth")), "beneficio_interanual": _num(i.get("earningsGrowth")),
        },
        "salud_financiera": {
            "caja_usd": _num(i.get("totalCash")), "deuda_usd": _num(i.get("totalDebt")),
            "flujo_caja_libre_usd": _num(i.get("freeCashflow")), "margen_bruto": _num(i.get("grossMargins")),
            "margen_operativo": _num(i.get("operatingMargins")),
        },
        "accionariado": {
            "insiders_pct": _num(i.get("heldPercentInsiders")), "instituciones_pct": _num(i.get("heldPercentInstitutions")),
            "cortos_sobre_flotante": _num(i.get("shortPercentOfFloat")),
        },
    }
    try:
        cal = t.calendar or {}
        fechas = cal.get("Earnings Date") or []
        f["proximos_resultados"] = [str(d) for d in fechas]
    except Exception:  # noqa: BLE001
        f["proximos_resultados"] = []
    try:
        ud = t.upgrades_downgrades
        if ud is not None and len(ud):
            desde = datetime.now(timezone.utc) - timedelta(days=120)
            ud = ud[ud.index >= desde.replace(tzinfo=None)] if ud.index.tz is None else ud[ud.index >= desde]
            f["cambios_analistas_120d"] = [
                {"fecha": str(idx.date()), **{k: str(v) for k, v in row.items()}} for idx, row in ud.head(15).iterrows()]
    except Exception:  # noqa: BLE001
        pass
    try:
        f["noticias"] = [
            (n.get("content") or n).get("title") for n in (t.news or [])[:10] if (n.get("content") or n).get("title")]
    except Exception:  # noqa: BLE001
        f["noticias"] = []
    return f
