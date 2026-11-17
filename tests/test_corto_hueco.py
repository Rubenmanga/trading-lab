from datetime import datetime

import pandas as pd
import pytest

from tradinglab.common import config
from tradinglab.intradia.corto_hueco import escaner, etoro, riesgo, sesion

NY = sesion.NY
CFG = config.cargar("corto_hueco")


def test_solo_rutas_demo():
    assert etoro.ruta_permitida("POST", "/api/v2/trading/execution/demo/orders")
    assert etoro.ruta_permitida("POST", "/api/v1/trading/execution/demo/market-close-orders/positions/5")
    assert not etoro.ruta_permitida("POST", "/api/v2/trading/execution/orders")          # dinero real
    assert not etoro.ruta_permitida("POST", "/api/v1/trading/execution/market-close-orders/positions/5")
    assert not etoro.ruta_permitida("GET", "/api/v1/trading/info/real/portfolio")
    assert etoro.ruta_permitida("GET", "/api/v1/trading/info/demo/portfolio")


def test_cliente_se_niega_sin_demo(monkeypatch):
    monkeypatch.setenv("ETORO_DEMO", "false")
    with pytest.raises(SystemExit):
        etoro.EToroDemo()


def test_tamano_y_stop():
    imp, _ = riesgo.tamano(100_000, 100_000, 0, 15, CFG)
    assert imp == pytest.approx(6666.67, abs=0.01)           # 1 % de riesgo con stop 15 %
    imp, motivo = riesgo.tamano(100_000, 100_000, 29_990, 15, CFG)
    assert imp == 0 and "pequeño" in motivo                 # exposición máxima del 30 % ya usada
    assert riesgo.precio_stop(10, 15) == 11.5              # en corto el stop va por encima
    assert riesgo.freno_activado(89_000, 100_000, CFG) and not riesgo.freno_activado(95_000, 100_000, CFG)
    assert riesgo.stop_ajustado(15, None, 10) == 10


class AlpacaFalsa:
    def __init__(self):
        self.llamadas = 0

    def _get(self, url, params):
        if url.endswith("/v2/clock"):
            return {"is_open": True}
        return {"AAA": {"prevDailyBar": {"c": 2.0}, "dailyBar": {"o": 3.4, "t": "2026-11-16T05:00:00Z"},
                        "latestTrade": {"p": 3.2}},
                "BBB": {"prevDailyBar": {"c": 10.0}, "dailyBar": {"o": 10.5, "t": "2026-11-16T05:00:00Z"},
                        "latestTrade": {"p": 10.4}}}

    def valores(self):
        return [{"symbol": s, "status": "active", "tradable": True, "exchange": "NASDAQ"} for s in ("AAA", "BBB")]

    def velas(self, sims, tf, desde, hasta):
        t = pd.date_range("2026-10-20", periods=20, freq="B", tz="UTC")
        return pd.concat([pd.DataFrame({"simbolo": s, "t": t, "o": 2.0, "h": 2.1, "l": 1.9, "c": 2.0, "v": 500_000})
                          for s in sims], ignore_index=True)


class EToroFalso:
    def __init__(self):
        self.ordenes, self.cierres = [], []
        self.posiciones = []

    def cartera(self):
        return 100_000.0, list(self.posiciones)

    def instrumento(self, s):
        return {"AAA": 77}.get(s)

    def corto_permitido(self, iid):
        return {"ok": True, "apalancamientos": [1], "stop_min": 0, "stop_max": None, "forma": []}

    def precios(self, ids):
        return {77: {"instrumentId": 77, "bid": 3.3, "ask": 3.31, "quoteType": "realtime"}}

    def abrir_corto(self, iid, importe, stop, lev=1):
        self.ordenes.append((iid, importe, stop))
        self.posiciones.append({"positionID": 999, "instrumentID": iid, "isBuy": False, "amount": importe, "openRate": 3.3})
        return {"ok": True, "orderId": 1}

    def cerrar(self, pid, iid):
        self.cierres.append(pid)
        return {"ok": True, "motivo": ""}


@pytest.fixture()
def carpeta_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(sesion, "carpeta", lambda: tmp_path)
    return tmp_path


def test_escaner_encuentra_el_hueco():
    c = escaner.candidatos(AlpacaFalsa(), CFG, datetime(2026, 11, 16, 9, 34, tzinfo=NY))
    assert [x["simbolo"] for x in c] == ["AAA"] and c[0]["hueco"] == pytest.approx(0.7)


def test_operar_y_cerrar(carpeta_tmp):
    reloj = [datetime(2026, 11, 16, 9, 10, tzinfo=NY)]

    def dormir(s):
        reloj[0] = reloj[0] + pd.Timedelta(seconds=s)

    et = EToroFalso()
    d = sesion.operar(CFG, AlpacaFalsa(), et, reloj=lambda: reloj[0], dormir=dormir)
    assert len(et.ordenes) == 1 and et.ordenes[0][2] == pytest.approx(3.31 * 1.15, abs=1e-3)
    assert reloj[0] >= datetime(2026, 11, 16, 9, 35, tzinfo=NY)            # esperó a las 9:35
    assert any(f["accion"] == "abierta" for f in d.filas)
    assert (carpeta_tmp / "registro.csv").exists() and (carpeta_tmp / "aviso.md").exists()
    # una segunda ejecución el mismo día no repite
    sesion.operar(CFG, AlpacaFalsa(), et, reloj=lambda: reloj[0], dormir=dormir)
    assert len(et.ordenes) == 1
    # antes de la hora de cierre no cierra; después sí
    sesion.cerrar(CFG, et, reloj=lambda: datetime(2026, 11, 16, 12, 0, tzinfo=NY))
    assert et.cierres == []
    sesion.cerrar(CFG, et, reloj=lambda: datetime(2026, 11, 16, 15, 47, tzinfo=NY))
    assert et.cierres == [999] and sesion.leer_estado()["abiertas"] == []


def test_fuera_de_ventana_no_hace_nada(carpeta_tmp):
    et = EToroFalso()
    sesion.operar(CFG, AlpacaFalsa(), et, reloj=lambda: datetime(2026, 11, 16, 10, 5, tzinfo=NY), dormir=lambda s: None)
    sesion.operar(CFG, AlpacaFalsa(), et, reloj=lambda: datetime(2026, 11, 15, 9, 20, tzinfo=NY), dormir=lambda s: None)  # domingo
    assert et.ordenes == []


def test_ensayo_no_envia_ordenes(carpeta_tmp):
    et = EToroFalso()
    d = sesion.operar(CFG, AlpacaFalsa(), et, ensayo=True, simbolos=["AAA"],
                      reloj=lambda: datetime(2026, 11, 16, 9, 34, tzinfo=NY), dormir=lambda s: None)
    assert et.ordenes == [] and any(f["accion"] == "ensayo" for f in d.filas)


class AlpacaDosHuecos(AlpacaFalsa):
    def _get(self, url, params):
        if url.endswith("/v2/clock"):
            return {"is_open": True}
        barra = {"prevDailyBar": {"c": 2.0}, "dailyBar": {"o": 3.4, "t": "2026-11-16T05:00:00Z"}, "latestTrade": {"p": 3.2}}
        return {"AAA": barra, "BBB": barra}


class EToroFallaEnLaSegunda(EToroFalso):
    def instrumento(self, s):
        if s == "AAA":
            return 77
        raise ValueError("respuesta rara de eToro")


def test_un_fallo_no_pierde_la_posicion_ya_abierta(carpeta_tmp):
    """Auditoría 17-nov (D2): si eToro falla con la 2.ª candidata, la 1.ª ya abierta queda apuntada para cerrarla."""
    et = EToroFallaEnLaSegunda()
    ahora = datetime(2026, 11, 16, 9, 36, tzinfo=NY)
    d = sesion.operar(CFG, AlpacaDosHuecos(), et, reloj=lambda: ahora, dormir=lambda s: None)
    assert len(et.ordenes) == 1
    assert [a["simbolo"] for a in sesion.leer_estado()["abiertas"]] == ["AAA"]
    assert any(f["accion"] == "error" and f["simbolo"] == "BBB" for f in d.filas)
    assert (carpeta_tmp / "registro.csv").exists() and "BBB" in (carpeta_tmp / "aviso.md").read_text(encoding="utf-8")
    sesion.cerrar(CFG, et, reloj=lambda: datetime(2026, 11, 16, 15, 47, tzinfo=NY))
    assert et.cierres == [999]


def test_sin_cartera_no_abre_y_lo_apunta(carpeta_tmp):
    class SinCartera(EToroFalso):
        def cartera(self):
            raise RuntimeError("eToro no responde")

    et = SinCartera()
    d = sesion.operar(CFG, AlpacaFalsa(), et, reloj=lambda: datetime(2026, 11, 16, 9, 36, tzinfo=NY), dormir=lambda s: None)
    assert et.ordenes == [] and any(f["accion"] == "error" for f in d.filas) and (carpeta_tmp / "aviso.md").exists()
