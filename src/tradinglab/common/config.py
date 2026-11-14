"""Carga de configuración con comprobaciones de seguridad."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]  # carpeta del repo


def ruta(*partes: str) -> Path:
    return RAIZ.joinpath(*partes)


def cargar_env() -> None:
    """Lee el archivo .env si existe (claves de Alpaca)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ruta(".env"))
    except ImportError:  # pragma: no cover
        pass


def cargar(nombre: str) -> dict:
    """Carga config/<nombre>.yaml y se niega a seguir si no es modo demo."""
    with open(ruta("config", f"{nombre}.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    exigir_demo(cfg)
    return cfg


def exigir_demo(cfg: dict) -> None:
    if cfg.get("modo_cuenta") != "demo":
        raise SystemExit("Este proyecto SOLO funciona con cuentas demo (modo_cuenta: demo). Cancelado.")
    if os.getenv("ALPACA_PAPER", "true").strip().lower() != "true":
        raise SystemExit("ALPACA_PAPER debe ser 'true' en el archivo .env. Cancelado.")
