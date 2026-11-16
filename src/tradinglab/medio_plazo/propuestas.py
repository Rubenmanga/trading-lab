"""Investigador diario (Paso 6 de la revisión del 16-nov-2026).

Una sesión ligera de Claude (tarea programada, sin API de pago) lee SOLO `investigacion/hoy.md` y escribe
`investigacion/propuestas/AAAA-MM-DD.md` con 3-5 ideas en una tabla fija. Este módulo, sin IA:
- comprueba que la tabla está bien (precios con sentido, 3-5 ideas, texto corto),
- apunta cada idea en el libro de predicciones (`predicciones.csv`, solo añadir) para que el marcador
  la puntúe frente a IWM, sin repetir una acción ya propuesta en los últimos 30 días.

Tabla (cabecera exacta):
| ticker | idea | precio | entrada | stop | objetivo | motivo |
idea = comprar_en_zona (entrar si baja a «entrada») · vigilar (aún no) · evitar (no comprar).
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from . import marcador

CARPETA = marcador.RAIZ / "investigacion" / "propuestas"
IDEAS = {"comprar_en_zona", "vigilar", "evitar"}
HORIZONTE_DIAS = 90  # una idea del día se revisa a los 3 meses (el marcador la cierra antes si toca stop u objetivo)
SIN_REPETIR_DIAS = 30
MAX_PALABRAS = 260  # Fable pide ~200 palabras; algo de margen por la tabla


def _num(x: str) -> float | None:
    try:
        return float(x.replace("$", "").replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def leer_tabla(texto: str) -> list[dict]:
    filas, cab = [], None
    for linea in texto.splitlines():
        if not linea.strip().startswith("|"):
            if filas:
                break  # solo cuenta la primera tabla
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if cab is None:
            if [c.lower() for c in celdas[:6]] == ["ticker", "idea", "precio", "entrada", "stop", "objetivo"]:
                cab = [c.lower() for c in celdas]
            continue
        if set("".join(celdas)) <= set("-: "):
            continue
        filas.append(dict(zip(cab, celdas)))
    return filas


def validar(texto: str) -> tuple[list[dict], list[str]]:
    """Devuelve (ideas, errores). Sin errores, las ideas se pueden apuntar."""
    filas, err = leer_tabla(texto), []
    if not 3 <= len(filas) <= 5:
        err.append(f"Hay {len(filas)} ideas; deben ser de 3 a 5.")
    palabras = len(re.sub(r"\|[-: |]+\|", " ", texto).split())
    if palabras > MAX_PALABRAS:
        err.append(f"Demasiado largo: {palabras} palabras (máx. {MAX_PALABRAS}).")
    ideas = []
    for f in filas:
        t = (f.get("ticker") or "").upper().strip("* ")
        idea = (f.get("idea") or "").lower().strip("* ")
        p, e, s, o = (_num(f.get(k, "")) for k in ("precio", "entrada", "stop", "objetivo"))
        if not re.fullmatch(r"[A-Z.]{1,6}", t):
            err.append(f"Ticker raro: {t!r}.")
        if idea not in IDEAS:
            err.append(f"{t}: idea «{idea}» no vale (usa {', '.join(sorted(IDEAS))}).")
        if not all((p, e, s, o)):
            err.append(f"{t}: faltan precio, entrada, stop u objetivo.")
        elif not s < e < o:
            err.append(f"{t}: debe cumplirse stop < entrada < objetivo ({s} < {e} < {o}).")
        if not (f.get("motivo") or "").strip():
            err.append(f"{t}: falta el motivo.")
        ideas.append(dict(ticker=t, idea=idea, precio=p, entrada=e, stop=s, objetivo=o, motivo=f.get("motivo", "")))
    return ideas, err


def apuntar(archivo: Path, libro: Path = marcador.LIBRO) -> dict:
    """Valida el archivo del día y añade sus ideas al libro. Devuelve {añadidas, repetidas, errores}."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", archivo.name)
    if not m:
        return dict(añadidas=0, repetidas=[], errores=["El nombre debe llevar la fecha AAAA-MM-DD."])
    dia = date.fromisoformat(m.group(1))
    ideas, err = validar(archivo.read_text(encoding="utf-8"))
    if err:
        return dict(añadidas=0, repetidas=[], errores=err)
    previas = marcador.leer(libro) if libro.exists() else []
    ids = {r["id"] for r in previas}
    desde = (dia - timedelta(days=SIN_REPETIR_DIAS)).isoformat()
    recientes = {r["ticker"] for r in previas if r["id"].startswith("PROP-") and r["fecha"] >= desde}
    try:
        rel = archivo.resolve().relative_to(marcador.RAIZ).as_posix()
    except ValueError:
        rel = archivo.name
    nuevas, repetidas = [], []
    for i in ideas:
        pid = f"PROP-{dia.isoformat()}-{i['ticker']}"
        if pid in ids or i["ticker"] in recientes:
            repetidas.append(i["ticker"])
            continue
        nuevas.append(dict(id=pid, fecha=dia.isoformat(), ticker=i["ticker"], informe=rel, veredicto=i["idea"],
                           conviccion="", probabilidad="", precio=i["precio"], zona_entrada_max=i["entrada"],
                           objetivo=i["objetivo"], stop_tesis=i["stop"],
                           fecha_revision=(dia + timedelta(days=HORIZONTE_DIAS)).isoformat(),
                           nota="investigador diario: " + i["motivo"][:120].replace(",", ";")))
    if nuevas:
        nuevo = not libro.exists()
        libro.parent.mkdir(parents=True, exist_ok=True)
        with open(libro, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=marcador.COLUMNAS, extrasaction="ignore")
            if nuevo:
                w.writeheader()
            w.writerows(nuevas)
    return dict(añadidas=len(nuevas), repetidas=repetidas, errores=[])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    archivo = Path(argv[0]) if argv else CARPETA / f"{date.today().isoformat()}.md"
    if not archivo.exists():
        print(f"No existe {archivo}")
        return 1
    r = apuntar(archivo)
    if r["errores"]:
        print("NO apuntado. Corrige:\n- " + "\n- ".join(r["errores"]))
        return 1
    print(f"Apuntadas {r['añadidas']} ideas en el libro de predicciones"
          + (f" · ya propuestas hace poco (no se repiten): {', '.join(r['repetidas'])}" if r["repetidas"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
