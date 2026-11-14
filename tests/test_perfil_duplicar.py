"""Pruebas sin internet del perfil «¿puede duplicar?»."""
from tradinglab.common.config import cargar
from tradinglab.perfiles.duplicar import evaluar, racha_mejora


def test_racha_mejora():
    assert racha_mejora([["q1", -10], ["q2", -8], ["q3", -5]]) == 2
    assert racha_mejora([["q1", -5], ["q2", -8], ["q3", -6]]) == 1
    assert racha_mejora(None) == 0


def _fila(**kw):
    f = dict(ticker="X", precio=11.6, analistas=12, potencial_analistas_pct=150,
             duplicar=dict(trimestres_mejorando=2, rachas={}, meses_caja=36, acciones_nuevas_12m_pct=3, deuda_sobre_caja=0.2))
    f.update(kw)
    return f


def test_cumple_todo_y_falla_sin_relajar():
    c = cargar("perfil_duplicar")["criterios"]
    assert evaluar(_fila(), c, 1.16)["cumple_todo"]
    # 9 analistas no vale aunque el potencial sea enorme
    assert not evaluar(_fila(analistas=9, potencial_analistas_pct=300), c, 1.16)["criterios"]["objetivo_100_10_analistas"]["cumple"]
    # precio en euros: 30 $ / 1.16 = 25.9 € → fuera
    assert not evaluar(_fila(precio=30), c, 1.16)["criterios"]["precio_5_25_eur"]["cumple"]
    # mucha dilución
    d = _fila()["duplicar"] | {"acciones_nuevas_12m_pct": 25}
    assert not evaluar(_fila(duplicar=d), c, 1.16)["criterios"]["poca_dilucion"]["cumple"]
