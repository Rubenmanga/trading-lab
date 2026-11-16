"""Punto de entrada: el comando `lab`.

  lab intradia demo         Prueba completa con datos inventados (no necesita claves)
  lab intradia comprobar    Comprueba tus claves de Alpaca demo y si la bolsa está abierta
  lab intradia backtest     Prueba la estrategia con datos reales del pasado (Alpaca, gratis)
  lab intradia sesion       Sesión en vivo durante la ventana de trading
  lab intradia cerrar-todo  Botón del pánico: cierra todo en la cuenta demo
  lab estudio universo      Estudio intradía (Alpaca, solo lectura): velas diarias -> candidatas
  lab estudio tramo         ... velas de 1 min de las candidatas -> top gainers y operaciones ORB
  lab estudio informe       ... junta todo y escribe el informe en investigacion/estrategias/
  lab laboratorio tramo     Laboratorio intradía: 6 estrategias en papel con el pasado (un tramo de fechas)
  lab laboratorio dia       ... cuenta sombra: apunta lo que habría hecho cada estrategia hoy
  lab laboratorio demo      ... EN DIRECTO en la demo de Alpaca (cada 10 min; a las 15:45 NY cierra)
  lab laboratorio directo   ... igual que demo pero con conexión continua (websocket Alpaca IEX, 30 acciones, al segundo)
  lab laboratorio informe   ... compara las estrategias y escribe investigacion/laboratorio/
  lab corto operar          Corto del hueco en eToro DEMO: escanea a las 9:34 NY y vende en corto a las 9:35
  lab corto cerrar          ... cierra las posiciones del bot (a partir de las 15:45 NY)
  lab diario                Escribe el diario del día en diario/
  lab medio oportunidades   Buscador: puntúa todas las small caps (8 factores) y guarda el ranking
  lab medio fuentes TICKER  Prueba las fuentes públicas gratis (SEC EDGAR, ClinicalTrials.gov, FRED)
  lab medio cribado         Cribado sencillo antiguo (solo potencial según analistas)
  lab medio ficha TICKER    Datos de una empresa (los usa la skill de análisis)
  lab medio alertas         Revisa la lista de vigilancia y avisa
  lab medio seguimiento     Seguimiento diario de las empresas en config (momento de entrada + lista de noticias)
  lab medio noticias        Solo la lista de noticias (revisión rápida cada 2 h en horario de bolsa)
  lab medio expediente [T]  Expediente por acción: hechos con fuente, fecha y reacción del precio
  lab medio marcador        Marcador: ¿aciertan los análisis? (libro de predicciones frente a IWM)
  lab radar parte|informe   Radar de resultados: prueba con el pasado (corre en GitHub Actions)
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
        from .medio_plazo import sec_cuentas
        for tk in (t, "AMSC", "PGY"):   # cuentas XBRL + Piotroski / Altman Z'' / Beneish M
            print(f"SEC cuentas {tk}:", json.dumps(sec_cuentas.descargar([tk]).get(tk), ensure_ascii=False),
                  fp.ULTIMO_ERROR.get("data.sec.gov") or "")
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
    elif args.accion == "expediente":
        from .medio_plazo import expediente
        res = expediente.ejecutar(cfg, [args.ticker] if args.ticker else None)
        for t, r in res.items():
            print(f"{t}: {r['eventos']} hechos (+{r['añadidas']} nuevos) · {r.get('ultimo') or '-'}"
                  + (f" · AVISO: {r['error']}" if r.get("error") else ""))
    elif args.accion == "regla-fuentes":
        from .medio_plazo import regla_fuentes
        if regla_fuentes.main([args.ticker] if args.ticker else []):
            raise SystemExit(1)
    elif args.accion == "hoy":
        from .medio_plazo import carpeta_dia
        print(carpeta_dia.ejecutar().read_text(encoding="utf-8"))
    elif args.accion == "marcador":
        from .medio_plazo import marcador
        r = marcador.ejecutar()
        print(f"Libro: {r['total']} predicciones (+{r['añadidas']} nuevas) · puntuadas {r['puntuadas']} · "
              f"aciertos {r['aciertos_pct']} % · {r['muestra']}")
    elif args.accion == "noticias":
        from .medio_plazo import seguimiento
        res = seguimiento.solo_lista(cfg)
        for t, e in {**(res.get("lista") or {}).get("empresas", {}), **(res.get("lista") or {}).get("materias_primas", {})}.items():
            print(f"{t}: {e.get('cambio_pct')} % · {e.get('resumen')} · {'; '.join(a['texto'] for a in e.get('avisos_nuevos', []))}")
    elif args.accion == "seguimiento":
        from .medio_plazo import seguimiento
        res = seguimiento.ejecutar(cfg)
        for t, e in res["empresas"].items():
            print(f"{t} {e.get('fecha')}: {e['estado']} · cierre {e.get('cierre')} · RSI {e.get('rsi')} · "
                  + "; ".join(a["texto"] for a in e.get("avisos", [])))


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


def _laboratorio(args):
    from pathlib import Path

    import pandas as pd

    from .common import config
    from .intradia.laboratorio import informe, motor

    config.cargar_env()
    cfg = config.cargar("laboratorio_intradia")
    carpeta = config.ruta("investigacion", "laboratorio")
    sombra_csv = carpeta / "sombra" / "operaciones.csv"
    if args.accion == "informe":
        back = informe.leer_ops(carpeta / "backtest", "ops-*.csv.gz")
        if args.entrada and Path(args.entrada).exists():
            nuevo = informe.leer_ops(Path(args.entrada), "ops-*.csv.gz")
            if len(nuevo):  # los años recalculados sustituyen a los guardados
                back = pd.concat([back[~back["fecha"].str[:4].isin(set(nuevo["fecha"].str[:4]))] if len(back) else back, nuevo])
                (carpeta / "backtest").mkdir(parents=True, exist_ok=True)
                for anio, g in nuevo.groupby(nuevo["fecha"].str[:4]):
                    g.to_csv(carpeta / "backtest" / f"ops-{anio}.csv.gz", index=False)
        sombra = informe.leer_ops(sombra_csv.parent, sombra_csv.name)
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        md = informe.guardar(informe.generar(back, sombra, cfg, hoy), carpeta)
        print(md.read_text(encoding="utf-8"))
        return
    from .intradia.estudio.alpaca_rest import Alpaca
    from .intradia.estudio.universo import leer_csv
    cliente = Alpaca(por_minuto=args.por_minuto)
    if args.accion == "directo":
        from .intradia.laboratorio import directo
        from .intradia.laboratorio.alpaca_demo import AlpacaDemo
        directo.ejecutar(cfg, config.cargar("estudio_intradia"), cliente, None if args.ensayo else AlpacaDemo(),
                         ensayo=args.ensayo, cache=Path(args.salida), max_simbolos=args.max)
        return
    if args.accion == "demo":
        from .intradia.laboratorio import demo
        from .intradia.laboratorio.alpaca_demo import AlpacaDemo
        broker = None if args.ensayo else AlpacaDemo()
        ahora = datetime.fromisoformat(args.ahora) if args.ahora else None
        demo.pasada(cfg, config.cargar("estudio_intradia"), cliente, broker, ahora=ahora, ensayo=args.ensayo,
                    cache=Path(args.salida), max_simbolos=args.max)
        return
    if args.accion == "tramo":
        ops = motor.procesar(cliente, leer_csv(args.candidatas), args.desde, args.hasta, cfg)
        sal = Path(args.salida)
        sal.mkdir(parents=True, exist_ok=True)
        ops.to_csv(sal / f"ops-{args.nombre}.csv.gz", index=False)
        print(f"Tramo {args.nombre}: {len(ops)} operaciones · {cliente.llamadas} llamadas")
    else:  # dia: cuenta sombra
        from zoneinfo import ZoneInfo

        from .intradia.estudio import universo
        fecha = args.fecha or datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        cands = universo.descargar(cliente, fecha, fecha, config.cargar("estudio_intradia"), max_simbolos=args.max)
        ops = motor.procesar(cliente, cands, fecha, fecha, cfg) if len(cands) else pd.DataFrame()
        print(f"{fecha}: {len(cands)} candidatas, {len(ops)} operaciones en papel · {cliente.llamadas} llamadas")
        if ops.empty:
            print("Sin operaciones (¿festivo o fin de semana?): no se apunta nada.")
            return
        viejo = informe.leer_ops(sombra_csv.parent, sombra_csv.name)
        if len(viejo):
            viejo = viejo[viejo["fecha"] != fecha]
        sombra_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.concat([viejo, ops], ignore_index=True).sort_values(["fecha", "estrategia", "hora_entrada"]).to_csv(sombra_csv, index=False)


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


def _radar(args):
    import csv
    import json
    import zlib
    from pathlib import Path

    from .common import config
    from .radar import resultados as rr

    if args.accion == "parte":
        with open(config.ruta("investigacion", "duplicar", "universo.csv"), newline="", encoding="utf-8") as fh:
            tks = sorted({f["ticker"].strip().upper() for f in csv.DictReader(fh) if f.get("ticker")})
        mios = [t for t in tks if zlib.crc32(t.encode()) % args.de == args.parte - 1]
        if args.max:
            mios = mios[: args.max]
        Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        r = rr.correr_parte(mios, Path(args.salida), minutos=args.minutos or 50)
        print(f"Parte {args.parte}/{args.de}: {len(mios)} empresas, {r['ok']} bajadas, {len(r['fallos'])} fallos")
        (Path(args.salida).with_suffix(".fallos.json")).write_text(json.dumps(r["fallos"]), encoding="utf-8")
    else:  # informe
        evs, fallos = [], []
        for f in sorted(Path(args.entrada).glob("*.jsonl")):
            for linea in f.read_text(encoding="utf-8").splitlines():
                try:
                    evs += json.loads(linea)["eventos"]
                except Exception:  # noqa: BLE001
                    pass
        for f in Path(args.entrada).glob("*.fallos.json"):
            fallos += json.loads(f.read_text(encoding="utf-8"))
        res = rr.analizar(evs)
        sal = config.ruta("investigacion", "radar")
        sal.mkdir(parents=True, exist_ok=True)
        import pandas as pd
        pd.DataFrame(evs).to_csv(sal / "eventos-resultados.csv.gz", index=False)   # datos para reutilizar en otras pruebas
        (sal / "prueba-resultados.md").write_text(rr.informe(res, fallos), encoding="utf-8")
        (sal / "prueba-resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print((sal / "prueba-resultados.md").read_text(encoding="utf-8"))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # para que Windows muestre bien las tildes
    p = argparse.ArgumentParser(prog="lab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="grupo", required=True)
    pi = sub.add_parser("intradia", help="Agente A: trading intradía")
    pi.add_argument("accion", choices=["demo", "comprobar", "backtest", "sesion", "cerrar-todo"])
    pi.add_argument("--dias", type=int, default=30)
    pm = sub.add_parser("medio", help="Agente B: inversión a 12 meses")
    pm.add_argument("accion", choices=["oportunidades", "cribado", "ficha", "probar", "alertas", "fuentes", "seguimiento", "noticias", "expediente", "marcador", "regla-fuentes", "hoy"])
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
    pr = sub.add_parser("radar", help="Radar de resultados (agente B): prueba con el pasado")
    pr.add_argument("accion", choices=["parte", "informe"])
    pr.add_argument("--parte", type=int, default=1)
    pr.add_argument("--de", type=int, default=1)
    pr.add_argument("--max", type=int, default=None)
    pr.add_argument("--minutos", type=float, default=None)
    pr.add_argument("--salida", default="partes_radar/parte-1.jsonl")
    pr.add_argument("--entrada", default="partes_radar")
    pl = sub.add_parser("laboratorio", help="Agente A · laboratorio de estrategias en cuenta sombra (solo papel)")
    pl.add_argument("accion", choices=["tramo", "dia", "informe", "demo", "directo"])
    pl.add_argument("--ensayo", action="store_true", help="demo: todo menos enviar órdenes")
    pl.add_argument("--ahora", help="demo (ensayo): hacer como si fuera esta hora, AAAA-MM-DDTHH:MM-05:00")
    pl.add_argument("--desde")
    pl.add_argument("--hasta")
    pl.add_argument("--fecha", help="dia: AAAA-MM-DD (por defecto hoy en Nueva York)")
    pl.add_argument("--candidatas", default="datos_estudio/candidatas.csv.gz")
    pl.add_argument("--salida", default="datos_lab")
    pl.add_argument("--entrada", default=None, help="informe: carpeta con ops-*.csv.gz nuevos")
    pl.add_argument("--nombre", default="tramo")
    pl.add_argument("--max", type=int, default=None)
    pl.add_argument("--por-minuto", type=int, default=None)
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
    elif args.grupo == "laboratorio":
        _laboratorio(args)
    elif args.grupo == "radar":
        _radar(args)
    elif args.grupo == "diario":
        from .diario import escribir
        print("Diario guardado en", escribir())
    elif args.grupo == "panel":
        from .common.config import ruta
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(ruta("dashboard", "app.py"))])


if __name__ == "__main__":
    main()
