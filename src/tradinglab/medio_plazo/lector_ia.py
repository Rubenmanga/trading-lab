"""Lectura de titulares con Claude Haiku (opcional, la eligió Ruben el 15-nov-2026: ~1-2 $ al mes).

Las reglas de `novedades.py` ya calculan precio, volumen y una causa probable. Haiku solo LEE los titulares que
ya han bajado gratis (Finnhub/Alpaca) y escribe un resumen corto en español por empresa: qué pasó, causa
probable y si hay algo importante. No busca en la web (eso costaría mucho más) y no recomienda comprar ni vender.

Solo corre si existe el secreto ANTHROPIC_API_KEY. Tope de gasto: `lista_noticias.ia.tope_mensual_usd`
(3 $ por defecto); al llegar, deja de llamar hasta el mes siguiente. Si nada cambió desde la última lectura,
reutiliza la anterior y no gasta.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date

MODELO = "claude-haiku-5-5"
PRECIO_ENTRADA, PRECIO_SALIDA = 0.10 / 1e6, 0.50 / 1e6   # $ por token (Haiku 5.5, hasta 100K tokens)

SISTEMA = """Eres un analista que resume noticias de bolsa para un principiante español.
Recibes, por empresa, datos de precio ya calculados y titulares reales de los últimos días.
Reglas:
- Usa SOLO los titulares y datos recibidos. No inventes hechos, cifras ni causas.
- Si ningún titular explica el movimiento del precio, dilo claramente ("no hay noticia que lo explique").
- Español sencillo. Explica entre paréntesis cualquier término técnico (p. ej. "BPA (beneficio por acción)").
- Resumen de 1 a 3 frases por empresa, centrado en lo NUEVO. Si no hay nada nuevo, dilo en una frase.
- "importante" = true solo si un titular nuevo puede mover mucho el precio: resultados, decisión de la FDA,
  datos de un ensayo clínico, venta de acciones nuevas, compra/fusión, contrato grande, problema legal grave.
- Nunca recomiendes comprar ni vender."""

ESQUEMA = {
    "type": "object",
    "properties": {"empresas": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string"},
            "resumen": {"type": "string"},
            "causa_probable": {"type": "string"},
            "confianza": {"type": "string", "enum": ["alta", "media", "baja", "ninguna"]},
            "importante": {"type": "boolean"},
            "motivo_importante": {"type": "string"},
        },
        "required": ["ticker", "resumen", "causa_probable", "confianza", "importante", "motivo_importante"],
        "additionalProperties": False,
    }}},
    "required": ["empresas"],
    "additionalProperties": False,
}


def entrada(empresas: dict) -> list[dict]:
    """Lo que se le pasa a Haiku: datos calculados + titulares (sin URLs, para gastar menos)."""
    out = []
    for t, e in empresas.items():
        out.append(dict(ticker=t, nombre=e.get("nombre"), fecha=e.get("fecha"), cambio_pct=e.get("cambio_pct"),
                        cambio_5d_pct=e.get("cambio_5d_pct"), lo_normal_pct=e.get("sigma_pct"),
                        volumen_vs_normal=e.get("volumen_rel"), sector_hoy=(e.get("referencia") or {}).get("cambio_pct"),
                        lectura_reglas=e.get("porque"), cambios=e.get("cambios"), catalizadores=e.get("catalizadores"),
                        titulares=[dict(fecha=n["fecha"], titulo=n["titulo"], nuevo=n["nueva"]) for n in e.get("titulares") or []]))
    return out


def huella(datos: list[dict]) -> str:
    return hashlib.sha1(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def leer(empresas: dict, previo: dict | None, cfg_ia: dict | None = None, cliente=None) -> dict | None:
    """Devuelve {"por_ticker": {...}, "huella", "gasto_mes": {"AAAA-MM": $}, "modelo", ...} o None si no hay clave."""
    cfg_ia = cfg_ia or {}
    previo = previo or {}
    if cfg_ia.get("activar") is False or (cliente is None and not os.getenv("ANTHROPIC_API_KEY")):
        return None
    datos = entrada(empresas)
    h = huella(datos)
    mes = date.today().strftime("%Y-%m")
    gasto = dict(previo.get("gasto_mes") or {})
    base = dict(modelo=MODELO, gasto_mes=gasto)
    if previo.get("huella") == h and previo.get("por_ticker"):
        return {**previo, "reutilizada": True}
    tope = float(cfg_ia.get("tope_mensual_usd", 3))
    if gasto.get(mes, 0) >= tope:
        return {**base, "por_ticker": previo.get("por_ticker") or {}, "huella": previo.get("huella"),
                "aviso": f"Tope de gasto del mes alcanzado ({tope} $): no se llama a Haiku hasta el mes que viene."}
    if cliente is None:
        import anthropic
        cliente = anthropic.Anthropic()
    r = cliente.messages.create(
        model=MODELO, max_tokens=4000, system=SISTEMA,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
        messages=[{"role": "user", "content": json.dumps(datos, ensure_ascii=False)}],
    )
    u = getattr(r, "usage", None)
    coste = ((getattr(u, "input_tokens", 0) or 0) * PRECIO_ENTRADA + (getattr(u, "output_tokens", 0) or 0) * PRECIO_SALIDA)
    gasto[mes] = round(gasto.get(mes, 0) + coste, 4)
    if r.stop_reason in ("refusal", "max_tokens"):
        return {**base, "por_ticker": previo.get("por_ticker") or {}, "huella": previo.get("huella"),
                "aviso": f"Haiku no respondió bien ({r.stop_reason}); se mantiene la lectura anterior."}
    texto = next((b.text for b in r.content if b.type == "text"), "{}")
    try:
        filas = json.loads(texto).get("empresas") or []
    except json.JSONDecodeError:
        filas = []
    por = {f["ticker"]: f for f in filas if f.get("ticker") in empresas}
    return {**base, "por_ticker": por, "huella": h, "coste_ultima_usd": round(coste, 5),
            "tokens": dict(entrada=getattr(u, "input_tokens", None), salida=getattr(u, "output_tokens", None))}
