# Laboratorio intradía · 2026-11-25

**Resumen**

1. Se prueban 6 estrategias a la vez con las mismas reglas de riesgo (stop 1 %, objetivo 3R, trailing, todo cerrado a las 15:45 NY), con costes.
2. Pasado: 2016-01-19 a 2026-11-13. Mejor por R medio: **Corto del hueco** (+0,11 R).
3. Aprueban el listón (≥ 100 operaciones, ≥ +0,20 R de media y margen de error por encima de 0): **ninguna**.
4. Cuenta sombra: 6 días apuntados desde el 16-nov-2026. Hacen falta ~100 operaciones por estrategia para una primera lectura.
5. Todo es papel: no se envía ninguna orden. R = lo que se arriesga en una operación.

## Pasado (backtest)

| | Estrategia | Ops | Ops/día | R medio | Margen (95 %) | Con 4R | Aciertos | PF | Peor caída | Años + | Vs azar |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 🟡 | Corto del hueco | 7042 | 3,3 | +0,11 | +0,09 a +0,14 | +0,11 | 50 % | 1,28 | -38 R | 11/11 | +0,22 |
| 🟡 | Ruptura de apertura (ORB) | 21180 | 7,8 | +0,02 | -0,00 a +0,04 | +0,02 | 48 % | 1,03 | -298 R | 6/11 | +0,12 |
| 🔴 | Rebote tras caída | 7750 | 4,0 | -0,09 | -0,12 a -0,05 | -0,08 | 42 % | 0,86 | -674 R | 2/11 | +0,02 |
| 🔴 | Azar (control) | 10884 | 4,0 | -0,11 | -0,13 a -0,09 | -0,11 | 44 % | 0,80 | -1213 R | 0/11 | +0,00 |
| 🔴 | Retroceso al VWAP | 33329 | 12,2 | -0,12 | -0,13 a -0,10 | -0,12 | 44 % | 0,79 | -3857 R | 0/11 | -0,01 |
| 🔴 | Hueco con volumen (catalizador) | 14841 | 5,7 | -0,17 | -0,19 a -0,15 | -0,15 | 38 % | 0,74 | -2564 R | 0/11 | -0,06 |

Corto del hueco **como el bot de eToro** (hueco ≥ +50 %, 3 al día): 2222 operaciones, +0,24 R de media (+3,68 % por operación), aciertos 49 %.

## Cuenta sombra (desde el 16-nov-2026)

| | Estrategia | Ops | R medio | Aciertos | R total | Vs azar |
|---|---|---|---|---|---|---|
| 🟡 | Corto del hueco | 13 | -0,01 | 46 % | -0,1 | — |
| ⚪ | Ruptura de apertura (ORB) | 0 | — | — | — | — |
| ⚪ | Rebote tras caída | 0 | — | — | — | — |
| ⚪ | Azar (control) | 0 | — | — | — | — |
| ⚪ | Retroceso al VWAP | 0 | — | — | — | — |
| ⚪ | Hueco con volumen (catalizador) | 0 | — | — | — | — |

## Qué hace cada estrategia

- **Ruptura de apertura (ORB)**: Compra si rompe el máximo de los 5 primeros minutos (vela verde) o vende en corto si rompe el mínimo (vela roja). Solo las 10 acciones con más volumen al abrir.
- **Hueco con volumen (catalizador)**: Acciones que abren con hueco de ±4 % y mucho volumen (suele haber noticia o resultados). Entra a favor del hueco si rompe el rango de los 15 primeros minutos y está del lado bueno del VWAP.
- **Retroceso al VWAP**: Si en la primera media hora va claramente al alza (o a la baja), espera a que el precio vuelva al VWAP (precio medio del día) y entra a favor de la tendencia.
- **Corto del hueco**: Vende en corto a las 9:35 las que abren +25 % o más; stop 15 %, sin objetivo, cierra a las 15:45. «Como el bot» = hueco ≥ +50 % y las 3 primeras del día.
- **Rebote tras caída**: Acciones que abren un 8 % o más abajo: compra cuando el precio vuelve a subir por encima del VWAP.
- **Azar (control)**: CONTROL: 4 acciones en juego al azar, lado y hora al azar, mismas reglas de riesgo. Una estrategia que no le gane no aporta nada.

## Cómo leerlo

- **R medio**: lo que gana o pierde de media cada operación, en unidades de riesgo. Tras costes.
- **Margen (95 %)**: con estas operaciones, el R medio «de verdad» está casi seguro entre esos dos números. Si el de la izquierda es mayor que 0, no parece suerte.
- **PF** (factor de beneficio): lo ganado entre lo perdido. Por encima de 1,3 es bueno.
- **Peor caída**: la mayor racha de pérdidas acumulada, en R. Con 0,5 % de riesgo por operación, −20 R = −10 % de la cuenta.
- **Vs azar**: cuánto mejora a la estrategia de control. Si es ~0, la estrategia no aporta.
- Semáforo: 🟢 aprueba · 🟡 prometedora o faltan operaciones · 🔴 pierde · ⚪ sin datos.
- Límites: las velas son de 1 minuto (no vemos el orden exacto dentro del minuto: se supone lo peor); no sabemos qué acciones se podían vender en corto ese día; el pasado no garantiza el futuro.
