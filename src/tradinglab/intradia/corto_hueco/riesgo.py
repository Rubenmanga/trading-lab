"""Reglas de riesgo del corto del hueco. Código fijo, SIN IA: siempre manda."""
from __future__ import annotations


def capital(credito: float, posiciones: list[dict]) -> float:
    """Capital aproximado de la cuenta demo: dinero libre + lo invertido en posiciones abiertas."""
    return float(credito) + sum(float(p.get("amount") or 0) for p in posiciones)


def freno_activado(cap: float, cap_inicial: float | None, cfg: dict) -> bool:
    return bool(cap_inicial) and cap < cap_inicial * (1 - cfg["freno_caida_pct"] / 100)


def tamano(cap: float, credito: float, expuesto_usd: float, stop_pct: float, cfg: dict) -> tuple[float, str]:
    """Importe (en $) a invertir en un corto. Devuelve (importe, motivo si es 0)."""
    lev = max(1, int(cfg.get("apalancamiento", 1)))
    riesgo_usd = cap * cfg["riesgo_pct"] / 100
    posicion = riesgo_usd / (stop_pct / 100)                       # si salta el stop se pierde riesgo_usd
    posicion = min(posicion, cap * cfg["max_posicion_pct"] / 100)
    posicion = min(posicion, cap * cfg["max_exposicion_pct"] / 100 - expuesto_usd)
    importe = min(posicion / lev, credito * 0.95)
    if importe < cfg.get("importe_min_usd", 50):
        return 0.0, f"importe demasiado pequeño ({importe:.0f} $): límite de exposición o poco dinero libre"
    return round(importe, 2), ""


def precio_stop(precio_entrada: float, stop_pct: float) -> float:
    """En un corto el stop está POR ENCIMA del precio de entrada."""
    return round(precio_entrada * (1 + stop_pct / 100), 4)


def stop_ajustado(stop_pct: float, stop_min: float | None, stop_max: float | None) -> float:
    if stop_min is not None and stop_pct < stop_min:
        return float(stop_min)
    if stop_max is not None and stop_max > 0 and stop_pct > stop_max:
        return float(stop_max)
    return float(stop_pct)
