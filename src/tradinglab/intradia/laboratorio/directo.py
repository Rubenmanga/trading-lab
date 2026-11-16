"""Laboratorio EN DIRECTO por conexión continua (websocket) con Alpaca IEX, gratis y en tiempo real.

Diferencia con `demo.pasada` (cada 10 min): aquí el programa se queda conectado y, cada vez que cierra una vela
de 1 minuto de alguna de las 30 acciones seguidas, pasa las estrategias, el filtro y el riesgo en 1-2 segundos.

- Las 30 acciones (límite del plan gratis) son las candidatas del día: primero las de más hueco (arriba o abajo).
  QQQ (el Nasdaq) ocupa una plaza porque el filtro lo necesita.
- La historia de la sesión viene por consulta (SIP todo el mercado hasta hace 16 min, IEX lo más reciente) y se
  refresca cada 5 min; las velas nuevas llegan por la conexión. Así el volumen de las primeras velas es el real.
- IEX es una parte pequeña del volumen: precios y velas son fiables, el volumen de las velas recientes es menor.
- Solo cuenta DEMO: la URL de órdenes está fija en paper (`alpaca_demo.py`).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from zoneinfo import ZoneInfo

from ...common.alpaca_cliente import _claves
from ..estudio import simular, universo
from . import demo, motor

NY = ZoneInfo("America/New_York")
WS = "wss://stream.data.alpaca.markets/v2/iex"
MAX_SIMBOLOS = 30          # límite del plan gratis de Alpaca


def elegir(cands: pd.DataFrame, max_n: int = MAX_SIMBOLOS) -> list[str]:
    """Las acciones a seguir: las de más hueco primero. Siempre se añade QQQ (el Nasdaq)."""
    u = motor.universo_dia(cands)
    if u.empty:
        return [motor.INDICE]
    u = u.assign(_a=u["hueco"].abs()).sort_values("_a", ascending=False)
    sims = [s for s in dict.fromkeys(u["simbolo"]) if s != motor.INDICE][: max_n - 1]
    return sims + [motor.INDICE]


def latido(estado: "Estado", sims: list[str], ahora: datetime, extra: dict | None = None):
    """Escribe un archivo pequeño con el estado de la conexión (se guarda en el repo cada 10 min)."""
    f = demo.carpeta() / "estado-directo.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(dict(hora_ny=ahora.strftime("%H:%M:%S"), acciones=len(sims), conectado=estado.conectado,
                                 reconexiones=estado.reconexiones, velas_recibidas=estado.velas, operaciones_vistas=len(estado.ultimo),
                                 ultima_vela=estado.hora_ultima_vela, **(extra or {})), ensure_ascii=False), encoding="utf-8")


class Estado:
    """Velas del día por acción: la base por consulta + las velas nuevas de la conexión."""

    def __init__(self):
        self.base: dict[str, pd.DataFrame] = {}
        self.nuevas: dict[str, dict[str, dict]] = {}   # símbolo -> {hora ISO -> vela}
        self.ultimo: dict[str, float] = {}
        self.sucio = False
        self.ultimo_mensaje = 0.0
        self.conectado, self.reconexiones, self.velas, self.hora_ultima_vela = False, 0, 0, None

    def poner_base(self, m: pd.DataFrame):
        self.base = {s: g for s, g in m.groupby("simbolo")} if len(m) else {}

    def mensaje(self, msgs: list[dict], ahora_ts: float):
        for x in msgs:
            tipo, s = x.get("T"), x.get("S")
            if tipo in ("b", "u") and s:      # vela de 1 min cerrada (o corregida)
                self.nuevas.setdefault(s, {})[x["t"]] = dict(simbolo=s, t=pd.Timestamp(x["t"]), o=x["o"], h=x["h"],
                                                             l=x["l"], c=x["c"], v=x["v"])
                self.ultimo[s] = x["c"]
                self.velas += 1
                self.hora_ultima_vela = x["t"]
                self.sucio, self.ultimo_mensaje = True, ahora_ts
            elif tipo == "t" and s:           # última operación: precio al instante
                self.ultimo[s] = x["p"]

    def por_sim(self, ahora: datetime | None = None) -> dict[str, pd.DataFrame]:
        """Velas por acción. Con `ahora`, si la última vela acaba de cerrarse se añade una vela «de entrada»
        sintética (precio = última operación): así la señal se ve en el MISMO segundo en que cierra la vela, sin
        esperar un minuto más a que cierre la vela de entrada."""
        out = {}
        for s in set(self.base) | set(self.nuevas):
            partes = []
            b = self.base.get(s)
            if b is not None and len(b):
                partes.append(b)
            if s in self.nuevas:
                n = pd.DataFrame(list(self.nuevas[s].values()))
                n["t"] = pd.to_datetime(n["t"], utc=True)
                if b is not None and len(b):
                    n = n[n["t"] > b["t"].max()]
                if len(n):
                    partes.append(n)
            if partes:
                m = pd.concat(partes, ignore_index=True).drop_duplicates("t", keep="last").sort_values("t")
                if ahora is not None:
                    minuto = pd.Timestamp(ahora).tz_convert("UTC").floor("min")
                    if m["t"].iloc[-1] + pd.Timedelta(minutes=1) == minuto:
                        px = float(self.ultimo.get(s, m["c"].iloc[-1]))
                        m = pd.concat([m, pd.DataFrame([dict(simbolo=s, t=minuto, o=px, h=px, l=px, c=px, v=0)])],
                                      ignore_index=True)
                out[s] = simular.preparar(m[["simbolo", "t", "o", "h", "l", "c", "v"]])
        return out


async def _conexion(estado: Estado, sims: list[str], parar: asyncio.Event):
    import websockets
    key, secret = _claves()
    while not parar.is_set():
        try:
            async with websockets.connect(WS, ping_interval=20, ping_timeout=20) as ws:
                await ws.recv()   # «connected»
                await ws.send(json.dumps({"action": "auth", "key": key, "secret": secret}))
                r = json.loads(await ws.recv())
                if not any(x.get("msg") == "authenticated" for x in r):
                    raise RuntimeError(f"Alpaca no deja entrar: {r}")
                await ws.send(json.dumps({"action": "subscribe", "bars": sims, "trades": sims}))
                estado.conectado = True
                print(f"Conectado: siguiendo {len(sims)} acciones", flush=True)
                while not parar.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        continue
                    estado.mensaje(json.loads(raw), asyncio.get_running_loop().time())
        except Exception as e:  # noqa: BLE001 - si se corta, se reconecta
            estado.conectado = False
            estado.reconexiones += 1
            if parar.is_set():
                return
            print(f"Conexión cortada ({e}); reconecto en 5 s", flush=True)
            await asyncio.sleep(5)


async def correr(cfg: dict, cfg_estudio: dict, datos, broker, ensayo: bool = False, cache: Path | None = None,
                 max_simbolos: int | None = None):
    D = cfg["demo"]
    loop = asyncio.get_running_loop()
    ahora = lambda: datetime.now(timezone.utc).astimezone(NY)  # noqa: E731
    fecha = ahora().strftime("%Y-%m-%d")
    hasta = datetime.strptime(fecha + " " + D["hasta"], "%Y-%m-%d %H:%M").replace(tzinfo=NY)
    # La apertura de hoy se conoce a las 9:30; se espera un par de minutos para tener la foto y las primeras velas
    inicio = datetime.strptime(fecha + " 09:32", "%Y-%m-%d %H:%M").replace(tzinfo=NY)
    while ahora() < inicio:
        await asyncio.sleep(5)
    if ahora() >= hasta:
        print("Fuera de ventana, no hago nada.")
        return
    if not ensayo and not broker.reloj().get("is_open"):
        print("La bolsa está cerrada (festivo): no hago nada.")
        return
    f = (cache or Path("datos_demo")) / f"candidatas-{fecha}.csv.gz"
    if f.exists():
        cands = universo.leer_csv(f)
    else:
        cands = await asyncio.to_thread(demo.candidatas_hoy, datos, fecha, cfg_estudio, max_simbolos)
        f.parent.mkdir(parents=True, exist_ok=True)
        cands.to_csv(f, index=False)
    if cands.empty:
        print("Sin candidatas hoy.")
        return
    sims = elegir(cands)
    estado, parar = Estado(), asyncio.Event()
    refrescar = lambda: demo.velas_hasta_ahora(datos, sims, fecha, ahora())  # noqa: E731
    estado.poner_base(await asyncio.to_thread(refrescar))
    tarea = asyncio.create_task(_conexion(estado, sims, parar))
    ultima_base, ultimo_latido, n = loop.time(), 0.0, 0
    try:
        while ahora() < hasta:
            await asyncio.sleep(0.5)
            if loop.time() - ultimo_latido > 30:
                latido(estado, sims, ahora(), dict(pasadas=n, ensayo=ensayo))
                ultimo_latido = loop.time()
            if loop.time() - ultima_base > 300:           # cada 5 min: historia al día (SIP hasta hace 16 min)
                estado.poner_base(await asyncio.to_thread(refrescar))
                ultima_base = loop.time()
            if estado.sucio and loop.time() - estado.ultimo_mensaje >= 1.5:   # ya llegaron las velas del minuto
                estado.sucio = False
                t0 = loop.time()
                filas = await asyncio.to_thread(demo.decidir, cfg, cands, estado.por_sim(ahora()), broker, ahora(), ensayo,
                                                D.get("senal_max_min_directo", 2), dict(estado.ultimo))
                n += 1
                if filas:
                    print(f"{ahora():%H:%M:%S} NY · {len(filas)} decisiones · {loop.time() - t0:.1f} s", flush=True)
    finally:
        latido(estado, sims, ahora(), dict(pasadas=n, ensayo=ensayo, fin=True))
        parar.set()
        await asyncio.wait([tarea], timeout=5)
    print(f"Fin de la ventana: {n} pasadas en directo.")


def ejecutar(cfg, cfg_estudio, datos, broker, ensayo=False, cache=None, max_simbolos=None):
    asyncio.run(correr(cfg, cfg_estudio, datos, broker, ensayo, cache, max_simbolos))
