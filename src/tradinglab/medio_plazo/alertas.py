"""Alertas del agente de medio plazo. NO compra nada: solo avisa."""
from __future__ import annotations

import json
from datetime import date, datetime

from ..common.config import ruta
from ..common.db import DB, ahora
from . import datos, watchlist


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _fecha(x):
    try:
        return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def revisar(cfg: dict, filas: list[dict] | None = None, precio_de=datos.precio, hoy: date | None = None) -> list[dict]:
    a_cfg = cfg["alertas"]
    hoy = hoy or date.today()
    alertas = []
    for w in filas if filas is not None else watchlist.leer():
        if w.get("veredicto") == "descartar":
            continue
        t = w["ticker"]
        p = precio_de(t)

        def add(tipo, msg):
            alertas.append(dict(ticker=t, tipo=tipo, mensaje=msg, precio=p))

        zona, obj, stop = _f(w.get("zona_entrada_max")), _f(w.get("precio_objetivo_12m")), _f(w.get("stop_tesis"))
        if p is not None:
            if w.get("veredicto") == "comprar_en_zona" and zona and p <= zona and not (stop and p <= stop):
                pot = f", potencial {((obj / p) - 1) * 100:.0f}% hasta objetivo" if obj else ""
                add("ZONA DE ENTRADA", f"{t} a {p:.2f} $ está en su zona de entrada (≤ {zona}){pot}")
            if stop and p <= stop:
                add("TESIS EN PELIGRO", f"{t} a {p:.2f} $ ha caído bajo el stop de tesis ({stop}). Revisar.")
            if obj and p >= obj:
                add("OBJETIVO ALCANZADO", f"{t} a {p:.2f} $ ha llegado al precio objetivo ({obj}).")
        fc = _fecha(w.get("fecha_catalizador"))
        if fc and 0 <= (fc - hoy).days <= a_cfg["dias_aviso_catalizador"]:
            add("CATALIZADOR CERCA", f"{t}: '{w.get('proximo_catalizador')}' el {fc} (en {(fc - hoy).days} días)")
        fa = _fecha(w.get("fecha_analisis"))
        if fa and (hoy - fa).days > a_cfg["revisar_tesis_cada_dias"]:
            add("REVISAR ANÁLISIS", f"{t}: el análisis es del {fa}; conviene repasarlo")
    return alertas


def estado(filas: list[dict], precio_de) -> list[dict]:
    """Foto de la lista de vigilancia con el precio de hoy (la usa el panel web)."""
    res = []
    for w in filas:
        p = precio_de(w["ticker"])
        zona, obj, stop = _f(w.get("zona_entrada_max")), _f(w.get("precio_objetivo_12m")), _f(w.get("stop_tesis"))
        res.append(dict(
            ticker=w["ticker"], precio=p,
            distancia_zona_pct=round((p / zona - 1) * 100, 1) if p and zona else None,
            potencial_pct=round((obj / p - 1) * 100, 1) if p and obj else None,
            distancia_stop_pct=round((p / stop - 1) * 100, 1) if p and stop else None,
        ))
    return res


def guardar_json(alertas: list[dict], estado_filas: list[dict]) -> str:
    path = ruta("investigacion", "estado.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(actualizado=ahora(), alertas=alertas, precios=estado_filas), fh, ensure_ascii=False, indent=1)
    return str(path)


def guardar(alertas: list[dict], db: DB | None = None) -> str:
    db = db or DB()
    for a in alertas:
        db.insertar("alertas", ts=ahora(), ticker=a["ticker"], tipo=a["tipo"], mensaje=a["mensaje"])
    path = ruta("investigacion", "alertas.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# Alertas de medio plazo\n\n_Actualizado: {ahora()}_\n\n")
        if not alertas:
            fh.write("Sin alertas.\n")
        for a in alertas:
            fh.write(f"- **{a['tipo']}** · {a['mensaje']}\n")
    return str(path)
