# Código y material de terceros

Este proyecto reutiliza trabajo de otros respetando sus licencias.

## tradermonty/claude-trading-skills — MIT
https://github.com/tradermonty/claude-trading-skills (commit `fdfff01`, 14-nov-2026)
Copyright (c) 2026 TraderMonty. Copiadas sin cambios en `.claude/skills/` (cada carpeta incluye
`LICENSE-tradermonty`):
`position-sizer`, `drawdown-circuit-breaker`, `pre-trade-discipline-gate`, `market-environment-analysis`,
`us-stock-analysis`, `market-news-analyst`, `trader-memory-core`.
Las ideas de `src/tradinglab/intradia/riesgo.py` (tamaño por riesgo y corte por pérdidas) y de la skill
`diario-operaciones` se inspiran en ellas.

## TauricResearch/TradingAgents — Apache License 2.0
https://github.com/TauricResearch/TradingAgents (commit `9fa1196`)
La skill `.claude/skills/analizar-empresa-12m` adapta su **estructura de roles** (analistas fundamental,
de noticias, de sentimiento y técnico; debate alcista/bajista; gestor de riesgo). No se ha copiado su
código; los textos están reescritos en español y adaptados para ejecutarse como skill de Claude en lugar
de llamadas a APIs de pago. Cambios: roles redefinidos para inversión a 12 meses en small caps,
análisis de catalizadores con fecha y salida a una lista de vigilancia.

## HKUDS/Vibe-Trading — MIT
https://github.com/HKUDS/Vibe-Trading
Ideas (no código) para el backtest con costes y la "cuenta sombra" (`intradia/backtest.py`,
`intradia/brokers/simulado.py`).

## Descartados a propósito
FinceptTerminal (AGPL) y TradingAgents-CN (partes con licencia propietaria): no se usa nada de ellos.
backtrader (GPL) no se incluye; si algún día se usa, que sea como dependencia aparte.
