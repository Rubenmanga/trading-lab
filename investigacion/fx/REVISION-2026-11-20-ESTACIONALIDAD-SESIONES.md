# Revisión 2026-11-20: estacionalidad direccional por sesión (Agente C)

**Estado:** hipótesis nuevas, NO backtesteadas ni aprobadas. 0/2 verificadas. Solo investigación; ninguna orden, ningún merge.

## Auditoría de antecedentes
Leído `investigacion/fx/INFORME-2026-11-17-6-ANOS.md`: doce sistemas M5 perdedores en seis años, seis M15 sin consistencia, 96 salidas fallidas y controles aleatorios negativos. No reutilizar esas señales ni ajustar el período OOS. Los estudios sobre fixing y señales de volatilidad ya se investigaron en revisiones anteriores.

## Nueva hipótesis S1: sesgo direccional por horario local (no fixing)
**Base:** Breedon y Ranaldo (2013), *Intraday Patterns in FX Returns and Order Flow*, Journal of Money, Credit and Banking 45(5), 953-965, DOI https://doi.org/10.1111/jmcb.12032. Los autores encuentran depreciación de divisas durante horarios de negociación locales; la ficha RePEc menciona una estrategia EUR/USD rentable en su muestra, sin garantía de que siga funcionando neta en 2021–2026.

**Protocolo previo a resultados:** trabajar en UTC con calendario Europe/London y America/New_York correctamente convertido por fecha y horario de verano; evaluar como dos hipótesis *direccionales* separadas, no como una búsqueda de horas óptimas: (a) comprar EUR/USD a las 08:00 hora de Londres y cerrar a las 09:30 Londres; (b) vender EUR/USD a las 08:00 hora de Nueva York y cerrar a las 09:30 Nueva York. Una operación máxima por sesión y fecha; no operar si falta la primera cotización posterior al instante previsto o hay hueco >5 min. Las direcciones se derivan de la hipótesis de depreciación de la moneda local en su sesión (GBP no es componente de EUR/USD, así que el brazo Londres es un control exploratorio y no debe presentarse como derivación causal). Para evitar esa confusión, tratar (a) como control negativo; el brazo Nueva York es la hipótesis principal de USD débil. Entrada ASK/salida BID en largos; entrada BID/salida ASK en cortos; ejecución siguiente tick después del horario; cierre obligatorio <=90 min. Stop de emergencia fijo 20 pips, no optimizado, con ejecución conservadora. Riesgo en R definido por 20 pips + costes ex ante; rechazar cualquier señal si spread >2 pips al inicio. No optimizar horarios ni stop usando OOS.

**Control alternativo:** comparar con trades aleatorios emparejados por día, sesión y duración, y con señal invertida, manteniendo spreads y costes idénticos. Advertencia: 90 min de exposición a movimientos EUR/USD puede ser insuficiente para superar costes; la hipótesis se rechaza si no supera el umbral OOS.

## Nueva hipótesis S2: efecto de día de semana × sesión estadounidense, preespecificado
Investigar si la dirección de S1 depende del día de la semana usando **solo entrenamiento** para estimar diferencias, sin elegir retrospectivamente el mejor día. Modelo de entrenamiento: regresión logística penalizada de signo de retorno futuro de 90 min con indicadores de día de semana y efecto fijo de año; señal únicamente cuando la probabilidad estimada supera 0.60 o es inferior a 0.40, umbral congelado antes de OOS; de otro modo no operar. Entrar 08:00 Nueva York, cerrar 09:30, stop 20 pips y filtros idénticos a S1. **No es independiente de S1** por compartir el mismo mecanismo; aunque ambas pasaran no cuentan como las dos estrategias distintas exigidas. La independencia requiere un segundo mecanismo causal, no un filtro del primero.

## Datos y controles obligatorios
1. Reconstruir series históricas BID/ASK de ticks o como mínimo M1 con cotizaciones contemporáneas; verificar timestamps, duplicados, spread negativo, huecos, DST, fines de semana y cambios de sesión.
2. Separación cronológica: 2021–2023 desarrollo; 2024–2025 validación cerrada; 2026 exclusivamente evaluación final, sin reoptimizar ni usar 2026 para elegir hipótesis. **Advertencia:** 2024–2026 se han consultado previamente en el laboratorio, así que NO son OOS verdaderamente vírgenes a nivel de proyecto; etiquetar como *pseudo-OOS* y exigir además forward paper posterior al congelado.
3. Coste base: spread histórico + 0.15 pip deslizamiento por lado + 0.25 pip comisión por round-trip, siguiendo el informe; escenario doble: duplicar componentes de coste añadidos y el diferencial efectivo simulado, evitando contabilizar dos veces el spread.
4. Walk-forward cronológico anclado, con cada modelo ajustado solo en ventanas anteriores; bootstrap por día y año; aleatorización emparejada por hora, día y duración; flip test; reportar intervalos y distribución por año, no solo media.
5. Criterio de aprobación invariable: >=200 operaciones OOS por estrategia, >=+0.10R neto, PF>=1.20, consistencia anual y resistencia a costes dobles, además de independencia económica entre dos estrategias.
6. Sin órdenes DEMO ni LIVE. No cambiar parámetros por resultados OOS.

## Lecturas críticas de comunidad
- https://www.reddit.com/r/algotrading/comments/1xprhrh/update_after_60_backtested_strategies_6_are_now/ (6 noviembre 2026): ejemplo anecdótico de reglas congeladas, flip test y fills BID/ASK; no evidencia de ventaja.
- https://www.reddit.com/r/algotrading/comments/1tnl249/the_single_biggest_gap_between_my_backtests_and/ (25 mayo 2026): riesgo de fills a midpoint; experiencia no verificada.
- https://www.reddit.com/r/algotrading/comments/12km0x8 (13 abril 2023): discusión sobre spreads, comisión y slippage.

## Resultado de esta revisión
No se han ejecutado nuevos backtests: esta revisión no dispone de acceso directo a la serie histórica en formato ejecutable ni a la ejecución CI validada. No inventar número de operaciones ni rentabilidades. Prioridad siguiente: implementar S1 en motor de ticks y ejecutar CI con datos auditados; S2 queda como análisis complementario, no segunda estrategia independiente. Buscar un segundo mecanismo económico separado antes de declarar 2/2.
