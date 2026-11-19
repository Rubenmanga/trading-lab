"""Sesión del «corto del hueco» en eToro DEMO: escanear a las 9:34 NY, vender en corto a las 9:35, cerrar a las 15:45.

Todo lo que decide se apunta con su motivo en investigacion/corto-hueco/ (registro.csv + un .md por día).
Si hay algo que contar, deja aviso.md para que GitHub abra un issue (aviso al móvil).
"""
from __future__ import annotations

import csv
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ...common.config import ruta
from . import riesgo

NY = ZoneInfo("America/New_York")
CAMPOS = ["fecha_hora_ny", "simbolo", "accion", "motivo", "hueco", "precio", "importe_usd", "stop", "order_id",
          "position_id", "resultado_pct"]


def carpeta() -> Path:
    c = ruta("investigacion", "corto-hueco")
    c.mkdir(parents=True, exist_ok=True)
    return c


def leer_estado() -> dict:
    f = carpeta() / "estado.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def guardar_estado(e: dict) -> None:
    (carpeta() / "estado.json").write_text(json.dumps(e, indent=1, ensure_ascii=False), encoding="utf-8")


def _hora(txt: str):
    p = [int(x) for x in txt.split(":")]
    return p[0], p[1], p[2] if len(p) > 2 else 0


def _en(ahora: datetime, txt: str) -> datetime:
    h, m, s = _hora(txt)
    return ahora.replace(hour=h, minute=m, second=s, microsecond=0)


class Diario:
    """Registro de decisiones (regla 4 del proyecto) y resumen del día."""

    def __init__(self, reloj):
        self.reloj = reloj
        self.filas: list[dict] = []
        self.avisos: list[str] = []

    def apuntar(self, simbolo: str, accion: str, motivo: str, **datos) -> None:
        fila = {"fecha_hora_ny": self.reloj().strftime("%Y-%m-%d %H:%M:%S"), "simbolo": simbolo, "accion": accion,
                "motivo": motivo, **{k: datos.get(k, "") for k in CAMPOS[4:]}}
        self.filas.append(fila)
        print(f"[{fila['fecha_hora_ny']}] {simbolo or '-'} · {accion} · {motivo}", flush=True)

    def guardar(self, titulo: str) -> None:
        if not self.filas:
            return
        f = carpeta() / "registro.csv"
        nuevo = not f.exists()
        with open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CAMPOS)
            if nuevo:
                w.writeheader()
            w.writerows(self.filas)
        dia = self.filas[0]["fecha_hora_ny"][:10]
        md = carpeta() / f"{dia}.md"
        previo = md.read_text(encoding="utf-8") if md.exists() else ""
        lineas = [f"## {titulo} ({self.filas[-1]['fecha_hora_ny'][11:16]} NY)", ""]
        lineas += [f"- **{x['simbolo'] or '—'}** · {x['accion']}: {x['motivo']}" for x in self.filas]
        if not previo:
            previo = (f"# Corto del hueco · {dia} (eToro DEMO)\n\n"
                      "*Resumen: cada día a las 9:35 de Nueva York (15:35 en España) el bot vende en corto, en la "
                      "cuenta demo, las acciones que abren ≥ +50 % y que eToro deja vender; stop 15 % por encima "
                      "y cierre de todo a las 15:45 NY (21:45 en España). Abajo, cada decisión con su motivo. "
                      "Es una prueba en demo: no es dinero real.*\n")
        md.write_text(previo.rstrip() + "\n\n" + "\n".join(lineas) + "\n", encoding="utf-8")
        if self.avisos:
            (carpeta() / "aviso.md").write_text(f"# Corto del hueco · {dia}\n\n" + "\n".join(f"- {a}" for a in self.avisos)
                                                + f"\n\nDetalle: investigacion/corto-hueco/{dia}.md\n", encoding="utf-8")


def _esperar(hasta: datetime, reloj, dormir) -> None:
    while (falta := (hasta - reloj()).total_seconds()) > 0:
        dormir(min(falta, 30))


def operar(cfg: dict, alpaca, etoro, ensayo: bool = False, simbolos: list[str] | None = None,
           reloj=lambda: datetime.now(NY), dormir=time.sleep) -> Diario:
    from . import escaner
    diario = Diario(reloj)
    ahora = reloj()
    hoy = ahora.strftime("%Y-%m-%d")
    estado = leer_estado()
    if not ensayo:
        if ahora.weekday() >= 5:
            print("Fin de semana: nada que hacer.")
            return diario
        if ahora < _en(ahora, cfg["hora_ventana_desde"]) or ahora > _en(ahora, cfg["hora_limite_entrada"]):
            print(f"Fuera de la ventana ({ahora:%H:%M} NY). Otra ejecución programada se encarga.")
            return diario
        if estado.get("operado_dia") == hoy:
            print("Hoy ya se operó (otra ejecución llegó antes).")
            return diario
        if not escaner.mercado_abre_hoy(alpaca, hoy):
            print("Hoy la bolsa de EE. UU. está cerrada (festivo).")
            return diario
        estado["operado_dia"] = hoy   # se marca ya: si algo falla, no se repite el día
        guardar_estado(estado)
        _esperar(_en(ahora, cfg["hora_escaneo"]), reloj, dormir)

    cands = escaner.candidatos(alpaca, cfg, reloj(), simbolos)
    if not cands:
        diario.apuntar("", "nada", f"ninguna acción abre con hueco ≥ {cfg['hueco_min']:.0%} y liquidez suficiente")
        diario.guardar("Apertura")
        return diario
    for c in cands:
        diario.apuntar(c["simbolo"], "candidata", f"hueco {c['hueco']:+.0%}, cierre ayer {c['cierre_ant']:.2f} $, "
                       f"se negocian {c['dolares_dia']:,.0f} $/día", hueco=c["hueco"])
    if not ensayo:
        _esperar(_en(reloj(), cfg["hora_entrada"]), reloj, dormir)

    try:
        credito, posiciones = etoro.cartera()
    except Exception as e:  # noqa: BLE001 - sin cartera no se puede medir el riesgo: hoy no se abre nada, pero queda apuntado
        diario.apuntar("", "error", f"eToro no devuelve la cartera demo ({type(e).__name__}): hoy no se abre nada")
        diario.avisos.append("El bot no pudo leer la cuenta demo de eToro: hoy no abrió nada.")
        diario.guardar("Apertura")
        return diario
    cap = riesgo.capital(credito, posiciones)
    estado.setdefault("capital_inicial", round(cap, 2))
    if riesgo.freno_activado(cap, estado["capital_inicial"], cfg):
        diario.apuntar("", "freno", f"capital demo {cap:,.0f} $ ha caído más de un {cfg['freno_caida_pct']} % "
                       f"desde {estado['capital_inicial']:,.0f} $: hoy no se abre nada")
        diario.avisos.append("Freno de pérdidas activado: el bot no abre operaciones. Revisar.")
        guardar_estado(estado)
        diario.guardar("Apertura")
        return diario
    expuesto = sum(float(p.get("amount") or 0) for p in posiciones if p.get("isBuy") is False)
    abiertas = estado.get("abiertas", [])
    hechas = 0
    for c in cands:
        try:
            if hechas >= cfg["max_operaciones_dia"]:
                diario.apuntar(c["simbolo"], "descartada", f"ya hay {hechas} operaciones hoy (máximo)")
                continue
            iid = etoro.instrumento(c["simbolo"])
            if not iid:
                diario.apuntar(c["simbolo"], "descartada", "no está en eToro")
                continue
            el = etoro.corto_permitido(iid)
            if not el.get("ok"):
                diario.apuntar(c["simbolo"], "descartada", el.get("motivo", "eToro no deja corto"))
                continue
            if ensayo:
                print(f"  elegibilidad {c['simbolo']}: apalancamientos {el.get('apalancamientos')}, stop {el.get('stop_min')}-"
                      f"{el.get('stop_max')}, campos {el.get('forma')}")
            tasa = etoro.precios([iid]).get(iid) or {}
            bid, ask = tasa.get("bid"), tasa.get("ask")
            if not bid or not ask:
                diario.apuntar(c["simbolo"], "descartada", "eToro no da precio ahora mismo")
                continue
            if bid / c["cierre_ant"] - 1 < cfg["hueco_min"] / 2 and not simbolos:
                diario.apuntar(c["simbolo"], "descartada", f"ya ha bajado mucho antes de entrar ({bid / c['cierre_ant'] - 1:+.0%})")
                continue
            stop_pct = riesgo.stop_ajustado(cfg["stop_pct"], el.get("stop_min"), el.get("stop_max"))
            levs = el.get("apalancamientos") or []
            lev = 1 if (not levs or 1 in levs) else min(levs)       # sin apalancamiento si eToro lo permite
            cfg_op = {**cfg, "apalancamiento": lev,
                      "importe_min_usd": max(cfg.get("importe_min_usd", 50), float(el.get("importe_min") or 0))}
            importe, motivo = riesgo.tamano(cap, credito, expuesto, stop_pct, cfg_op)
            if not importe:
                diario.apuntar(c["simbolo"], "descartada", motivo)
                continue
            stop = riesgo.precio_stop(ask, stop_pct)
            if ensayo:
                diario.apuntar(c["simbolo"], "ensayo", f"vendería en corto {importe:,.0f} $ a ~{bid} $ con stop {stop} $ "
                               f"({stop_pct:g} %); precio {tasa.get('quoteType', '?')}", precio=bid, importe_usd=importe, stop=stop)
                hechas += 1
                continue
            r = etoro.abrir_corto(iid, importe, stop, lev)
            if not r.get("ok"):
                diario.apuntar(c["simbolo"], "error", r.get("motivo", "orden rechazada"))
                diario.avisos.append(f"{c['simbolo']}: eToro rechazó la orden ({r.get('motivo', '')[:120]})")
                continue
            hechas += 1
            expuesto += importe * lev
            credito -= importe
            abiertas.append({"simbolo": c["simbolo"], "instrumentId": iid, "orderId": r.get("orderId"), "dia": hoy,
                             "precio_aprox": bid, "importe": importe, "stop": stop})
            # Se guarda YA: si algo falla con la siguiente candidata, el cierre de las 15:45 sabe que esta existe.
            estado["abiertas"] = abiertas
            guardar_estado(estado)
            diario.apuntar(c["simbolo"], "abierta", f"corto de {importe:,.0f} $ a ~{bid} $ (hueco {c['hueco']:+.0%}), stop {stop} $",
                           hueco=c["hueco"], precio=bid, importe_usd=importe, stop=stop, order_id=r.get("orderId"))
            diario.avisos.append(f"Abierto corto DEMO en {c['simbolo']}: {importe:,.0f} $ a ~{bid} $, stop {stop} $ "
                                 f"(hueco {c['hueco']:+.0%}). Se cierra a las 15:45 NY (21:45 en España).")
        except Exception as e:  # noqa: BLE001 - un fallo con una candidata no puede tumbar el día ni perder lo ya abierto
            diario.apuntar(c["simbolo"], "error", f"fallo inesperado con esta candidata: {type(e).__name__}: {str(e)[:150]}")
            diario.avisos.append(f"{c['simbolo']}: fallo inesperado ({type(e).__name__}). Mira en la demo de eToro si quedó algo abierto.")
    if not ensayo:
        estado["abiertas"] = abiertas
        guardar_estado(estado)
    diario.guardar("Apertura" + (" (ensayo, sin órdenes)" if ensayo else ""))
    return diario


def cerrar(cfg: dict, etoro, ensayo: bool = False, reloj=lambda: datetime.now(NY), forzar: bool = False) -> Diario:
    diario = Diario(reloj)
    ahora = reloj()
    estado = leer_estado()
    abiertas = estado.get("abiertas", [])
    if not abiertas:
        print("No hay posiciones del bot abiertas.")
        return diario
    if not (ensayo or forzar) and ahora < _en(ahora, cfg["hora_cierre"]) and ahora.strftime("%Y-%m-%d") <= min(a["dia"] for a in abiertas):
        print(f"Aún no es la hora de cierre ({ahora:%H:%M} NY).")
        return diario
    credito, posiciones = etoro.cartera()
    ids = {int(a["instrumentId"]) for a in abiertas}
    mias = [p for p in posiciones if p.get("isBuy") is False and int(p.get("instrumentID") or 0) in ids]
    tasas = etoro.precios(sorted(ids)) if ids else {}
    quedan = []
    for a in abiertas:
        pos = [p for p in mias if int(p.get("instrumentID") or 0) == int(a["instrumentId"])]
        if not pos:
            diario.apuntar(a["simbolo"], "ya cerrada", "no sigue abierta en eToro (lo más probable: saltó el stop)")
            diario.avisos.append(f"{a['simbolo']}: la posición ya no estaba abierta (¿stop?).")
            continue
        for p in pos:
            ask = (tasas.get(int(a["instrumentId"])) or {}).get("ask")
            entrada = float(p.get("openRate") or a.get("precio_aprox") or 0)
            res = round((entrada - ask) / entrada * 100, 2) if ask and entrada else ""
            if ensayo:
                diario.apuntar(a["simbolo"], "ensayo cierre", f"cerraría la posición {p.get('positionID')} (resultado aprox. {res} %)")
                continue
            r = etoro.cerrar(p["positionID"], a["instrumentId"])
            if r["ok"]:
                diario.apuntar(a["simbolo"], "cerrada", f"cierre de fin de día; resultado aprox. {res} % (entrada {entrada} $, ahora ~{ask} $)",
                               position_id=p.get("positionID"), precio=ask, resultado_pct=res)
                diario.avisos.append(f"Cerrado corto DEMO en {a['simbolo']}: resultado aprox. {res} %.")
            else:
                diario.apuntar(a["simbolo"], "error", f"no se pudo cerrar: {r['motivo']}")
                diario.avisos.append(f"¡{a['simbolo']} NO se pudo cerrar! Ciérrala a mano en la demo de eToro. {r['motivo'][:120]}")
                quedan.append(a)
    if not ensayo:
        estado["abiertas"] = quedan
        guardar_estado(estado)
    diario.guardar("Cierre" + (" (ensayo)" if ensayo else ""))
    return diario
