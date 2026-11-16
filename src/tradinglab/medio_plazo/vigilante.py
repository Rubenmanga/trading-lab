"""Vigilante intradía cada 10 minutos (agente B, solo información: NO opera ni manda órdenes).

Lo lanza GitHub Actions (`vigilante-intradia.yml`) cada 10 minutos con la bolsa abierta, solo los días de
`config/vigilante.yaml`. Para cada empresa mira, con velas de 5 minutos de Yahoo:
  · cuánto sube o baja hoy frente a sus competidores (pares) y al fondo del sector,
  · si el volumen acumulado va por encima de lo normal A ESA HORA (mediana de las 10 sesiones anteriores),
  · si en los últimos 10 minutos hubo un acelerón con volumen fuerte.
Si algo se sale de lo normal, deja un aviso (el workflow abre un issue → notificación al móvil). Cada tipo de
aviso se manda una vez por día y dirección. A partir de `resumen_hora_ny` manda un resumen del día.

Ojo: las compras de directivos y fondos se publican días después; aquí solo se ve su posible huella en
precio y volumen, que antes de unos resultados es una pista débil, no una predicción.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from ..common.config import cargar, ruta

NY = ZoneInfo("America/New_York")
MAD = ZoneInfo("Europe/Madrid")
CAMPOS = ["hora_ny", "hora_espana", "precio", "cambio_pct", "pares_pct", "sector_pct", "mercado_pct",
          "exceso_pct", "volumen_rel", "mov_10m_pct", "volumen_rel_10m", "avisos"]


def _pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 2) if b else 0.0


def por_dia(velas: list[dict]) -> dict[date, list[dict]]:
    """velas = [{t: datetime NY, cierre, volumen}] ordenadas → {día: velas de la sesión normal}."""
    dias: dict[date, list[dict]] = {}
    for v in velas:
        if time(9, 30) <= v["t"].time() < time(16, 0):
            dias.setdefault(v["t"].date(), []).append(v)
    return dias


def medir(velas: list[dict], cierre_prev: float, hoy: date, ahora: time) -> dict | None:
    """Cambio de hoy, volumen relativo acumulado a esta hora y movimiento de los últimos 10 min."""
    dias = por_dia(velas)
    de_hoy = [v for v in dias.get(hoy, []) if v["t"].time() <= ahora]
    if not de_hoy or not cierre_prev:
        return None
    corte = de_hoy[-1]["t"].time()
    vol_hoy = sum(v["volumen"] for v in de_hoy)
    previos = [d for d in sorted(dias) if d < hoy][-10:]
    acumulados = [sum(v["volumen"] for v in dias[d] if v["t"].time() <= corte) for d in previos]
    acumulados = [a for a in acumulados if a > 0]
    normal = statistics.median(acumulados) if acumulados else 0
    # Últimos 10 minutos = 2 velas de 5 min (comparadas con esas mismas franjas en días anteriores).
    ult = de_hoy[-2:]
    base = de_hoy[-3]["cierre"] if len(de_hoy) >= 3 else cierre_prev
    franjas = {v["t"].time() for v in ult}
    vol_franja = [sum(v["volumen"] for v in dias[d] if v["t"].time() in franjas) for d in previos]
    vol_franja = [a for a in vol_franja if a > 0]
    normal_franja = statistics.median(vol_franja) if vol_franja else 0
    return dict(
        precio=round(de_hoy[-1]["cierre"], 4),
        cambio_pct=_pct(de_hoy[-1]["cierre"], cierre_prev),
        volumen_rel=round(vol_hoy / normal, 2) if normal else None,
        mov_10m_pct=_pct(de_hoy[-1]["cierre"], base),
        volumen_rel_10m=round(sum(v["volumen"] for v in ult) / normal_franja, 2) if normal_franja else None,
        hora=corte.strftime("%H:%M"),
    )


def sigma_diaria(cierres: list[float]) -> float:
    """Movimiento diario normal (desviación de los cambios de 20 días), en %."""
    c = cierres[-21:]
    cambios = [(c[i] / c[i - 1] - 1) * 100 for i in range(1, len(c)) if c[i - 1]]
    return round(statistics.pstdev(cambios), 2) if len(cambios) >= 5 else 5.0


def avisos(m: dict, pares_pct: float | None, sigma: float, u: dict) -> list[str]:
    """Tipos de aviso (con dirección) que dispara esta medición."""
    out = []
    rv, rv10 = m.get("volumen_rel") or 0, m.get("volumen_rel_10m") or 0
    if pares_pct is not None:
        exceso = m["cambio_pct"] - pares_pct
        if abs(exceso) >= max(u["separacion_sigmas"] * sigma, u["separacion_min_pct"]) and rv >= u["volumen_rel"]:
            out.append(f"SE SEPARA DEL SECTOR {'AL ALZA' if exceso > 0 else 'A LA BAJA'}")
    if rv >= u["volumen_extremo"]:
        out.append("VOLUMEN MUY ALTO")
    if abs(m["mov_10m_pct"]) >= u["acelerón_10m_pct"] and rv10 >= u["acelerón_10m_vol"]:
        out.append(f"ACELERÓN EN 10 MIN {'AL ALZA' if m['mov_10m_pct'] > 0 else 'A LA BAJA'}")
    return out


def texto_aviso(tk: str, tipo: str, fila: dict) -> str:
    return (f"- **{tk} · {tipo}** ({fila['hora_espana']} España): {fila['precio']} $ ({fila['cambio_pct']:+.2f} % hoy) · "
            f"competidores {fila['pares_pct']:+.2f} % · volumen {fila['volumen_rel']}x lo normal a esta hora · "
            f"últimos 10 min {fila['mov_10m_pct']:+.2f} % con {fila['volumen_rel_10m']}x de volumen")


def lectura(filas: list[dict]) -> str:
    """Frase sencilla del día para el resumen (reglas, sin IA)."""
    if not filas:
        return "Sin datos de hoy."
    f = filas[-1]
    ex, rv = f["exceso_pct"], f["volumen_rel"] or 0
    if abs(ex) < 3 and rv < 1.5:
        return "Día normal: se mueve con su sector y con volumen corriente. No hay huella de que alguien se posicione."
    lado = "por encima" if ex > 0 else "por debajo"
    fuerza = "con mucho volumen" if rv >= 2 else "con volumen corriente"
    return (f"Va {abs(ex):.1f} puntos {lado} de sus competidores {fuerza} ({rv}x). "
            + ("Puede ser alguien posicionándose antes de los resultados, o simple ruido: es una pista débil." if rv >= 2
               else "Sin volumen fuerte, la separación pesa poco."))


def guardar(tk: str, hoy: date, filas: list[dict], cfg_emp: dict) -> None:
    carpeta = ruta("investigacion", "vigilante")
    carpeta.mkdir(parents=True, exist_ok=True)
    with open(carpeta / f"{tk}-{hoy}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    ult = filas[-1]
    n_av = [x for r in filas for x in (r["avisos"].split(" | ") if r["avisos"] else [])]
    md = [f"# Vigilante {tk} · {hoy}", "",
          "**Resumen (5 líneas)**",
          f"1. {cfg_emp.get('nombre', tk)}: {cfg_emp.get('motivo', '')}.",
          f"2. Última lectura {ult['hora_espana']} (España): **{ult['precio']} $**, {ult['cambio_pct']:+.2f} % hoy; competidores {ult['pares_pct']:+.2f} %; sector {ult['sector_pct']:+.2f} %.",
          f"3. Volumen acumulado: **{ult['volumen_rel']}x** lo normal a esta hora.",
          f"4. {lectura(filas)}",
          f"5. Avisos del día: {len(set(n_av))} ({', '.join(sorted(set(n_av))) or 'ninguno'}). Información, no una orden.", "",
          "> Las compras de directivos y fondos se publican días después (SEC). Aquí solo se ve su posible huella en precio y volumen.", "",
          "| Hora España | Precio | Hoy | Competidores | Exceso | Volumen | 10 min | Aviso |",
          "|---|---|---|---|---|---|---|---|"]
    for r in reversed(filas[-40:]):
        md.append(f"| {r['hora_espana']} | {r['precio']} | {r['cambio_pct']:+.2f} % | {r['pares_pct']:+.2f} % | {r['exceso_pct']:+.2f} | "
                  f"{r['volumen_rel']}x | {r['mov_10m_pct']:+.2f} % | {r['avisos'] or '—'} |")
    (carpeta / f"{tk}-{hoy}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _descargar(tickers: list[str]) -> tuple[dict, dict]:  # pragma: no cover (red)
    import yfinance as yf
    velas, diarios = {}, {}
    for t in tickers:
        h = yf.Ticker(t).history(period="15d", interval="5m", prepost=False, auto_adjust=False)
        velas[t] = [dict(t=i.tz_convert(NY).to_pydatetime(), cierre=float(r["Close"]), volumen=float(r["Volume"]))
                    for i, r in h.iterrows() if r["Close"] == r["Close"]]
        d = yf.Ticker(t).history(period="3mo", interval="1d", auto_adjust=False)
        diarios[t] = [(i.date(), float(c)) for i, c in d["Close"].items() if c == c]
    return velas, diarios


def ejecutar(ahora: datetime | None = None) -> int:  # pragma: no cover (red)
    cfg = cargar("vigilante")
    ahora = (ahora or datetime.now(NY)).astimezone(NY)
    hoy = ahora.date()
    if not (cfg["desde"] <= hoy <= cfg["hasta"]) or ahora.weekday() >= 5:
        print("Hoy no toca vigilar.")
        return 0
    if not time(9, 35) <= ahora.time() <= time(16, 5):
        print("Fuera de la sesión normal.")
        return 0
    u = cfg["umbrales"]
    salida_aviso = []
    for tk, e in cfg["empresas"].items():
        lista = [tk, *e.get("pares", []), e.get("sector"), cfg.get("mercado")]
        velas, diarios = _descargar([t for t in lista if t])
        def prev(t):
            d = [c for f, c in diarios.get(t, []) if f < hoy]
            return d[-1] if d else 0
        med = {t: medir(velas.get(t, []), prev(t), hoy, ahora.time()) for t in velas}
        m = med.get(tk)
        if not m:
            print(f"{tk}: sin velas de hoy todavía.")
            continue
        pares = [med[p]["cambio_pct"] for p in e.get("pares", []) if med.get(p)]
        pares_pct = round(statistics.median(pares), 2) if pares else None
        sig = sigma_diaria([c for f, c in diarios.get(tk, []) if f < hoy])
        tipos = avisos(m, pares_pct, sig, u)
        h_ny = datetime.combine(hoy, datetime.strptime(m["hora"], "%H:%M").time(), NY)
        fila = dict(hora_ny=m["hora"], hora_espana=h_ny.astimezone(MAD).strftime("%H:%M"), precio=m["precio"],
                    cambio_pct=m["cambio_pct"], pares_pct=pares_pct if pares_pct is not None else 0.0,
                    sector_pct=(med.get(e.get("sector")) or {}).get("cambio_pct", 0.0),
                    mercado_pct=(med.get(cfg.get("mercado")) or {}).get("cambio_pct", 0.0),
                    exceso_pct=round(m["cambio_pct"] - (pares_pct or 0), 2), volumen_rel=m["volumen_rel"],
                    mov_10m_pct=m["mov_10m_pct"], volumen_rel_10m=m["volumen_rel_10m"], avisos=" | ".join(tipos))
        # Historial del día y avisos ya mandados (para no repetir).
        arch = ruta("investigacion", "vigilante", f"{tk}-{hoy}.csv")
        filas = []
        if arch.exists():
            with open(arch, encoding="utf-8") as f:
                filas = list(csv.DictReader(f))
            for r in filas:
                for k in CAMPOS[2:-1]:
                    r[k] = float(r[k]) if r[k] not in ("", "None") else None
        estado_p = ruta("investigacion", "vigilante", f"estado-{tk}-{hoy}.json")
        estado = json.loads(estado_p.read_text()) if estado_p.exists() else {"mandados": [], "resumen": False}
        filas = [r for r in filas if r["hora_ny"] != fila["hora_ny"]] + [fila]
        guardar(tk, hoy, filas, e)
        nuevos = [t for t in tipos if t not in estado["mandados"]]
        for t in nuevos:
            salida_aviso.append(texto_aviso(tk, t, fila))
        estado["mandados"] += nuevos
        if not estado["resumen"] and ahora.strftime("%H:%M") >= cfg.get("resumen_hora_ny", "15:25"):
            estado["resumen"] = True
            salida_aviso.append(f"\n**Resumen del día de {tk} ({fila['hora_espana']} España):** {fila['precio']} $, "
                                f"{fila['cambio_pct']:+.2f} % hoy frente a {fila['pares_pct']:+.2f} % de sus competidores, "
                                f"volumen {fila['volumen_rel']}x lo normal. {lectura(filas)}")
        estado_p.write_text(json.dumps(estado, ensure_ascii=False))
        print(texto_aviso(tk, ", ".join(tipos) or "sin aviso", fila))
    if salida_aviso:
        (ruta("aviso.md")).write_text("\n".join(salida_aviso) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(ejecutar())
