"""Novedades diarias de la lista de seguimiento de Ruben (agente B, solo información).

Cada día laborable (GitHub Actions, tras el cierre; lo llama `lab medio seguimiento`) mira cada empresa de
`config/medio_plazo.yaml` → `lista_noticias` y responde, SIN IA y sin gastar la sesión de Claude:
  · ¿Se movió el precio? Variación y volumen frente a lo normal de ESA acción (su volatilidad de 20 días).
  · ¿Por qué? Titulares desde la sesión anterior, clasificados por reglas (resultados, FDA, ensayo, contrato,
    ampliación de capital, analistas…). Si ningún titular lo explica, lo dice: no se inventa causas.
    También compara con el mercado (SPY) y con un fondo de su sector (XBI, QQQ…) por si se movió "con todos".
  · ¿Qué viene? Próximos resultados (Finnhub), ensayos clínicos (ClinicalTrials.gov, solo salud),
    documentos nuevos en la SEC (ventas de acciones, fondos >5 %).
  · ¿Qué cambió desde ayer? Solo titulares nuevos, cambios de analistas y fechas nuevas.
Guarda investigacion/seguimiento/lista.md (para el móvil) y la parte `lista` de seguimiento.json (panel).
Los avisos importantes van a estado.json → el workflow abre un issue (notificación al móvil).
Es información, no una recomendación de compra o venta. En la config solo hay tickers: nada de importes.
"""
from __future__ import annotations

import csv
import os
import re
import statistics
from datetime import date, timedelta

from ..common.config import ruta
from . import sentimiento as se

# (causa, expresión regular sobre el titular en minúsculas, ¿importante?). El orden marca la prioridad.
CAUSAS = [
    ("ampliación de capital", se.ALARMAS["ampliación de capital"], True),
    ("compra o fusión", r"\b(acquir\w*|merger|buyout|takeover|tender offer)\b", True),
    ("FDA / regulador", r"\b(fda|pdufa|ema|chmp|nda|bla|ind)\b|complete response|clinical hold|breakthrough therapy|fast track|orphan drug", True),
    ("ensayo clínico", r"\b(phase ?(1|2|3|i{1,3})[ab]?|trial|topline|endpoint|readout|clinical data|data from)\b", True),
    ("resultados", r"\b(earnings|quarterly results|(first|second|third|fourth)[- ]quarter|q[1-4]|fiscal \d{4}|revenue|eps|guidance|outlook)\b", True),
    ("contrato o pedido", r"\b(contract|orders?|awarded|award|deal|agreement|partnership|collaboration|licens\w+|army|pentagon|dod|navy|air force)\b", False),
    ("analistas", r"\b(upgrades?|downgrades?|upgraded|downgraded|price target|initiat\w+ coverage|reiterat\w+|outperform|overweight|underweight|buy rating|sell rating|neutral rating)\b", False),
    ("directivos", r"\b(ceo|cfo|chief \w+ officer|appoints?|resign\w*|steps down|board of directors)\b", False),
    ("legal", r"\b(lawsuit|investigation|subpoena|probe|settlement)\b", False),
]
TIPOS_AVISO = ("MOVIMIENTO GRANDE", "NOTICIA IMPORTANTE")


def clasificar(titular: str) -> dict:
    t = (titular or "").lower()
    ruido = bool(re.search(se.RUIDO, t))
    causas = [] if ruido else [c for c, r, _ in CAUSAS if re.search(r, t)]
    importante = (not ruido) and any(imp for c, _, imp in CAUSAS if c in causas)
    alarmas = [] if ruido else [n for n, r in se.ALARMAS.items() if re.search(r, t)]
    return dict(causas=causas, importante=importante or bool(alarmas), tono=se.puntuar_titular(titular),
                alarmas=alarmas, ruido=ruido)


def clave(titular: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (titular or "").lower())[:70].strip()


# ---------------------------------------------------------------- movimiento (reglas, sin IA)
def movimiento(velas: list[dict]) -> dict:
    """Variación del último día frente a lo normal de esa acción (desviación de sus últimas 20 sesiones)."""
    if len(velas) < 2:
        return {}
    c = [v["cierre"] for v in velas]
    vol = [v.get("volumen") or 0 for v in velas]
    i = len(c) - 1
    rets = [(c[k] / c[k - 1] - 1) * 100 for k in range(max(1, i - 20), i) if c[k - 1]]
    sigma = statistics.pstdev(rets) if len(rets) >= 5 else None
    cambio = (c[i] / c[i - 1] - 1) * 100 if c[i - 1] else 0.0
    base_vol = [x for x in vol[max(0, i - 20):i] if x]
    vrel = vol[i] / (sum(base_vol) / len(base_vol)) if base_vol and vol[i] else None
    return dict(fecha=velas[i]["fecha"], fecha_anterior=velas[i - 1]["fecha"], cierre=round(c[i], 2),
                cambio_pct=round(cambio, 2),
                cambio_5d_pct=round((c[i] / c[max(0, i - 5)] - 1) * 100, 1) if c[max(0, i - 5)] else None,
                sigma_pct=round(sigma, 2) if sigma else None,
                veces_normal=round(abs(cambio) / sigma, 1) if sigma else None,
                volumen_rel=round(vrel, 1) if vrel else None)


def es_grande(m: dict, u: dict) -> bool:
    if not m:
        return False
    a = abs(m["cambio_pct"])
    if a >= u["umbral_movimiento_pct"]:
        return True
    return bool(m.get("veces_normal") and m["veces_normal"] >= u["umbral_sigmas"] and a >= u["umbral_minimo_pct"])


def es_notable(m: dict, u: dict) -> bool:
    """Movimiento que merece explicación (aunque no sea para avisar)."""
    if not m:
        return False
    a = abs(m["cambio_pct"])
    return a >= u["umbral_movimiento_pct"] / 2 or bool(m.get("veces_normal") and m["veces_normal"] >= 1.5 and a >= 2) \
        or bool(m.get("volumen_rel") and m["volumen_rel"] >= u["umbral_volumen"])


def explicar(m: dict, recientes: list[dict], ref: dict | None, mercado: dict | None, u: dict) -> str:
    """Causa probable del movimiento, sin inventar: solo con titulares de la ventana o con el mercado/sector."""
    if not m:
        return "No hay precios de hoy."
    if not es_notable(m, u):
        return "Movimiento normal para esta acción."
    sube = m["cambio_pct"] > 0
    con = [n for n in recientes if n["causas"] or n["tono"]]
    con.sort(key=lambda n: (not n["importante"], -abs(n["tono"])))
    partes = []
    if con:
        n = con[0]
        tit = n["titulo"][:140]
        coherente = n["tono"] == 0 or (n["tono"] > 0) == sube
        etiqueta = ", ".join(n["causas"][:2]) or "noticia"
        if coherente:
            partes.append(f"Causa probable: «{tit}» ({etiqueta}, {n['fecha']}).")
        else:
            partes.append(f"Hay noticia («{tit}», {etiqueta}) pero su tono no cuadra con la dirección del precio: "
                          "la causa puede ser otra.")
    for nombre, r in (("su sector", ref), ("el mercado", mercado)):
        if r and r.get("cambio_pct") is not None:
            rc = r["cambio_pct"]
            if (rc > 0) == sube and abs(rc) >= 1 and abs(m["cambio_pct"] - rc) <= max(1.5, abs(m["cambio_pct"]) * 0.5):
                partes.append(f"Se movió en línea con {nombre} ({r['ticker']} {rc:+.1f} %).")
                break
    if not partes:
        partes.append("No hay ninguna noticia que lo explique en las fuentes gratuitas (puede ser flujo de compras/ventas, "
                      "sector o algo que aún no ha salido). No se inventa una causa.")
    return " ".join(partes)


# ---------------------------------------------------------------- fuentes (las de siempre, con claves gratis)
def _velas(t: str, periodo: str = "3mo") -> list[dict]:
    from .seguimiento import velas_yahoo
    return velas_yahoo(t, periodo)


def _finnhub(t: str, hoy: date) -> dict:
    from . import fuentes_extra as fx
    if not fx.hay_finnhub():
        return {}
    f, x = fx.Finnhub(), {}
    prof = f._q("/stock/profile2", symbol=t)
    if isinstance(prof, dict):
        x["nombre_fuente"] = prof.get("name")
    news = f._q("/company-news", symbol=t, **{"from": (hoy - timedelta(days=5)).isoformat(), "to": hoy.isoformat()})
    if isinstance(news, list):
        from datetime import datetime, timezone
        x["noticias"] = [dict(fecha=datetime.fromtimestamp(n.get("datetime", 0), timezone.utc).date().isoformat(),
                              titulo=n.get("headline"), fuente=n.get("source"), url=n.get("url"))
                         for n in news[:40] if n.get("headline")]
    recs = f._q("/stock/recommendation", symbol=t)
    if isinstance(recs, list) and recs:
        x.update(fx.tendencia_recomendaciones(recs))
        r0 = sorted(recs, key=lambda r: r.get("period", ""), reverse=True)[0]
        x["recs_n"] = sum(r0.get(k, 0) or 0 for k in ("strongBuy", "buy", "hold", "sell", "strongSell"))
    cal = f._q("/calendar/earnings", symbol=t, **{"from": (hoy - timedelta(days=4)).isoformat(),
                                                 "to": (hoy + timedelta(days=120)).isoformat()})
    ev = sorted((cal or {}).get("earningsCalendar") or [], key=lambda e: e.get("date") or "")
    hechos = [e for e in ev if (e.get("date") or "") <= hoy.isoformat() and e.get("epsActual") is not None]
    futuros = [e for e in ev if (e.get("date") or "") >= hoy.isoformat() and e.get("epsActual") is None]
    if hechos:
        e = hechos[-1]
        x["resultados_recientes"] = dict(fecha=e.get("date"), bpa=e.get("epsActual"), bpa_esperado=e.get("epsEstimate"),
                                         ventas=e.get("revenueActual"), ventas_esperadas=e.get("revenueEstimate"))
    if futuros:
        e = futuros[0]
        x["proximos_resultados"] = e.get("date")
        x["proximos_resultados_hora"] = {"bmo": "antes de abrir", "amc": "tras el cierre"}.get(e.get("hour") or "", "")
    return x


def _alpaca(t: str) -> list[dict]:
    from . import fuentes_extra as fx
    if not fx.hay_alpaca():
        return []
    return fx.noticias_alpaca([t], dias=5, por_empresa=20).get(t, [])


def _sec(tickers: list[str]) -> dict:
    from . import fuentes_publicas as fp
    return fp.datos_sec(tickers, hilos=2)


def _ensayos(empresas: dict[str, str]) -> dict:
    from . import fuentes_publicas as fp
    return fp.datos_ensayos(empresas)


FUENTES = dict(velas=_velas, finnhub=_finnhub, alpaca=_alpaca, sec=_sec, ensayos=_ensayos)


def _seguro(fn, *a, defecto=None, nombre=""):
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001  (una fuente caída no para el resto)
        print(f"lista_noticias: {nombre} falló ({type(e).__name__}: {str(e)[:80]})")
        return defecto


def _nombre_cuadra(config: str, fuente: str | None) -> bool | None:
    if not fuente:
        return None
    from .fuentes_publicas import nombre_simple
    a, b = nombre_simple(config).split(), nombre_simple(fuente).split()
    return bool(a and b and a[0] == b[0])


# ---------------------------------------------------------------- análisis de una empresa
def analizar(t: str, info: dict, d: dict, previo: dict, u: dict, ref: dict | None, mercado: dict | None) -> dict:
    """d = datos ya bajados: velas, finnhub, alpaca, sec, ensayos. previo = lo guardado ayer de esta empresa."""
    m = movimiento(d.get("velas") or [])
    mismo_dia = bool(previo.get("fecha") and previo.get("fecha") == m.get("fecha"))
    avisados = set(previo.get("avisados") or []) if mismo_dia else set()
    if mismo_dia:
        previo = previo.get("anterior") or {}   # segunda pasada del mismo día: comparar con el día anterior
    anterior = {k: previo.get(k) for k in ("fecha", "vistos", "sec_vistos", "recs_pct_compra",
                                           "proximos_resultados", "resultados_recientes")}
    primera = not previo.get("vistos")
    fh = d.get("finnhub") or {}
    vistos_antes = set(previo.get("vistos") or [])
    # Titulares de Finnhub + Alpaca, sin repetidos
    todas, ya = [], set()
    for n in (d.get("alpaca") or []) + (fh.get("noticias") or []):
        k = clave(n.get("titulo"))
        if not k or k in ya:
            continue
        ya.add(k)
        todas.append(dict(fecha=n.get("fecha") or "", titulo=n.get("titulo") or "", fuente=n.get("fuente") or "",
                          url=n.get("url") or "", clave=k, nueva=k not in vistos_antes, **clasificar(n.get("titulo"))))
    todas.sort(key=lambda n: n["fecha"], reverse=True)
    utiles = [n for n in todas if not n["ruido"]]
    desde = m.get("fecha_anterior") or (date.today() - timedelta(days=1)).isoformat()
    recientes = [n for n in utiles if n["fecha"] >= desde]
    nuevas = [n for n in utiles if n["nueva"]]
    if primera:  # primer día: no marcar 5 días de titulares como "nuevos"
        nuevas = recientes
    grande = es_grande(m, u)
    porque = explicar(m, recientes, ref, mercado, u)

    cambios = []
    if nuevas:
        cambios.append(f"{len(nuevas)} titular{'es' if len(nuevas) > 1 else ''} nuevo{'s' if len(nuevas) > 1 else ''}")
    pct, pct_antes = fh.get("recs_pct_compra"), previo.get("recs_pct_compra")
    if pct is not None and pct_antes is not None and abs(pct - pct_antes) >= 1:
        cambios.append(f"analistas que dicen comprar: {pct_antes:.0f} % → {pct:.0f} %")
    pr, pr_antes = fh.get("proximos_resultados"), previo.get("proximos_resultados")
    if pr and pr != pr_antes and not primera:
        cambios.append(f"fecha de resultados {'nueva' if not pr_antes else 'cambiada'}: {pr}")
    rr = fh.get("resultados_recientes")
    if rr and rr.get("fecha") != (previo.get("resultados_recientes") or {}).get("fecha"):
        txt = f"resultados del {rr['fecha']}: BPA {rr['bpa']} (esperado {rr['bpa_esperado']})"
        if rr.get("ventas") and rr.get("ventas_esperadas"):
            txt += f", ventas {rr['ventas'] / 1e6:,.1f} M (esperadas {rr['ventas_esperadas'] / 1e6:,.1f} M)"
        cambios.append(txt)
    sec_docs = (d.get("sec") or {}).get("sec_documentos") or []
    sec_vistos = set(previo.get("sec_vistos") or [])
    limite_sec = (date.today() - timedelta(days=5)).isoformat()
    sec_nuevos = [s for s in sec_docs if (s.get("fecha") or "") >= limite_sec and f"{s['fecha']}{s['tipo']}" not in sec_vistos]
    for s in sec_nuevos:
        cambios.append(f"SEC {s['fecha']}: {s['tipo']}")

    catalizadores = []
    if pr:
        catalizadores.append(f"Resultados el {pr}" + (f" ({fh['proximos_resultados_hora']})" if fh.get("proximos_resultados_hora") else ""))
    for e in ((d.get("ensayos") or {}).get("ensayos") or [])[:3]:
        catalizadores.append(f"Ensayo {e.get('fase')} «{(e.get('titulo') or '')[:80]}»: resultado principal previsto {e.get('fecha')}")
    for n in utiles[:15]:
        if "FDA / regulador" in n["causas"] and re.search(r"pdufa|target action date|decision", n["titulo"].lower()):
            catalizadores.append(f"Fecha regulatoria citada en titular: «{n['titulo'][:100]}»")
            break

    importantes = [n for n in nuevas if n["importante"]]
    avisos = []
    if grande:
        avisos.append(dict(tipo="MOVIMIENTO GRANDE",
                           texto=f"{m['cambio_pct']:+.1f} % hoy" + (f" ({m['veces_normal']}x lo normal)" if m.get("veces_normal") else "")
                                 + (f", volumen {m['volumen_rel']}x" if m.get("volumen_rel") else "") + f". {porque}"))
    for n in importantes[:2]:
        avisos.append(dict(tipo="NOTICIA IMPORTANTE", texto=f"{', '.join(n['causas'] + n['alarmas'])}: «{n['titulo'][:140]}»"))
    if any(s["tipo"].startswith(("Registro", "Colocación")) for s in sec_nuevos):
        avisos.append(dict(tipo="NOTICIA IMPORTANTE", texto="Documento nuevo en la SEC para vender acciones nuevas (posible dilución)"))

    nuevos_avisos = [a for a in avisos if f"{a['tipo']}|{a['texto'][:50]}" not in avisados]
    if any(a["tipo"] == "MOVIMIENTO GRANDE" for a in avisos) and any(x.startswith("MOVIMIENTO GRANDE|") for x in avisados):
        nuevos_avisos = [a for a in nuevos_avisos if a["tipo"] != "MOVIMIENTO GRANDE"]  # ya avisado hoy
    avisados |= {f"{a['tipo']}|{a['texto'][:50]}" for a in avisos}

    problemas = []
    if not d.get("velas"):
        problemas.append("Yahoo no devuelve precios para este ticker")
    if d.get("finnhub") is not None and fh and fh.get("nombre_fuente") is None:
        problemas.append("Finnhub no reconoce el ticker (sin ficha de empresa)")
    cuadra = _nombre_cuadra(info.get("nombre") or t, fh.get("nombre_fuente"))
    if cuadra is False:
        problemas.append(f"Finnhub lo identifica como «{fh.get('nombre_fuente')}», no como «{info.get('nombre')}»: revisar ticker")

    if not cambios and not grande and not es_notable(m, u):
        resumen = "Sin cambios: movimiento normal y nada nuevo."
    else:
        resumen = porque
    return dict(nombre=info.get("nombre") or t, sector=info.get("sector"), **m, grande=grande,
                porque=porque, resumen=resumen, cambios=cambios, catalizadores=catalizadores, avisos=avisos,
                avisos_nuevos=nuevos_avisos, avisados=sorted(avisados),
                problemas=problemas, nombre_fuente=fh.get("nombre_fuente"),
                recs_pct_compra=pct if pct is not None else pct_antes, recs_n=fh.get("recs_n"),
                proximos_resultados=pr or pr_antes, resultados_recientes=rr or previo.get("resultados_recientes"),
                referencia=ref, titulares=[{k: n[k] for k in ("fecha", "titulo", "fuente", "url", "causas", "nueva", "importante")}
                                           for n in utiles[:8]],
                vistos=sorted(vistos_antes | {n["clave"] for n in todas})[-300:],
                sec_vistos=sorted(sec_vistos | {f"{s['fecha']}{s['tipo']}" for s in sec_docs})[-60:],
                anterior=anterior)


def materia_prima(t: str, info: dict, velas: list[dict], u: dict, previo: dict | None = None) -> dict:
    m = movimiento(velas)
    ya = bool(previo and previo.get("fecha") == m.get("fecha") and previo.get("grande"))
    grande = bool(m) and abs(m["cambio_pct"]) >= info.get("umbral_movimiento_pct", 3)
    txt = "No hay precios de hoy." if not m else (
        "Movimiento grande para el oro: suele reaccionar a tipos de interés, dólar y tensiones geopolíticas."
        if grande else "Movimiento normal.")
    return dict(nombre=info.get("nombre") or t, sector="materia prima", **m, grande=grande, porque=txt, resumen=txt,
                cambios=[], catalizadores=[], titulares=[], problemas=[] if velas else [f"Yahoo no devuelve precios de {info.get('yahoo', t)}"],
                avisos=[dict(tipo="MOVIMIENTO GRANDE", texto=f"{m['cambio_pct']:+.1f} % hoy")] if grande else [],
                avisos_nuevos=[dict(tipo="MOVIMIENTO GRANDE", texto=f"{m['cambio_pct']:+.1f} % hoy")] if grande and not ya else [])


# ---------------------------------------------------------------- informe
def _flecha(e: dict) -> str:
    if e.get("cambio_pct") is None:
        return "sin precio"
    s = f"{'▲' if e['cambio_pct'] > 0 else ('▼' if e['cambio_pct'] < 0 else '=')} {e['cambio_pct']:+.1f} %"
    if e.get("volumen_rel"):
        s += f" · volumen {e['volumen_rel']}x lo normal"
    return s


def informe(res: dict) -> str:
    emp, mp = res["empresas"], res["materias_primas"]
    todo = {**emp, **mp}
    grandes = [f"{t} {e['cambio_pct']:+.1f} %" for t, e in todo.items() if e.get("grande")]
    imp = [t for t, e in emp.items() if any(a["tipo"] == "NOTICIA IMPORTANTE" for a in e.get("avisos", []))]
    hoy = date.today()
    pronto = [f"{t} ({e['proximos_resultados']})" for t, e in emp.items()
              if e.get("proximos_resultados") and e["proximos_resultados"] <= (hoy + timedelta(days=14)).isoformat()]
    probl = [f"{t}: {'; '.join(e['problemas'])}" for t, e in todo.items() if e.get("problemas")]
    mk = res.get("mercado") or {}
    l = [f"# Tu lista de seguimiento · {res.get('fecha') or hoy.isoformat()}", "",
         "## Resumen (5 líneas)",
         f"1. Mercado (S&P 500, {mk.get('ticker', 'SPY')}): {mk['cambio_pct']:+.1f} % hoy." if mk.get("cambio_pct") is not None
         else "1. Sin dato del mercado hoy.",
         f"2. Movimientos grandes: {', '.join(grandes) if grandes else 'ninguno'}.",
         f"3. Noticias importantes nuevas: {', '.join(imp) if imp else 'ninguna'}.",
         f"4. Resultados en los próximos 14 días: {', '.join(pronto) if pronto else 'ninguno'}.",
         f"5. Datos: {'; '.join(probl) if probl else 'todas las empresas se leyeron bien'}.", "",
         "> Información, no recomendación de compra o venta. Lo calcula un programa con reglas fijas (sin IA).", ""]
    for t, e in todo.items():
        l.append(f"## {t} · {e['nombre']} — {_flecha(e)}" + (" ⚠️" if e.get("avisos") else ""))
        if e.get("cierre") is not None:
            extra = f" · 5 días {e['cambio_5d_pct']:+.1f} %" if e.get("cambio_5d_pct") is not None else ""
            normal = f" · lo normal en un día: ±{e['sigma_pct']} %" if e.get("sigma_pct") else ""
            l.append(f"Cierre {e['cierre']} ({e.get('fecha')}){extra}{normal}.")
        l.append(f"- **Por qué:** {e['porque']}")
        l.append(f"- **Qué cambió:** {'; '.join(e['cambios']) if e.get('cambios') else 'nada nuevo'}.")
        if e.get("catalizadores"):
            l.append(f"- **Próximos catalizadores:** {'; '.join(e['catalizadores'])}.")
        if e.get("recs_pct_compra") is not None:
            l.append(f"- Analistas que dicen comprar: {e['recs_pct_compra']:.0f} %" + (f" de {e['recs_n']}" if e.get("recs_n") else "") + ".")
        for p in e.get("problemas") or []:
            l.append(f"- ❗ Datos: {p}.")
        for n in [n for n in e.get("titulares") or [] if n["nueva"]][:4]:
            tit = n["titulo"].replace("|", "/").replace("[", "(").replace("]", ")")
            etq = f" [{', '.join(n['causas'])}]" if n["causas"] else ""
            l.append(f"  - {n['fecha']} · " + (f"[{tit}]({n['url']})" if n["url"].startswith("http") else tit) + etq)
        l.append("")
    return "\n".join(l) + "\n"


def _historial(res: dict) -> None:
    path = ruta("investigacion", "seguimiento", "lista-historial.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cols = ["fecha", "ticker", "cierre", "cambio_pct", "volumen_rel", "grande", "porque"]
    filas = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as fh:
            filas = list(csv.DictReader(fh))
    hechas = {(f["fecha"], f["ticker"]) for f in filas}
    for t, e in {**res["empresas"], **res["materias_primas"]}.items():
        if e.get("fecha") and (e["fecha"], t) not in hechas:
            filas.append(dict(fecha=e["fecha"], ticker=t, cierre=e.get("cierre"), cambio_pct=e.get("cambio_pct"),
                              volumen_rel=e.get("volumen_rel"), grande=int(bool(e.get("grande"))), porque=e.get("porque")))
    filas.sort(key=lambda f: (f["fecha"], f["ticker"]))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas[-3000:])


# ---------------------------------------------------------------- todo junto
DEFECTOS = dict(umbral_movimiento_pct=8, umbral_sigmas=2.5, umbral_minimo_pct=3, umbral_volumen=2.5, mercado="SPY")


def ejecutar(cfg: dict, previo: dict | None = None, fuentes: dict | None = None, guardar: bool = True) -> dict | None:
    lc = cfg.get("lista_noticias") or {}
    if not lc.get("empresas") and not lc.get("materias_primas"):
        return None
    fu = {**FUENTES, **(fuentes or {})}
    previo = previo or {}
    base = {k: lc.get(k, v) for k, v in DEFECTOS.items()}
    hoy = date.today()
    cache: dict[str, dict] = {}

    def mov_de(t):
        if t not in cache:
            cache[t] = dict(ticker=t, **movimiento(_seguro(fu["velas"], t, defecto=[], nombre=f"precios {t}") or []))
        return cache[t]
    mercado = mov_de(base["mercado"])
    emp = lc.get("empresas") or {}
    sec = _seguro(fu["sec"], list(emp), defecto={}, nombre="SEC") or {}
    salud = {t: i.get("nombre") for t, i in emp.items() if (i.get("sector") or "").lower().startswith("salud") and i.get("nombre")}
    ens = _seguro(fu["ensayos"], salud, defecto={}, nombre="ClinicalTrials") if salud else {}
    res = {"fecha": mercado.get("fecha") or hoy.isoformat(), "mercado": mercado, "empresas": {}, "materias_primas": {}}
    for t, info in emp.items():
        info = info or {}
        u = {**base, **{k: info[k] for k in DEFECTOS if k in info}}
        d = dict(velas=_seguro(fu["velas"], t, defecto=[], nombre=f"precios {t}") or [],
                 finnhub=_seguro(fu["finnhub"], t, hoy, defecto=None, nombre=f"Finnhub {t}"),
                 alpaca=_seguro(fu["alpaca"], t, defecto=[], nombre=f"Alpaca {t}") or [],
                 sec=sec.get(t), ensayos=(ens or {}).get(t))
        ref = mov_de(info["referencia"]) if info.get("referencia") else None
        res["empresas"][t] = analizar(t, info, d, (previo.get("empresas") or {}).get(t) or {}, u, ref, mercado)
    for t, info in (lc.get("materias_primas") or {}).items():
        info = info or {}
        velas = _seguro(fu["velas"], info.get("yahoo") or t, defecto=[], nombre=f"precios {t}") or []
        res["materias_primas"][t] = materia_prima(t, info, velas, base, (previo.get("materias_primas") or {}).get(t))
    if guardar:
        os.makedirs(ruta("investigacion", "seguimiento"), exist_ok=True)
        with open(ruta("investigacion", "seguimiento", "lista.md"), "w", encoding="utf-8") as fh:
            fh.write(informe(res))
        _historial(res)
    return res
