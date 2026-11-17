"""Investigador diario autónomo y conservador del agente B (sin Claude ni API).

Convierte la carpeta diaria y sus DATOS ESTRUCTURADOS en una lista corta para
revisión humana. No verifica información fuera del proyecto y NO emite compras.
El libro de predicciones conserva los resultados sin reescribirlos.
"""
from __future__ import annotations

import csv
import json
import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import marcador, propuestas

MAX_ANTIGUEDAD = 2
MIN_IDEAS = 3
MAX_IDEAS = 5
RIESGOS_CRITICOS = ("TESIS EN PELIGRO", "SOPORTE PERDIDO")
RIESGO_BINARIO = ("apuesta binaria", "decisión fda", "510(k)", "fda de", "fda para")
RAIZ = marcador.RAIZ


def _csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _numero(valor: object) -> float | None:
    try:
        n = float(valor)
        return n if math.isfinite(n) and n > 0 else None
    except (TypeError, ValueError):
        return None


def _fecha_carpeta(contenido: str) -> date:
    m = re.search(r"^# Carpeta del día · (\d{2})/(\d{2})/(\d{4})\s*$", contenido, re.M)
    if not m:
        raise ValueError("hoy.md no tiene una fecha reconocible")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _senales(contenido: str) -> dict[str, list[tuple[int, str]]]:
    """Extrae únicamente menciones presentes en hoy.md (nunca inventa eventos)."""
    salida: dict[str, list[tuple[int, str]]] = {}
    seccion = ""
    for linea in contenido.splitlines():
        if linea.startswith("## "):
            seccion = linea.lower()
            continue
        if not linea.startswith("- ") or linea.startswith("- …"):
            continue
        tickers = re.findall(r"\*\*([A-Z]{1,5}(?:\.[A-Z])?)\*\*", linea)
        if not tickers and "avisos" in seccion:
            tickers = re.findall(r"·\s+([A-Z]{1,5}(?:\.[A-Z])?)\s*[:a]", linea)
        if not tickers:
            continue
        prioridad = (0 if "avisos" in seccion else
                     1 if "catalizadores" in seccion else
                     2 if "hechos" in seccion else
                     3 if "zona" in seccion else 4)
        texto = re.sub(r"\*\*|[*_]|[|]", "", linea.removeprefix("- ")).strip()
        for ticker in tickers:
            salida.setdefault(ticker, []).append((prioridad, texto))
    return salida


def _motivo(ticker: str, senales: list[tuple[int, str]], binario: bool, critico: bool,
            sin_calculadora: bool) -> str:
    senal = sorted(senales, key=lambda s: s[0])[0][1]
    senal = re.sub(r"\s+", " ", senal)
    senal = senal.replace(ticker + " · ", "").replace(ticker + ":", "").strip()
    if critico:
        motivo = "Alerta de tesis/soporte; revisar antes de cualquier operación"
    elif binario:
        motivo = "Catalizador regulatorio/binario; no anticipar su desenlace"
    else:
        motivo = "Dato: " + senal
    if sin_calculadora:
        motivo += "; sin calculadora"
    return motivo[:115].replace("|", "/").replace("\n", " ")


def _repetidos(libro: Path, dia: date) -> set[str]:
    desde = (dia - timedelta(days=propuestas.SIN_REPETIR_DIAS)).isoformat()
    if not libro.exists():
        return set()
    return {
        fila.get("ticker", "")
        for fila in _csv(libro)
        if fila.get("id", "").startswith("PROP-") and desde <= fila.get("fecha", "") <= dia.isoformat()
    }


def construir(
    dia: date,
    carpeta: str,
    estado: dict,
    watchlist: list[dict],
    entradas: dict,
    predicciones: list[dict],
) -> tuple[str | None, list[str]]:
    """Prepara 3-5 vigilancias trazables o no publica nada. Nunca rellena huecos al azar."""
    fecha_carpeta = _fecha_carpeta(carpeta)
    if not (date.fromordinal(dia.toordinal() - MAX_ANTIGUEDAD) <= fecha_carpeta <= dia):
        raise ValueError(f"hoy.md desactualizado o futuro: {fecha_carpeta} (hoy: {dia})")
    try:
        fecha_estado = datetime.fromisoformat(estado["actualizado"].replace("Z", "+00:00")).date()
    except (KeyError, ValueError, AttributeError) as exc:
        raise ValueError("estado.json sin fecha válida") from exc
    if not (dia - timedelta(days=MAX_ANTIGUEDAD) <= fecha_estado <= dia):
        raise ValueError(f"estado.json desactualizado o futuro: {fecha_estado}")

    senales = _senales(carpeta)
    precios = {
        fila.get("ticker", "").upper(): _numero(fila.get("precio"))
        for fila in estado.get("precios", [])
    }
    recientes = {
        fila.get("ticker", "")
        for fila in predicciones
        if fila.get("id", "").startswith("PROP-")
        and (dia - timedelta(days=propuestas.SIN_REPETIR_DIAS)).isoformat()
        <= fila.get("fecha", "") <= dia.isoformat()
    }
    elegibles: list[tuple[int, float, dict]] = []
    descartes = []
    for w in watchlist:
        t = (w.get("ticker") or "").upper()
        if not t or t not in senales or t in recientes:
            continue
        p = precios.get(t)
        stop = _numero(w.get("stop_tesis"))
        objetivo = _numero(w.get("precio_objetivo_12m"))
        zona = _numero(w.get("zona_entrada_max"))
        calculada = _numero(entradas.get(t, {}).get("entrada"))
        # La calculadora manda. Sin calculadora, se usa el menor entre zona y
        # precio observado, SOLO como referencia teórica, nunca como orden.
        entrada = calculada if calculada is not None else min(p, zona) if p and zona else None
        if not all((p, stop, objetivo, entrada)) or not 0 < stop < entrada < objetivo:
            descartes.append(t + ": faltan niveles coherentes (stop < entrada < objetivo)")
            continue
        detalles = " ".join(s for _, s in senales[t]).lower()
        catalizador = (w.get("proximo_catalizador") or "").lower()
        try:
            fecha_evento = date.fromisoformat(w.get("fecha_catalizador", ""))
        except ValueError:
            fecha_evento = None
        proximo_binario = bool(
            fecha_evento and dia <= fecha_evento <= dia + timedelta(days=14)
            and any(palabra in catalizador for palabra in RIESGO_BINARIO)
        )
        binario = bool(entradas.get(t, {}).get("binaria")) or proximo_binario or any(
            palabra in detalles for palabra in RIESGO_BINARIO
        )
        critico = any(palabra.lower() in detalles for palabra in RIESGOS_CRITICOS) or p <= stop
        # El sistema automático NO valida noticias ni probabilidad de acertar.
        # Por tanto NO autoriza "comprar_en_zona", ni siquiera con potencial alto.
        idea = "evitar" if binario or critico else "vigilar"
        motivo = _motivo(t, senales[t], binario, critico, calculada is None)
        rr = (objetivo - entrada) / (entrada - stop)
        prioridad = min(n for n, _ in senales[t])
        elegibles.append((prioridad, -rr, dict(
            ticker=t, idea=idea, precio=p, entrada=entrada,
            stop=stop, objetivo=objetivo, motivo=motivo,
        )))
    elegibles.sort(key=lambda item: (item[0], item[1], item[2]["ticker"]))
    filas = [r for _, _, r in elegibles[:MAX_IDEAS]]
    if len(filas) < MIN_IDEAS:
        return None, descartes + [
            f"Solo {len(filas)} candidatos con niveles y fuente del día; no se fuerzan {MIN_IDEAS} ideas."
        ]
    actualizacion = estado["actualizado"][:16].replace("T", " ") + " UTC"
    lineas = [
        f"# Propuestas de hoy · {dia:%d/%m/%Y}",
        "",
        f"_Automático, sin IA. Carpeta {fecha_carpeta:%d/%m}; precios internos {actualizacion}. "
        "Vigilancias, no órdenes ni recomendaciones de compra._",
        "",
        "Ninguna idea autoriza comprar: niveles y catalizadores requieren contrastar fuentes oficiales.",
        "",
        "| ticker | idea | precio | entrada | stop | objetivo | motivo |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        lineas.append(
            f"| {f['ticker']} | {f['idea']} | {f['precio']:.3f} | {f['entrada']:.3f} | "
            f"{f['stop']:.3f} | {f['objetivo']:.3f} | {f['motivo']} |"
        )
    lineas += [
        "",
        "**Regla de riesgo:** no operar eventos binarios; verificar la tesis, "
        "liquidez, costes y fuente primaria antes de decidir.",
        "",
    ]
    texto = "\n".join(lineas)
    _, errores = propuestas.validar(texto)
    if errores:
        raise ValueError("Informe inválido: " + "; ".join(errores))
    return texto, descartes


def ejecutar(dia: date | None = None, raiz: Path = RAIZ) -> dict:
    dia = dia or datetime.now(ZoneInfo("Europe/Madrid")).date()
    inv = raiz / "investigacion"
    salida = inv / "propuestas" / f"{dia.isoformat()}.md"
    libro = inv / "predicciones.csv"
    if salida.exists():
        r = propuestas.apuntar(salida, libro)
        if r["errores"]:
            raise ValueError("; ".join(r["errores"]))
        return {"estado": "existente", **r}
    contenido = (inv / "hoy.md").read_text(encoding="utf-8")
    estado = json.loads((inv / "estado.json").read_text(encoding="utf-8"))
    entradas = json.loads((inv / "entradas.json").read_text(encoding="utf-8"))
    texto, descartes = construir(
        dia, contenido, estado, _csv(inv / "watchlist.csv"),
        entradas, _csv(libro) if libro.exists() else [],
    )
    if texto is None:
        return {"estado": "sin_propuestas", "descartes": descartes, "añadidas": 0}
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8")
    r = propuestas.apuntar(salida, libro)
    if r["errores"]:
        salida.unlink()
        raise ValueError("; ".join(r["errores"]))
    return {"estado": "creado", "informe": str(salida), "descartes": descartes, **r}


if __name__ == "__main__":
    print(json.dumps(ejecutar(), ensure_ascii=False, indent=2))
