# Revisión crítica 2026-11-19: flujo de órdenes y expansión de volatilidad

Estado: **0/2 aprobadas**. Solo investigación; no órdenes, no dinero real, no merge. No se han ejecutado backtests nuevos en esta revisión. Este documento propone pruebas **antes de observar resultados**, no demuestra rentabilidad.

## Evidencia nueva y sus límites

1. Chen y Gau (2022), *The information effect of order flows in foreign currency futures and spot markets*, https://doi.org/10.1002/fut.22345: flujo de órdenes en futuros y contado EUR/USD participa en descubrimiento de precios y reacciones macro. No proporciona una regla rentable transferible directamente al feed Dukascopy.
2. *Price Impacts of Deals and Predictability of the Exchange Rate Movements*, NBER WP12682, https://www.nber.org/system/files/working_papers/w12682/w12682.pdf: predictibilidad de flujo muy breve, hasta ~5 minutos, débil a 15 y ausente a 30. Importante: sin datos de transacciones agresoras, un proxy OHLC no reproduce el flujo de órdenes.
3. Breedon y Ranaldo (2013), https://doi.org/10.1111/jmcb.12032: efectos horarios en retornos y flujo FX. No equivale a operar los fixings ya descartados.
4. Reddit 24-jul-2026, https://www.reddit.com/r/algotrading/comments/1v53mep/what_do_u_think_about_my_strategy/: compresión de ATR seguida de expansión con órdenes stop en ambos sentidos. Reglas incompletas, no hay validación independiente. La versión que sigue es una hipótesis propia y **no** una reproducción certificada.
5. Reddit 6-nov-2026, https://www.reddit.com/r/algotrading/comments/1xprhrh/update_after_60_backtested_strategies_6_are_now/: exige reglas congeladas, bid/ask y control aleatorio; 40 operaciones no bastan para aprobar nada.

## H1: expansión tras compresión intradía, sin basket ni martingala

Datos requeridos: EUR/USD BID/ASK M1 o tick con timestamps UTC, barras completas y calendario de noticias. Al cierre de cada vela M5, calcular ATR(14) usando midpoint **solo para señales**, y percentil ATR entre las 500 velas M5 cerradas previas (sin la actual). Condición de compresión: ATR previo <= percentil 15. Condición de activación: ATR actual >= 1,5 x ATR previo y rango actual >= 1,5 x ATR previo. Colocar una orden stop de compra a ASK high de vela señal + 0,2 ATR y una stop de venta a BID low - 0,2 ATR, válidas solo 15 minutos. Primera ejecución cancela la contraria (OCO). Stop a 1 ATR del precio ejecutado; objetivo 1,5 ATR; cierre obligatorio a 90 minutos desde la entrada. Una posición como máximo. Excluir spreads > percentil 90 del histórico de spreads **solo del entrenamiento**, y anuncios de alta importancia ±10 minutos con calendario verificable publicado antes del evento. No operar si no hay ticks suficientes para resolver activación OCO; nunca asumir el orden intrabar favorable.

Diferencia frente a 12 hipótesis anteriores: condición de compresión/expansión de volatilidad y órdenes OCO, no tendencia, impulso simple ni vela interior. Posible solapamiento económico con impulso: medir correlación de señales antes de contarla como estrategia distinta.

## H2: confirmación de flujo de órdenes contado/futuros, horizonte ultracorto

**No implementable con el OHLC BID/ASK disponible por sí solo**. Requiere datos históricos con transacciones y agresor o delta firmado EUR/USD futures y timestamps sincronizados con spot, derechos de uso y documentación de latencia. Construir delta firmado de 60 segundos; umbral predefinido de z-score >=2 o <=-2 respecto a 120 ventanas anteriores, volumen >= mediana histórica de la misma franja horaria. Solo entrar en dirección del delta si el retorno spot en esos 60 segundos es menor que 0,5 desviaciones típicas del retorno de 60 segundos de la misma franja (retraso de reacción). Señal solo después de cerrar ventana; entrada siguiente ASK/BID; stop 2 pips, TP 3 pips, cierre a 5 minutos. Cancelar si spread >0,8 pip; evitar periodos de noticias ±5 minutos. Si no hay datos de agresores **no sustituirlos silenciosamente por color de vela**. La regla se considera preregistrada y provisional; no ajustar el umbral mirando validación.

## Protocolo innegociable

- Congelar código, reglas y hashes de fuentes antes de validar; años cronológicos de desarrollo y prueba no solapados, embargo >=120 minutos en fronteras; walk-forward anclado sin recalibrar sobre prueba.
- Entrar al ASK para largos y al BID para cortos; salidas inversas; comisión + deslizamiento modelizados, después duplicados. Simular latencia y gaps; rechazar datos anómalos con reglas escritas de antemano.
- Controles: entradas aleatorias con misma hora, duración y riesgo; direcciones invertidas; bootstrap por días y por semanas; comparar diferencias, no solo PnL bruto.
- Requisitos por estrategia: >=200 operaciones fuera de muestra, esperanza neta >=+0,10R, PF >=1,20, consistencia interanual y rentabilidad con costes dobles. Comprobar además intervalo de confianza y sensibilidad a ejecución; ninguna promoción por una sola muestra.
- Riesgo de selección múltiple: cada hipótesis ensayada cuenta; no reciclar test final después de observarlo.
- Límite temporal: posiciones cerradas en <=120 minutos incluso ante datos faltantes; si no puede demostrarse, rechazar operación/periodo.

## Estado y próximos bloqueos

H1 se puede implementar con ticks o M1 bid/ask y simulador OCO que respete orden temporal. Con barras M5 y doble disparo intrabar no es demostrable el fill correcto. H2 necesita flujo firmado real de futuros y sincronización, no incluido en históricos anteriores. En esta revisión no se ha ejecutado código ni se han calculado métricas nuevas. **0/2 verificadas; sin aviso de éxito.**
