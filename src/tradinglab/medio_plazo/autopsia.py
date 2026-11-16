"""Autopsias de resultados (Paso 10 de la revisión del 16-nov-2026). Sin IA.

Tras cada presentación de resultados de una acción seguida se apuntan en `investigacion/autopsias/autopsias.csv`
(una línea por presentación, SOLO SE AÑADE) los hechos: qué se esperaba (consenso), qué salió, qué dijo la
empresa del futuro (previsión = «guía») y la lección, cada uno con su fuente. Lo escribe Claude o Ruben.

Este módulo pone lo que se puede medir sin opinar:
- cuánto había subido o bajado la acción en las 20 sesiones de antes (lo «descontado»),
- la reacción del precio a 1, 5 y 20 sesiones (desde el último cierre ANTES de conocer los resultados:
  si se publican tras el cierre, la base es el cierre de ese mismo día),
- qué decía nuestra predicción del libro (`predicciones.csv`, Paso 3) y si se rompió su stop de tesis,
- el resultado en una frase («supera y cae», «falla y cae»…).

Salidas: `investigacion/autopsias/autopsias.json` (panel), `investigacion/autopsias/resumen.md` (patrones por
trimestre) y `investigacion/expedientes/TICKER/autopsias.md` (las 10 líneas dentro del expediente, Paso 1).
También avisa de las presentaciones de resultados del expediente que aún no tienen autopsia.
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from ..common.config import ruta

COLUMNAS = ["ticker", "fecha", "hora", "trimestre", "ventas_esperadas", "ventas_reales", "bpa_esperado",
            "bpa_real", "guia", "guia_texto", "extendido_pct", "fuente_resultados", "fuente_consenso", "leccion"]
GUIA = {"sube": "la sube", "mantiene": "la mantiene", "baja": "la baja", "retira": "la retira",
        "retrasa": "retrasa entregas o fechas", "sin": "no da previsión"}
PLAZOS = {"r1": 1, "r5": 5, "r20": 20}


def _f(x):
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


def _pct(a, b):
    return round((a / b - 1) * 100, 2) if a and b else None


def leer(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("ticker")]


def medir(fila: dict, velas: list[dict]) -> dict:
    """Subida previa de 20 sesiones y reacción a 1/5/20 sesiones desde el último cierre sin conocer los resultados."""
    fechas = [v["fecha"] for v in velas]
    tras = fila.get("hora") == "tras_cierre"
    # índice de la vela base: último cierre antes de conocerse los resultados
    if tras:
        b = max((k for k, f in enumerate(fechas) if f <= fila["fecha"]), default=None)
    else:
        b = max((k for k, f in enumerate(fechas) if f < fila["fecha"]), default=None)
    out = {"precio_antes": None, "previa_20d": None, **{k: None for k in PLAZOS}}
    if b is None:
        return out
    base = velas[b]["cierre"]
    out["precio_antes"] = round(base, 4)
    if b >= 20:
        out["previa_20d"] = _pct(base, velas[b - 20]["cierre"])
    for k, n in PLAZOS.items():
        if b + n < len(velas):
            out[k] = _pct(velas[b + n]["cierre"], base)
    return out


def prediccion(ticker: str, fecha: str, libro: list[dict]) -> dict | None:
    """La última predicción del libro para esa acción hecha el día de los resultados o antes."""
    previas = [p for p in libro if p.get("ticker") == ticker and p.get("fecha", "") <= fecha]
    if not previas:
        return None
    p = max(previas, key=lambda x: x["fecha"])
    return {k: p.get(k, "") for k in ("id", "fecha", "veredicto", "precio", "stop_tesis", "objetivo", "zona_entrada_max")}


def desenlace(fila: dict, m: dict) -> dict:
    """Clasifica sin opinar: ¿superó lo esperado? ¿cómo reaccionó el precio?"""
    ve, vr = _f(fila.get("ventas_esperadas")), _f(fila.get("ventas_reales"))
    be, br = _f(fila.get("bpa_esperado")), _f(fila.get("bpa_real"))
    sv = _pct(vr, ve) if ve and vr is not None else None
    marcas = []
    if sv is not None:
        marcas.append(sv >= 0)
    if be is not None and br is not None:
        marcas.append(br >= be)
    if not marcas:
        resultado = "sin consenso"
    elif all(marcas):
        resultado = "supera"
    elif not any(marcas):
        resultado = "falla"
    else:
        resultado = "mixto"
    r = m.get("r1")
    medida = "1 sesión"
    if r is None and _f(fila.get("extendido_pct")) is not None:
        r, medida = _f(fila["extendido_pct"]), "horario extendido"
    precio = "sube" if r is not None and r > 0 else "cae" if r is not None and r < 0 else "sin reacción aún"
    return {"sorpresa_ventas_pct": sv, "resultado": resultado, "reaccion": r, "reaccion_medida": medida,
            "precio": precio, "frase": f"{resultado} y {precio}" if r is not None else f"{resultado} (reacción pendiente)"}


def autopsia(fila: dict, velas: list[dict], libro: list[dict]) -> dict:
    m = medir(fila, velas) if velas else {"precio_antes": None, "previa_20d": None, **{k: None for k in PLAZOS}}
    d = desenlace(fila, m)
    p = prediccion(fila["ticker"], fila["fecha"], libro)
    if p:
        stop, pa = _f(p.get("stop_tesis")), m.get("precio_antes")
        r = d["reaccion"]
        despues = round(pa * (1 + r / 100), 4) if pa and r is not None else None
        p["precio_despues"] = despues
        p["stop_roto"] = (despues < stop) if stop and despues else None
    return {**{k: fila.get(k, "") for k in COLUMNAS}, **m, **d, "prediccion": p}


def _n(x, dec=2, signo=False):
    if x is None:
        return "—"
    s = f"{x:+.{dec}f}" if signo else f"{x:.{dec}f}"
    return s.replace(".", ",")


def diez_lineas(a: dict) -> str:
    """La autopsia en ~10 líneas para el móvil (va dentro del expediente)."""
    cuando = "tras el cierre" if a["hora"] == "tras_cierre" else "antes de la apertura"
    p = a["prediccion"]
    if p:
        pred = f"«{p['veredicto']}» el {p['fecha']} a {p['precio']} $"
        if p.get("stop_tesis"):
            pred += f", stop de tesis {p['stop_tesis']} $" + (" → **ROTO**" if p.get("stop_roto") else
                                                             " → aguanta" if p.get("stop_roto") is False else "")
    else:
        pred = "no había predicción en el libro"
    reac = " · ".join(f"{n}: {_n(a[k], 1, True)} %" for k, n in (("r1", "1 sesión"), ("r5", "5"), ("r20", "20")))
    ext = f" (horario extendido: {_n(_f(a['extendido_pct']), 1, True)} %)" if _f(a.get("extendido_pct")) is not None else ""
    return "\n".join([
        f"### {a['fecha']} · {a['trimestre']} · **{a['frase']}**",
        f"1. **Cuándo**: {a['fecha']}, {cuando}.",
        f"2. **Se esperaba** (consenso): ventas {_n(_f(a['ventas_esperadas']))} M$, BPA {_n(_f(a['bpa_esperado']))} $. Fuente: {a['fuente_consenso']}.",
        f"3. **Salió**: ventas {_n(_f(a['ventas_reales']))} M$ ({_n(a['sorpresa_ventas_pct'], 0, True)} % frente a lo esperado), BPA {_n(_f(a['bpa_real']))} $. [Fuente oficial]({a['fuente_resultados']}).",
        f"4. **Previsión de la empresa**: {GUIA.get(a['guia'], a['guia'])}. {a['guia_texto']}",
        f"5. **Antes**: en las 20 sesiones previas se movió {_n(a['previa_20d'], 1, True)} % (lo ya «descontado»).",
        f"6. **Reacción**: {reac}{ext}.",
        f"7. **Nuestra predicción**: {pred}.",
        f"8. **Lección**: {a['leccion']}",
        "",
    ])


def resumen(auts: list[dict], pendientes: list[dict], hoy: date) -> str:
    n = len(auts)
    con = [a for a in auts if a["reaccion"] is not None]
    sup_cae = [a for a in con if a["resultado"] == "supera" and a["precio"] == "cae"]
    malas = [a for a in con if a["guia"] in ("baja", "retira", "retrasa")]
    buenas = [a for a in con if a["guia"] in ("sube", "mantiene")]
    media = lambda xs: _n(sum(x["reaccion"] for x in xs) / len(xs), 1, True) + " %" if xs else "—"  # noqa: E731
    lineas = [
        f"# Autopsias de resultados · {hoy.isoformat()}", "",
        f"1. **{n} autopsias** ({len(con)} con reacción medida). Con tan pocas, los patrones son pistas, no reglas.",
        f"2. Previsión recortada, retirada o retrasada: reacción media **{media(malas)}** ({len(malas)} casos); mantenida o subida: **{media(buenas)}** ({len(buenas)}).",
        f"3. «Supera y cae»: {len(sup_cae)} de {len([a for a in con if a['resultado'] == 'supera'])} que superaron (el radar ya vio un 42 %).",
        f"4. Stops de tesis rotos tras resultados: {sum(1 for a in auts if (a['prediccion'] or {}).get('stop_roto'))}.",
        f"5. Pendientes de autopsia: {len(pendientes)}." , "",
        "Qué es: tras cada presentación de resultados se apunta qué se esperaba, qué salió, qué dijo la empresa del "
        "futuro y cómo reaccionó el precio. Sirve para entender **por qué unas acciones caen con buenos resultados y otras suben**.", "",
    ]
    por_t: dict[str, list[dict]] = {}
    for a in auts:
        por_t.setdefault(a["trimestre"], []).append(a)
    for t in sorted(por_t, reverse=True):
        lineas += [f"## {t}", "", "| Acción | Fecha | Resultado | Previsión | Antes 20 s. | Reacción | Lección |", "|---|---|---|---|---|---|---|"]
        for a in sorted(por_t[t], key=lambda x: x["fecha"], reverse=True):
            lineas.append(f"| {a['ticker']} | {a['fecha']} | {a['frase']} | {GUIA.get(a['guia'], a['guia'])} | "
                          f"{_n(a['previa_20d'], 1, True)} % | {_n(a['reaccion'], 1, True)} % ({a['reaccion_medida']}) | "
                          f"{a['leccion'].split(':')[0][:90]} |")
        lineas.append("")
    if pendientes:
        lineas += ["## Pendientes (resultados del expediente sin autopsia)", ""]
        lineas += [f"- {p['ticker']} · {p['fecha']} · [{p['resumen']}]({p['fuente_url']})" for p in pendientes]
        lineas.append("")
    lineas.append("Fuentes: notas de resultados en la SEC (enlace en cada autopsia); consenso de webs intermediarias "
                  "(dicho en cada caso); precios de Yahoo. Reacción = cierre N sesiones después ÷ último cierre antes de los resultados − 1.")
    return "\n".join(lineas) + "\n"


def pendientes_expediente(carpeta: Path, hechas: set[tuple], hoy: date, dias: int = 45) -> list[dict]:
    desde = (hoy - timedelta(days=dias)).isoformat()
    out = []
    if not carpeta.exists():
        return out
    for d in sorted(carpeta.iterdir()):
        ev = d / "eventos.csv"
        if not ev.exists():
            continue
        with ev.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("tipo") == "resultados" and r.get("fecha", "") >= desde and (d.name, r["fecha"]) not in hechas:
                    out.append({"ticker": d.name, **r})
    return out


def ejecutar(fuente_velas=None, base: Path | None = None, hoy: date | None = None) -> list[dict]:
    hoy = hoy or date.today()
    base = base or ruta("investigacion")
    filas = leer(base / "autopsias" / "autopsias.csv")
    libro = leer(base / "predicciones.csv")
    if fuente_velas is None:
        from .seguimiento import velas_yahoo

        def fuente_velas(t):
            return velas_yahoo(t, "1y")
    cache: dict[str, list] = {}
    auts = []
    for f in filas:
        t = f["ticker"]
        if t not in cache:
            try:
                cache[t] = fuente_velas(t) or []
            except Exception as e:  # noqa: BLE001
                print(f"{t}: sin precios ({type(e).__name__})")
                cache[t] = []
        auts.append(autopsia(f, cache[t], libro))
    auts.sort(key=lambda a: (a["fecha"], a["ticker"]), reverse=True)
    exp = base / "expedientes"
    pend = pendientes_expediente(exp, {(a["ticker"], a["fecha"]) for a in auts}, hoy)
    sal = base / "autopsias"
    sal.mkdir(parents=True, exist_ok=True)
    (sal / "autopsias.json").write_text(json.dumps({"actualizado": hoy.isoformat(), "autopsias": auts,
                                                    "pendientes": [{k: p.get(k) for k in ("ticker", "fecha", "resumen", "fuente_url")} for p in pend]},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    (sal / "resumen.md").write_text(resumen(auts, pend, hoy), encoding="utf-8")
    for t in {a["ticker"] for a in auts}:
        d = exp / t
        d.mkdir(parents=True, exist_ok=True)
        txt = "\n".join(diez_lineas(a) for a in auts if a["ticker"] == t)
        (d / "autopsias.md").write_text(f"# {t} · Autopsias de resultados\n\nLo más nuevo arriba. Datos en "
                                        f"`investigacion/autopsias/autopsias.csv` (solo se añade).\n\n{txt}", encoding="utf-8")
    return auts
