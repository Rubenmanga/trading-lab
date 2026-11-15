"""Cliente mínimo de la API pública de eToro, SOLO CUENTA DEMO.

Lista blanca de rutas: solo datos de mercado y las rutas de trading que llevan /demo/.
Las rutas de dinero real (las mismas sin /demo/) están prohibidas aquí: el cliente se niega a llamarlas.
Claves por variables de entorno (secretos de GitHub): ETORO_API_KEY, ETORO_USER_KEY. Nunca se imprimen.
"""
from __future__ import annotations

import os
import time
import uuid

import requests

BASE = "https://public-api.etoro.com"
GET_PERMITIDAS = (
    "/api/v2/market-data/instruments",
    "/api/v2/market-data/rates",
    "/api/v1/trading/info/demo/",
    "/api/v2/trading/info/demo/",
)
POST_PERMITIDAS = (
    "/api/v2/trading/info/demo/eligibility",
    "/api/v2/trading/execution/demo/orders",
    "/api/v1/trading/execution/demo/market-close-orders/positions/",
)


def ruta_permitida(metodo: str, ruta: str) -> bool:
    if "/real" in ruta.lower():
        return False
    if metodo == "GET":
        return ruta.startswith(GET_PERMITIDAS)
    return ruta.startswith(POST_PERMITIDAS) and "/demo/" in ruta


class EToroDemo:
    def __init__(self, sesion: requests.Session | None = None):
        if os.getenv("ETORO_DEMO", "true").strip().lower() != "true":
            raise SystemExit("ETORO_DEMO debe ser 'true'. Este proyecto no opera con dinero real.")
        self.k = os.getenv("ETORO_API_KEY", "").strip()
        self.u = os.getenv("ETORO_USER_KEY", "").strip()
        if not self.k or not self.u:
            raise SystemExit("Faltan los secretos ETORO_API_KEY y ETORO_USER_KEY (cuenta demo).")
        self.s = sesion or requests.Session()

    def _llamar(self, metodo: str, ruta: str, **kw):
        if not ruta_permitida(metodo, ruta):
            raise SystemExit(f"Ruta no permitida (solo demo): {metodo} {ruta}")
        for intento in range(5):
            cab = {"x-api-key": self.k, "x-user-key": self.u, "x-request-id": str(uuid.uuid4())}
            try:
                r = self.s.request(metodo, BASE + ruta, headers=cab, timeout=30, **kw)
            except requests.RequestException:
                time.sleep(2 * (intento + 1))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 3 * (intento + 1))))
                continue
            return r
        raise RuntimeError(f"eToro no responde: {metodo} {ruta}")

    # ------------------------------------------------------------------ datos
    def instrumento(self, simbolo: str) -> int | None:
        r = self._llamar("GET", "/api/v2/market-data/instruments", params={"symbols": simbolo})
        if not r.ok:
            return None
        for inst in _lista(r.json()):
            sim = next((str(inst[k]) for k in ("symbol", "symbolFull", "internalSymbolFull", "ticker") if inst.get(k)), "")
            if sim.upper().split(".")[0] == simbolo.upper():
                iid = inst.get("instrumentId") or inst.get("instrumentID") or inst.get("id")
                return int(iid) if iid else None
        return None

    def corto_permitido(self, iid: int) -> dict:
        """¿Deja eToro abrir un corto (CFD) en este instrumento? Devuelve {ok, apalancamientos, stop_min, stop_max, forma}."""
        r = self._llamar("POST", "/api/v2/trading/info/demo/eligibility", json={"instrumentIds": [iid], "currency": "USD"})
        if not r.ok:
            return {"ok": False, "motivo": f"elegibilidad HTTP {r.status_code}"}
        elig = (r.json().get("eligibilities") or [{}])[0]
        cortos = [c for c in (elig.get("leverageConfigs") or []) if str(c.get("direction", "")).lower() == "short"]
        if not cortos:
            return {"ok": False, "motivo": "eToro no permite corto en esta acción"}
        lev = set()
        for c in cortos:
            for k in ("leverage", "leverages", "allowedLeverages", "availableLeverages", "defaultLeverage"):
                v = c.get(k)
                if isinstance(v, (int, float)):
                    lev.add(int(v))
                elif isinstance(v, list):
                    lev |= {int(x) for x in v if isinstance(x, (int, float))}
        mins = [c["minStopLossPercentage"] for c in cortos if c.get("minStopLossPercentage") is not None]
        maxs = [c["maxStopLossPercentage"] for c in cortos if c.get("maxStopLossPercentage") is not None]
        return {"ok": True, "apalancamientos": sorted(lev), "stop_min": min(mins) if mins else None,
                "stop_max": max(maxs) if maxs else None, "forma": sorted(cortos[0].keys())}

    def precios(self, ids: list[int]) -> dict[int, dict]:
        r = self._llamar("GET", "/api/v2/market-data/rates", params={"instrumentIds": ",".join(str(i) for i in ids)})
        if r.status_code not in (200, 206):
            return {}
        return {int(x["instrumentId"]): x for x in r.json().get("results", []) if x.get("instrumentId") is not None}

    def cartera(self) -> tuple[float, list[dict]]:
        """(crédito libre en $, posiciones abiertas) de la cuenta demo."""
        r = self._llamar("GET", "/api/v1/trading/info/demo/portfolio")
        r.raise_for_status()
        cp = r.json().get("clientPortfolio") or {}
        return float(cp.get("credit") or 0), list(cp.get("positions") or [])

    # ------------------------------------------------------------------ órdenes (demo)
    def abrir_corto(self, iid: int, importe: float, stop: float, apalancamiento: int = 1) -> dict:
        cuerpo = {"action": "open", "transaction": "sellShort", "instrumentId": iid, "settlementType": "cfd",
                  "orderType": "mkt", "leverage": int(apalancamiento), "amount": round(importe, 2),
                  "orderCurrency": "usd", "stopLossRate": round(stop, 4), "stopLossType": "fixed"}
        r = self._llamar("POST", "/api/v2/trading/execution/demo/orders", json=cuerpo)
        if not r.ok:
            return {"ok": False, "motivo": f"orden rechazada HTTP {r.status_code}: {r.text[:300]}"}
        j = r.json()
        return {"ok": True, "orderId": j.get("orderId"), "referenceId": j.get("referenceId")}

    def consultar_orden(self, order_id) -> dict:
        r = self._llamar("GET", "/api/v2/trading/info/demo/orders:lookup", params={"orderId": order_id})
        return r.json() if r.ok else {"error": r.status_code}

    def cerrar(self, position_id: int, iid: int) -> dict:
        r = self._llamar("POST", f"/api/v1/trading/execution/demo/market-close-orders/positions/{int(position_id)}",
                         json={"InstrumentID": int(iid), "UnitsToDeduct": None})
        return {"ok": r.ok, "motivo": "" if r.ok else f"HTTP {r.status_code}: {r.text[:300]}"}


def _lista(datos) -> list[dict]:
    if isinstance(datos, list):
        return [d for d in datos if isinstance(d, dict)]
    if isinstance(datos, dict):
        for v in datos.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        for v in datos.values():
            if isinstance(v, dict) and (sub := _lista(v)):
                return sub
    return []


def buscar_clave(datos, nombres: tuple[str, ...]):
    """Primer valor de cualquiera de esas claves, buscando en todo el JSON (las respuestas cambian de forma)."""
    if isinstance(datos, dict):
        for k, v in datos.items():
            if k in nombres and v not in (None, ""):
                return v
        for v in datos.values():
            if (x := buscar_clave(v, nombres)) is not None:
                return x
    elif isinstance(datos, list):
        for v in datos:
            if (x := buscar_clave(v, nombres)) is not None:
                return x
    return None
