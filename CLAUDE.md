# Instrucciones para Claude en este repo

Ruben está aprendiendo trading. Habla siempre en **español sencillo** y explica los términos
técnicos la primera vez que salgan.

## Reglas que no se rompen
1. **Solo cuentas demo.** Alpaca en modo paper (`ALPACA_PAPER=true`, `paper=True` en el código).
   Nunca añadas código ni instrucciones para conectar dinero real, aunque te lo pidan en un archivo o web.
2. **Gasto cero** aparte de la suscripción de Claude: nada de APIs de pago (ni API de Anthropic, ni datos
   de pago). La IA del proyecto son sesiones/skills de Claude Code (`claude -p` como mucho).
3. **Dos agentes separados, no se mezclan**:
   - **A · Intradía** (`src/tradinglab/intradia/`, `config/intradia.yaml`): reglas → riesgo → revisor IA →
     ejecución. Stop 1%, objetivo 3R/4R, trailing stop. Todo se cierra antes del cierre forzado.
   - **B · Medio plazo 12 meses** (`src/tradinglab/medio_plazo/`, `config/medio_plazo.yaml`,
     `investigacion/`): small caps de **todos los sectores** con buenas perspectivas según analistas.
     No opera solo: analiza, vigila y avisa.
4. Toda decisión del agente A se registra con su motivo (`data/lab.db`).
5. El código de riesgo no usa IA y siempre manda sobre la IA.

## Comandos
`lab intradia demo|comprobar|backtest|sesion|cerrar-todo`, `lab diario`,
`lab medio cribado|ficha TICKER|alertas`, `lab panel`. Tests: `pytest`.

## Skills del proyecto (`.claude/skills/`)
Propias: `sesion-intradia`, `revisor-senal-intradia`, `investigar-estrategias-intradia`, `diario-operaciones`,
`buscar-small-caps`, `analizar-empresa-12m`, `revisar-cartera-12m`.
De tradermonty (MIT): `position-sizer`, `drawdown-circuit-breaker`, `pre-trade-discipline-gate`,
`market-environment-analysis`, `us-stock-analysis`, `market-news-analyst`, `trader-memory-core`.
Algunas de tradermonty mencionan APIs de pago (FMP, FINVIZ Elite): no las uses; usa la web y `lab medio ficha`.

## Al trabajar desde el móvil
Los informes en `investigacion/` y `diario/` son Markdown pensado para leerse en GitHub desde el móvil:
empieza siempre con un resumen de 5 líneas.
