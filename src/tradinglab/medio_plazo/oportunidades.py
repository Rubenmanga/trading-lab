"""Buscador de oportunidades a 12 meses (agente B): embudo + puntuación multifactor.

Embudo:
  1. Universo: TODAS las small caps de EE. UU. del rango configurado (Yahoo, gratis), sin sectores excluidos.
  2. Filtro rápido: liquidez, precio mínimo, solo acciones normales (fuera fondos y SPAC).
  3. Datos a fondo de cada superviviente (metricas.empresa).
  4. Puntuación 0-100 en 8 factores, comparando cada empresa con el resto (y con su sector en
     valoración y calidad), más penalizaciones por banderas rojas.
  5. Carril (tipo de oportunidad) y señales técnicas de entrada.
  6. Ranking en investigacion/ranking.json y ranking.md → panel web y skill `oportunidades-12m`.

La parte de puntuación (puntuar) es pura: no descarga nada, así se puede probar sin internet.
Inspiración: us-undervalued-growth-screener, canslim-screener, vcp-screener, pead-screener
(tradermonty/claude-trading-skills, MIT) y el flujo de analistas de TauricResearch/TradingAgents (Apache-2.0).
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean

from ..common.config import ruta
from ..common.db import ahora

# ---------------------------------------------------------------- factores
# Cada factor = lista de (métrica, sentido). sentido +1: más es mejor; -1: menos es mejor.
# "sector": True → se compara solo con empresas de su sector (si hay suficientes).
FACTORES = {
    "calidad": dict(sector=True, metricas=[
        ("margen_bruto", 1), ("margen_operativo", 1), ("roe", 1), ("roa", 1),
        ("rent_fcf_pct", 1), ("fcf_trim_positivos", 1)]),
    "crecimiento": dict(sector=False, metricas=[
        ("crec_ventas", 1), ("crec_ventas_ult_trim", 1), ("crec_ventas_sig_anio", 1),
        ("crec_bpa_anio", 1), ("crec_bpa_sig_anio", 1)]),
    "valoracion": dict(sector=True, metricas=[
        ("per_futuro_pos", -1), ("ev_ventas", -1), ("ev_ebitda_pos", -1),
        ("rent_fcf_menos_sbc_pct", 1), ("peg_pos", -1)]),
    "revisiones": dict(sector=False, metricas=[
        ("rev_bpa_30d_anio", 1), ("rev_bpa_90d_anio", 1), ("rev_bpa_90d_sig", 1),
        ("revisiones_neto", 1), ("mejoras_neto_90d", 1), ("objetivos_neto_90d", 1)]),
    "insiders": dict(sector=False, metricas=[("insiders_neto_pct", 1), ("insiders_compras_n", 1)]),
    "momentum": dict(sector=False, metricas=[
        ("ret_12m_1m", 1), ("ret_6m", 1), ("fuerza_relativa_6m", 1), ("sobre_ma200_pct", 1),
        ("dist_max52_pct", 1)]),
    "catalizadores": dict(sector=False, metricas=[
        ("sorpresa_media", 1), ("sorpresas_positivas", 1), ("resultados_cerca", 1), ("hueco_pead", 1)]),
    "solidez": dict(sector=False, metricas=[
        ("caja_neta_sobre_cap", 1), ("meses_de_caja_cap", 1), ("dilucion_1a_pct", -1),
        ("cortos_flotante", -1), ("deuda_neta_ebitda", -1), ("max_caida_1a_pct", 1)]),
}

PESOS_DEFECTO = dict(calidad=15, crecimiento=15, valoracion=15, revisiones=20, insiders=5,
                     momentum=10, catalizadores=5, solidez=15)

NOMBRES = dict(calidad="Calidad", crecimiento="Crecimiento", valoracion="Valoración",
               revisiones="Revisiones analistas", insiders="Directivos", momentum="Momentum",
               catalizadores="Catalizadores", solidez="Solidez")


def _derivadas(f: dict, hoy=None) -> dict:
    """Métricas auxiliares para que todas 'apunten' bien (p. ej. PER negativo = sin dato)."""
    from datetime import date
    hoy = hoy or date.today()
    pos = lambda x: x if (x is not None and x > 0) else None  # noqa: E731
    f["per_futuro_pos"] = pos(f.get("per_futuro"))
    f["ev_ebitda_pos"] = pos(f.get("ev_ebitda"))
    f["peg_pos"] = pos(f.get("peg"))
    s, b = f.get("revisiones_suben_30d"), f.get("revisiones_bajan_30d")
    f["revisiones_neto"] = (s - b) if s is not None and b is not None else None
    mu, mb = f.get("mejoras_90d"), f.get("rebajas_90d")
    f["mejoras_neto_90d"] = (mu - mb) if mu is not None and mb is not None else None
    ou, ob = f.get("objetivos_suben_90d"), f.get("objetivos_bajan_90d")
    f["objetivos_neto_90d"] = (ou - ob) if ou is not None and ob is not None else None
    cap, caja, deuda = f.get("capitalizacion"), f.get("caja"), f.get("deuda")
    fcf0 = f.get("fcf_4t", f.get("fcf"))
    if f.get("meses_de_caja") is None and caja is not None and fcf0 is not None and fcf0 < 0:
        f["meses_de_caja"] = caja / (-fcf0 / 12)
    f["caja_neta_sobre_cap"] = ((caja or 0) - (deuda or 0)) / cap if cap and caja is not None else None
    mc = f.get("meses_de_caja")
    fcf = f.get("fcf_4t", f.get("fcf"))
    f["meses_de_caja_cap"] = 60 if (fcf is not None and fcf >= 0) else (min(mc, 60) if mc is not None else None)
    pr = f.get("proximos_resultados")
    try:
        dias = (date.fromisoformat(pr[:10]) - hoy).days if pr else None
    except ValueError:
        dias = None
    f["dias_a_resultados"] = dias
    f["resultados_cerca"] = (1 if 0 <= dias <= 45 else 0) if dias is not None else None
    f["hueco_pead"] = (1 if f.get("hueco_mantenido") else 0) if "hueco_reciente_pct" in f else 0
    return f


def _percentiles(valores: list[float | None], sentido: int) -> list[float | None]:
    """Convierte valores en percentil 0-100 (empates comparten puesto). None se queda None."""
    pares = sorted((v * sentido, i) for i, v in enumerate(valores) if v is not None)
    out: list[float | None] = [None] * len(valores)
    n = len(pares)
    if n == 0:
        return out
    j = 0
    while j < n:
        k = j
        while k + 1 < n and pares[k + 1][0] == pares[j][0]:
            k += 1
        p = 100.0 * ((j + k) / 2) / (n - 1) if n > 1 else 50.0
        for t in range(j, k + 1):
            out[pares[t][1]] = p
        j = k + 1
    return out


def banderas(f: dict) -> list[tuple[str, int]]:
    """Banderas rojas con su penalización (puntos que se restan a la nota total)."""
    b = []
    d = f.get("dilucion_1a_pct")
    if d is not None and d > 25:
        b.append(("Dilución muy fuerte (+%.0f%% acciones en 1 año)" % d, 15))
    elif d is not None and d > 10:
        b.append(("Dilución (+%.0f%% acciones en 1 año)" % d, 8))
    mc = f.get("meses_de_caja")
    if mc is not None and mc < 12:
        b.append(("Caja para menos de 12 meses (%.0f)" % mc, 15))
    elif mc is not None and mc < 24:
        b.append(("Caja para menos de 2 años (%.0f meses)" % mc, 6))
    dn = f.get("deuda_neta_ebitda")
    if dn is not None and dn > 4:
        b.append(("Deuda alta (%.1f veces EBITDA)" % dn, 8))
    c = f.get("cortos_flotante")
    if c is not None and c > 0.20:
        b.append(("Muchas posiciones cortas (%.0f%%)" % (c * 100), 5))
    if (f.get("analistas") or 0) < 2:
        b.append(("Casi sin analistas (datos de previsión poco fiables)", 5))
    if f.get("rev_bpa_90d_anio") is not None and f["rev_bpa_90d_anio"] < -15:
        b.append(("Previsiones de beneficio recortadas >15%% en 90 días", 6))
    return b


def carril(sc: dict) -> str:
    """Tipo de oportunidad (idea de los 'lanes' del screener GARP de tradermonty)."""
    g, v, q, r, mo = (sc.get(k, 50) for k in ("crecimiento", "valoracion", "calidad", "revisiones", "momentum"))
    if g >= 60 and v >= 55 and q >= 50:
        return "GARP (crecimiento a buen precio)"
    if g >= 80 and r >= 60:
        return "Crecimiento fuerte"
    if q >= 65 and v >= 65:
        return "Calidad barata"
    if r >= 75 and mo < 50:
        return "Giro: previsiones mejorando tras caída"
    if mo >= 80 and r >= 55:
        return "Líder en tendencia"
    return "Mixta"


def puntuar(filas: list[dict], pesos: dict | None = None, min_sector: int = 8, hoy=None) -> list[dict]:
    pesos = pesos or PESOS_DEFECTO
    for f in filas:
        _derivadas(f, hoy)
    for fac, d in FACTORES.items():
        subs: list[list[float | None]] = []
        for met, sentido in d["metricas"]:
            col = [None] * len(filas)
            if d["sector"]:
                grupos: dict[str, list[int]] = {}
                for i, f in enumerate(filas):
                    grupos.setdefault(f.get("sector") or "?", []).append(i)
                resto = [i for g in grupos.values() if len(g) < min_sector for i in g]
                for g in [g for g in grupos.values() if len(g) >= min_sector] + [resto]:
                    ps = _percentiles([filas[i].get(met) for i in g], sentido)
                    for i, p in zip(g, ps):
                        col[i] = p
            else:
                col = _percentiles([f.get(met) for f in filas], sentido)
            subs.append(col)
        for i, f in enumerate(filas):
            vals = [s[i] for s in subs if s[i] is not None]
            f.setdefault("factores", {})[fac] = round(mean(vals), 1) if vals else None
            f.setdefault("cobertura", {})[fac] = round(len(vals) / len(subs), 2)
    total_peso = sum(pesos.values())
    for f in filas:
        sc = f["factores"]
        base = sum(pesos[k] * (sc[k] if sc[k] is not None else 40) for k in pesos) / total_peso  # sin dato = algo peor que neutro
        bs = banderas(f)
        f["banderas"] = [b for b, _ in bs]
        f["nota_base"] = round(base, 1)
        f["nota"] = round(max(0.0, base - sum(p for _, p in bs)), 1)
        f["cobertura_total"] = round(mean(f["cobertura"].values()), 2)
        f["carril"] = carril({k: (v if v is not None else 50) for k, v in sc.items()})
        sen = []
        if f.get("tendencia_fase2"):
            sen.append("Tendencia alcista (fase 2)")
        if f.get("base_vcp"):
            sen.append("Base estrecha tipo VCP")
        if f.get("hueco_mantenido"):
            sen.append("Hueco al alza tras noticia/resultados que se mantiene (PEAD)")
        f["senales"] = sen
    filas.sort(key=lambda f: -f["nota"])
    for i, f in enumerate(filas, 1):
        f["puesto"] = i
    return filas


# ---------------------------------------------------------------- descarga
def universo(cfg: dict) -> list[dict]:
    """Paso 1-2: todas las small caps de EE. UU. que pasan el filtro rápido."""
    import yfinance as yf
    from yfinance import EquityQuery as Q

    c = cfg["oportunidades"]
    q = Q("and", [
        Q("eq", ["region", "us"]),
        Q("is-in", ["exchange", "NMS", "NYQ", "ASE", "NGM", "NCM"]),
        Q("btwn", ["intradaymarketcap", c["capitalizacion_min_usd"], c["capitalizacion_max_usd"]]),
        Q("gt", ["intradayprice", c["precio_min_usd"]]),
        Q("gt", ["avgdailyvol3m", c["volumen_medio_min"]]),
    ])
    quotes, offset = [], 0
    while offset < 6000:
        r = yf.screen(q, offset=offset, size=250, sortField="intradaymarketcap", sortAsc=False)
        lote = r.get("quotes", [])
        quotes += lote
        if len(lote) < 250:
            break
        offset += 250
        time.sleep(0.5)
    vistos, out = set(), []
    for x in quotes:
        s, nombre = x.get("symbol"), (x.get("longName") or x.get("shortName") or "")
        if not s or s in vistos or x.get("quoteType", "EQUITY") != "EQUITY":
            continue
        if any(p in nombre.lower() for p in ("acquisition corp", "acquisition co", "blank check", " spac")):
            continue
        p, v = x.get("regularMarketPrice") or 0, x.get("averageDailyVolume3Month") or 0
        if p * v < c["volumen_dolares_min"]:
            continue
        vistos.add(s)
        out.append(dict(ticker=s, empresa=nombre, precio=p, capitalizacion=x.get("marketCap"),
                        rating_medio=x.get("averageAnalystRating")))
    return out


def enriquecer(tickers: list[str], hilos: int = 4, pausa: float = 0.15, limite_seg: float | None = None,
               al_bajar=None) -> list[dict]:
    """Descarga los datos de cada empresa. `limite_seg`: deja de pedir empresas nuevas al llegar a ese tiempo
    (lo que falte se queda para la próxima vez). `al_bajar(m)`: se llama con cada empresa descargada."""
    import yfinance as yf

    from .metricas import empresa
    try:
        ref = yf.Ticker("IWM").history(period="15mo", interval="1d", auto_adjust=True)["Close"]
    except Exception:  # noqa: BLE001
        ref = None
    out = []

    estado = {"pausa": pausa}
    inicio = time.monotonic()

    def uno(t):
        if limite_seg and time.monotonic() - inicio > limite_seg:
            return None  # sin tiempo: se queda pendiente
        m = {"ticker": t, "errores": ["todo"]}
        for intento in range(4):
            try:
                m = empresa(t, ref)
            except Exception as e:  # noqa: BLE001
                m = {"ticker": t, "errores": [f"todo: {type(e).__name__}"]}
            fallo_info = any(x.startswith(("info", "todo")) for x in m["errores"])
            if not fallo_info:
                estado["pausa"] = max(pausa, estado["pausa"] * 0.9)
                break
            # Yahoo limita si se le pide demasiado rápido: esperar cada vez más y ir más despacio.
            estado["pausa"] = min(3.0, estado["pausa"] * 1.5 + 0.2)
            time.sleep(5 * (intento + 1))
        time.sleep(estado["pausa"])
        return m

    with ThreadPoolExecutor(max_workers=hilos) as ex:
        futs = {ex.submit(uno, t): t for t in tickers}
        for k, fu in enumerate(as_completed(futs), 1):
            m = fu.result()
            if m is None:
                continue
            out.append(m)
            if al_bajar:
                al_bajar(m)
            if k % 100 == 0:
                print(f"  ... {k}/{len(tickers)} empresas descargadas (pausa {estado['pausa']:.2f}s)", flush=True)
    from collections import Counter
    errores = Counter(e.split(":")[0] + ":" + e.split(":")[-1].strip() for m in out for e in m.get("errores", []))
    print("Errores de descarga por bloque:", dict(errores.most_common(12)) or "ninguno", flush=True)
    return out


def _parte(lista: list, parte: int, de: int) -> list:
    """Reparte la lista en `de` trozos. Cada empresa va siempre al mismo trozo (según su ticker), aunque cada
    máquina reciba la lista de Yahoo en un orden algo distinto: así no hay empresas repetidas ni olvidadas."""
    import zlib
    return sorted((b for b in lista if zlib.crc32(b["ticker"].encode()) % de == parte), key=lambda b: b["ticker"])


def descargar_parte(cfg: dict, parte: int = 0, de: int = 1, salida: str | None = None, minutos: float | None = None,
                    maximo: int | None = None) -> dict:
    """Paso 3 en un trozo del universo. Guarda cada empresa en `salida` (una línea JSON por empresa) según se
    descarga: si el trabajo se corta, lo bajado no se pierde y la próxima vez se continúa por donde iba."""
    import os

    c = cfg["oportunidades"]
    base = universo(cfg)
    maximo = maximo or c.get("max_empresas", 2000)
    mias = _parte(base[:maximo], parte, de)
    hechas: dict[str, dict] = {}
    if salida and os.path.exists(salida):
        for linea in open(salida, encoding="utf-8"):
            try:
                m = json.loads(linea)
            except ValueError:
                continue
            if not any(e.startswith(("info", "todo")) for e in m.get("errores", [])):
                hechas[m["ticker"]] = m
    pendientes = [b["ticker"] for b in mias if b["ticker"] not in hechas]
    print(f"Parte {parte + 1}/{de}: {len(mias)} empresas · ya bajadas hoy {len(hechas)} · pendientes {len(pendientes)}",
          flush=True)
    fh = open(salida, "a", encoding="utf-8") if salida else None

    cap = {b["ticker"]: b.get("capitalizacion") for b in mias}

    def al_bajar(m):
        m["capitalizacion"] = m.get("capitalizacion") or cap.get(m["ticker"])
        if fh:
            fh.write(json.dumps({k: _limpio(v) for k, v in m.items()}, ensure_ascii=False, default=str) + "\n")
            fh.flush()
    nuevas = enriquecer(pendientes, hilos=c.get("hilos", 4), limite_seg=minutos * 60 if minutos else None,
                        al_bajar=al_bajar)
    if fh:
        fh.close()
        with open(salida + ".meta.json", "w", encoding="utf-8") as fm:
            json.dump({"universo": len(base), "parte": len(mias)}, fm)
    filas = list(hechas.values()) + nuevas
    faltan = len(mias) - len({f["ticker"] for f in filas})
    print(f"Parte {parte + 1}/{de}: {len(filas)} descargadas, {faltan} sin tiempo (quedan para la próxima)", flush=True)
    return dict(universo=len(base), parte=len(mias), filas=filas, base=base)


def leer_partes(rutas: list[str]) -> list[dict]:
    vistas: dict[str, dict] = {}
    for r in rutas:
        for linea in open(r, encoding="utf-8"):
            try:
                m = json.loads(linea)
            except ValueError:
                continue
            previo = vistas.get(m["ticker"])
            # si hay dos versiones, quedarse con la que tenga menos errores
            if previo is None or len(m.get("errores", [])) < len(previo.get("errores", [])):
                vistas[m["ticker"]] = m
    return list(vistas.values())


def combinar(cfg: dict, filas: list[dict], universo_n: int, base: list[dict] | None = None) -> dict:
    """Pasos 4-6: filtra, puntúa y añade datos extra. Sirve también con un universo a medias (ranking provisional)."""
    c = cfg["oportunidades"]
    elegidas = base or []
    descargadas = len(filas)
    cap_base = {b["ticker"]: b.get("capitalizacion") for b in elegidas}
    motivos = {"no_es_accion": 0, "sin_sector": 0, "sin_capitalizacion": 0}
    buenas = []
    for f in filas:
        f["capitalizacion"] = f.get("capitalizacion") or cap_base.get(f["ticker"])
        if f.get("tipo") not in (None, "EQUITY"):
            motivos["no_es_accion"] += 1
        elif not f.get("sector"):   # fondos cerrados y similares no tienen sector
            motivos["sin_sector"] += 1
        elif not f.get("capitalizacion"):
            motivos["sin_capitalizacion"] += 1
        else:
            buenas.append(f)
    print(f"Descartadas antes de puntuar: {motivos}", flush=True)
    filas = buenas
    # Datos extra con claves gratuitas (si existen). El calendario de resultados de Finnhub se aplica a todas
    # ANTES de puntuar; noticias, recomendaciones e insiders de Finnhub/Alpaca se añaden a las mejores DESPUÉS
    # (para el panel y el análisis profundo), sin cambiar la nota, para que la comparación sea justa.
    from . import fuentes_extra
    extra = {}
    if fuentes_extra.hay_finnhub():
        try:
            cal = fuentes_extra.Finnhub().calendario_resultados()
            for f in filas:
                if f["ticker"] in cal:
                    f["proximos_resultados"] = cal[f["ticker"]]
            extra["calendario_resultados"] = len(cal)
        except PermissionError as e:
            extra["finnhub_error"] = str(e)
    puntuar(filas, c.get("pesos"))
    if fuentes_extra.hay_finnhub() or fuentes_extra.hay_alpaca():
        extra |= fuentes_extra.completar(filas, top=c.get("extra_top", 60), calendario=False)
    print("Fuentes extra:", extra or "ninguna (sin claves)")
    completo = descargadas >= universo_n * 0.97
    return dict(actualizado=ahora(), universo=universo_n, descargadas=descargadas, analizadas=len(filas),
                provisional=not completo, pesos=c.get("pesos") or PESOS_DEFECTO, fuentes_extra=extra, filas=filas)


def ejecutar(cfg: dict, maximo: int | None = None) -> dict:
    """Todo de una vez (uso en el PC)."""
    d = descargar_parte(cfg, maximo=maximo)
    return combinar(cfg, d["filas"], d["parte"], d["base"])





COLUMNAS_PANEL = [
    "puesto", "ticker", "empresa", "sector", "industria", "nota", "nota_base", "carril", "factores", "cobertura_total",
    "banderas", "senales", "precio", "capitalizacion", "analistas", "recomendacion", "objetivo_medio",
    "potencial_analistas_pct", "potencial_objetivo_bajo_pct", "per_futuro", "ev_ventas", "rent_fcf_pct",
    "crec_ventas", "crec_ventas_sig_anio", "crec_bpa_sig_anio", "rev_bpa_90d_anio", "revisiones_neto",
    "mejoras_neto_90d", "insiders_neto_pct", "ret_6m", "dist_max52_pct", "dilucion_1a_pct", "meses_de_caja",
    "cortos_flotante", "proximos_resultados", "dias_a_resultados", "extra"]


def _limpio(v):
    if isinstance(v, float):
        return round(v, 4)
    return v


def ranking_actual() -> dict | None:
    try:
        with open(ruta("investigacion", "ranking.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return {k: v for k, v in d.items() if k != "filas"}
    except (OSError, ValueError):
        return None


def guardar(res: dict, top: int = 150) -> tuple[str, str]:
    filas = res["filas"]
    ligero = [{k: _limpio(f.get(k)) for k in COLUMNAS_PANEL} for f in filas[:top]]
    pj = ruta("investigacion", "ranking.json")
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in res.items() if k != "filas"} | {"filas": ligero}, fh, ensure_ascii=False)
    # Ficha completa (todas las métricas) de las 40 primeras, para el análisis profundo.
    with open(ruta("investigacion", "ranking_detalle.json"), "w", encoding="utf-8") as fh:
        json.dump({"actualizado": res["actualizado"],
                   "filas": [{k: _limpio(v) for k, v in f.items()} for f in filas[:40]]}, fh, ensure_ascii=False, indent=0)
    pm = ruta("investigacion", "ranking.md")
    with open(pm, "w", encoding="utf-8") as fh:
        fh.write("# Ranking de oportunidades (small caps EE. UU.)\n\n")
        fh.write(f"_Actualizado: {res['actualizado']} · universo {res['universo']} · analizadas {res['analizadas']}_\n\n")
        fh.write("Nota 0-100 = suma ponderada de 8 factores comparando cada empresa con las demás, menos "
                 "penalizaciones por banderas rojas. **No es una recomendación**: es la lista de las que merecen "
                 "un análisis a fondo.\n\n")
        fh.write("| # | Ticker | Sector | Nota | Tipo | Calidad | Crec. | Valor. | Revis. | Momentum | Solidez | Banderas |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for f in filas[:30]:
            s = f["factores"]
            g = lambda k: "—" if s.get(k) is None else f"{s[k]:.0f}"  # noqa: E731
            fh.write(f"| {f['puesto']} | {f['ticker']} | {f.get('sector') or ''} | **{f['nota']:.0f}** | {f['carril']} | "
                     f"{g('calidad')} | {g('crecimiento')} | {g('valoracion')} | {g('revisiones')} | {g('momentum')} | "
                     f"{g('solidez')} | {len(f['banderas'])} |\n")
    return str(pj), str(pm)
