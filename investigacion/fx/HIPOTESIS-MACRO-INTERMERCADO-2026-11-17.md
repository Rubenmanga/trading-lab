# Agente C — hipótesis nuevas y requisitos de datos (17-11-2026, revisión adicional)

**Estado: investigación, 0/2 estrategias verificadas.** No reutilizar las 12 estrategias M5, seis M15 ni 96 salidas del informe anterior. Ninguna de las propuestas siguientes es rentable por demostración; son hipótesis que requieren datos adicionales y pruebas.

## H1: sorpresa macroeconómica normalizada y continuación limitada

**Fundamento:** Andersen, Bollerslev, Diebold y Vega, *American Economic Review* (2003), https://doi.org/10.1257/000282803321455151, encuentran saltos condicionados a sorpresas macroeconómicas, con asimetrías de signo. **No** prueban una ventaja minorista neta actual.

**Datos imprescindibles:** archivo histórico punto-en-el-tiempo de publicaciones EUR/USD (NFP, CPI, tipos BCE/Fed) con hora exacta, consenso disponible *antes* de cada publicación, dato inicial (no revisado), desviación estándar histórica calculada solo con datos anteriores, calendario de festivos y BID/ASK por tick o segundo. No usar el consenso revisado posteriormente.

**Reglas pre-registrables:** calcular z=(actual-consenso)/desviación histórica de sorpresas previas; operar únicamente si |z|>=1,5 y el signo tiene correspondencia económica inequívoca; esperar 60 segundos desde la publicación; dirección del primer movimiento BID/ASK entre t+15s y t+60s, y solo si coincide con el signo fundamental esperado. Entrar al ASK (largo) o BID (corto) en el primer tick >=t+60s, siempre que spread <=percentil 75 de la misma ventana horaria, estimado únicamente en entrenamiento. Stop de 1 ATR de 5 minutos anterior al anuncio, TP 1,5R, salida forzosa 30 minutos después de entrada; no operar eventos simultáneos contradictorios ni publicaciones con fecha/hora dudosa. Costes normales y dobles, y estrés específico de deslizamiento de noticias. Un evento como máximo.

**Riesgo de sesgo:** selección de eventos y mapeo de signo; documentar decisiones antes de abrir test. Un único conjunto de datos de calendario puede contener errores de revisión.

## H2: divergencia de retorno entre EUR/USD y cesta USD, con retardo de precio

**Fundamento:** Evans y Lyons, *Journal of Political Economy* (2002), https://doi.org/10.1086/324391; el flujo de órdenes contiene información, pero **no** equivale a señales obtenibles del precio. No atribuir a este trabajo una validación de la estrategia.

**Datos imprescindibles:** BID/ASK sincronizado por segundo de EUR/USD, GBP/USD y USD/JPY, timestamps UTC y calidad de ticks. Sin estos datos no ejecutar el test ni reemplazar por retornos futuros.

**Reglas pre-registrables:** en cada cierre de minuto, medir retornos de los 10 minutos previos de GBP/USD y USD/JPY, invirtiendo signo USD/JPY; promediar z-scores calculados con medias/desviaciones de 60 días *anteriores*. Señal larga EUR/USD si cesta >=+1,5 desviaciones y retorno EUR/USD de los mismos 10 minutos <=+0,25 desviaciones; señal corta simétrica. Entrada siguiente tick, máximo una posición, stop 1 ATR(14) M5 y TP 1,5R; cierre a 45 minutos. No operar con timestamps faltantes o spread superior al percentil 75 histórico horario. Prohibir señales dentro de +/-5 minutos de eventos macro importantes para aislar la hipótesis.

**Riesgos:** correlación espuria, precios asincrónicos y uso de datos que llegan más tarde que el instante de señal. Probar también la dirección invertida y entradas aleatorias de frecuencia/horario equivalente.

## Protocolo de evaluación obligatorio

1. Congelar reglas, hash del código y calendario de particiones antes de inspeccionar validación. Entrenamiento 2021–2023; selección 2024; test bloqueado 2025–2026. Si el test ya fue inspeccionado para diseñar reglas, **no** declararlo intacto; usar paper forward futuro.
2. Walk-forward de ventanas cronológicas sin solapamiento, embargo de 120 minutos entre cortes; conservar cada operación, hora, precios BID/ASK, spread, comisión, deslizamiento, motivo de salida y R.
3. Ejecutar costes normales y dobles; límites de 120 minutos medidos en tiempo real, sin excepciones por lagunas. Tratar barras faltantes como error de simulación, no como una salida tardía favorable.
4. Control aleatorio con entradas emparejadas por hora/volatilidad y misma política de riesgo, además de flip test y bootstrap por día.
5. Aprobar solo si **cada una** de dos estrategias independientes alcanza >=200 operaciones OOS, esperanza neta >=+0,10R, PF >=1,20, consistencia interanual y robustez con costes dobles. Informar intervalos de confianza y todas las variantes descartadas; no seleccionar parámetros por el test.
6. Sin órdenes, ni siquiera demo automática, mientras no se apruebe explícitamente la etapa correspondiente.

## Hallazgos comunitarios: evidencia metodológica, no estrategias validadas

- https://www.reddit.com/r/algotrading/comments/1xprhrh/update_after_60_backtested_strategies_6_are_now/ (6-nov-2026): relato de 60+ variantes y reglas congeladas en paper; autorreportado, no verificación independiente.
- https://www.reddit.com/r/algotrading/comments/1xxs7go/how_do_you_simulate_realistic_slippage_when/ (16-nov-2026): discusión sobre deslizamiento dinámico alrededor de noticias; no ofrece parámetros demostrados para EUR/USD.
- https://www.reddit.com/r/algotrading/comments/zivzzd (2022): advertencias sobre latencia y BID/ASK.

## Estado de ejecución

**No se ejecutó backtest nuevo para H1/H2**: los archivos locales disponibles de EUR/USD M5 BID/ASK no incluyen consenso macro punto-en-el-tiempo ni cotizaciones sincronizadas de GBP/USD y USD/JPY. Ejecutarlas solo con EUR/USD sería cambiar la hipótesis y producir resultados no auditables. Pendiente adquisición legal y gratuita de series apropiadas y validación de integridad. **No se encontraron dos estrategias aprobadas.**
