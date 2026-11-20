# EUR/USD · Segunda investigación 2021–2026

**17 de noviembre de 2026. Agente C. Solo investigación. Ninguna estrategia aprobada para enviar órdenes.**

## Resultado ejecutivo

- Se utilizaron históricos EUR/USD M5 BID y ASK de Dukascopy, por años 2021–2026 (2026 hasta el 16 de noviembre). Se auditaron spreads anómalos, excluyendo sin interpolar barras inválidas.
- 12 hipótesis nuevas definidas de antemano: **0 con esperanza positiva en algún año completo de los 6**.
- 6 variantes extra con señal M15 y ejecución M5: 5 con esperanza negativa todos los años; la sexta solo positiva en 2025 y 2026 con una muestra muy pequeña (7 y 12 trades), pero negativa los cuatro años anteriores.
- 96 combinaciones adicionales de ocho políticas de cierre/stop/objetivo sobre las 12 estrategias, diseñadas en 2023–2024: **0 superaron simultáneamente +0,10R y estabilidad anual**.
- Control de entradas aleatorias en el conjunto exploratorio de 2026: entre -0,19R y -0,29R por operación en 5 semillas. Muchos sistemas técnicos están cerca del control sin habilidad predictiva.
- **No se han encontrado dos estrategias de rentabilidad comprobada. No fingirlo.**

## 12 estrategias M5: esperanza neta R/operación

| Estrategia | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| dema_band | -0.227 | -0.190 | -0.171 | -0.245 | -0.231 | -0.249 |
| trend_continuation | -0.267 | -0.244 | -0.213 | -0.230 | -0.227 | -0.252 |
| range_zfade | -0.169 | -0.194 | -0.181 | -0.140 | -0.215 | -0.224 |
| swing_failure | -0.191 | -0.130 | -0.192 | -0.176 | -0.150 | -0.188 |
| inside_bar | -0.177 | -0.184 | -0.248 | -0.209 | -0.267 | -0.267 |
| impulse_fade | -0.221 | -0.139 | -0.200 | -0.242 | -0.209 | -0.618 |
| impulse_follow | -0.192 | -0.213 | -0.247 | -0.227 | -0.273 | -0.275 |
| micro_pullback | -0.195 | -0.205 | -0.188 | -0.208 | -0.234 | -0.217 |
| tokyo_post_fix | -0.162 | -0.216 | -0.205 | -0.231 | -0.364 | -0.309 |
| london_post_fix | -0.202 | -0.106 | -0.025 | -0.110 | -0.160 | -0.221 |
| ecb_post_fix | -0.244 | -0.136 | -0.193 | -0.251 | -0.306 | -0.234 |
| pre_london_fix | -0.106 | -0.052 | -0.082 | -0.083 | -0.210 | -0.128 |

La versión 2 reproducible está en src/tradinglab/fx/research2.py; CI de cuatro años en .github/workflows/fx-investigacion-plurianual.yml; datos de 2021 y 2022 en .github/workflows/fx-datos-2021-2022.yml. La versión inicial de 5 estrategias permanece en fx/engine.py sin cambios.

## Pruebas de quince minutos

| Estrategia | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| M15 tendencia EMA | -0.235 | -0.248 | -0.272 | -0.193 | -0.252 | -0.238 |
| M15 continuación impulso | -0.203 | -0.223 | -0.223 | -0.244 | -0.207 | -0.246 |
| M15 inversión impulso | -0.140 | -0.268 | -0.298 | -0.140 | -0.213 | -0.180 |
| M15 RSI reversión | -0.179 | -0.207 | -0.214 | -0.265 | -0.238 | -0.212 |
| M15 rechazo mecha | -0.195 | -0.446 | -0.115 | -0.509 | +0.015 | +0.179 |
| M15 z-score fade | -0.168 | -0.186 | -0.194 | -0.149 | -0.176 | -0.181 |

## 96 políticas alternativas de cierre

Definidas antes de evaluar: stops de 1,5/2/3 ATR, cierre a 30/60/90/120min y TP 1/1,5R o solo stop de protección. Entrenamiento cronológico 2023–2024. **0 cumplen**: >=100 operaciones; expectativa positiva en ambos años; media >=0,10R.

Candidato más cercano (no aprobado): retorno posterior al fixing BCE con stop 2 ATR y cierre 90min. En 2023+2024 suma 499 operaciones y media +0,056R. Otras muestras: 2021 -0,043R, 2022 +0,070R, 2025 +0,020R, 2026 -0,004R. Expectativa demasiado débil para cubrir incertidumbre sobre bróker, latencia y ticks.

## Costes y limitaciones

- Datos históricos descargados del feed Dukascopy mediante la biblioteca externa dukascopy-node, transformados con spreads históricos de precios BID y ASK, más **slippage 0,15 pip por lado** y **comisión equivalente 0,25 pip por operación**.
- Entrar al siguiente open después de señal cerrada, stop prioritario cuando una vela toca simultáneamente SL/TP, máximo de 120 minutos en condiciones normales; las lagunas de histórico pueden forzar salida en la siguiente barra.
- Velas M5 no permiten reconstruir ejecución de cada tick y el spread agregado es aproximado; no son resultados de un bróker en vivo.
- La selección de nuevas reglas tras observar datos anteriores puede producir overfitting. Una estrategia futura necesita un conjunto intacto de validación y pruebas paper forward.

## Fuentes externas contrastadas

- Investigacion académica sobre FX fixings (1999–2019): https://doi.org/10.1111/jofi.13306. El patrón publicado no basta para demostrar rentabilidad EUR/USD minorista actual.
- Disertación sobre bandas DEMA y EUR/USD intradía: https://www.maddoxmetrics.io/static/pdfs/dissertation.pdf
- Debate r/algotrading sobre 60 sistemas, flip test, randomización y forward testing: https://www.reddit.com/r/algotrading/comments/1xprhrh/update_after_60_backtested_strategies_6_are_now/
- Sistema EURUSD de cestas sin stop tradicional, que se ha **excluido por riesgo**: https://www.reddit.com/r/Forexstrategy/comments/1vdqgu9/i_backtested_an_eurusd_m15_engulfing_basket/

## Decisión y siguientes hipótesis de investigación

**Estado: 0/2 aprobadas.** Mantener Agente C en simulación. No habilitar la cuenta DEMO ni LIVE para estas estrategias.

Futuras líneas: modelos causales de datos macro sorpresa vs expectativa, microestructura tick BID/ASK, contexto intermercados, estrategias de ejecución por fixing con calendario real de publicación y filtros de eventos. Diseñarlas con hipótesis económicas, congelar reglas, probar contra control aleatorio y validar en periodos no usados para desarrollo. No convertir el requisito de encontrar dos en permiso para sobreoptimizar.

**Ejecuciones auditables:**
- https://github.com/Rubenmanga/trading-lab/actions/runs/43987986034
- https://github.com/Rubenmanga/trading-lab/actions/runs/43988169220

**Sin merge a main.** No se recomiendan operaciones con dinero real.
