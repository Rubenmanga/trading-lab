"""Seguimiento diario de una empresa concreta para elegir el MOMENTO de entrada (agente B).

Cada día laborable (GitHub Actions, tras el cierre) baja el último año de precios, calcula los
indicadores del análisis (EMA 9, medias de 50 y 200, RSI 14, volumen) y comprueba las señales del
plan del trader guardadas en `config/medio_plazo.yaml` → `seguimiento`:

  · Señal A (suelo en soporte): toca la zona de soporte y hace una vela de giro con volumen,
    mejor si el RSI marca un mínimo más alto que en la caída anterior (divergencia alcista).
  · Señal B (confirmación): dos cierres seguidos por encima del nivel de confirmación.
  · Peligro: cierre bajo el soporte con volumen, o bajo el stop de tesis.

Añade noticias de Finnhub/Alpaca (si hay claves gratis) y guarda:
  investigacion/seguimiento/TICKER.md   (informe para el móvil y el panel)
  investigacion/seguimiento/TICKER.csv  (historial día a día)
  investigacion/seguimiento.json        (lo lee el panel)
Las señales importantes se añaden a estado.json → el workflow abre un aviso (issue) al móvil.
NO compra nada: solo avisa. El código de reglas no usa IA.
"""
from __future__ import annotations

import csv
import json
import os

from ..common.config import ruta
from ..common.db import ahora

TIPOS_AVISO = ("SEÑAL DE ENTRADA", "SOPORTE PERDIDO", "TESIS EN PELIGRO")


# ---------------------------------------------------------------- indicadores (sin IA, deterministas)
def _ema(v: list[float], n: int) -> list[float]:
    k, out = 2 / (n + 1), []
    for i, x in enumerate(v):
        out.append(x if i == 0 else x * k + out[-1] * (1 - k))
    return out


def _media(v: list[float], n: int) -> list[float | None]:
    return [None if i + 1 < n else sum(v[i + 1 - n:i + 1]) / n for i in range(len(v))]


def _rsi(c: list[float], n: int = 14) -> list[float | None]:
    """RSI de Wilder (el mismo que enseñan las apps de bolsa)."""
    out: list[float | None] = [None] * len(c)
    if len(c) <= n:
        return out
    sub = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    baj = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ms, mb = sum(sub[:n]) / n, sum(baj[:n]) / n
    for i in range(n, len(c)):
        if i > n:
            ms = (ms * (n - 1) + sub[i - 1]) / n
            mb = (mb * (n - 1) + baj[i - 1]) / n
        out[i] = 100.0 if mb == 0 else 100 - 100 / (1 + ms / mb)
    return out


def evaluar(velas: list[dict], niv: dict) -> dict:
    """velas: lista ordenada de dicts con fecha, apertura, maximo, minimo, cierre, volumen.
    niv: soporte [bajo, alto], confirmacion, entrada_max, stop, objetivo."""
    if len(velas) < 30:
        return dict(estado="SIN DATOS", senales=[], avisos=[])
    o = [v["apertura"] for v in velas]
    h = [v["maximo"] for v in velas]
    lo = [v["minimo"] for v in velas]
    c = [v["cierre"] for v in velas]
    vol = [v["volumen"] for v in velas]
    ema9, ma50, ma200, rsi, vol20 = _ema(c, 9), _media(c, 50), _media(c, 200), _rsi(c), _media(vol, 20)
    i = len(c) - 1
    s_bajo, s_alto = niv["soporte"]
    conf, stop, emax = niv["confirmacion"], niv["stop"], niv["entrada_max"]

    # Divergencia alcista: el mínimo de estos 5 días está cerca o por debajo del mínimo anterior
    # (entre 6 y 60 sesiones atrás), pero el RSI en ese punto es claramente más alto.
    ini = max(0, i - 60)
    previo = range(ini, max(ini, i - 5))
    reciente = range(max(0, i - 4), i + 1)
    divergencia = False
    if previo and all(rsi[k] is not None for k in reciente):
        kp = min(previo, key=lambda k: lo[k])
        kr = min(reciente, key=lambda k: lo[k])
        if rsi[kp] is not None and lo[kr] <= lo[kp] * 1.03 and rsi[kr] >= rsi[kp] + 3:
            divergencia = True

    toca_soporte = min(lo[k] for k in reciente) <= s_alto * 1.01 and c[i] >= s_bajo
    rango = h[i] - lo[i]
    vela_giro = c[i] > o[i] and c[i] > c[i - 1] and (rango == 0 or (c[i] - lo[i]) / rango >= 0.6)
    vol_rel = vol[i] / vol20[i] if vol20[i] else None
    con_volumen = vol_rel is not None and vol_rel >= 1.0

    senales, avisos = [], []
    if c[i] < stop:
        avisos.append(("TESIS EN PELIGRO", f"cierre {c[i]:.2f} $ por debajo del stop de tesis ({stop} $)"))
    elif c[i] < s_bajo and (vol_rel or 0) >= 1.3:
        avisos.append(("SOPORTE PERDIDO", f"cierre {c[i]:.2f} $ bajo el soporte ({s_bajo} $) con volumen {vol_rel:.1f}x"))
    venia_de_abajo = min(c[max(0, i - 20):i - 1] or [conf]) < conf   # recupera el nivel, no solo está encima
    if c[i] > conf and c[i - 1] > conf and venia_de_abajo and c[i] > ema9[i]:
        senales.append(("B", f"dos cierres seguidos por encima de {conf} $ (confirmación de cambio de tendencia)"))
    if toca_soporte and vela_giro and con_volumen and (divergencia or (rsi[i] or 50) < 40) and c[i] <= emax:
        senales.append(("A", "suelo en soporte: vela de giro con volumen"
                        + (" y divergencia alcista del RSI" if divergencia else " con RSI bajo")))
    for tipo, txt in senales:
        avisos.append(("SEÑAL DE ENTRADA", f"señal {tipo}: {txt}"))

    # Pistas (no son señal, ayudan a ver si la caída se frena)
    pistas = []
    if c[i] > ema9[i]:
        pistas.append("cierra por encima de la EMA 9 (primer síntoma de freno)")
    else:
        pistas.append("sigue por debajo de la EMA 9 (la caída no ha frenado)")
    if divergencia:
        pistas.append("divergencia alcista del RSI")
    if toca_soporte:
        pistas.append(f"está en la zona de soporte {s_bajo}-{s_alto} $")
    if vol_rel is not None and vol_rel < 0.7 and c[i] < c[i - 1]:
        pistas.append("baja con poco volumen (la venta se está secando)")
    if rsi[i] is not None and rsi[i] < 30:
        pistas.append("RSI en sobreventa (< 30)")

    if any(a[0] == "TESIS EN PELIGRO" for a in avisos):
        estado = "PELIGRO"
    elif senales:
        estado = "SEÑAL DE ENTRADA"
    elif any(a[0] == "SOPORTE PERDIDO" for a in avisos):
        estado = "ESPERAR (soporte perdido)"
    elif toca_soporte or c[i] > ema9[i]:
        estado = "ATENTO"
    else:
        estado = "ESPERAR"

    r = lambda x, d=2: None if x is None else round(x, d)  # noqa: E731
    return dict(
        fecha=velas[i]["fecha"], cierre=r(c[i]), cambio_dia_pct=r((c[i] / c[i - 1] - 1) * 100, 1),
        ema9=r(ema9[i]), ma50=r(ma50[i]), ma200=r(ma200[i]), rsi=r(rsi[i], 1),
        volumen_rel=r(vol_rel, 2), minimo_52s=r(min(lo[-252:])), maximo_52s=r(max(h[-252:])),
        divergencia=divergencia, toca_soporte=toca_soporte, vela_giro=vela_giro,
        estado=estado, senales=[dict(tipo=t, texto=x) for t, x in senales],
        avisos=[dict(tipo=t, texto=x) for t, x in avisos], pistas=pistas,
        distancia_entrada_pct=r((c[i] / emax - 1) * 100, 1), distancia_stop_pct=r((c[i] / stop - 1) * 100, 1),
        distancia_confirmacion_pct=r((c[i] / conf - 1) * 100, 1),
        potencial_pct=r((niv["objetivo"] / c[i] - 1) * 100, 1) if niv.get("objetivo") else None,
    )


# ---------------------------------------------------------------- datos
def velas_yahoo(ticker: str, periodo: str = "2y") -> list[dict]:
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=periodo, interval="1d", auto_adjust=False)
    out = []
    for idx, f in df.iterrows():
        if f["Close"] != f["Close"]:  # NaN
            continue
        out.append(dict(fecha=str(idx.date()), apertura=float(f["Open"]), maximo=float(f["High"]),
                        minimo=float(f["Low"]), cierre=float(f["Close"]), volumen=float(f["Volume"])))
    return out


def noticias(ticker: str) -> dict:
    """Noticias de los últimos días y datos de analistas (solo si hay claves gratuitas)."""
    from . import fuentes_extra as fx
    x: dict = {}
    if fx.hay_finnhub():
        try:
            x.update(fx.Finnhub().empresa(ticker))
            cal = fx.Finnhub().calendario_resultados(dias=60)
            if ticker in cal:
                x["proximos_resultados"] = cal[ticker]
        except PermissionError as e:
            x["finnhub_error"] = str(e)
    if fx.hay_alpaca():
        try:
            x["noticias_alpaca"] = fx.noticias_alpaca([ticker], dias=7, por_empresa=8).get(ticker, [])
        except PermissionError as e:
            x["alpaca_error"] = str(e)
    return x


# ---------------------------------------------------------------- informe
def _md(t: str, niv: dict, ev: dict, extra: dict, hist: list[dict]) -> str:
    s_bajo, s_alto = niv["soporte"]
    que_hacer = {
        "SEÑAL DE ENTRADA": f"Hay señal de entrada. Revisa la tesis con Claude (\"revisa {t}\") antes de comprar en la demo, "
                            f"como máximo {niv.get('tamano_max', '2 %')} de la cartera y con stop en {niv['stop']} $.",
        "PELIGRO": f"Ha roto el stop de tesis ({niv['stop']} $). No comprar; pedir a Claude que revise si la tesis sigue viva.",
        "ESPERAR (soporte perdido)": f"Ha perdido el soporte de {s_bajo} $. Esperar: el siguiente soporte está más abajo.",
        "ATENTO": "Se acerca el momento: está en soporte o empieza a frenar. Aún falta la señal; mirar cada día.",
        "ESPERAR": "La caída no ha frenado. Esperar a una de las dos señales del plan.",
        "SIN DATOS": "No se pudieron bajar los precios hoy.",
    }[ev["estado"]]
    nots = (extra.get("noticias_alpaca") or []) + [n for n in (extra.get("noticias") or [])]
    vistos, nots_ok = set(), []
    for n in sorted(nots, key=lambda n: n.get("fecha") or "", reverse=True):
        clave = (n.get("titulo") or "")[:60].lower()
        if clave and clave not in vistos:
            vistos.add(clave)
            nots_ok.append(n)
    l = [f"# Seguimiento diario de {t} · {ev.get('fecha', '')}", "",
         "## Resumen (5 líneas)",
         f"1. **Estado: {ev['estado']}.** {que_hacer}",
         f"2. Cierre {ev.get('cierre')} $ ({ev.get('cambio_dia_pct'):+} % en el día). RSI {ev.get('rsi')} · EMA 9 {ev.get('ema9')} $ · media 50 {ev.get('ma50')} $.",
         f"3. Señales del plan: A = suelo en {s_bajo}-{s_alto} $ con vela de giro y volumen · B = dos cierres por encima de {niv['confirmacion']} $ "
         f"(ahora a {ev.get('distancia_confirmacion_pct')} %).",
         f"4. Pistas de hoy: {'; '.join(ev.get('pistas') or ['—'])}.",
         f"5. Comprar como mucho hasta {niv['entrada_max']} $ · stop de tesis {niv['stop']} $ (a {ev.get('distancia_stop_pct')} %) · "
         f"objetivo {niv.get('objetivo')} $ (potencial {ev.get('potencial_pct')} %).", "",
         "## Indicadores de hoy",
         "| Indicador | Valor |", "|---|---|"]
    for k, nom in [("cierre", "Cierre ($)"), ("ema9", "EMA 9"), ("ma50", "Media 50"), ("ma200", "Media 200"),
                   ("rsi", "RSI 14"), ("volumen_rel", "Volumen frente a su media de 20 días"),
                   ("minimo_52s", "Mínimo 52 semanas"), ("maximo_52s", "Máximo 52 semanas")]:
        l.append(f"| {nom} | {ev.get(k)} |")
    l += [f"| ¿En zona de soporte? | {'sí' if ev.get('toca_soporte') else 'no'} |",
          f"| ¿Vela de giro? | {'sí' if ev.get('vela_giro') else 'no'} |",
          f"| ¿Divergencia alcista del RSI? | {'sí' if ev.get('divergencia') else 'no'} |", ""]
    if ev.get("avisos"):
        l += ["## ⚠️ Avisos", *[f"- **{a['tipo']}**: {a['texto']}" for a in ev["avisos"]], ""]
    l += ["## Noticias y analistas (últimos días)"]
    if extra.get("proximos_resultados"):
        l.append(f"- Próximos resultados: **{extra['proximos_resultados']}**")
    if extra.get("recs_pct_compra") is not None:
        l.append(f"- Analistas que dicen comprar: {extra['recs_pct_compra']} % (cambio en 3 meses: {extra.get('recs_cambio_3m', '—')} puntos)")
    if extra.get("insiders_mspr_3m") is not None:
        l.append(f"- Sentimiento de directivos (MSPR 3 meses): {extra['insiders_mspr_3m']}")
    for n in nots_ok[:8]:
        url = n.get("url") or ""
        tit = (n.get("titulo") or "").replace("|", "/")
        l.append(f"- {n.get('fecha', '')} · " + (f"[{tit}]({url})" if url.startswith("http") else tit))
    if not nots_ok and not extra:
        l.append("- Sin datos de noticias hoy (faltan las claves gratuitas de Finnhub/Alpaca o no respondieron).")
    l += ["", "## Últimos días", "| Fecha | Cierre | RSI | EMA 9 | Vol. rel. | Estado |", "|---|---|---|---|---|---|"]
    for f in reversed(hist[-15:]):
        l.append(f"| {f['fecha']} | {f['cierre']} | {f['rsi']} | {f['ema9']} | {f['volumen_rel']} | {f['estado']} |")
    l += ["", f"Plan completo: [{niv.get('informe', '')}](../../{niv.get('informe', '')})" if niv.get("informe") else "",
          "", "> Lo calcula un programa con reglas fijas (sin IA) cada día laborable tras el cierre. "
          "No compra nada: solo avisa. Practica en la cuenta demo."]
    return "\n".join(l) + "\n"


def _historial(t: str, ev: dict) -> list[dict]:
    path = ruta("investigacion", "seguimiento", f"{t}.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cols = ["fecha", "cierre", "rsi", "ema9", "ma50", "volumen_rel", "estado"]
    filas: list[dict] = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as fh:
            filas = [f for f in csv.DictReader(fh) if f.get("fecha") != ev.get("fecha")]
    if ev.get("fecha"):
        filas.append({k: ev.get(k) for k in cols})
    filas.sort(key=lambda f: f["fecha"])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    return filas


def ejecutar(cfg: dict, velas_de=velas_yahoo, extra_de=noticias) -> dict:
    res = {"actualizado": ahora(), "empresas": {}}
    for t, niv in (cfg.get("seguimiento") or {}).items():
        try:
            velas = velas_de(t)
        except Exception as e:  # noqa: BLE001
            velas = []
            print(f"{t}: no se pudieron bajar precios ({type(e).__name__})")
        ev = evaluar(velas, niv)
        extra = {}
        try:
            extra = extra_de(t) or {}
        except Exception as e:  # noqa: BLE001
            print(f"{t}: sin noticias ({type(e).__name__})")
        hist = _historial(t, ev) if ev.get("fecha") else []
        with open(ruta("investigacion", "seguimiento", f"{t}.md"), "w", encoding="utf-8") as fh:
            fh.write(_md(t, niv, ev, extra, hist))
        res["empresas"][t] = dict(niveles=niv, **ev, proximos_resultados=extra.get("proximos_resultados"),
                                  historial=hist[-60:])
    with open(ruta("investigacion", "seguimiento.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    _a_estado(res)
    return res


def _a_estado(res: dict) -> None:
    """Añade las señales a estado.json para que el workflow mande el aviso al móvil."""
    path = ruta("investigacion", "estado.json")
    try:
        with open(path, encoding="utf-8") as fh:
            est = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        est = {"actualizado": ahora(), "alertas": [], "precios": []}
    est["alertas"] = [a for a in est.get("alertas", []) if not a.get("seguimiento")]
    for t, e in res["empresas"].items():
        for a in e.get("avisos", []):
            est["alertas"].append(dict(ticker=t, tipo=a["tipo"], precio=e.get("cierre"), seguimiento=True,
                                       mensaje=f"{t} ({e.get('fecha')}, {e.get('cierre')} $): {a['texto']}. "
                                               f"Ver investigacion/seguimiento/{t}.md"))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(est, fh, ensure_ascii=False, indent=1)

