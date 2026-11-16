from datetime import date, datetime, time, timedelta

from tradinglab.medio_plazo import vigilante as vg

U = dict(separacion_sigmas=1.0, separacion_min_pct=5, volumen_rel=2.0, volumen_extremo=3.0,
         **{"acelerón_10m_pct": 3, "acelerón_10m_vol": 3.0})


def _dia(d, precio, vol, n=24, ultimo=None, vol_ult=None):
    out = []
    t0 = datetime.combine(d, time(9, 30), vg.NY)
    for i in range(n):
        out.append(dict(t=t0 + timedelta(minutes=5 * i), cierre=precio, volumen=vol))
    if ultimo:
        out[-1]["cierre"] = ultimo
        if vol_ult:
            out[-1]["volumen"] = vol_ult
            out[-2]["volumen"] = vol_ult
    return out


def test_medir_volumen_y_acelerón():
    hoy = date(2026, 11, 16)
    velas = []
    for k in range(10, 0, -1):
        velas += _dia(hoy - timedelta(days=k), 4.0, 1000)
    velas += _dia(hoy, 4.0, 1000, ultimo=4.4, vol_ult=5000)
    m = vg.medir(velas, 4.0, hoy, time(11, 30))
    assert m["cambio_pct"] == 10.0 and m["mov_10m_pct"] == 10.0
    assert m["volumen_rel_10m"] == 5.0 and m["volumen_rel"] > 1
    assert "ACELERÓN EN 10 MIN AL ALZA" in vg.avisos(m, 0.0, 7.6, U)


def test_sin_separacion_no_avisa():
    m = dict(cambio_pct=-3.0, volumen_rel=1.1, mov_10m_pct=-0.5, volumen_rel_10m=1.0)
    assert vg.avisos(m, -2.5, 7.6, U) == []
    m2 = dict(cambio_pct=-12.0, volumen_rel=2.5, mov_10m_pct=-0.5, volumen_rel_10m=1.0)
    assert vg.avisos(m2, -2.0, 7.6, U) == ["SE SEPARA DEL SECTOR A LA BAJA"]


def test_lectura_y_sigma():
    assert "Día normal" in vg.lectura([dict(exceso_pct=1.0, volumen_rel=1.0)])
    assert vg.sigma_diaria([10, 11, 10, 11, 10, 11, 10]) > 5
