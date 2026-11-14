"""El motor del agente intradía. Lo usan igual el backtest, la demo y la sesión en vivo.

Flujo de cada señal (todo queda apuntado con su motivo):
  1. Reglas fijas    -> horario, ratio beneficio/riesgo, ya hay posición...
  2. Gestor de riesgo -> corte de pérdida diaria, máximo de operaciones, tamaño
  3. Analista IA     -> opina (modo sombra) o puede frenar (modo veto)
  4. Ejecución       -> orden con stop y objetivo; luego trailing stop
"""
from __future__ import annotations

from ..common.db import DB, ahora
from . import reglas
from .estrategias import Estrategia
from .modelos import Senal
from .riesgo import GestorRiesgo
from .trailing import nuevo_stop


class Motor:
    def __init__(self, cfg: dict, estrategia: Estrategia, broker, db: DB, revisor, origen: str):
        self.cfg, self.estrategia, self.broker, self.db, self.revisor = cfg, estrategia, broker, db, revisor
        self.origen = origen
        self.riesgo = GestorRiesgo(cfg["riesgo"])
        self.trail = cfg.get("trailing", {"activo": False})
        self.ia_modo = cfg["ia"]["modo"]
        self.ops_hoy = 0
        self.abiertas: dict[str, dict] = {}   # simbolo -> datos de la operación abierta

    # ---------- día ----------
    def nuevo_dia(self):
        self.ops_hoy = 0
        self.broker.nuevo_dia()

    # ---------- velas ----------
    def nueva_vela(self, simbolo: str, velas, ctx: dict):
        """Llamar cada vez que cierra una vela. `velas` incluye la vela recién cerrada al final."""
        vela = velas.iloc[-1]
        for cierre in self.broker.procesar_vela(simbolo, vela):
            self._registrar_cierre(cierre, ts=ctx.get("ts"))
        if simbolo in self.abiertas:
            self._trailing(simbolo, vela)
        s = self.estrategia.senal(simbolo, velas)
        if s is not None:
            if ctx.get("ts") is not None:
                s.ts = ctx["ts"]
            self.procesar_senal(s, ctx)

    # ---------- tubería ----------
    def procesar_senal(self, s: Senal, ctx: dict):
        self.riesgo.poner_stop_y_objetivo(s)
        ctx = {**ctx, "ya_hay_posicion": s.simbolo in self.abiertas or s.simbolo in self.broker.posiciones()}
        traza = []

        def frenar(capa, motivo, ia=None):
            self._decision(s, "FRENADA", capa, motivo, ia, traza)
            return None

        r1 = reglas.revisar(s, self.riesgo.ratio(s), self.riesgo.rr_min, ctx)
        traza.append(r1.__dict__)
        if not r1.pasa:
            return frenar("reglas", r1.motivo)

        ok, motivo = self.riesgo.puede_operar(self.broker.capital_inicio_dia(), self.broker.capital(),
                                              self.ops_hoy, len(self.abiertas))
        if not ok:
            return frenar("riesgo", motivo)
        cantidad = self.riesgo.tamano(self.broker.capital(), s)
        if cantidad < 1:
            return frenar("riesgo", "El tamaño calculado es menor que 1 acción")

        ia = self.revisor.revisar(s, {k: v for k, v in ctx.items() if k != "ts"})
        traza.append(ia.__dict__)
        if not ia.pasa and self.ia_modo == "veto":
            return frenar("ia", ia.motivo, ia)
        nota = "" if ia.pasa else f" [sombra: la IA habría frenado: {ia.motivo}]"

        broker_id, precio = self.broker.abrir(s, cantidad)
        self.ops_hoy += 1
        dec_id = self._decision(s, "PASADA", "ejecucion", f"Orden {broker_id}, {cantidad} acciones{nota}", ia, traza)
        op_id = self.db.insertar(
            "operaciones", decision_id=dec_id, origen=self.origen, broker_id=broker_id, simbolo=s.simbolo,
            lado=s.lado, cantidad=cantidad, entrada=precio, stop_inicial=s.stop, stop_actual=s.stop,
            objetivo=s.objetivo, ts_apertura=str(s.ts))
        self.abiertas[s.simbolo] = dict(id=op_id, broker_id=broker_id, lado=s.lado, cantidad=cantidad,
                                        entrada=precio, stop_inicial=s.stop, stop=s.stop, mejor=precio)
        return broker_id

    # ---------- gestión de posiciones ----------
    def _trailing(self, simbolo, vela):
        if not self.trail.get("activo"):
            return
        op = self.abiertas[simbolo]
        op["mejor"] = max(op["mejor"], float(vela["high"])) if op["lado"] == "compra" else min(op["mejor"], float(vela["low"]))
        stop = nuevo_stop(op["lado"], op["entrada"], op["stop_inicial"], op["stop"], op["mejor"],
                          self.trail["activar_en_R"], self.trail["distancia_pct"])
        if stop != op["stop"]:
            op["stop"] = stop
            self.broker.actualizar_stop(simbolo, stop)
            self.db.actualizar("operaciones", op["id"], stop_actual=stop)

    def sincronizar(self, ts=None):
        for cierre in self.broker.sincronizar(self.abiertas):
            self._registrar_cierre(cierre, ts)

    def cerrar_todo(self, precios: dict[str, float], motivo: str, ts=None):
        for cierre in self.broker.cerrar_todo(precios, motivo):
            self._registrar_cierre(cierre, ts)

    def _registrar_cierre(self, cierre: dict, ts=None):
        op = self.abiertas.pop(cierre["simbolo"], None)
        if not op:
            return
        signo = 1 if op["lado"] == "compra" else -1
        por_accion = signo * (cierre["salida"] - op["entrada"])
        riesgo = abs(op["entrada"] - op["stop_inicial"]) or 1e-9
        motivo = cierre["motivo"]
        if motivo == "stop" and op["stop"] != op["stop_inicial"]:
            motivo = "trailing stop"
        self.db.actualizar("operaciones", op["id"], ts_cierre=str(ts or ahora()), salida=cierre["salida"],
                           motivo_salida=motivo, pnl=round(por_accion * op["cantidad"], 2),
                           r_multiple=round(por_accion / riesgo, 2))

    def _decision(self, s: Senal, resultado, capa, motivo, ia, traza):
        return self.db.insertar(
            "decisiones", ts=str(s.ts), origen=self.origen, simbolo=s.simbolo, lado=s.lado,
            estrategia=s.estrategia, entrada=s.entrada, stop=s.stop, objetivo=s.objetivo,
            resultado=resultado, capa=capa, motivo=motivo, ia_modo=self.ia_modo,
            ia_veredicto=(ia.extra.get("veredicto") if ia else None), ia_motivo=(ia.motivo if ia else None),
            detalle=traza)
