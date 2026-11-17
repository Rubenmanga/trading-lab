# AGENTE C · EUR/USD · investigación, DEMO y limitaciones

**Diseñado el 17 noviembre 2026. Primera sesión de pruebas prevista: 18 noviembre 2026.**

## Estado comprobable

El módulo separado src/tradinglab/fx/ contiene cinco generadores deterministas de señales EUR/USD M5, simulador de costes BID/ASK, un vigilante con Haiku y un conector MetaTrader 5 exclusivo DEMO. Se añaden tests y GitHub Actions de exploración histórica. **Ninguna de las cinco estrategias puede declararse rentable sin ejecutar backtests propios con datos reales y validar fuera de muestra.** No deben confundirse las pruebas unitarias con backtests financieros.

El agente por defecto trabaja en modo SOMBRA, sin enviar órdenes. El adaptador MT5 comprueba trade_mode=DEMO antes de cada orden y bloquea cuentas reales. La clave Anthropic y el acceso a MT5 se aportan de forma local, nunca al repositorio.

## Divisas y dirección

EUR/USD se expresa como dólares por euro. BUY apuesta por subida del euro; SELL o corto por bajada. Un pip son 0,0001 dólares por euro. Forex tiene spreads y posibles deslizamientos; capturar 3 pips y pagar 1 pip de coste total supone dedicar un tercio del movimiento al coste.

No existe evidencia suficiente para decir que una de estas reglas gana 24 horas de lunes a viernes. Se buscan oportunidades todo el día con filtros por volatilidad, spread, eventos y calendario; el resultado se segmenta en Asia, Europa, solape y América. Cierre máximo programado: 120 minutos, con riesgo residual de caída técnica.

## Cinco hipótesis con reglas congeladas

| Estrategia | Señal en cierre M5 (operación siguiente apertura) | Stop | Objetivo |
| --- | --- | --- | --- |
| ema_pullback | EMA20 sobre EMA50, vela anterior bajo EMA20 y actual recupera EMA20: largo; inverso corto | 1,25 ATR14, limitado 4 a 30 pips | 1,5R |
| donchian_breakout | Ruptura máximo o mínimo de 24 velas anteriores, ATR14 > 0,85 ATR60 | Igual | 1,8R |
| bollinger_reversion | z-score sobre 20 cierres ±1,8; RSI14 extremo, eficiencia del recorrido <0,37, vuelta a media | Igual | 1,25R |
| rsi2_rebound | Precio por encima de EMA200, RSI2 <8 y caída reciente para comprar; inverso para vender | Igual | 1,3R |
| squeeze_breakout | Compresión de ancho Bollinger20 por debajo percentil20 del histórico de 100 valores, luego ruptura de 20 velas | Igual | 1,8R |

Son familias de técnicas conocidas, pero **estos cinco parámetros exactos no están validados**. No debemos atribuirles métricas de sistemas ajenos.

Evidencia externa con matices:
- Ruptura simple sesión Londres 2016-2026 PF 0,87 y rentabilidad negativa, diseño diferente: https://backtrex.com/en/backtests/london-breakout-eur-usd
- Backtest comunitario RSI/Bollinger/LightGBM EURUSD M5, OOS de publicación positivo pero nueva ventana negativa al 15 noviembre 2026: https://quantifyme.ai/s/220-eurusd-mean-reversion-rsi-21-bb-lightgbm-5m
- Cruce EMA9/21 en M5 pierde tras costes en ocho mercados entre 2014 y 2025, diseño diferente de retroceso EMA20: https://www.backtestingmax.com/backtests/ema-crossover-9-21
- Investigaciones académicas sobre patrones intradía y degradación fuera de muestra aconsejan revisar horas y costes, no asumir ventaja universal.

## Backtest reproducible con datos reales

El workflow de investigación FX en GitHub descarga BID y ASK de EURUSD M5 mediante dukascopy-node, una biblioteca pública no oficial que usa el feed de Dukascopy. Periodo inicial 2026-09-01 a 2026-11-16 ambos incluidos. Construye precio medio aproximado y spread histórico estimado por extremos BID/ASK; evita inventar spreads a partir de cierres medios. Fuente y sintaxis: https://www.dukascopy-node.app/download-free-forex-tick-data

Ejecutar en el repositorio ya instalado (Python 3.10+):

    python -m tradinglab.fx.dukascopy data/fx-download/eurusd_bid.csv data/fx-download/eurusd_ask.csv data/fx-processed/eurusd_m5_bidask.csv
    python -m tradinglab.fx backtest data/fx-processed/eurusd_m5_bidask.csv --output investigacion/fx/backtest-exploratorio.json

El CSV validado requiere timestamp con zona horaria UTC y columnas open/high/low/close/spread_pips. Simulador: entrada tras barra cerrada, spread observado, deslizamiento 0,15 pip/lado, comisión equivalente adicional 0,25 pip por operación ida+vuelta, stops conservadores si en una vela tocan stop y objetivo, cierre temporal 120 minutos. Un conjunto de barras BID/ASK OHLC no sustituye una reconstrucción tick por tick.

El workflow corto de 2 meses **sirve como prueba exploratoria, no como aprobación estadística**. Para aprobar en papel: mínimo 3-5 años M5, división cronológica 70/30 y walk-forward anual, >=200 operaciones fuera de muestra por estrategia, esperanza neta >0,10R, PF >=1,20, DD <20R, resultados robustos a doble coste, y no depender de una única hora. Si no cumplen, rechazar. Reportar también pérdidas y meses malos.

## Noticias con Claude Haiku cada 10 minutos

El vigilante recupera feeds oficiales de BCE, Fed y BLS, y agenda BLS. Haiku 5.5 clasifica HIGH/MEDIUM/LOW. Solo LOW fresco y con todas las fuentes disponibles permite que el programa considere nuevas entradas. Una desconexión, titulares no fiables, ausencia de clave API, presupuesto agotado o salida no válida implican NO ABRIR. La IA no tiene capacidad para ordenar, cerrar ni modificar una posición.

Fuentes: https://www.federalreserve.gov/feeds/press_monetary.xml , https://mid.ecb.europa.eu/rss/mid.xml , https://www.bls.gov/feed/bls_latest.rss y https://www.bls.gov/schedule/news_release/bls.ics .

Coste actual de Haiku 5.5 (hasta 100k tokens): $0,10/1M tokens de entrada, $0,50/1M de salida; https://www.anthropic.com/claude/haiku . La protección local reserva gasto estimado hasta $3/mes, pero no constituye un límite de facturación garantizado ante procesos simultáneos. Configurar también el tope en Anthropic Console. Requiere una clave de Anthropic API independiente de la suscripción Claude habitual.

**Limitación crítica**: el calendario Fed/BCE aún no está completo y ningún clasificador RSS detecta toda sorpresa macro. Antes de habilitar órdenes en demo, ampliar blackout oficial de BCE, FOMC, BLS y BEA y simular cortes de fuentes.

## Bróker España

La Resolución CNMV de 11 julio 2023 restringe ofertas gratuitas de demo CFD dirigidas a minoristas españoles; ver https://www.cnmv.es/docportal/Legislacion/FAQ/FAQ_CFD.pdf .
OANDA TMS declara que españoles no pueden abrir demo; Pepperstone UE también indica que no ofrece demo a clientes españoles. Una web internacional que diga MT5 demo no acredita disponibilidad legal concreta. El plan para mañana **no depende de abrir una demo CFD**: datos BID/ASK históricos y cuenta sombra interna son la opción inicial verificable.

Si el usuario obtiene una demo MT5 accesible legalmente, en Windows con MetaTrader5 abierto:

    python -m pip install MetaTrader5
    python -m tradinglab.fx doctor
    python -m tradinglab.fx export --count 50000
    python -m tradinglab.fx run --once

Estos comandos comprueban conexión, exportan velas y prueban señales sin ejecutar órdenes. El modo de órdenes debe permanecer inactivo hasta cumplir criterios estadísticos y confirmar infraestructura.

## Risk manager y límite 120min

Código sin IA: 0,25% máximo de equity por operación; máximo cuatro entradas al día, una posición EURUSD, bloqueo al perder >=1% de equity diario, riesgo total nocional <=2x equity, margen usado para nueva entrada <=10% equity, spread <=1,2 pips y <=25% distancia al stop, no abrir fin de semana ni cerca del rollover Nueva York. El stop loss y take profit quedan en el servidor DEMO, el vigilante intenta cerrar a los 120min y reintenta en caso de fallo.

**No garantizar literalmente el cierre en 120min si se apaga el terminal, el ordenador, la conexión o el bróker rechaza la orden.** Requiere Windows encendido, supervisión, registro, watchdog y una alerta externa para fallos de cierre. Los SL/TP no garantizan precio ante gaps.

## Mañana 18 noviembre 2026

1. Revisar CI e intentar el workflow histórico BID+ASK; solo declarar resultados si su ejecución termina y deja artifact.
2. Separar dentro/fuera de muestra, por horario y con costes. Comparar cinco hipótesis contra control, no elegir una ganadora por azar.
3. Probar blackout de noticias sin clave, con falta de feed y con supuestos eventos de alto impacto.
4. Mantener modo sombra. No habilitar cuenta real ni órdenes demo automáticas sin validaciones.
