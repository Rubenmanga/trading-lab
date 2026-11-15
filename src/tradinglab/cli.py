"""Punto de entrada: el comando `lab`.

  lab intradia demo         Prueba completa con datos inventados (no necesita claves)
  lab intradia comprobar    Comprueba tus claves de Alpaca demo y si la bolsa está abierta
  lab intradia backtest     Prueba la estrategia con datos reales del pasado (Alpaca, gratis)
  lab intradia sesion       Sesión en vivo durante la ventana de trading
  lab intradia cerrar-todo  Botón del pánico: cierra todo en la cuenta demo
  lab estudio universo      Estudio intradía (Alpaca, solo lectura): velas diarias -> candidatas
  lab estudio tramo         ... velas de 1 min de las candidatas -> top gainers y operaciones ORB
  lab estudio informe       ... junta todo y escribe el informe en investigacion/estrategias/
  lab corto operar          Corto del hueco en eToro DEMO: escanea a las 9:34 NY y vende en corto a las 9:35
  lab corto cerrar          ... cierra las posiciones del bot (a partir de las 15:45 NY)
  lab diario                Escribe el diario del día en diario/
  lab medio oportunidades   Buscador: puntúa todas las small caps (8 factores) y guarda el ranking
  lab medio fuentes TICKER  Prueba las fuentes públicas gratis (SEC EDGAR, ClinicalTrials.gov, FRED)
  lab medio cribado         Cribado sencillo antiguo (solo potencial según analistas)
  lab medio ficha TICKER    Datos de una empresa (los usa la skill de análisis)
  lab medio alertas         Revisa la lista de vigilancia y avisa
  lab panel                 Abre el panel web
"""
from __future__ import annotations

import argparse
import json
import os
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
    elif args.accion == "oportunidades":
        from .medio_plazo import oportunidades
        if args.salida:  # solo descargar un trozo (GitHub Actions reparte el trabajo en varias máquinas)
            d = oportunidades.descargar_parte(cfg, parte=args.parte - 1, de=args.de, salida=args.salida,
                                              minutos=args.minutos, maximo=args.max)
            print(f"Guardado en {args.salida}: {len(d['filas'])} de {d['parte']} empresas de esta parte")
            return
        if args.entrada:  # juntar los trozos ya descargados y puntuar (aunque falte alguno: ranking provisional)
            import glob
            rutas = sorted(glob.glob(os.path.join(args.entrada, "*.jsonl")))
            metas = [json.load(open(r + ".meta.json")) for r in rutas if os.path.exists(r + ".meta.json")]
            universo_n = max([m["universo"] for m in metas] or [0])
            filas = oportunidades.leer_partes(rutas)
            print(f"{len(rutas)} partes · {len(filas)} empresas descargadas de un universo de {universo_n}")
            res = oportunidades.combinar(cfg, filas, universo_n or len(filas))
            previo = oportunidades.ranking_actual()
            if res.get("provisional") and previo and previo.get("analizadas", 0) > res["analizadas"] \
                    and not previo.get("provisional"):
                print(f"Ranking de hoy a medias ({res['analizadas']} empresas): se mantiene el anterior, más completo "
                      f"({previo['analizadas']}). Lo bajado se guarda y la siguiente ejecución continúa.")
                return
        else:
            res = oportunidades.ejecutar(cfg, maximo=args.max)
        pj, pm = oportunidades.guardar(res, top=cfg["oportunidades"].get("top_guardado", 150))
        for f in res["filas"][:25]:
            s = f["factores"]
            print(f"{f['puesto']:>3} {f['ticker']:6} nota {f['nota']:5.1f}  {str(f.get('sector'))[:20]:20} {f['carril'][:28]:28} "
                  + " ".join(f"{k[:4]}={'—' if v is None else round(v)}" for k, v in s.items())
                  + (f"  ⚠ {'; '.join(f['banderas'])}" if f['banderas'] else ""))
        print(f"\nUniverso {res['universo']} · analizadas {res['analizadas']}"
              + (" · PROVISIONAL" if res.get("provisional") else "") + f" · guardado en {pj} y {pm}")
    elif args.accion == "fuentes":   # prueba de las fuentes públicas sin clave (SEC, ensayos, macro)
        from .medio_plazo import fuentes_publicas as fp
        t = (args.ticker or "ORIC").upper()
        sec = fp.datos_sec([t])
        print("SEC EDGAR:", json.dumps(sec.get(t), indent=1, ensure_ascii=False), fp.ULTIMO_ERROR or "")
        nombre = args.nombre or t
        print("ClinicalTrials.gov:", json.dumps(fp.datos_ensayos({t: nombre}).get(t), indent=1, ensure_ascii=False))
        print("Macro:", json.dumps(fp.datos_macro(), indent=1, ensure_ascii=False, default=str))
    elif args.accion == "probar":
        from .medio_plazo import metricas
        print(json.dumps(metricas.empresa(args.ticker.upper()), indent=1, ensure_ascii=False, default=str))
    elif args.accion == "ficha":
        from .medio_plazo import datos
        print(json.dumps(datos.ficha(args.ticker), indent=2, ensure_ascii=False, default=str))
    elif args.accion == "alertas":
        from functools import lru_cache

        from .medio_plazo import alertas, datos, watchlist
        precio_de = lru_cache(maxsize=None)(datos.precio)  # cada precio se pide una sola vez
        filas = watchlist.leer()
        lista = alertas.revisar(cfg, filas, precio_de)
        path = alertas.guardar(lista)
        alertas.guardar_json(lista, alertas.estado(filas, precio_de))
        for a in lista:
            print(f"[{a['tipo']}] {a['mensaje']}")
        print(f"{len(lista)} alertas. Guardadas en {path}")


def _estudio(args):
    from pathlib import Path

    import pandas as pd

    from .common import config
    from .intradia.estudio import informe

    config.cargar_env()
    cfg = config.cargar("estudio_intradia")
    desde, hasta = args.desde or cfg["desde"], args.hasta or cfg["hasta"]
    if args.accion == "informe":
        res = informe.generar(Path(args.entrada), cfg)
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        md = informe.guardar(res, config.ruta("investigacion", "estrategias", "backtest"), hoy)
        print(md.read_text(encoding="utf-8"))
        return
    from .intradia.estudio.alpaca_rest import Alpaca
    cliente = Alpaca(por_minuto=args.por_minuto)
    if args.accion == "universo":
        from .intradia.estudio import universo
        c = universo.descargar(cliente, desde, hasta, cfg, max_simbolos=args.max)
        Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        c.to_csv(args.salida, index=False)
        print(f"{len(c)} candidatas ({int(c['A'].sum()) if len(c) else 0} A, {int(c['B'].sum()) if len(c) else 0} B) "
              f"en {c['fecha'].nunique() if len(c) else 0} días · {cliente.llamadas} llamadas · feed {cliente.feed}")
    elif args.accion == "tramo":
        from .intradia.estudio import ejecutar
        from .intradia.estudio.universo import leer_csv
        cands = leer_csv(args.candidatas)  # "NA" es un ticker, no un vacío
        g, o = ejecutar.procesar(cliente, cands, desde, hasta, cfg)
        sal = Path(args.salida)
        sal.mkdir(parents=True, exist_ok=True)
        g.to_csv(sal / f"gainers-{args.nombre}.csv.gz", index=False)
        o.to_csv(sal / f"orb-{args.nombre}.csv.gz", index=False)
        print(f"Tramo {args.nombre}: {len(g)} filas gainers, {len(o)} operaciones ORB · {cliente.llamadas} llamadas")


def _corto(args):
    from .common import config
    from .intradia.corto_hueco import sesion
    from .intradia.corto_hueco.etoro import EToroDemo

    config.cargar_env()
    cfg = config.cargar("corto_hueco")
    sims = [x.strip().upper() for x in (args.simbolos or "").split(",") if x.strip()] or None
    etoro = EToroDemo()
    if args.accion == "operar":
        from .intradia.estudio.alpaca_rest import Alpaca
        d = sesion.operar(cfg, Alpaca(), etoro, ensayo=args.ensayo, simbolos=sims)
    else:
        d = sesion.cerrar(cfg, etoro, ensayo=args.ensayo, forzar=args.forzar)
    print(f"{len(d.filas)} decisiones apuntadas; {len(d.avisos)} avisos.")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # para que Windows muestre bien las tildes
    p = argparse.ArgumentParser(prog="lab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="grupo", required=True)
    pi = sub.add_parser("intradia", help="Agente A: trading intradía")
    pi.add_argument("accion", choices=["demo", "comprobar", "backtest", "sesion", "cerrar-todo"])
    pi.add_argument("--dias", type=int, default=30)
    pm = sub.add_parser("medio", help="Agente B: inversión a 12 meses")
    pm.add_argument("accion", choices=["oportunidades", "cribado", "ficha", "probar", "alertas", "fuentes"])
    pm.add_argument("ticker", nargs="?")
    pm.add_argument("--max", type=int, default=None, help="máximo de empresas a analizar (para pruebas)")
    pm.add_argument("--parte", type=int, default=1, help="oportunidades: qué trozo del universo descargar (1..N)")
    pm.add_argument("--de", type=int, default=1, help="oportunidades: en cuántos trozos se reparte")
    pm.add_argument("--salida", help="oportunidades: solo descargar y guardar en este archivo .jsonl")
    pm.add_argument("--minutos", type=float, default=None, help="oportunidades: tiempo máximo de descarga")
    pm.add_argument("--nombre", help="fuentes: nombre de la empresa para buscar sus ensayos clínicos")
    pm.add_argument("--entrada", help="oportunidades: carpeta con los .jsonl descargados para juntar y puntuar")
    pe = sub.add_parser("estudio", help="Estudio intradía con datos históricos de Alpaca (solo lectura)")
    pe.add_argument("accion", choices=["universo", "tramo", "informe"])
    pe.add_argument("--desde")
    pe.add_argument("--hasta")
    pe.add_argument("--salida", default="datos_estudio")
    pe.add_argument("--candidatas", default="datos_estudio/candidatas.csv.gz")
    pe.add_argument("--entrada", default="datos_estudio")
    pe.add_argument("--nombre", default="tramo")
    pe.add_argument("--max", type=int, default=None, help="universo: máximo de símbolos (para pruebas)")
    pe.add_argument("--por-minuto", type=int, default=None, help="llamadas por minuto a Alpaca (máx. 200 gratis)")
    pc = sub.add_parser("corto", help="Agente A · corto del hueco en eToro DEMO")
    pc.add_argument("accion", choices=["operar", "cerrar"])
    pc.add_argument("--ensayo", action="store_true", help="hace todo menos enviar órdenes")
    pc.add_argument("--simbolos", help="ensayo: mirar estos tickers aunque no tengan hueco")
    pc.add_argument("--forzar", action="store_true", help="cerrar: cerrar ya, sin esperar a la hora")
    sub.add_parser("diario", help="Escribe el diario del día")
    sub.add_parser("panel", help="Abre el panel web")
    args = p.parse_args(argv)

    if args.grupo == "intradia":
        _intradia(args)
    elif args.grupo == "medio":
        if args.accion in ("ficha", "probar") and not args.ticker:
            p.error("indica el ticker, por ejemplo: lab medio ficha ABCD")
        _medio(args)
    elif args.grupo == "estudio":
        _estudio(args)
    elif args.grupo == "corto":
        _corto(args)
    elif args.grupo == "diario":
        from .diario import escribir
        print("Diario guardado en", escribir())
    elif args.grupo == "panel":
        from .common.config import ruta
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(ruta("dashboard", "app.py"))])


if __name__ == "__main__":
    main()
