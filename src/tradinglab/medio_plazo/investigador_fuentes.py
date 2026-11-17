"""Fuentes actuales y selección para la investigación IA.
Los metadatos SEC prueban la existencia de un documento, no su contenido.
Los titulares RSS se etiquetan como secundarios y no verifican afirmaciones.
"""
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime

BUSQUEDAS = [
    'small cap earnings guidance stock when:2d',
    'biotech clinical trial FDA phase 3 stock when:2d',
    'small cap company government contract stock when:2d',
    'small cap merger acquisition 8-K news when:2d',
]
MATERIALES = {"8-K", "10-Q", "10-K", "6-K", "20-F", "S-3", "424B5", "SC 13D"}


def descargar(url, cabeceras=None):
    cab = {"User-Agent": "Trading Lab / research (research@tradinglab.example)",
           "Accept": "application/json,application/xml,*/*"}
    cab.update(cabeceras or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=13) as r:
        return r.read(1_500_000)


def fuente(ticker, fecha, tipo, url, titulo, primaria=False):
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
    digest = hashlib.sha256((ticker + "|" + str(fecha) + "|" + url).encode()).hexdigest()[:12]
    return {"id": digest, "ticker": ticker, "fecha": str(fecha), "tipo": tipo,
            "titulo": re.sub(r"\s+", " ", str(titulo))[:200],
            "url": url, "primaria": bool(primaria)}


def dia_valido(texto, hoy, dias):
    try:
        d = date.fromisoformat(str(texto)[:10])
        return hoy - timedelta(days=dias) <= d <= hoy
    except (ValueError, TypeError):
        return False


def rss_actual(hoy, fetch=descargar):
    noticias, problemas = [], []
    for q in BUSQUEDAS:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        try:
            root = ET.fromstring(fetch(url))
            for nodo in root.findall(".//item")[:20]:
                titulo = (nodo.findtext("title") or "").strip()
                enlace = (nodo.findtext("link") or "").strip()
                try:
                    dia = parsedate_to_datetime(nodo.findtext("pubDate") or "").date()
                except (ValueError, TypeError, IndexError):
                    continue
                if titulo and dia_valido(dia, hoy, 4) and enlace.startswith("https://"):
                    noticias.append((dia.isoformat(), titulo[:200], enlace))
        except (OSError, ValueError, ET.ParseError) as exc:
            problemas.append("RSS: " + type(exc).__name__)
    return list(dict.fromkeys(noticias)), problemas


def titular_corresponde(titulo, ticker, empresa):
    # Evita emparejar siglas cortas al azar.
    if re.search(r"\((?:NASDAQ:|NYSE:)?\s*" + re.escape(ticker) + r"\s*\)", titulo, re.I):
        return True
    if re.search(r"\$" + re.escape(ticker) + r"\b", titulo, re.I):
        return True
    nombre = str(empresa or "")
    nombre = re.sub(r"(?i)\s+(?:inc\.?|corp\.?|corporation|holdings|limited|ltd\.?)$", "", nombre)
    return len(nombre) >= 7 and nombre.lower() in titulo.lower()


def sec_actual(tickers, hoy, fetch=descargar):
    """Metadatos recientes por CIK, hasta 16 compañías; SEC puede bloquear peticiones."""
    resultado, errores = {}, []
    headers = {"User-Agent": os.getenv("SEC_USER_AGENT", "Trading Lab analyst (research@tradinglab.example)")}
    try:
        mapa = json.loads(fetch("https://www.sec.gov/files/company_tickers.json", headers))
        ciks = {x.get("ticker", "").upper(): int(x["cik_str"]) for x in mapa.values()
                if x.get("ticker", "").upper() in tickers}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {}, ["No se pudo obtener CIK oficial: " + type(exc).__name__]
    for ticker in tickers[:16]:
        cik = ciks.get(ticker)
        if not cik:
            continue
        try:
            obj = json.loads(fetch("https://data.sec.gov/submissions/CIK" + str(cik).zfill(10) + ".json", headers))
            filas = obj.get("filings", {}).get("recent", {})
            encontrados = []
            for i, (forma, fecha) in enumerate(zip(filas.get("form", []), filas.get("filingDate", []))):
                if i >= 70:
                    break
                if forma not in MATERIALES or not dia_valido(fecha, hoy, 14):
                    continue
                acceso = filas["accessionNumber"][i].replace("-", "")
                doc = filas["primaryDocument"][i]
                if not re.fullmatch("[0-9]+", acceso) or "/" in doc or ".." in doc:
                    continue
                url = "https://www.sec.gov/Archives/edgar/data/" + str(cik) + "/" + acceso + "/" + doc
                encontrados.append(fuente(ticker, fecha, "SEC " + forma, url,
                                          "Formulario " + forma + " presentado (contenido sin verificar)", True))
            resultado[ticker] = [f for f in encontrados if f]
        except (OSError, ValueError, TypeError, IndexError, KeyError) as exc:
            errores.append("SEC " + ticker + ": " + type(exc).__name__)
    return resultado, errores


def fuentes_ranking(row, hoy):
    t = row["ticker"]
    salida = []
    for doc in (row.get("sec_documentos") or [])[:6]:
        if dia_valido(doc.get("fecha"), hoy, 14):
            # La etiqueta SEC listada no demuestra materialidad para reactivación.
            x = fuente(t, doc["fecha"], "SEC listado", doc.get("url"),
                       doc.get("tipo", "Formulario"), True)
            if x:
                salida.append(x)
    extra = row.get("extra") or {}
    for n in (extra.get("noticias") or [])[:8] + (extra.get("noticias_alpaca") or [])[:8]:
        if dia_valido(n.get("fecha"), hoy, 4):
            x = fuente(t, n["fecha"], "noticia", n.get("url"),
                       n.get("titulo", ""), False)
            if x:
                salida.append(x)
    return salida


def reactivable(previo, fuentes, hoy):
    if previo.get("estado") != "evitar":
        return True
    desde = previo.get("desde", hoy.isoformat())
    ya = set(previo.get("vistas", []))
    return any(
        f["primaria"] and f["tipo"].startswith("SEC ")
        and f["tipo"][4:] in MATERIALES
        and f["fecha"] >= desde and f["id"] not in ya
        for f in fuentes
    )


def candidatos(ranking, watchlist, memoria, noticias, hoy, sec=None, incluir_dormidos=False):
    sec = sec or {}
    seguidas = {w.get("ticker", "").upper() for w in watchlist}
    encontrados = []
    for pos, row in enumerate((ranking.get("filas") or [])[:150]):
        t = str(row.get("ticker", "")).upper()
        if not re.fullmatch(r"[A-Z.]{1,6}", t):
            continue
        try:
            precio = float(row.get("precio", 0))
            if not (precio > 0):
                continue
        except (ValueError, TypeError):
            continue
        fuentes = fuentes_ranking(row, hoy) + sec.get(t, [])
        for fecha, titulo, url in noticias:
            if titular_corresponde(titulo, t, row.get("empresa", "")):
                x = fuente(t, fecha, "titular RSS", url, titulo)
                if x:
                    fuentes.append(x)
        fuentes = list({x["id"]: x for x in fuentes}.values())
        fuentes.sort(key=lambda x: (x["fecha"], x["primaria"]), reverse=True)
        fuentes = fuentes[:10]
        anterior = memoria.get(t, {})
        if not incluir_dormidos and not reactivable(anterior, fuentes, hoy):
            continue
        nueva = t not in seguidas and t not in memoria
        reciente = sum(f["fecha"] >= (hoy - timedelta(days=2)).isoformat() for f in fuentes)
        prioridad = float(row.get("nota") or 0) + (7 if nueva else 0) + min(12, 3*reciente)
        encontrados.append({
            "ticker": t, "empresa": row.get("empresa", ""), "sector": row.get("sector", ""),
            "precio": precio, "precio_fecha": ranking["actualizado"][:10],
            "nota": row.get("nota"), "factores": row.get("factores", {}),
            "banderas": row.get("banderas", []), "proximos_resultados": row.get("proximos_resultados"),
            "capitalizacion": row.get("capitalizacion"), "meses_de_caja": row.get("meses_de_caja"),
            "dilucion_1a_pct": row.get("dilucion_1a_pct"), "fuentes": fuentes,
            "nueva": nueva, "reactivada": anterior.get("estado") == "evitar",
            "prioridad": prioridad, "pos": pos,
        })
    encontrados.sort(key=lambda x: (-x["prioridad"], x["pos"]))
    # El radar debe DESCUBRIR: hasta 20 no seguidas y 10 conocidas con tesis relevantes.
    nuevas = [x for x in encontrados if x["nueva"]][:20]
    conocidas = [x for x in encontrados if not x["nueva"]][:10]
    reactivadas = [x for x in encontrados if x["reactivada"]][:4]
    conjunto = {x["ticker"]: x for x in nuevas + conocidas + reactivadas}
    return sorted(conjunto.values(), key=lambda x: (-x["prioridad"], x["pos"]))[:34]
