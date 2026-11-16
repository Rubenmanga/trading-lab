"""Marcador del bot del corto del hueco (agente A, Paso 9 de la revisión).

Compara lo que hace el bot de verdad (eToro DEMO, investigacion/corto-hueco/registro.csv)
con lo que decía el backtest 2016-hoy (investigacion/laboratorio/resumen.json, «como el bot»),
y recuerda la fecha de decisión: si ese día hay menos de `ops_min` operaciones o la media es
menor de `R_min`, el bot se apaga. Sin IA. Salida: investigacion/corto-hueco/marcador.json.

R = lo que se gana o pierde medido en «riesgos»: 1 R = lo que se pierde si salta el stop (15 %).
Un corto que acaba un +3 % vale +0,2 R.
"""
from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path

from ...common import config

_STOP_SUPUESTO = "ya cerrada"  # el bot no la encuentra abierta al cierre: lo más probable es que saltara el stop


def _leer_csv(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    with open(ruta, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _num(x) -> float | None:
    try:
        return None if x is None or str(x).strip() == "" else float(x)
    except (TypeError, ValueError):
        return None


def operaciones_bot(filas: list[dict], stop_pct: float) -> list[dict]:
    """Une cada «abierta» con su cierre (misma acción, el primero que llega después)."""
    ops, pendientes = [], []
    for f in filas:
        acc, sim = f.get("accion"), (f.get("simbolo") or "").upper()
        if acc == "abierta":
            o = {"dia": f["fecha_hora_ny"][:10], "simbolo": sim, "hueco": _num(f.get("hueco")),
                 "entrada": _num(f.get("precio")), "estado": "abierta", "resultado_pct": None, "R": None}
            ops.append(o)
            pendientes.append(o)
        elif acc in ("cerrada", _STOP_SUPUESTO):
            o = next((p for p in pendientes if p["simbolo"] == sim), None)
            if not o:
                continue
            pendientes.remove(o)
            if acc == "cerrada" and _num(f.get("resultado_pct")) is not None:
                o["resultado_pct"] = _num(f["resultado_pct"])
                o["estado"] = "cerrada"
            else:
                o["resultado_pct"] = -stop_pct
                o["estado"] = "stop (supuesto)"
            o["R"] = round(o["resultado_pct"] / stop_pct, 3)
    return ops


def _resumen(rs: list[float]) -> dict:
    n = len(rs)
    if not n:
        return {"n": 0, "R_medio": None, "R_total": 0.0, "aciertos_pct": None, "margen95": None}
    m = sum(rs) / n
    sd = math.sqrt(sum((r - m) ** 2 for r in rs) / (n - 1)) if n > 1 else None
    return {"n": n, "R_medio": round(m, 3), "R_total": round(sum(rs), 2),
            "aciertos_pct": round(100 * sum(r > 0 for r in rs) / n, 1),
            "margen95": round(1.96 * sd / math.sqrt(n), 3) if sd else None}


def _laborables(a: date, b: date) -> int:
    """Días de lunes a viernes entre a y b (ambos incluidos; sin contar festivos)."""
    if b < a:
        return 0
    dias = (b - a).days + 1
    semanas, resto = divmod(dias, 7)
    return semanas * 5 + sum((a.weekday() + i) % 7 < 5 for i in range(resto))


def veredicto(n: int, R_medio: float | None, hoy: date, dec: dict) -> dict:
    fecha = date.fromisoformat(str(dec["fecha"]))
    ops_min, R_min = int(dec["ops_min"]), float(dec["R_min"])
    cumple = n >= ops_min and R_medio is not None and R_medio >= R_min
    if hoy >= fecha:
        estado = "seguir" if cumple else "apagar"
        texto = (f"Ha llegado la fecha de decisión ({fecha:%d-%m-%Y}). "
                 + (f"Cumple el listón ({n} operaciones, media {R_medio:+.2f} R): puede seguir en demo."
                    if cumple else
                    f"No cumple el listón (hace falta ≥ {ops_min} operaciones y media ≥ {R_min:+.1f} R; "
                    f"hay {n} y {'sin media' if R_medio is None else f'{R_medio:+.2f} R'}): toca apagarlo."))
    elif n < 20:
        estado = "pronto"
        texto = ("Aún no hay operaciones cerradas." if n == 0 else
                 f"Solo {n} operación{'es' if n > 1 else ''} cerrada{'s' if n > 1 else ''}: es demasiado pronto, "
                 "con tan pocas cualquier resultado puede ser suerte.")
        texto += f" Se decide el {fecha:%d-%m-%Y}."
    else:
        estado = "en camino" if cumple else ("faltan operaciones" if R_medio is not None and R_medio >= R_min else "por debajo")
        texto = {"en camino": f"De momento cumple el listón ({n} operaciones, media {R_medio:+.2f} R).",
                 "faltan operaciones": f"La media ({R_medio:+.2f} R) va bien, pero faltan operaciones ({n} de {ops_min}).",
                 "por debajo": f"La media ({R_medio:+.2f} R) está por debajo del listón de {R_min:+.1f} R."}[estado]
        texto += f" Se decide el {fecha:%d-%m-%Y}."
    return {"estado": estado, "texto": texto, "fecha": fecha.isoformat(), "dias": (fecha - hoy).days,
            "ops_min": ops_min, "R_min": R_min}


def calcular(cfg: dict, hoy: date | None = None, base: Path | None = None) -> dict:
    hoy = hoy or date.today()
    inv = base or config.ruta("investigacion")
    stop = float(cfg.get("stop_pct", 15))
    ops = operaciones_bot(_leer_csv(inv / "corto-hueco" / "registro.csv"), stop)
    cerradas = [o for o in ops if o["R"] is not None]
    bot = _resumen([o["R"] for o in cerradas])
    bot.update(abiertas=sum(o["R"] is None for o in ops), stops_supuestos=sum(o["estado"] == "stop (supuesto)" for o in ops),
               ret_pct_medio=round(sum(o["resultado_pct"] for o in cerradas) / len(cerradas), 2) if cerradas else None,
               dias=len({o["dia"] for o in ops}), primer_dia=ops[0]["dia"] if ops else None)
    try:
        lab = json.loads((inv / "laboratorio" / "resumen.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        lab = {}
    pb = (lab.get("estrategias", {}).get("corto_hueco", {}) or {}).get("pasado_como_bot") or {}
    backtest = {k: pb.get(k) for k in ("n", "R_medio", "ic95", "aciertos_pct", "ret_pct_medio", "ops_dia", "dias")}
    backtest["periodo"] = lab.get("periodo_pasado")
    dec = cfg.get("decision") or {"fecha": "2027-02-15", "ops_min": 40, "R_min": 0.1}
    # Cuántas operaciones saldrían hasta la fecha de decisión al ritmo del backtest (operaciones por día de bolsa).
    per = backtest["periodo"] or []
    if pb.get("n") and len(per) == 2:
        ritmo = pb["n"] / max(1, _laborables(date.fromisoformat(per[0]), date.fromisoformat(per[1])))
        desde = date.fromisoformat(bot["primer_dia"]) if bot["primer_dia"] else hoy
        backtest["ops_por_dia_bolsa"] = round(ritmo, 2)
        backtest["esperadas_a_la_decision"] = round(ritmo * _laborables(desde, date.fromisoformat(str(dec["fecha"]))))
    # Demo de Alpaca (laboratorio): operaciones con R ya apuntado, por estrategia, frente a su backtest.
    alpaca = {}
    for f in _leer_csv(inv / "laboratorio" / "demo" / "registro.csv"):
        r = _num(f.get("R"))
        if r is not None:
            alpaca.setdefault(f.get("estrategia") or "?", []).append(r)
    alpaca = {e: {**_resumen(rs), "nombre": (lab.get("estrategias", {}).get(e) or {}).get("nombre", e),
                  "backtest_R": ((lab.get("estrategias", {}).get(e) or {}).get("pasado") or {}).get("R_medio")}
              for e, rs in sorted(alpaca.items())}
    return {"actualizado": hoy.isoformat(), "stop_pct": stop, "bot": bot, "backtest": backtest,
            "decision": veredicto(bot["n"], bot["R_medio"], hoy, dec),
            "operaciones": ops[-60:], "alpaca": alpaca}


def guardar(m: dict, base: Path | None = None) -> Path:
    f = (base or config.ruta("investigacion")) / "corto-hueco" / "marcador.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return f


def texto(m: dict) -> str:
    b, t, d = m["bot"], m["backtest"], m["decision"]
    rm = "—" if b["R_medio"] is None else f"{b['R_medio']:+.2f} R"
    tb = "—" if t.get("R_medio") is None else f"{t['R_medio']:+.2f} R"
    return (f"Marcador del bot: {b['n']} cerradas ({b['abiertas']} abiertas), media {rm}; backtest {tb}.\n"
            f"Decisión {d['fecha']} (faltan {d['dias']} días): {d['estado']}. {d['texto']}")
