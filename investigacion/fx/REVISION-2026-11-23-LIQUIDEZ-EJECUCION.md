# Revisión 2026-11-23: impacto de liquidez y control de ejecución

Estado: investigación, 0/2 aprobadas. No órdenes ni backtests nuevos. No reutilizar 12 hipótesis M5, 96 salidas, ni la estacionalidad fija del 20/11.

## Evidencia revisada
- Breedon y Vitale (2004), ECB WP424: flujo de órdenes tiene componentes de liquidez e información; correlación contemporánea no implica pronóstico explotable. https://ideas.repec.org/p/ecb/ecbwps/2004424.html
- Patzelt y Bouchaud (2017): impacto no lineal; desequilibrio extremo no implica retorno extremo; riesgo de interpretar presión de órdenes como tendencia. https://arxiv.org/abs/1706.04163
- Reddit r/algotrading, 06/11/2026: 60+ variantes, comparación contra entradas aleatorias, inversión de señal y paper forward; evidencia anecdótica, no prueba independiente. https://www.reddit.com/r/algotrading/comments/1xprhrh/update_after_60_backtested_strategies_6_are_now/
- Reddit r/algotrading, 05/09/2025: EURUSD M15 con spread fijo de 1 pip y sin slippage; excluir como evidencia de robustez. https://www.reddit.com/r/algotrading/comments/1n9bi1u

## Hipótesis nueva A: reversión de impacto temporal de liquidez
Requiere tick trades firmados o datos de profundidad reales, no aproximar órdenes con velas. En cada minuto t calcular desequilibrio firmado normalizado por volumen de los 5 minutos anteriores, percentiles calibrados exclusivamente en entrenamiento; detectar desequilibrio extremo >p95 y cambio de precio contemporáneo <p50 de su distribución condicionada por volatilidad. Tras cierre del minuto de señal, entrar en dirección opuesta al desequilibrio en siguiente ASK/BID ejecutable, stop 1x volatilidad realizada previa de 30 minutos, salida a 20 minutos o stop, sin TP. Una sola posición. **Solo propuesta preregistrada**: falta feed real de flujo firmado, definición de clasificación de operaciones, reloj y pruebas de latencia; no implementar usando proxies de M5.

## Hipótesis nueva B: asimetría de recuperación de spread tras shock de liquidez
Requiere ticks BID/ASK. Definir shock como spread actual >p99 de su distribución histórica para la misma franja horaria y movimiento medio del midprice en los 2 minutos anteriores >p90. Esperar normalización del spread a <p50 antes de entrar, máximo 10 minutos después del shock. Dirección contraria al movimiento inicial, entrada ejecutable al siguiente tick, stop 1x rango realizado pre-shock de 15 minutos, salida por tiempo 15 minutos o stop. Sin martingala. Es hipótesis distinta de patrones de vela; comprobar solapamiento de operaciones con A y dependencia de régimen. Advertencia: selección por spread puede generar sesgo de supervivencia y no ejecutabilidad.

## Plan de validación sin fuga
1. Verificar timestamps UTC, bid<ask, huecos, duplicados, fuente, derechos de redistribución y ticks ejecutables. Si solo hay M5, marcar ambas NO TESTABLE.
2. Congelar reglas y percentiles en 2021–2023; walk-forward con recalibración solo pasada y embargo mínimo 120 min; reservar 2025–2026 como auditoría final **no virgen** por exploraciones previas, exigir nuevo forward paper posterior al congelamiento.
3. Comisión, slippage, spread BID/ASK observados; repetir con doble coste; stops al lado correcto de cotización, prioridad conservadora en simultaneidad.
4. Controles: entradas aleatorias pareadas por hora/volatilidad (>=1000 semillas), señal invertida, bootstrap por día, comparación con mantener cero posición.
5. Aprobar solo si CADA una tiene >=200 operaciones OOS, esperanza >=+0.10R, PF>=1.20, consistencia interanual y rentabilidad con doble coste. Si se selecciona sobre OOS, invalidar esa muestra para confirmación.
6. No fusionar main, no habilitar DEMO ni LIVE ni enviar órdenes.

## Resultado
Sin acceso a históricos tick de flujo firmado/profundidad y ticks BID/ASK auditables para ejecutar estas reglas, **no se ha realizado backtest ni se declara rentabilidad**. El siguiente paso es adquisición verificable de datos y validación de calidad, no seguir variando parámetros sobre 2021–2026.
