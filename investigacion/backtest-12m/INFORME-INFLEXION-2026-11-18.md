# Detector de punto de inflexión: ¿encuentra las x3?

**Resumen en 5 líneas**

1. Veredicto: **NO PASA el listón**: en los años de comprobación no encontró el doble de x3 que la media. No se usa para elegir acciones; queda solo como dato informativo.
2. Comprobación (2021 en adelante): del 10 % con más señales, **9.8 %** multiplicó x3 en 3 años; la media de todas fue 7.7 %. Listón: 12 % y el doble de la media.
3. Ajuste (2014-2020): 8.1 % frente a 6.9 % de media (variante elegida: «seis señales»).
4. Riesgo: del 10 % elegido, 20.4 % perdió la mitad o más. Mediana a 3 años: 3.8 % (todas: -2.2 %).
5. Aun cuando funcione, la mayoría de las elegidas NO triplica: se juega con una cesta de 10-15 posiciones pequeñas.

## Qué mira el detector (6 señales, con datos oficiales de la SEC de aquel día)

- Ventas que aceleran
- Margen bruto mejor que hace un año
- Gastos que crecen menos que las ventas
- Genera caja o tiene para 18+ meses
- Poca dilución (acciones +10 % o menos en un año)
- 2+ directivos comprando en 30 días

«x3» = la acción vale 3 veces más (o más) a los 3 años, con dividendos. «Base» = % de x3 entre TODAS las small caps de ese trimestre. «Decil» = el 10 % con más señales.

## Resultado por variante

| Variante | Ajuste 2014-2020 | Comprobación 2021+ | Base comprobación |
|---|---|---|---|
| seis senales (elegida) | 8.1 % | 9.8 % | 7.7 % |
| solo cuentas | 7.4 % | 9.3 % | 7.7 % |
| ventas y margen doble | 7.4 % | 10.1 % | 7.7 % |

## Cada señal por separado (todo el periodo, solo informativo)

| Señal | % de x3 con la señal | sin la señal | casos con señal |
|---|---|---|---|
| Ventas que aceleran | 6.5 % | 7.5 % | 6191 |
| Margen bruto mejor que hace un año | 7.9 % | 6.8 % | 6043 |
| Gastos que crecen menos que las ventas | 7.6 % | 6.8 % | 8201 |
| Genera caja o tiene para 18+ meses | 7.0 % | 7.9 % | 14811 |
| Poca dilución (acciones +10 % o menos en un año) | 7.2 % | 6.9 % | 14786 |
| 2+ directivos comprando en 30 días | 8.3 % | 7.0 % | 1717 |

Casos: 11767 (ajuste) y 6431 (comprobación); cada caso es una empresa en un trimestre. Datos hasta 2026-11.

## Límites

- Solo empresas que cotizan hoy (las que quebraron no están): las tasas de x3 salen algo infladas, para todas por igual.
- La comprobación solo llega a trimestres con 3 años ya cumplidos (hasta ~3 años antes de hoy): pocos años.
- Una misma empresa cuenta en varios trimestres seguidos.
- Pasado no es futuro. Esto es un filtro para estudiar, no una orden de compra.

Fuentes: SEC companyfacts (10-Q/10-K por fecha de presentación), SEC Insider Transactions Data Sets (Form 4), precios de Yahoo. Código: `src/tradinglab/backtest12m/inflexion.py`.
