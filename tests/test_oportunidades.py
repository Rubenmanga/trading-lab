from datetime import date

import numpy as np
import pandas as pd

from tradinglab.medio_plazo import metricas, oportunidades as op


def _fila(t, sector="Technology", **kw):
    base = dict(ticker=t, sector=sector, capitalizacion=1e9, caja=1e8, deuda=0, analistas=6,
                margen_bruto=0.4, margen_operativo=0.1, roe=0.1, roa=0.05, rent_fcf_pct=3, fcf_4t=3e7,
                fcf_trim_positivos=3, crec_ventas=0.1, crec_ventas_sig_anio=0.1, crec_bpa_sig_anio=0.1,
                per_futuro=20, ev_ventas=3, ev_ebitda=15, rent_fcf_menos_sbc_pct=2,
                rev_bpa_30d_anio=0, rev_bpa_90d_anio=0, rev_bpa_90d_sig=0, revisiones_suben_30d=1,
                revisiones_bajan_30d=1, ret_12m_1m=10, ret_6m=5, sobre_ma200_pct=2, dist_max52_pct=-10,
                dilucion_1a_pct=1, cortos_flotante=0.05, max_caida_1a_pct=-25)
    base.update(kw)
    return base


def test_percentiles_y_empates():
    assert op._percentiles([1, 2, 3, None], 1) == [0.0, 50.0, 100.0, None]
    assert op._percentiles([5, 5, 1], -1) == [25.0, 25.0, 100.0]


def test_la_mejor_gana_y_las_banderas_restan():
    filas = [_fila("BUENA", crec_ventas=0.4, crec_bpa_sig_anio=0.5, rev_bpa_90d_anio=12, rev_bpa_90d_sig=15,
                   revisiones_suben_30d=6, revisiones_bajan_30d=0, per_futuro=14, margen_operativo=0.2),
             _fila("NORMAL"),
             _fila("DILUYE", crec_ventas=0.4, crec_bpa_sig_anio=0.5, rev_bpa_90d_anio=12, rev_bpa_90d_sig=15,
                   revisiones_suben_30d=6, revisiones_bajan_30d=0, per_futuro=14, margen_operativo=0.2,
                   dilucion_1a_pct=30, fcf_4t=-4e7, caja=2e7)]
    r = op.puntuar(filas, hoy=date(2026, 11, 14))
    assert r[0]["ticker"] == "BUENA"
    d = next(f for f in r if f["ticker"] == "DILUYE")
    assert any("Dilución muy fuerte" in b for b in d["banderas"]) and any("Caja para menos de 12" in b for b in d["banderas"])
    assert d["nota"] < d["nota_base"]
    assert set(r[0]["factores"]) == set(op.FACTORES)


def test_sin_datos_no_rompe():
    r = op.puntuar([dict(ticker="X", capitalizacion=5e8), _fila("Y")])
    assert len(r) == 2 and all(0 <= f["nota"] <= 100 for f in r)


def test_tecnico_detecta_tendencia():
    n = 300
    idx = pd.date_range("2025-08-01", periods=n, freq="B")
    c = np.linspace(10, 30, n)
    h = pd.DataFrame(dict(Open=c, High=c * 1.01, Low=c * 0.99, Close=c, Volume=np.full(n, 1e6)), index=idx)
    t = metricas.tecnico(h)
    assert t["tendencia_fase2"] and t["ret_6m"] > 0 and t["dist_max52_pct"] > -2


def test_tendencia_recomendaciones():
    from tradinglab.medio_plazo.fuentes_extra import tendencia_recomendaciones
    recs = [dict(period="2026-11-01", strongBuy=3, buy=5, hold=2, sell=0, strongSell=0),
            dict(period="2026-10-01", strongBuy=2, buy=4, hold=4),
            dict(period="2026-09-01", strongBuy=2, buy=3, hold=5),
            dict(period="2026-08-01", strongBuy=1, buy=3, hold=6)]
    r = tendencia_recomendaciones(recs)
    assert r["recs_pct_compra"] == 80.0 and r["recs_cambio_3m"] == 40.0


def test_sin_claves_no_hace_nada(monkeypatch):
    from tradinglab.medio_plazo import fuentes_extra
    for k in ("FINNHUB_API_KEY", "ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert fuentes_extra.completar([{"ticker": "X"}]) == {"finnhub": False, "alpaca": False}


def test_partes_y_ranking_provisional(tmp_path):
    import json

    from tradinglab.medio_plazo import oportunidades as op
    lista = [{"ticker": t} for t in ("AAPL", "MSFT", "AEHR", "AMSC", "DFIN", "REPX", "IRWD", "ZZZ")]
    trozos = [op._parte(lista, k, 4) for k in range(4)]
    assert sorted(b["ticker"] for t in trozos for b in t) == sorted(b["ticker"] for b in lista)  # ni repetidas ni olvidadas
    assert op._parte(list(reversed(lista)), 2, 4) == trozos[2]  # el orden de llegada no importa
    r = tmp_path / "p.jsonl"
    filas = [{"ticker": "AAA", "errores": ["info: X"]}, {"ticker": "AAA", "errores": []},
             {"ticker": "BBB", "errores": [], "sector": "Technology", "capitalizacion": 1e9}]
    r.write_text("\n".join(json.dumps(f) for f in filas) + "\nlinea rota\n", encoding="utf-8")
    leidas = op.leer_partes([str(r)])
    assert len(leidas) == 2 and next(f for f in leidas if f["ticker"] == "AAA")["errores"] == []
    cfg = {"oportunidades": {"extra_top": 0}}
    res = op.combinar(cfg, leidas, universo_n=100)
    assert res["provisional"] is True and res["descargadas"] == 2 and res["analizadas"] == 1
