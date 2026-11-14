from tradinglab.intradia.modelos import Senal
from tradinglab.intradia.riesgo import GestorRiesgo
from tradinglab.intradia.trailing import nuevo_stop

CFG = dict(stop_loss_pct=1.0, ratio_beneficio_riesgo=3.0, ratio_minimo=3.0, riesgo_por_operacion_pct=0.5,
           max_exposicion_por_operacion_pct=25, corte_perdida_diaria_pct=2.0, max_operaciones_dia=4,
           max_posiciones_abiertas=2)


def test_stop_1pct_y_objetivo_3R():
    g = GestorRiesgo(CFG)
    s = g.poner_stop_y_objetivo(Senal("X", "compra", 100.0, "t"))
    assert (s.stop, s.objetivo) == (99.0, 103.0)
    v = g.poner_stop_y_objetivo(Senal("X", "venta", 100.0, "t"))
    assert (v.stop, v.objetivo) == (101.0, 97.0)
    assert round(g.ratio(s), 2) == 3.0


def test_tamano_limitado_por_riesgo_y_exposicion():
    g = GestorRiesgo(CFG)
    s = g.poner_stop_y_objetivo(Senal("X", "compra", 100.0, "t"))
    # riesgo: 10000*0.5% = 50$ / 1$ = 50 acciones; exposición: 25% de 10000 / 100 = 25 acciones
    assert g.tamano(10_000, s) == 25


def test_corte_diario_y_maximos():
    g = GestorRiesgo(CFG)
    assert g.puede_operar(10_000, 9_790, 0, 0)[0] is False
    assert g.puede_operar(10_000, 10_000, 4, 0)[0] is False
    assert g.puede_operar(10_000, 10_000, 0, 2)[0] is False
    assert g.puede_operar(10_000, 9_900, 1, 1)[0] is True


def test_trailing_no_se_activa_antes_de_1R_y_nunca_empeora():
    assert nuevo_stop("compra", 100, 99, 99, 100.5, 1.0, 1.0) == 99
    assert nuevo_stop("compra", 100, 99, 99, 101.0, 1.0, 1.0) == 100     # a precio de entrada
    assert nuevo_stop("compra", 100, 99, 100, 103.0, 1.0, 1.0) == 101.97  # sigue al precio
    assert nuevo_stop("compra", 100, 99, 101.97, 102.0, 1.0, 1.0) == 101.97
    assert nuevo_stop("venta", 100, 101, 101, 98.0, 1.0, 1.0) == 98.98
