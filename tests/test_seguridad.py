import pytest

from tradinglab.common import config


def test_se_niega_si_no_es_demo():
    with pytest.raises(SystemExit):
        config.exigir_demo({"modo_cuenta": "real"})


def test_se_niega_si_alpaca_paper_no_es_true(monkeypatch):
    monkeypatch.setenv("ALPACA_PAPER", "false")
    with pytest.raises(SystemExit):
        config.exigir_demo({"modo_cuenta": "demo"})
