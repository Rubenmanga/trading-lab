"""Laboratorio EN DIRECTO en la cuenta DEMO de Alpaca (dinero ficticio). GitHub lo lanza cada 10 minutos.

En cada pasada:
  1) Elige las acciones del día (solo la primera vez; luego se reutiliza la lista guardada).
  2) Baja las velas de 1 minuto hasta ahora y pasa las MISMAS estrategias que el laboratorio en papel.
  3) Una señal nueva (de los últimos minutos) pasa por el filtro «¿entrar o no?» y por las reglas de
     riesgo (código fijo, sin IA). Si pasa, se envía una orden con stop y objetivo ya puestos en Alpaca.
  4) Si una operación ya gana 1R, sube el stop (trailing).
A partir de las 15:45 NY se cierra todo lo que abrió el laboratorio y se apunta el resultado.
Cada decisión (también las que NO se hacen) queda en investigacion/laboratorio/demo/registro.csv con su motivo.
"""
from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from zoneinfo import ZoneInfo

from ...common import config
from ..estudio import simular, universo
from ..estudio.alpaca_rest import DATOS
from ..trailing import nuevo_stop
from . import motor

NY = ZoneInfo("America/New_York")
PREFIJO = "lab"
CAMPOS = ["fecha_hora_ny", "estrategia", "simbolo", "accion", "lado", "precio", "stop", "objetivo", "acciones",
          "nota", "filtro", "R", "motivo", "precio_senal", "retraso_s", "relleno", "deslizamiento_pct"]


VISTAS: set = set()   # señales ya decididas (descartadas o enviadas) en esta ejecución


def carpeta() -> Path:
    return config.ruta("investigacion", "laboratorio", "demo")


def apuntar(filas: list[dict]):
    if not filas:
        return
    f = carpeta() / "registro.csv"
    f.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not f.exists()
    with open(f, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        w.writerows(filas)


def id_cliente(fecha: str, estrategia: str, simbolo: str) -> str:
    return f"{PREFIJO}-{fecha.replace('-', '')}-{estrategia}-{simbolo}"


def de_lab(o: dict) -> bool:
    return str(o.get("client_order_id", "")).startswith(PREFIJO + "-")


def estrategia_de(o: dict) -> str:
    partes = str(o.get("client_order_id", "")).split("-")
    return partes[2] if len(partes) >= 4 else "?"


# ---------------------------------------------------------------- acciones del día
def candidatas_hoy(cliente, fecha: str, cfg_estudio: dict, max_simbolos: int | None = None) -> pd.DataFrame:
    """Como `lab estudio universo`, pero para HOY: historial diario hasta ayer + apertura de hoy (foto en
    tiempo real del feed IEX, gratis)."""
    sims = universo.simbolos_validos([a for a in cliente.valores() if a.get("status") == "active" and a.get("tradable")])
    if max_simbolos:
        sims = sims[:max_simbolos]
    hoy0 = datetime.fromisoformat(fecha).replace(tzinfo=NY)
    hist = [universo.velas_seguras(cliente, sims[i:i + 100], "1Day", hoy0 - timedelta(days=40), hoy0 - timedelta(minutes=1))
            for i in range(0, len(sims), 100)]
    hist = pd.concat([h for h in hist if len(h)], ignore_index=True) if any(len(h) for h in hist) else pd.DataFrame()
    filas = []
    for i in range(0, len(sims), 500):
        j = cliente._get(f"{DATOS}/v2/stocks/snapshots", {"symbols": ",".join(sims[i:i + 500]), "feed": "iex"})
        for s, x in (j or {}).items():
            d = (x or {}).get("dailyBar") or {}
            if d.get("o") and str(d.get("t", ""))[:10] == fecha:
                filas.append((s, pd.Timestamp(d["t"]), d["o"], d.get("h", d["o"]), d.get("l", d["o"]), d.get("c", d["o"]), d.get("v", 0)))
    if hist.empty or not filas:
        return pd.DataFrame()
    hoy = pd.DataFrame(filas, columns=["simbolo", "t", "o", "h", "l", "c", "v"])
    hoy["t"] = pd.to_datetime(hoy["t"], utc=True)
    c = universo.candidatas(universo.rasgos_diarios(pd.concat([hist, hoy], ignore_index=True)), cfg_estudio)
    return c[c["fecha"] == fecha].reset_index(drop=True)


def velas_hasta_ahora(cliente, sims: list[str], fecha: str, ahora: datetime) -> pd.DataFrame:
    """Plan gratis: SIP (todo el mercado) solo con 15 min de retraso; lo más reciente, del feed IEX."""
    ini = datetime.fromisoformat(fecha).replace(hour=9, minute=30, tzinfo=NY)
    corte = ahora - timedelta(minutes=16)
    partes = []
    for feed, a, b in (("sip", ini, corte), ("iex", max(ini, corte), ahora)):
        if b <= a:
            continue
        cliente.feed = feed
        for i in range(0, len(sims), 100):
            p = universo.velas_seguras(cliente, sims[i:i + 100], "1Min", a, b)
            if len(p):
                partes.append(p)
    if not partes:
        return pd.DataFrame()
    m = pd.concat(partes, ignore_index=True)
    return m.drop_duplicates(["simbolo", "t"], keep="first").sort_values(["simbolo", "t"])


# ---------------------------------------------------------------- riesgo (código fijo, sin IA)
def tamano(capital: float, precio: float, stop_pct: float, R: dict) -> tuple[int, str]:
    if precio <= 0:
        return 0, "precio no válido"
    riesgo_usd = capital * R["riesgo_pct"] / 100
    qty = riesgo_usd / (precio * stop_pct / 100)
    qty = min(qty, capital * R["max_posicion_pct"] / 100 / precio)
    qty = int(math.floor(qty))
    return (qty, "") if qty >= 1 else (0, "tamaño menor de 1 acción")


def niveles(precio: float, lado: str, stop_pct: float, rr: float | None) -> tuple[float, float | None]:
    s = 1 if lado == "compra" else -1
    dist = precio * stop_pct / 100
    return round(precio - s * dist, 2), (round(precio + s * dist * rr, 2) if rr else None)


# ---------------------------------------------------------------- una pasada
def pasada(cfg: dict, cfg_estudio: dict, datos, broker, ahora: datetime | None = None, ensayo: bool = False,
           cache: Path | None = None, max_simbolos: int | None = None) -> list[dict]:
    ahora = (ahora or datetime.now(timezone.utc)).astimezone(NY)
    fecha, hh = ahora.strftime("%Y-%m-%d"), ahora.time()
    D = cfg["demo"]
    marca = ahora.strftime("%Y-%m-%d %H:%M")
    if hh >= simular.T(cfg["riesgo"]["cierre"]):
        return cerrar(cfg, broker, ahora, ensayo)
    if hh < simular.T(D["desde"]) or hh >= simular.T(D["hasta"]):
        print(f"{marca} NY: fuera de la ventana {D['desde']}-{D['hasta']}, no hago nada.")
        return []
    if not ensayo and not broker.reloj().get("is_open"):
        print("La bolsa está cerrada (festivo): no hago nada.")
        return []
    # 1) Acciones del día (guardadas para las pasadas siguientes)
    f = (cache or Path("datos_demo")) / f"candidatas-{fecha}.csv.gz"
    if f.exists():
        cands = universo.leer_csv(f)
    else:
        cands = candidatas_hoy(datos, fecha, cfg_estudio, max_simbolos)
        f.parent.mkdir(parents=True, exist_ok=True)
        cands.to_csv(f, index=False)
    if cands.empty:
        print("Sin candidatas hoy.")
        return []
    # 2) Velas y señales de todas las estrategias
    sims = sorted(set(motor.universo_dia(cands)["simbolo"]) | {motor.INDICE})
    m = velas_hasta_ahora(datos, sims, fecha, ahora)
    por_sim = {s: simular.preparar(g) for s, g in m.groupby("simbolo")}
    return decidir(cfg, cands, por_sim, broker, ahora, ensayo, D["senal_max_min"])


def decidir(cfg: dict, cands: pd.DataFrame, por_sim: dict, broker, ahora: datetime, ensayo: bool, senal_max_min: float,
            ultimo: dict | None = None) -> list[dict]:
    """Pasa las estrategias por las velas que hay, filtra, aplica el riesgo y envía las órdenes.
    `ultimo`: último precio por acción (conexión en directo); si no se da, se usa el cierre de la última vela."""
    fecha, D = ahora.strftime("%Y-%m-%d"), cfg["demo"]
    marca = ahora.strftime("%Y-%m-%d %H:%M:%S")
    ops = motor.operaciones_dia(fecha, cands, por_sim, cfg)
    reciente = (ahora - timedelta(minutes=senal_max_min)).strftime("%H:%M")
    nuevas = [o for o in ops if o["estrategia"] in D["estrategias"] and o["hora_entrada"] >= reciente]
    # 3) Filtro y riesgo
    ya = {o.get("client_order_id") for o in broker.ordenes("all", fecha + "T00:00:00Z")} if not ensayo else set()
    pos = {p["symbol"]: p for p in broker.posiciones()} if not ensayo else {}
    cuenta = broker.cuenta() if not ensayo else {"equity": "100000", "last_equity": "100000"}
    cap, cap_ayer = float(cuenta["equity"]), float(cuenta.get("last_equity") or cuenta["equity"])
    hoy_lab = sum(1 for x in ya if str(x).startswith(id_cliente(fecha, "", "")[:13]))
    F, R = cfg["filtro"], D["riesgo"]
    filas = []
    for o in sorted(nuevas, key=lambda o: -o.get("nota", 0)):
        cid = id_cliente(fecha, o["estrategia"], o["simbolo"])
        if cid in ya:
            continue
        clave = (fecha, o["estrategia"], o["simbolo"], o["hora_entrada"])
        if clave in VISTAS:       # la misma señal se vuelve a ver en las pasadas siguientes: se apunta una sola vez
            continue
        base = dict(fecha_hora_ny=marca, estrategia=o["estrategia"], simbolo=o["simbolo"], lado=o["lado"],
                    nota=o.get("nota"), filtro=o.get("filtro"))
        stop_pct = cfg["estrategias"][o["estrategia"]].get("stop_pct", cfg["riesgo"]["stop_pct"])
        rr = None if cfg["estrategias"][o["estrategia"]].get("sin_objetivo") else cfg["riesgo"]["rr"]
        ult = (ultimo or {}).get(o["simbolo"]) or por_sim[o["simbolo"]]["c"].iloc[-1]
        hs = datetime.strptime(fecha + " " + o["hora_entrada"], "%Y-%m-%d %H:%M").replace(tzinfo=NY)
        retraso = int((ahora - hs).total_seconds())
        motivo = ""
        if o["estrategia"] in F["aplicar_a"] and o.get("nota", 0) < F["umbral"]:
            motivo = f"el filtro dice que mejor no entrar (nota {o.get('nota')} < {F['umbral']})"
        elif abs(ult / o["entrada_bruta"] - 1) * 100 > stop_pct:
            motivo = f"señal pasada: el precio ya se ha movido más que el stop desde la señal ({o['entrada_bruta']} → {ult})"
        elif cap < cap_ayer * (1 - R["freno_dia_pct"] / 100):
            motivo = f"freno del día: la cuenta cae más de un {R['freno_dia_pct']} %"
        elif hoy_lab >= R["max_ops_dia"]:
            motivo = f"ya hay {hoy_lab} operaciones hoy (máximo {R['max_ops_dia']})"
        elif o["simbolo"] in pos:
            motivo = "ya hay una posición abierta en esa acción (de otra estrategia)"
        elif sum(abs(float(p.get("market_value") or 0)) for p in pos.values()) > cap * R["max_exposicion_pct"] / 100:
            motivo = f"exposición total por encima del {R['max_exposicion_pct']} % de la cuenta"
        qty, por_que = tamano(cap, float(ult), stop_pct, R)
        if not motivo and not qty:
            motivo = por_que
        if not motivo and o["lado"] == "venta" and not ensayo:
            a = broker.valor(o["simbolo"])
            if not (a.get("shortable") and a.get("easy_to_borrow")):
                motivo = "Alpaca no deja venderla en corto (no hay acciones para prestar)"
        stop, obj = niveles(float(ult), o["lado"], stop_pct, rr)
        if rr is None:  # sin objetivo (corto del hueco): el bracket necesita uno; se pone muy lejos
            obj = round(float(ult) * (0.5 if o["lado"] == "venta" else 1.5), 2)
        fila = {**base, "precio": round(float(ult), 4), "stop": stop, "objetivo": obj, "acciones": qty,
                "precio_senal": o["entrada_bruta"], "retraso_s": retraso}
        VISTAS.add(clave)
        if motivo:
            filas.append({**fila, "accion": "descartada", "motivo": motivo})
            continue
        if ensayo:
            filas.append({**fila, "accion": "ensayo", "motivo": f"señal de las {o['hora_entrada']}: se habría enviado la orden"})
            continue
        try:
            broker.orden_con_stop(o["simbolo"], qty, o["lado"], stop, obj, cid)
            filas.append({**fila, "accion": "abierta", "motivo": f"señal de las {o['hora_entrada']} · nota del filtro {o.get('nota')}"})
            hoy_lab += 1
            pos[o["simbolo"]] = {"market_value": qty * float(ult)}
        except Exception as e:  # noqa: BLE001 - un rechazo no para el resto
            filas.append({**fila, "accion": "error", "motivo": str(e)[:200]})
    # 4) Trailing: si ya gana 1R, el stop sube (nunca baja)
    if not ensayo:
        filas += trailing(cfg, broker, fecha, marca, por_sim)
    apuntar(filas)
    print(f"{marca} NY: {len(ops)} señales en el día, {len(nuevas)} recientes, "
          f"{sum(f['accion'] == 'abierta' for f in filas)} órdenes, {sum(f['accion'] == 'descartada' for f in filas)} descartadas.")
    return filas


def trailing(cfg: dict, broker, fecha: str, marca: str, por_sim: dict) -> list[dict]:
    t, filas = cfg["riesgo"].get("trailing") or {}, []
    if not t.get("activo"):
        return filas
    for o in broker.ordenes("all", fecha + "T00:00:00Z"):
        if not de_lab(o) or not o.get("filled_avg_price"):
            continue
        lado = "compra" if o["side"] == "buy" else "venta"
        entrada = float(o.get("filled_avg_price") or 0)
        pierna = next((x for x in o.get("legs") or [] if x.get("type") in ("stop", "stop_limit")
                       and x.get("status") in ("new", "held", "accepted", "replaced", "pending_replace")), None)
        velas = por_sim.get(o["symbol"])
        if not entrada or not pierna or velas is None:
            continue
        stop_pct = cfg["estrategias"].get(estrategia_de(o), {}).get("stop_pct", cfg["riesgo"]["stop_pct"])
        stop_ini = entrada * (1 - stop_pct / 100) if lado == "compra" else entrada * (1 + stop_pct / 100)
        desde = pd.Timestamp(o.get("filled_at") or o["created_at"]).tz_convert(NY)
        tras = velas[velas.index >= desde.floor("min")]
        if tras.empty:
            continue
        mejor = float(tras["h"].max()) if lado == "compra" else float(tras["l"].min())
        actual = float(pierna["stop_price"])
        nuevo = nuevo_stop(lado, entrada, stop_ini, actual, mejor, t["activar_en_R"], t["distancia_pct"])
        if (nuevo > actual + 0.005) if lado == "compra" else (nuevo < actual - 0.005):
            try:
                broker.mover_stop(pierna["id"], nuevo)
                filas.append(dict(fecha_hora_ny=marca, estrategia=estrategia_de(o), simbolo=o["symbol"], accion="trailing",
                                  lado=lado, precio=round(mejor, 4), stop=nuevo, motivo=f"ya gana ≥ {t['activar_en_R']}R: stop de {actual} a {nuevo}"))
            except Exception as e:  # noqa: BLE001
                print("  trailing:", o["symbol"], e)
    return filas


def cerrar(cfg: dict, broker, ahora: datetime, ensayo: bool = False) -> list[dict]:
    """15:45 NY: cancela lo pendiente del laboratorio, cierra sus posiciones y apunta el resultado en R."""
    fecha, marca = ahora.strftime("%Y-%m-%d"), ahora.strftime("%Y-%m-%d %H:%M")
    if ensayo:
        return []
    ords = [o for o in broker.ordenes("all", fecha + "T00:00:00Z") if de_lab(o)]
    hechas = {r["simbolo"] + r["estrategia"] for r in _registro() if r.get("fecha_hora_ny", "").startswith(fecha) and r["accion"] == "cerrada"}
    for o in ords:
        if o.get("status") in ("new", "accepted", "partially_filled", "held"):
            try:
                broker.cancelar(o["id"])
            except Exception as e:  # noqa: BLE001
                print("  cancelar:", e)
    for p in broker.posiciones():
        if any(o["symbol"] == p["symbol"] for o in ords):
            try:
                broker.cerrar_posicion(p["symbol"])
            except Exception as e:  # noqa: BLE001
                print("  cerrar:", p["symbol"], e)
    import time
    time.sleep(8)
    todas = broker.ordenes("all", fecha + "T00:00:00Z")
    filas = []
    for o in ords:
        if o.get("filled_avg_price") is None or (o["symbol"] + estrategia_de(o)) in hechas:
            continue
        lado = "compra" if o["side"] == "buy" else "venta"
        entrada = float(o["filled_avg_price"])
        salidas = [x for x in (o.get("legs") or []) if x.get("filled_avg_price")]
        if not salidas:  # cerrada a mano a las 15:45
            salidas = [x for x in todas if x["symbol"] == o["symbol"] and x["side"] != o["side"] and x.get("filled_avg_price")
                       and not de_lab(x) and x["created_at"] >= o["created_at"]]
        if not salidas:
            continue
        sal = salidas[-1]
        salida, s = float(sal["filled_avg_price"]), (1 if lado == "compra" else -1)
        stop_pct = cfg["estrategias"].get(estrategia_de(o), {}).get("stop_pct", cfg["riesgo"]["stop_pct"])
        R = round(s * (salida - entrada) / (entrada * stop_pct / 100), 3)
        motivo = {"limit": "objetivo", "stop": "stop", "stop_limit": "stop"}.get(sal.get("type"), "cierre 15:45")
        cid = str(o.get("client_order_id", ""))
        env = next((r for r in _registro() if r["accion"] == "abierta" and r["simbolo"] == o["symbol"]
                    and r["estrategia"] == estrategia_de(o) and r["fecha_hora_ny"].startswith(fecha)), None)
        ps = float(env["precio_senal"]) if env and env.get("precio_senal") not in (None, "") else None
        desl = round(s * (entrada - ps) / ps * 100, 3) if ps else None   # + = entramos peor que la señal
        filas.append(dict(fecha_hora_ny=marca, estrategia=estrategia_de(o), simbolo=o["symbol"], accion="cerrada", lado=lado,
                          precio=salida, acciones=o.get("filled_qty"), R=R, relleno=entrada, precio_senal=ps, deslizamiento_pct=desl,
                          motivo=f"{motivo}: entrada {entrada} → salida {salida}"))
    apuntar(filas)
    print(f"Cierre {marca}: {len(filas)} operaciones del laboratorio cerradas.")
    return filas


def _registro() -> list[dict]:
    f = carpeta() / "registro.csv"
    if not f.exists():
        return []
    with open(f, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
