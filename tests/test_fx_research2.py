"""Pruebas de invariantes de estrategia del Agente C FX v2."""
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest

from tradinglab.fx.research2 import NAMES, prepare, signals, simulate, summarize


def synthetic(n=600):
    # Datos sintéticos SOLO para tests del SOFTWARE, nunca para presumir beneficios.
    start=datetime(2026,11,2,0,tzinfo=timezone.utc)
    rows=[]
    for i in range(n):
        p=1.1 + .0003*np.sin(i/7) + .000002*i
        rows.append({"timestamp":start+timedelta(minutes=5*i),
                     "open":p,"high":p+.00015,"low":p-.00015,
                     "close":p+.00001,"spread_pips":.5})
    return pd.DataFrame(rows)


def test_all_twelve_hypotheses_and_data_integrity():
    f=prepare(synthetic())
    s=signals(f)
    assert set(s.columns)==set(NAMES)
    assert all(x in (-1,0,1) for x in np.unique(s.to_numpy()))
    assert s.iloc[:200].to_numpy().sum()==0


def test_no_future_data_affects_past_signal():
    d=synthetic()
    f=prepare(d)
    original=signals(f).iloc[:490].copy()
    d.loc[490:,"close"]+=.002
    # corrija high/low de esas velas, ya no afectan a las primeras 490
    d.loc[490:,"high"]+=.002
    d.loc[490:,"low"]+=.002
    d.loc[490:,"open"]+=.002
    modified=signals(prepare(d)).iloc[:490]
    pd.testing.assert_frame_equal(original,modified)


def test_cost_sensitivity_always_no_better():
    f=prepare(synthetic(1000))
    sig=signals(f)
    normal=simulate(f,sig,cost_multiplier=1)
    doubled=simulate(f,sig,cost_multiplier=2)
    assert set(normal)==set(NAMES)
    for name in NAMES:
        assert len(normal[name])>=0
    with pytest.raises(ValueError):
        simulate(f,sig,cost_multiplier=0)


def test_invalid_spread_rejected():
    d=synthetic()
    d.loc[1,"spread_pips"]=0
    with pytest.raises(ValueError):
        prepare(d)


def test_summary_negative_example():
    s=pd.DataFrame({"R":[-1.,-1.,1.5]})
    result=summarize(s)
    assert result["operations"]==3
    assert result["profit_factor"]==.75
    assert result["total_R"]==-.5
