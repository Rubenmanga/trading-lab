"""Radar de resultados (agente B) · PASO 1: prueba con el pasado.

Pregunta: de las empresas que presentan resultados, ¿qué se puede saber ANTES para quedarse con las que
tienen más probabilidad de subir y evitar la «trampa de buenas noticias» (resultados buenos y la acción cae)?

Por cada presentación de resultados (2019-hoy) de las small caps del universo calcula:
  · Lo que se sabía la víspera (filtros): subida de las últimas 4 semanas, distancia al máximo de 52 semanas,
    volumen reciente, cuántas de las últimas 4 veces superó las previsiones y cómo reaccionó el precio.
  · Lo que pasó: reacción del precio ese día, y la deriva a 5 y 20 sesiones (entrando en la apertura del día siguiente).
Luego compara cada filtro con «todas las empresas» y marca la trampa (superó previsiones y aun así cayó).
Solo datos gratis de Yahoo. Sin IA. No hay datos históricos de las revisiones de analistas, así que ese filtro
NO se puede probar aquí (lo dice el informe). Los datos solo incluyen empresas que hoy siguen cotizando
(sesgo de supervivencia: los resultados reales serán algo peores).
"""
from __future__ import annotations

import json
import math
import statistics
from datetime import date, datetime
from pathlib import Path

DESDE = "2018-06-01"
HORIZONTES = (5, 20)


# ------------------------------------------------------------------ un evento (función pura, con pruebas)
def _sig_dia(velas: list[dict], fecha: str) -> int | None:
    """Índice de la primera sesión con fecha >= fecha."""
    for i, v in enumerate(velas):
        if v["fecha"] >= fecha:
            return i
    return None


def momento(hora: int | None) -> str | None:
    """'antes' (de abrir), 'despues' (del cierre) o None si no se sabe con seguridad."""
    if hora is None:
        return None
    if 4 <= hora <= 9:
        return "antes"
    if hora >= 16 or hora <= 1:
        return "despues"
    return None


def construir_evento(velas: list[dict], fecha: str, hora: int | None, sorpresa_pct: float | None,
                     previos: list[dict]) -> dict | None:
    """velas: lista ordenada con fecha, apertura, cierre, volumen. previos: eventos anteriores YA calculados de la misma empresa."""
    m = momento(hora)
    if m is None or sorpresa_pct is None or len(velas) < 80:
        return None
    i0 = _sig_dia(velas, fecha)
    if i0 is None or velas[i0]["fecha"] != fecha and m == "antes":
        return None
    ir = i0 if m == "antes" else i0 + 1       # sesión en la que el mercado reacciona
    if m == "despues" and velas[i0]["fecha"] != fecha:
        return None
    if ir < 253 or ir + max(HORIZONTES) + 2 >= len(velas):
        return None
    c = [v["cierre"] for v in velas]
    vol = [v["volumen"] for v in velas]
    b = ir - 1                                  # última sesión antes de la reacción
    if not (c[b] > 0 and c[ir] > 0 and velas[ir]["apertura"] > 0):
        return None
    pico = max(c[b - 251:b + 1])
    v5, v60 = statistics.fmean(vol[b - 4:b + 1]), statistics.fmean(vol[b - 59:b + 1])
    rets = [c[k] / c[k - 1] - 1 for k in range(b - 19, b + 1)]
    ev = dict(
        fecha=fecha, momento=m, sorpresa_pct=round(sorpresa_pct, 2), supero=sorpresa_pct > 0,
        subida_4s=round((c[b] / c[b - 20] - 1) * 100, 1),
        dist_max52=round((c[b] / pico - 1) * 100, 1),
        volumen_rel=round(v5 / v60, 2) if v60 else None,
        volatilidad_20d=round(statistics.pstdev(rets) * 100, 2),
        previas_superadas=sum(1 for p in previos[-4:] if p["supero"]) if len(previos) >= 4 else None,
        reaccion_previa=round(statistics.fmean([p["reaccion"] for p in previos[-4:]]), 2) if len(previos) >= 4 else None,
        hueco=round((velas[ir]["apertura"] / c[b] - 1) * 100, 2),
        reaccion=round((c[ir] / c[b] - 1) * 100, 2),
    )
    entrada = velas[ir + 1]["apertura"]
    for h in HORIZONTES:
        ev[f"deriva_{h}d"] = round((c[ir + h] / entrada - 1) * 100, 2) if entrada > 0 else None
    ev["trampa"] = bool(ev["supero"] and ev["reaccion"] < 0)
    return ev


def eventos_de_empresa(velas: list[dict], citas: list[tuple[str, int | None, float | None]]) -> list[dict]:
    """citas: [(fecha 'AAAA-MM-DD', hora local de EE. UU., sorpresa %)], en cualquier orden."""
    out: list[dict] = []
    for fecha, hora, sorp in sorted(citas):
        if fecha < "2019-06-01":
            continue
        ev = construir_evento(velas, fecha, hora, sorp, out)
        if ev:
            out.append(ev)
    return out


# ------------------------------------------------------------------ descarga (solo en Actions: Yahoo)
def descargar_empresa(ticker: str) -> list[dict]:
    import yfinance as yf
    t = yf.Ticker(ticker)
    df = t.history(start=DESDE, interval="1d", auto_adjust=True)
    velas = [dict(fecha=str(i.date()), apertura=float(f["Open"]), cierre=float(f["Close"]), volumen=float(f["Volume"]))
             for i, f in df.iterrows() if f["Close"] == f["Close"] and f["Open"] == f["Open"]]
    ed = t.get_earnings_dates(limit=60)
    citas = []
    if ed is not None and len(ed):
        for idx, f in ed.iterrows():
            sorp = f.get("Surprise(%)")
            if sorp is None or sorp != sorp:
                continue
            hora = idx.hour if getattr(idx, "hour", None) is not None else None
            citas.append((str(idx.date()), hora, float(sorp)))
    return eventos_de_empresa(velas, citas)


def correr_parte(tickers: list[str], salida: Path, pausa: float = 0.6, minutos: float = 50) -> dict:
    import time
    t0, ok, fallos = time.time(), 0, []
    hechos = set()
    if salida.exists():
        for linea in salida.read_text(encoding="utf-8").splitlines():
            try:
                hechos.add(json.loads(linea)["ticker"])
            except Exception:  # noqa: BLE001
                pass
    with open(salida, "a", encoding="utf-8") as fh:
        for tk in tickers:
            if tk in hechos:
                continue
            if time.time() - t0 > minutos * 60:
                fallos.append(f"{tk}… (tiempo agotado)")
                break
            for intento in range(3):
                try:
                    evs = descargar_empresa(tk)
                    fh.write(json.dumps(dict(ticker=tk, eventos=evs), ensure_ascii=False) + "\n")
                    fh.flush()
                    ok += 1
                    break
                except Exception as e:  # noqa: BLE001
                    if intento == 2:
                        fallos.append(f"{tk}: {type(e).__name__}")
                    time.sleep(3 * (intento + 1))
            time.sleep(pausa)
    return dict(ok=ok, fallos=fallos)


# ------------------------------------------------------------------ análisis
def _stats(vals: list[float]) -> dict:
    v = [x for x in vals if x is not None]
    if not v:
        return dict(n=0)
    sd = statistics.pstdev(v) if len(v) > 1 else 0
    return dict(n=len(v), media=round(statistics.fmean(v), 2), mediana=round(statistics.median(v), 2),
                aciertos=round(sum(1 for x in v if x > 0) / len(v) * 100, 1),
                peor10=round(sorted(v)[max(0, int(len(v) * 0.1) - 1)], 1),
                t=round(statistics.fmean(v) / (sd / math.sqrt(len(v))), 1) if sd else 0)


REGLAS = {
    "No ha subido mucho antes (últimas 4 semanas < +10 %)": lambda e: e["subida_4s"] < 10,
    "Lejos de su máximo de 52 semanas (a más de 10 % por debajo)": lambda e: e["dist_max52"] < -10,
    "Superó previsiones 3 o 4 de las últimas 4 veces": lambda e: e["previas_superadas"] is not None and e["previas_superadas"] >= 3,
    "Suele subir tras resultados (reacción media previa > 0)": lambda e: e["reaccion_previa"] is not None and e["reaccion_previa"] > 0,
    "Volumen reciente normal o bajo (< 1,3x)": lambda e: e["volumen_rel"] is not None and e["volumen_rel"] < 1.3,
}


def _combos():
    k = list(REGLAS)
    return {
        "TODAS (referencia)": lambda e: True,
        **{n: f for n, f in REGLAS.items()},
        "Combinada: no ha subido + suele subir tras resultados": lambda e: REGLAS[k[0]](e) and REGLAS[k[3]](e),
        "Combinada: no ha subido + superó 3-4 veces + suele subir": lambda e: REGLAS[k[0]](e) and REGLAS[k[2]](e) and REGLAS[k[3]](e),
        "Combinada: lejos del máximo + superó 3-4 veces": lambda e: REGLAS[k[1]](e) and REGLAS[k[2]](e),
        "Combinada de las 4 primeras": lambda e: all(REGLAS[x](e) for x in k[:4]),
    }


def analizar(eventos: list[dict]) -> dict:
    """Devuelve estadísticas por regla, en conjunto y separadas por mitades de años (para ver si se mantiene)."""
    ev = [e for e in eventos if e.get("reaccion") is not None]
    fechas = sorted(e["fecha"] for e in ev)
    corte = fechas[len(fechas) // 2] if fechas else "2022-01-01"
    res = {"n_eventos": len(ev), "corte_mitades": corte, "reglas": {}}
    for nombre, f in _combos().items():
        sel = [e for e in ev if f(e)]
        a, b = [e for e in sel if e["fecha"] < corte], [e for e in sel if e["fecha"] >= corte]
        supero = [e for e in sel if e["supero"]]
        res["reglas"][nombre] = dict(
            reaccion=_stats([e["reaccion"] for e in sel]),
            reaccion_1a_mitad=_stats([e["reaccion"] for e in a]),
            reaccion_2a_mitad=_stats([e["reaccion"] for e in b]),
            trampa_pct=round(sum(1 for e in supero if e["reaccion"] < 0) / len(supero) * 100, 1) if supero else None,
            deriva_20d_tras_subida=_stats([e["deriva_20d"] for e in sel if e["reaccion"] >= 5 and e["supero"]]),
            deriva_20d_tras_trampa=_stats([e["deriva_20d"] for e in sel if e["trampa"]]),
        )
    return res


def veredicto(regla: dict, base: dict, minimo_n: int = 300) -> str:
    """Una regla solo 'funciona' si mejora a la referencia en las DOS mitades, con suficientes casos."""
    r, b = regla["reaccion"], base["reaccion"]
    if r["n"] < minimo_n:
        return "pocos casos"
    m1, m2 = regla["reaccion_1a_mitad"], regla["reaccion_2a_mitad"]
    b1, b2 = base["reaccion_1a_mitad"], base["reaccion_2a_mitad"]
    if not (m1.get("n") and m2.get("n")):
        return "pocos casos"
    mejora = r["media"] - b["media"]
    if mejora >= 0.5 and m1["media"] > b1["media"] and m2["media"] > b2["media"] and r["t"] >= 2:
        return "SÍ mejora (en las dos mitades)"
    if mejora <= -0.5 and m1["media"] < b1["media"] and m2["media"] < b2["media"]:
        return "EMPEORA (mejor evitarla)"
    return "no se nota"


def informe(res: dict, fallos: list[str] | None = None) -> str:
    base = res["reglas"]["TODAS (referencia)"]
    hoy = date.today().isoformat()
    n = res["n_eventos"]
    l = [f"# Radar de resultados · prueba con el pasado · {hoy}", "",
         "## Resumen (5 líneas)",
         f"1. Se probaron **{n:,}** presentaciones de resultados de small caps de EE. UU. (2019 a hoy).".replace(",", "."),
         f"2. De media la acción se mueve **{base['reaccion']['media']:+} %** el día de la reacción y sube el {base['reaccion']['aciertos']} % de las veces.",
         f"3. La **trampa** (superó previsiones y aun así cayó) ocurre en el **{base['trampa_pct']} %** de los casos en que se superan.",
         "4. Mira abajo qué filtros mejoran de verdad a la referencia (deben mejorar en las dos mitades del periodo).",
         "5. Límites: sin datos históricos de analistas, y solo empresas que hoy siguen cotizando (los resultados reales serían algo peores).", "",
         "## Cómo leer las tablas",
         "- **Reacción**: cambio del precio entre el cierre de la víspera y el cierre del día en que el mercado reacciona a los resultados. "
         "Es lo que ganaría quien compra la víspera y vende ese día.",
         "- **Aciertos**: % de veces que la reacción fue positiva. **Peor 10 %**: la reacción por debajo de la cual está el 10 % de los peores casos (el riesgo).",
         "- **t**: fiabilidad estadística (por encima de 2 es poco probable que sea casualidad).",
         "- **Trampa**: de las veces que superó previsiones, % en que aun así cayó.",
         "- **Veredicto**: solo es «SÍ» si mejora a la referencia en la primera y en la segunda mitad del periodo.", "",
         "## Filtros de la víspera", "",
         "| Filtro | Casos | Reacción media | Aciertos | Peor 10 % | t | Trampa | Mitad 1 → mitad 2 | Veredicto |",
         "|---|---|---|---|---|---|---|---|---|"]
    for nombre, r in res["reglas"].items():
        s = r["reaccion"]
        if not s.get("n"):
            continue
        v = "—" if nombre.startswith("TODAS") else veredicto(r, base)
        a, b = r["reaccion_1a_mitad"], r["reaccion_2a_mitad"]
        l.append(f"| {nombre} | {s['n']} | {s['media']:+} % | {s['aciertos']} % | {s['peor10']} % | {s['t']} | {r['trampa_pct']} % | "
                 f"{a.get('media', '—')} → {b.get('media', '—')} | {v} |")
    l += ["", "## Después de los resultados (¿conviene esperar y entrar con la noticia ya conocida?)",
          "Entrando en la apertura del día siguiente a la reacción. Se mira la deriva (lo que hace el precio después) a 20 sesiones.", "",
          "| Situación | Casos | Deriva media 20 sesiones | Aciertos | Peor 10 % |", "|---|---|---|---|---|"]
    r0 = base
    for etiqueta, k in (("Superó y subió ≥ 5 % el día de resultados", "deriva_20d_tras_subida"),
                        ("Superó previsiones pero cayó (trampa)", "deriva_20d_tras_trampa")):
        s = r0[k]
        if s.get("n"):
            l.append(f"| {etiqueta} | {s['n']} | {s['media']:+} % | {s['aciertos']} % | {s['peor10']} % |")
    l += ["", "## Qué NO se pudo probar",
          "- Revisiones de analistas, valoración frente al precio objetivo y ventas en corto: no hay histórico gratuito de esos datos tal como se veían entonces.",
          "- Costes de comprar y vender (en small caps el hueco entre compra y venta puede comerse parte de la ganancia).", ""]
    if fallos:
        l += [f"Empresas que no se pudieron bajar ({len(fallos)}): " + ", ".join(fallos[:40]) + ("…" if len(fallos) > 40 else ""), ""]
    return "\n".join(l)
