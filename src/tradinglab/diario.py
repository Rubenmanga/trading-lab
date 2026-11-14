"""Diario de operaciones: resume el día en diario/AAAA-MM-DD.md (se puede leer desde el móvil en GitHub)."""
from __future__ import annotations

from datetime import date

from .common.config import ruta
from .common.db import DB


def escribir(dia: date | None = None, db: DB | None = None) -> str:
    db, dia = db or DB(), dia or date.today()
    d = dia.isoformat()
    decs = db.filas("SELECT * FROM decisiones WHERE origen LIKE 'sesion%' AND ts LIKE ? ORDER BY id", (f"{d}%",))
    ops = db.filas("SELECT * FROM operaciones WHERE origen LIKE 'sesion%' AND ts_apertura LIKE ? ORDER BY id", (f"{d}%",))
    pnl = sum(o["pnl"] or 0 for o in ops)
    lineas = [f"# Diario {d}", "", f"- Señales: {len(decs)} · ejecutadas: {sum(x['resultado'] == 'PASADA' for x in decs)}"
              f" · frenadas: {sum(x['resultado'] == 'FRENADA' for x in decs)}",
              f"- Resultado del día: {pnl:+.2f} $", "", "## Operaciones", "",
              "| Valor | Lado | Entrada | Salida | Motivo salida | Resultado $ | R |", "|---|---|---|---|---|---|---|"]
    for o in ops:
        lineas.append(f"| {o['simbolo']} | {o['lado']} | {o['entrada']} | {o['salida'] or '-'} | "
                      f"{o['motivo_salida'] or 'abierta'} | {o['pnl'] if o['pnl'] is not None else '-'} | {o['r_multiple'] or '-'} |")
    lineas += ["", "## Todas las decisiones y por qué", ""]
    for x in decs:
        ia = f" · IA: {x['ia_veredicto']} ({x['ia_motivo']})" if x["ia_veredicto"] not in (None, "sin_ia") else ""
        lineas.append(f"- {x['ts'][11:16]} {x['simbolo']} {x['lado']} → **{x['resultado']}** [{x['capa']}] {x['motivo']}{ia}")
    lineas += ["", "## Reflexión (la escribe Claude con la skill diario-operaciones)", "", "_Pendiente._", ""]
    path = ruta("diario", f"{d}.md")
    path.write_text("\n".join(lineas), encoding="utf-8")
    return str(path)
