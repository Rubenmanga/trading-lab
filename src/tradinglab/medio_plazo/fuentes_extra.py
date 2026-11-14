"""Datos extra con claves GRATUITAS (opcionales): Finnhub y noticias de Alpaca.

Las claves se leen SOLO de variables de entorno (en GitHub: Settings → Secrets → Actions):
  FINNHUB_API_KEY                       → https://finnhub.io (plan gratis: 60 peticiones/minuto)
  ALPACA_API_KEY, ALPACA_SECRET_KEY     → cuenta paper de Alpaca (noticias de Benzinga, gratis)
Si no están, todo sigue funcionando sin estos datos. Las claves nunca se imprimen ni se guardan.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

FINNHUB = "https://finnhub.io/api/v1"
ALPACA_NEWS = "https://data.alpaca.markets/v1beta1/news"


def hay_finnhub() -> bool:
    return bool(os.getenv("FINNHUB_API_KEY"))


def hay_alpaca() -> bool:
    return bool(os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"))


def _get(url: str, cabeceras: dict, intentos: int = 3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "trading-lab", **cabeceras})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:            # demasiadas peticiones: esperar y reintentar
                time.sleep(20 * (i + 1))
                continue
            if e.code in (401, 403):
                raise PermissionError(f"clave rechazada ({e.code})") from None
            return None
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    return None


class Finnhub:
    def __init__(self, pausa: float = 1.05):
        self.cab = {"X-Finnhub-Token": os.environ["FINNHUB_API_KEY"]}  # en cabecera: no sale en URLs ni registros
        self.pausa = pausa

    def _q(self, ruta: str, **params):
        url = f"{FINNHUB}{ruta}?{urllib.parse.urlencode(params)}"
        r = _get(url, self.cab)
        time.sleep(self.pausa)
        return r

    def calendario_resultados(self, dias: int = 75) -> dict[str, str]:
        hoy = date.today()
        r = self._q("/calendar/earnings", **{"from": hoy.isoformat(), "to": (hoy + timedelta(days=dias)).isoformat()})
        out: dict[str, str] = {}
        for e in (r or {}).get("earningsCalendar", []) or []:
            s, d = e.get("symbol"), e.get("date")
            if s and d and (s not in out or d < out[s]):
                out[s] = d
        return out

    def empresa(self, t: str) -> dict:
        hoy = date.today()
        x: dict = {}
        recs = self._q("/stock/recommendation", symbol=t)
        if isinstance(recs, list) and recs:
            x.update(tendencia_recomendaciones(recs))
        ins = self._q("/stock/insider-sentiment", symbol=t, **{"from": (hoy - timedelta(days=200)).isoformat(),
                                                              "to": hoy.isoformat()})
        datos = (ins or {}).get("data") or []
        if datos:
            ult = sorted(datos, key=lambda d: (d.get("year", 0), d.get("month", 0)))[-3:]
            x["insiders_mspr_3m"] = round(sum(d.get("mspr") or 0 for d in ult) / len(ult), 1)
            x["insiders_cambio_acciones_3m"] = sum(d.get("change") or 0 for d in ult)
        ear = self._q("/stock/earnings", symbol=t)
        if isinstance(ear, list) and ear:
            x["sorpresas_finnhub"] = [dict(periodo=e.get("period"), real=e.get("actual"), estimado=e.get("estimate"),
                                           sorpresa_pct=e.get("surprisePercent")) for e in ear[:4]]
        news = self._q("/company-news", symbol=t, **{"from": (hoy - timedelta(days=30)).isoformat(), "to": hoy.isoformat()})
        if isinstance(news, list):
            x["noticias_30d_n"] = len(news)
            x["noticias"] = [dict(fecha=datetime.fromtimestamp(n.get("datetime", 0), timezone.utc).date().isoformat(),
                                  titulo=n.get("headline"), fuente=n.get("source"), url=n.get("url"))
                             for n in news[:6] if n.get("headline")]
        return x


def tendencia_recomendaciones(recs: list[dict]) -> dict:
    """Finnhub da un resumen mensual de recomendaciones. Mide si los analistas se vuelven más optimistas."""
    rs = sorted(recs, key=lambda r: r.get("period", ""), reverse=True)

    def alcista(r):
        tot = sum(r.get(k, 0) or 0 for k in ("strongBuy", "buy", "hold", "sell", "strongSell"))
        return ((r.get("strongBuy", 0) or 0) + (r.get("buy", 0) or 0)) / tot * 100 if tot else None
    ahora = alcista(rs[0])
    antes = alcista(rs[3]) if len(rs) > 3 else (alcista(rs[-1]) if len(rs) > 1 else None)
    out = {"recs_pct_compra": round(ahora, 1) if ahora is not None else None, "recs_periodo": rs[0].get("period")}
    if ahora is not None and antes is not None:
        out["recs_cambio_3m"] = round(ahora - antes, 1)
    return out


def noticias_alpaca(tickers: list[str], dias: int = 30, por_empresa: int = 5) -> dict[str, list[dict]]:
    cab = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: dict[str, list[dict]] = {t: [] for t in tickers}
    for i in range(0, len(tickers), 10):
        grupo = tickers[i:i + 10]
        token = None
        for _ in range(4):  # como mucho 4 páginas de 50 por grupo
            p = dict(symbols=",".join(grupo), start=desde, limit=50, sort="desc")
            if token:
                p["page_token"] = token
            r = _get(f"{ALPACA_NEWS}?{urllib.parse.urlencode(p)}", cab)
            if not r:
                break
            for n in r.get("news", []):
                for s in n.get("symbols", []):
                    if s in out and len(out[s]) < por_empresa:
                        out[s].append(dict(fecha=(n.get("created_at") or "")[:10], titulo=n.get("headline"),
                                           fuente=n.get("source"), url=n.get("url")))
            token = r.get("next_page_token")
            if not token or all(len(out[s]) >= por_empresa for s in grupo):
                break
            time.sleep(0.4)
    return out


def completar(filas: list[dict], top: int = 80, calendario: bool = True) -> dict:
    """Añade datos extra. Devuelve un resumen de lo que se ha podido usar (sin claves)."""
    resumen = {"finnhub": hay_finnhub(), "alpaca": hay_alpaca()}
    if hay_finnhub():
        try:
            fh = Finnhub()
            if calendario:
                cal = fh.calendario_resultados()
                resumen["calendario_resultados"] = len(cal)
                for f in filas:
                    if f["ticker"] in cal:
                        f["proximos_resultados"] = cal[f["ticker"]]
            for f in filas[:top]:
                f.setdefault("extra", {}).update(fh.empresa(f["ticker"]))
            resumen["finnhub_empresas"] = min(top, len(filas))
        except PermissionError as e:
            resumen["finnhub_error"] = str(e)
    if hay_alpaca():
        try:
            nots = noticias_alpaca([f["ticker"] for f in filas[:top]])
            for f in filas[:top]:
                if nots.get(f["ticker"]):
                    f.setdefault("extra", {})["noticias_alpaca"] = nots[f["ticker"]]
            resumen["alpaca_empresas_con_noticias"] = sum(1 for v in nots.values() if v)
        except PermissionError as e:
            resumen["alpaca_error"] = str(e)
    return resumen
