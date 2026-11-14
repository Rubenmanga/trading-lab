import json

from tradinglab.medio_plazo import seguimiento

NIV = dict(soporte=[7.2, 7.5], confirmacion=9.3, entrada_max=8.5, stop=6.5, objetivo=13)


def _velas(cierres, vol=1e6, ultima=None):
    out = []
    for i, c in enumerate(cierres):
        out.append(dict(fecha=f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", apertura=c * 1.01, maximo=c * 1.02,
                        minimo=c * 0.98, cierre=c, volumen=vol))
    if ultima:
        out[-1].update(ultima)
    return out


def test_caida_sin_freno_es_esperar():
    v = _velas([13 - i * 0.07 for i in range(70)])        # baja todos los días
    ev = seguimiento.evaluar(v, NIV)
    assert ev["estado"] == "ESPERAR"
    assert not ev["senales"]


def test_senal_b_confirmacion():
    v = _velas([8.0] * 60 + [9.5, 9.6])
    ev = seguimiento.evaluar(v, NIV)
    assert ev["estado"] == "SEÑAL DE ENTRADA"
    assert any(s["tipo"] == "B" for s in ev["senales"])


def test_senal_a_suelo_en_soporte():
    cierres = [12 - i * 0.1 for i in range(45)] + [7.6, 7.45, 7.35, 7.3]
    v = _velas(cierres)
    # vela de giro: abre en mínimos, cierra arriba, con volumen doble
    v.append(dict(fecha="2026-12-30", apertura=7.25, maximo=7.75, minimo=7.22, cierre=7.7, volumen=2.5e6))
    ev = seguimiento.evaluar(v, NIV)
    assert ev["toca_soporte"] and ev["vela_giro"]
    assert any(s["tipo"] == "A" for s in ev["senales"])


def test_stop_y_soporte_perdido():
    ev = seguimiento.evaluar(_velas([8.0] * 60 + [6.3]), NIV)
    assert ev["estado"] == "PELIGRO"
    ev2 = seguimiento.evaluar(_velas([8.0] * 60 + [7.0], ultima=None)[:-1]
                              + [dict(fecha="2026-12-30", apertura=7.3, maximo=7.4, minimo=6.9, cierre=7.0, volumen=3e6)], NIV)
    assert any(a["tipo"] == "SOPORTE PERDIDO" for a in ev2["avisos"])


def test_ejecutar_escribe_informe_y_aviso(tmp_path, monkeypatch):
    monkeypatch.setattr(seguimiento, "ruta", lambda *p: str(tmp_path.joinpath(*p)))
    (tmp_path / "investigacion").mkdir()
    (tmp_path / "investigacion" / "estado.json").write_text(json.dumps({"alertas": [], "precios": []}))
    cfg = {"seguimiento": {"ZZZ": NIV}}
    res = seguimiento.ejecutar(cfg, velas_de=lambda t: _velas([8.0] * 60 + [9.5, 9.6]), extra_de=lambda t: {})
    assert res["empresas"]["ZZZ"]["estado"] == "SEÑAL DE ENTRADA"
    md = (tmp_path / "investigacion" / "seguimiento" / "ZZZ.md").read_text()
    assert md.startswith("# Seguimiento diario de ZZZ") and "Resumen (5 líneas)" in md
    est = json.loads((tmp_path / "investigacion" / "estado.json").read_text())
    assert any(a["tipo"] == "SEÑAL DE ENTRADA" and a["seguimiento"] for a in est["alertas"])
