"""Pruebas del investigador diario sin modelos generativos ni conexión a bolsa."""
import csv
import json
from datetime import date

import pytest

from tradinglab.medio_plazo import investigador_auto as auto, propuestas


DIA = date(2026, 11, 17)
CARPETA = """# Carpeta del día · 17/11/2026

_Resumen automático, sin IA. Precios y avisos del 2026-11-17 05:16 UTC._

## 🔔 Avisos de hoy
- **ZONA DE ENTRADA** · REPX a 43.56 $ está en su zona de entrada
- **CATALIZADOR CERCA** · SVRA: decisión FDA 22/11
- **CATALIZADOR CERCA** · SSII: retraso 10-Q y posible FDA

## 📰 Hechos nuevos
- 16/11 **RCAT** · Cuentas del trimestre (10-Q)

## 🎯 Dentro de su zona de entrada
- **AMPX** a 7.12 $ ≤ zona 9.5, objetivo 11.5, stop 6.8 · vigilar
- **TE** a 1.49 $ ≤ zona 2.1, objetivo 2.4, stop 1.35 · vigilar
- **SVRA** a 4.47 $ ≤ zona 4.8, objetivo 8, stop 4.1 · vigilar
- **SSII** a 1.35 $ ≤ zona 2.6, objetivo 2.2, stop 1.2 · vigilar
"""
WATCH = [
    dict(ticker="REPX", veredicto="comprar_en_zona", zona_entrada_max="46",
         precio_objetivo_12m="58", stop_tesis="36"),
    dict(ticker="RCAT", veredicto="vigilar", zona_entrada_max="5",
         precio_objetivo_12m="6", stop_tesis="3.2"),
    dict(ticker="AMPX", veredicto="vigilar", zona_entrada_max="9.5",
         precio_objetivo_12m="11.5", stop_tesis="6.8"),
    dict(ticker="TE", veredicto="vigilar", zona_entrada_max="2.1",
         precio_objetivo_12m="2.4", stop_tesis="1.35"),
    dict(ticker="SSII", veredicto="vigilar", zona_entrada_max="2.6",
         precio_objetivo_12m="2.2", stop_tesis="1.2",
         proximo_catalizador="Decisión FDA 510(k)", fecha_catalizador="2026-11-23"),
    dict(ticker="SVRA", veredicto="vigilar", zona_entrada_max="4.8",
         precio_objetivo_12m="8", stop_tesis="4.1",
         proximo_catalizador="Decisión FDA; apuesta binaria", fecha_catalizador="2026-11-22"),
]
ESTADO = {
    "actualizado": "2026-11-17T05:16:18+00:00",
    "precios": [{"ticker": t, "precio": p} for t, p in [
        ("REPX", 43.56), ("RCAT", 3.53), ("AMPX", 7.12),
        ("TE", 1.49), ("SSII", 1.35), ("SVRA", 4.47),
    ]],
}


def test_crea_cinco_vigilancias_sin_emitir_compras():
    texto, avisos = auto.construir(
        DIA, CARPETA, ESTADO, WATCH, {"REPX": {"entrada": 39.75}}, []
    )
    assert not avisos
    assert texto is not None
    filas, errores = propuestas.validar(texto)
    assert errores == [] and len(filas) == 5
    assert all(f["idea"] != "comprar_en_zona" for f in filas)
    por_ticker = {f["ticker"]: f for f in filas}
    assert por_ticker["REPX"]["entrada"] == 39.75  # no usar la zona 46 en vez de calculadora
    assert por_ticker["SVRA"]["idea"] == "evitar"
    assert por_ticker["SSII"]["idea"] == "evitar"


def test_rechaza_datos_antiguos_y_futuros():
    with pytest.raises(ValueError, match="desactualizado"):
        auto.construir(date(2026, 11, 21), CARPETA, ESTADO, WATCH, {}, [])
    with pytest.raises(ValueError, match="futuro"):
        auto.construir(date(2026, 11, 16), CARPETA, ESTADO, WATCH, {}, [])


def test_no_fabrica_tres_ideas_si_solo_hay_dos():
    texto, motivos = auto.construir(DIA, CARPETA, ESTADO, WATCH[:2], {}, [])
    assert texto is None
    assert any("no se fuerzan" in x for x in motivos)


def test_no_repite_propuestas_de_los_ultimos_treinta_dias():
    ya = [{"id": "PROP-2026-11-16-REPX", "ticker": "REPX", "fecha": "2026-11-16"}]
    texto, _ = auto.construir(DIA, CARPETA, ESTADO, WATCH, {}, ya)
    assert texto is not None
    assert "| REPX |" not in texto
    assert len(propuestas.validar(texto)[0]) == 5


def test_ejecucion_registra_en_el_libro_una_vez(tmp_path):
    inv = tmp_path / "investigacion"
    inv.mkdir()
    (inv / "hoy.md").write_text(CARPETA, encoding="utf-8")
    (inv / "estado.json").write_text(json.dumps(ESTADO), encoding="utf-8")
    (inv / "entradas.json").write_text(json.dumps({"REPX": {"entrada": 39.75}}), encoding="utf-8")
    with (inv / "watchlist.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list({k for x in WATCH for k in x}))
        w.writeheader()
        w.writerows(WATCH)

    primera = auto.ejecutar(DIA, tmp_path)
    assert primera["estado"] == "creado" and primera["añadidas"] == 5
    segunda = auto.ejecutar(DIA, tmp_path)
    assert segunda["estado"] == "existente" and segunda["añadidas"] == 0
    assert len(auto._csv(inv / "predicciones.csv")) == 5
