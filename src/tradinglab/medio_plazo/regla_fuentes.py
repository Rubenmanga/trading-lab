"""Regla de fuentes (paso 4 de la revisión del 16-nov-2026). Sin IA, solo librería estándar.

Todo informe de `investigacion/analisis/TICKER-AAAA-MM-DD*.md` fechado desde `DESDE` debe acabar con
una sección «## Tabla de fuentes» con la tabla `dato | valor | fuente | fecha` (columna `nivel` opcional).

Niveles de fuente:
  1 = oficial: SEC, FDA, ClinicalTrials.gov, nota de prensa de la empresa (agencias de notas o su web).
  2 = datos de mercado: Alpaca, Finnhub, Yahoo, Nasdaq, o los ficheros que deja GitHub Actions en `investigacion/`.
  3 = webs intermediarias (stockanalysis, MarketBeat, TipRanks…): se pueden usar diciéndolo, nunca para precio o caja.

El informe NO pasa si:
  - falta la tabla o le faltan columnas;
  - una fila no tiene fuente (enlace o fichero de `investigacion/`) o fecha AAAA-MM-DD;
  - no hay fila de precio, o el precio tiene más de 2 días de bolsa respecto a la fecha del informe;
  - el precio o la caja salen de una web de nivel 3;
  - ninguna fila usa una fuente de nivel 1;
  - la columna `nivel` dice un nivel mejor que el que tiene la web.

Uso: `python -m tradinglab.medio_plazo.regla_fuentes [ficheros…]` (sin ficheros: todo `investigacion/analisis/`).
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

DESDE = date(2026, 11, 17)  # los informes anteriores a la regla no se revisan
MAX_DIAS_BOLSA_PRECIO = 2
CARPETA = Path("investigacion/analisis")

NIVEL1 = ("sec.gov", "fda.gov", "clinicaltrials.gov", "nih.gov", "globenewswire.com", "prnewswire.com",
          "businesswire.com", "accessnewswire.com", "accesswire.com", "newsfilecorp.com", "usaspending.gov",
          "finra.org", "federalregister.gov", "uspto.gov", "energy.gov", "defense.gov")
NIVEL2 = ("alpaca.markets", "finnhub.io", "finance.yahoo.com", "yahoo.com", "nasdaq.com", "nyse.com",
          "otcmarkets.com", "cboe.com")
NIVEL3 = ("stockanalysis.com", "marketbeat.com", "finviz.com", "tipranks.com", "investing.com", "fool.com",
          "stocktitan.net", "seekingalpha.com", "zacks.com", "simplywall.st", "macrotrends.net",
          "stocktwits.com", "ad-hoc-news.de", "benzinga.com", "marketscreener.com", "wallstreetzen.com",
          "gurufocus.com", "quiverquant.com", "barchart.com", "morningstar.com", "reuters.com",
          "bloomberg.com", "cnbc.com", "wsj.com", "ft.com", "kalkinemedia.com", "boerse-express.com",
          "panabee.com", "quantisnow.com", "insidermonkey.com", "nasdaq.com/articles", "biopharmcatalyst.com",
          "fintel.io", "statista.com")

_NOMBRE = re.compile(r"^(?P<t>[A-Z0-9.]+)-(?P<f>\d{4}-\d{2}-\d{2})(?:-.*)?\.md$")
_URL = re.compile(r"https?://[^\s)\]>|]+")
_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")


def _en(host: str, url: str, lista) -> bool:
    for d in lista:
        dom, _, ruta = d.partition("/")
        if (host == dom or host.endswith("." + dom)) and (not ruta or ("/" + ruta) in url):
            return True
    return False


def nivel_fuente(fuente: str) -> int | None:
    """1, 2 o 3 según la fuente; None si no hay enlace ni fichero del repo. Web desconocida = 3 (sin verificar)."""
    if "investigacion/" in fuente and not _URL.search(fuente):
        return 2
    urls = _URL.findall(fuente)
    if not urls:
        return None
    peor = 1
    for u in urls:
        host = (urlparse(u).hostname or "").lower().removeprefix("www.")
        # el orden importa: nasdaq.com/articles es noticia (3), nasdaq.com a secas es mercado (2)
        n = 3 if _en(host, u, NIVEL3) else 1 if _en(host, u, NIVEL1) else 2 if _en(host, u, NIVEL2) else 3
        peor = max(peor, n)
    return peor


def dias_bolsa(desde: date, hasta: date) -> int:
    """Días laborables (L-V) después de `desde` hasta `hasta` incluido."""
    n, d = 0, desde
    while d < hasta:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def leer_tabla(texto: str) -> tuple[list[str], list[dict]] | None:
    m = re.search(r"^#{2,3}\s*(?:\d+\s*·\s*)?Tabla de fuentes.*$", texto, re.M | re.I)
    if not m:
        return None
    lineas = [l for l in texto[m.end():].splitlines() if l.strip()]
    tabla = []
    for l in lineas:
        if not l.lstrip().startswith("|"):
            if tabla:
                break
            if l.startswith("#"):
                break
            continue
        tabla.append(l)
    if len(tabla) < 2:
        return [], []
    cab = [c.lower() for c in _celdas(tabla[0])]
    filas = [dict(zip(cab, _celdas(l))) for l in tabla[2:]]
    return cab, filas


def revisar(ruta: Path, texto: str | None = None) -> list[str]:
    """Lista de fallos (vacía = pasa). Informes antiguos o con otro nombre: no se revisan."""
    m = _NOMBRE.match(ruta.name)
    if not m:
        return []
    f_inf = date.fromisoformat(m["f"])
    if f_inf < DESDE:
        return []
    texto = ruta.read_text(encoding="utf-8") if texto is None else texto
    t = leer_tabla(texto)
    if t is None:
        return ["falta la sección «## Tabla de fuentes» al final del informe"]
    cab, filas = t
    faltan = [c for c in ("dato", "valor", "fuente", "fecha") if c not in cab]
    if faltan:
        return [f"a la tabla de fuentes le faltan columnas: {', '.join(faltan)}"]
    if not filas:
        return ["la tabla de fuentes está vacía"]
    fallos, hay_n1, hay_precio = [], False, False
    for i, f in enumerate(filas, 1):
        dato = f.get("dato", "") or f"fila {i}"
        n = nivel_fuente(f.get("fuente", ""))
        fe = _FECHA.search(f.get("fecha", ""))
        if n is None:
            fallos.append(f"«{dato}»: sin fuente (pon el enlace o el fichero de investigacion/)")
            continue
        if not fe:
            fallos.append(f"«{dato}»: sin fecha AAAA-MM-DD")
            continue
        try:
            fecha_dato = date.fromisoformat(fe.group())
        except ValueError:
            fallos.append(f"«{dato}»: fecha no válida ({fe.group()})")
            continue
        if fecha_dato > f_inf:
            fallos.append(f"«{dato}»: fecha {fecha_dato} posterior al informe ({f_inf})")
        hay_n1 |= n == 1
        dicho = re.search(r"[123]", f.get("nivel", ""))
        if dicho and int(dicho.group()) < n:
            fallos.append(f"«{dato}»: dice nivel {dicho.group()} pero la web es de nivel {n}")
        clave = dato.lower()
        es_precio = clave.startswith("precio") and "objetivo" not in clave
        es_caja = clave.startswith(("caja", "efectivo", "tesorer"))
        if (es_precio or es_caja) and n == 3:
            fallos.append(f"«{dato}»: el precio y la caja no pueden salir de una web intermediaria (nivel 3)")
        if es_precio:
            hay_precio = True
            if fecha_dato <= f_inf and dias_bolsa(fecha_dato, f_inf) > MAX_DIAS_BOLSA_PRECIO:
                fallos.append(f"«{dato}»: precio del {fecha_dato}, más de {MAX_DIAS_BOLSA_PRECIO} días de bolsa "
                              f"antes del informe ({f_inf})")
    if not hay_precio:
        fallos.append("falta la fila «precio» (con su fecha) en la tabla de fuentes")
    if not hay_n1:
        fallos.append("ninguna fuente oficial (nivel 1: SEC, FDA, ClinicalTrials.gov, nota de la empresa)")
    return fallos


def main(argv: list[str]) -> int:
    rutas = [Path(a) for a in argv] or sorted(CARPETA.glob("*.md"))
    rutas = [r for r in rutas if r.suffix == ".md" and "analisis" in r.parts and r.exists()]
    malos = 0
    for r in rutas:
        fallos = revisar(r)
        if fallos:
            malos += 1
            print(f"NO PASA {r}:")
            for x in fallos:
                print(f"  - {x}")
        elif _NOMBRE.match(r.name) and date.fromisoformat(_NOMBRE.match(r.name)["f"]) >= DESDE:
            print(f"pasa    {r}")
    print(f"Regla de fuentes: {len(rutas)} informes mirados, {malos} no pasan.")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
