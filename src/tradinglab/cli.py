"""Punto de entrada: el comando `lab`.

  lab intradia demo         Prueba completa con datos inventados (no necesita claves)
  lab intradia comprobar    Comprueba tus claves de Alpaca demo y si la bolsa está abierta
  lab intradia backtest     Prueba la estrategia con datos reales del pasado (Alpaca, gratis)
  lab intradia sesion       Sesión en vivo durante la ventana de trading
  lab intradia cerrar-todo  Botón del pánico: cierra todo en la cuenta demo
  lab diario                Escribe el diario del día en diario/
  lab medio cribado         Busca small caps con potencial según analistas
  lab medio ficha TICKER    Datos de una empresa (los usa la skill de análisis)
  lab medio alertas         Revisa la lista de vigilancia y avisa
  lab panel                 Abre el panel web
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def _intradia(args):
    from .common import config
    from .common.db import DB

    config.cargar_env()
    cfg = config.cargar("intradia")
    if args.accion == "demo":
        from .intradia import backtest, datos_sinteticos
        cfg["estrategia"] = cfg["estrategia"] if cfg["estrategia"]["nombre"] != "ninguna" else \
            {"nombre": "ejemplo_cruce_medias", "parametros": {}}
        datos = datos_sinteticos.generar(cfg["simbolos"], dias=args.dias)
        r = backtest.ejecutar(cfg, datos, DB(), etiqueta="demo")
        print("DEMO con datos INVENTADOS (no dice nada de si la estrategia funciona):")
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print("Ahora abre el panel con:  lab panel")
    elif args.accion == "backtest":
        from .common.alpaca_cliente import velas
        from .intradia import backtest
        hasta = datetime.now(timezone.utc) - timedelta(minutes=20)
        datos = velas(cfg["simbolos"], cfg["temporalidad_min"], desde=hasta - timedelta(days=args.dias), hasta=hasta)
        r = backtest.ejecutar(cfg, datos, DB())
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif args.accion == "comprobar":
        from .common.alpaca_cliente import cliente_trading
        c = cliente_trading()
        a, reloj = c.get_account(), c.get_clock()
        print(f"Conectado a Alpaca DEMO. Capital: {float(a.equity):,.2f} $. Estado: {a.status}.")
        print(f"Bolsa abierta ahora: {'sí' if reloj.is_open else 'no'}. Próxima apertura: {reloj.next_open}.")
    elif args.accion == "sesion":
        from .intradia import sesion
        sesion.ejecutar(cfg)
    elif args.accion == "cerrar-todo":
        from .intradia.cerrar import cerrar_todo
        cerrar_todo()


def _medio(args):
    from .common import config

    cfg = config.cargar("medio_plazo")
    if args.accion == "cribado":
        from .medio_plazo import cribado
        filas = cribado.cribar(cfg)
        path = cribado.guardar(filas)
        for f in filas[:25]:
            print(f"{f['ticker']:6} {str(f.get('sector'))[:22]:22} {f['precio']:>8.2f} $  potencial {f['potencial_pct']:>6.1f}%  "
                  f"({f.get('analistas')} analistas)")
        print(f"\n{len(filas)} candidatos guardados en {path}")
    elif args.accion == "ficha":
        from .medio_plazo import datos
        print(json.dumps(datos.ficha(args.ticker), indent=2, ensure_ascii=False, default=str))
    elif args.accion == "alertas":
        from .medio_plazo import alertas
        lista = alertas.revisar(cfg)
        path = alertas.guardar(lista)
        for a in lista:
            print(f"[{a['tipo']}] {a['mensaje']}")
        print(f"{len(lista)} alertas. Guardadas en {path}")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # para que Windows muestre bien las tildes
    p = argparse.ArgumentParser(prog="lab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="grupo", required=True)
    pi = sub.add_parser("intradia", help="Agente A: trading intradía")
    pi.add_argument("accion", choices=["demo", "comprobar", "backtest", "sesion", "cerrar-todo"])
    pi.add_argument("--dias", type=int, default=30)
    pm = sub.add_parser("medio", help="Agente B: inversión a 12 meses")
    pm.add_argument("accion", choices=["cribado", "ficha", "alertas"])
    pm.add_argument("ticker", nargs="?")
    sub.add_parser("diario", help="Escribe el diario del día")
    sub.add_parser("panel", help="Abre el panel web")
    args = p.parse_args(argv)

    if args.grupo == "intradia":
        _intradia(args)
    elif args.grupo == "medio":
        if args.accion == "ficha" and not args.ticker:
            p.error("indica el ticker, por ejemplo: lab medio ficha ABCD")
        _medio(args)
    elif args.grupo == "diario":
        from .diario import escribir
        print("Diario guardado en", escribir())
    elif args.grupo == "panel":
        from .common.config import ruta
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(ruta("dashboard", "app.py"))])


if __name__ == "__main__":
    main()
