"""Carpeta del día (Paso 5 de la revisión del 16-nov-2026).

Junta en `investigacion/hoy.md` lo que ya han dejado otros programas, SIN IA y sin descargar nada:
avisos de hoy, hechos nuevos de los expedientes, acciones dentro de su zona de entrada,
catalizadores de los próximos 14 días y caras nuevas en lo alto del ranking.
Tiene que caber en una pantalla del móvil: el investigador diario (Paso 6) lee solo este archivo.
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from ..common.config import ruta
from .expediente import seguidas

DIAS_HECHOS = 4        # hechos de los expedientes de los últimos 4 días (cubre el fin de semana)
DIAS_CATALIZADOR = 14
MAX_POR_SECCION = 6
TOP = 10
IMPORTANTES = ("ZONA DE ENTRADA", "TESIS EN PELIGRO", "OBJETIVO ALCANZADO", "CATALIZADOR CERCA",
               "SEÑAL DE ENTRADA", "SOPORTE PERDIDO", "MOVIMIENTO GRANDE", "NOTICIA IMPORTANTE")


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _csv(path: Path) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except FileNotFoundError:
        return []


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _fecha(x) -> date | None:
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _recorta(filas: list[str]) -> list[str]:
    if len(filas) > MAX_POR_SECCION:
        return filas[:MAX_POR_SECCION] + [f"- … y {len(filas) - MAX_POR_SECCION} más"]
    return filas


# ------------------------------------------------------------------ secciones
def avisos(estado: dict) -> list[str]:
    vistos, out = set(), []
    for a in estado.get("alertas") or []:
        if a.get("tipo") in IMPORTANTES and (a.get("ticker"), a.get("tipo")) not in vistos:
            vistos.add((a.get("ticker"), a.get("tipo")))
            out.append(f"- **{a['tipo']}** · {a.get('mensaje', '')}")
    return out


def hechos_nuevos(tickers: dict[str, str], carpeta: Path, hoy: date) -> list[str]:
    desde = hoy - timedelta(days=DIAS_HECHOS)
    filas = []
    for t in tickers:
        for e in _csv(carpeta / t / "eventos.csv"):
            f = _fecha(e.get("fecha"))
            if f and desde <= f <= hoy:
                r1 = e.get("reaccion_1d")
                reac = f" (1 día: {r1} %)" if r1 not in (None, "") else ""
                filas.append((f, f"- {f:%d/%m} **{t}** · {e.get('resumen', '')}{reac}"))
    return [x for _, x in sorted(filas, key=lambda p: p[0], reverse=True)]


def en_zona(watch: list[dict], precios: dict[str, float]) -> list[str]:
    out = []
    for w in watch:
        t = (w.get("ticker") or "").upper()
        p, zona = precios.get(t), _num(w.get("zona_entrada_max"))
        if p is None or zona is None or p > zona:
            continue
        obj, stop = _num(w.get("precio_objetivo_12m")), _num(w.get("stop_tesis"))
        extra = f", objetivo {obj:g} (+{(obj / p - 1) * 100:.0f} %)" if obj else ""
        extra += f", stop de tesis {stop:g}" if stop else ""
        out.append(f"- **{t}** a {p:.2f} $ ≤ zona {zona:g}{extra} · {w.get('veredicto', '')}")
    return out


def catalizadores(watch: list[dict], ranking: list[dict], tickers: dict[str, str], hoy: date) -> list[str]:
    hasta = hoy + timedelta(days=DIAS_CATALIZADOR)
    filas, vistos = [], set()
    for w in watch:
        f = _fecha(w.get("fecha_catalizador"))
        t = (w.get("ticker") or "").upper()
        if f and hoy <= f <= hasta:
            vistos.add(t)
            filas.append((f, f"- {f:%d/%m} **{t}** · {w.get('proximo_catalizador', '')}"))
    for r in ranking:   # resultados trimestrales de las que sigues (dato del ranking diario)
        t = (r.get("ticker") or "").upper()
        f = _fecha(r.get("proximos_resultados"))
        if t in tickers and t not in vistos and f and hoy <= f <= hasta:
            filas.append((f, f"- {f:%d/%m} **{t}** · presenta resultados"))
    return [x for _, x in sorted(filas, key=lambda p: p[0])]


def nuevas_arriba(ranking: list[dict], anterior: list[dict]) -> list[str]:
    if not anterior:
        return []
    antes = {(r.get("ticker") or "").upper() for r in anterior[:TOP]}
    out = []
    for r in ranking[:TOP]:
        t = (r.get("ticker") or "").upper()
        if t and t not in antes:
            out.append(f"- #{r.get('puesto')} **{t}** · nota {r.get('nota')} · {r.get('carril', '')}")
    return out


def _ranking_anterior(carpeta: Path, hoy: date, actualizado: str) -> list[dict]:
    """El último CSV de `historico/` anterior al ranking actual."""
    fecha_rank = (actualizado or "")[:10] or hoy.isoformat()
    previos = sorted(p for p in carpeta.glob("*.csv") if p.stem < fecha_rank)
    return _csv(previos[-1]) if previos else []


# ------------------------------------------------------------------ armado
def construir(hoy: date | None = None, base: Path | None = None, tickers: dict[str, str] | None = None) -> str:
    hoy = hoy or date.today()
    inv = base or Path(ruta("investigacion"))
    estado = _json(inv / "estado.json")
    rank = _json(inv / "ranking.json")
    filas_rank = rank.get("filas") or []
    watch = _csv(inv / "watchlist.csv")
    precios = {(p.get("ticker") or "").upper(): _num(p.get("precio")) for p in estado.get("precios") or []
               if _num(p.get("precio")) is not None}
    tickers = tickers if tickers is not None else seguidas()

    secciones = [
        ("🔔 Avisos de hoy", avisos(estado)),
        (f"📰 Hechos nuevos en tus expedientes (últimos {DIAS_HECHOS} días)",
         hechos_nuevos(tickers, inv / "expedientes", hoy)),
        ("🎯 Dentro de su zona de entrada", en_zona(watch, precios)),
        (f"📅 Catalizadores en los próximos {DIAS_CATALIZADOR} días", catalizadores(watch, filas_rank, tickers, hoy)),
        (f"🆕 Nuevas en el top {TOP} del ranking",
         nuevas_arriba(filas_rank, _ranking_anterior(inv / "historico", hoy, rank.get("actualizado", "")))),
    ]
    act = (estado.get("actualizado") or "")[:16].replace("T", " ")
    lineas = [f"# Carpeta del día · {hoy:%d/%m/%Y}", "",
              f"_Resumen automático, sin IA. Precios y avisos del {act or '¿?'} UTC. "
              f"Sigues {len(tickers)} acciones._"]
    for titulo, filas in secciones:
        lineas += ["", f"## {titulo}"] + (_recorta(filas) or ["- Nada."])
    lineas += ["", "_Detector de inflexión x3-x4: llegará en el Paso 8._", ""]
    return "\n".join(lineas)


def ejecutar(hoy: date | None = None, base: Path | None = None) -> Path:
    inv = base or Path(ruta("investigacion"))
    texto = construir(hoy, inv)
    salida = inv / "hoy.md"
    salida.write_text(texto, encoding="utf-8")
    return salida


if __name__ == "__main__":
    print(ejecutar().read_text(encoding="utf-8"))
