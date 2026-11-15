# Lectura en sencillo: ¿se puede ganar con los top gainers o con el ORB? (2016-2026)

**Resumen en 5 líneas**
1. **Comprar las acciones que abren disparadas pierde dinero.** De 37.522 casos con hueco ≥ +10 %, el 61 % cerró por debajo de su apertura. Comprar a las 9:35 y vender al cierre deja −1,0 % de media, y con las reglas del agente A da −0,23 R.
2. **Cuanto más fuerte es el hueco, peor.** Con huecos ≥ +50 %, la mediana del día es −11 %. Aquí el rebote a la baja es lo habitual.
3. **El ORB original (el del estudio publicado) gana antes de costes, pero los costes se lo comen todo.** Da +0,30 R por operación sin costes y 0,00 R con ellos, en 44.924 operaciones.
4. **La versión adaptada al agente A (stop 1 %, objetivo 3R, cierre 12:20) es la única con algo positivo.** Da +0,03 R por operación, unos +5 % al año y una peor caída del −22 %. Ha ganado en los 4 últimos años, pero no llega al listón de +0,2 R que nos pusimos.
5. **Conclusión:** de momento no hay una estrategia lista para dinero real. Lo sensato es probar el ORB del agente A **en demo**, con el listón claro, y no perseguir las acciones que ya han subido.

---

## Qué hemos probado

Usamos datos de Alpaca de casi 11 años (enero de 2016 a noviembre de 2026), vela a vela de 1 minuto, **incluidas las acciones que ya no cotizan**. Si las dejáramos fuera, el resultado saldría demasiado bonito: es lo que se llama *sesgo de supervivencia*. A cada operación le restamos un deslizamiento del 0,05 % por lado y 0,0035 $ por acción. El *deslizamiento* es la diferencia entre el precio que quieres y el que te dan de verdad.

- **R** = lo ganado o perdido en veces lo arriesgado. Si arriesgas 10 € y ganas 30 €, son +3 R. Si salta el stop, son −1 R.
- **Profit factor** = lo ganado dividido entre lo perdido. Por encima de 1 se gana. Un sistema bueno suele estar por encima de 1,3.
- **Hueco (gap)** = cuánto abre la acción por encima del cierre del día anterior.

## 1. Las «top gainers» del día (las que ves en Revolut)

- Cada día hay unas **22 acciones** que suben ≥ +15 % (58.960 en total).
- Solo **1 de cada 4** ya subía ≥ +10 % a las 9:00 de Nueva York (las 15:00 en España). Las demás aparecen más tarde, sin aviso.
- El **73 %** hace su máximo del día **después de las 12:00**. Es decir, muchas suben poco a poco durante la tarde, y eso no se ve a primera hora.

**Lo que sí se ve a tiempo son los huecos de apertura.** Pero comprarlos sale mal:

| Grupo | Casos | Comprar 9:35 → cierre (media) | Reglas agente A |
|---|---|---|---|
| Todas con hueco ≥ 10 % | 37.522 | −1,0 % | −0,23 R |
| Precio < 5 $ | 7.807 | 0,0 % (mediana −1,8 %) | −0,41 R |
| Hueco 20-50 % | 7.961 | −1,4 % | −0,18 R |
| Hueco ≥ 50 % | 2.385 | **−5,9 %** (mediana −11 %) | −0,37 R |

Ningún grupo sale positivo. Solo el 44 % de estas acciones acaba el día subiendo ≥ +15 %. La mayoría devuelve parte de la subida.

**¿Y el motivo (la noticia)?** Miramos los titulares de una muestra. Para las acciones con hueco, las que suben por **resultados** o por una **compra de la empresa** aguantan algo mejor (+2 % y +4 % de la apertura al cierre). Las que no tienen noticia, o suben por FDA o por modas (cripto/IA), caen más (−4 % a −11 %). Las muestras son pequeñas (20-300 casos), así que es una pista, no una regla.

*Ojo:* el 37-48 % de los casos salen «sin noticia». Puede ser que de verdad no la haya (subidas por especulación o por una ampliación de capital anunciada fuera de hora), o que la fuente gratuita de noticias de Alpaca no cubra bien las empresas muy pequeñas. Lo tomamos con prudencia.

## 2. ORB «stocks in play» (romper el rango de los 5 primeros minutos)

El **ORB** (*Opening Range Breakout*) funciona así. Se miran los 5 primeros minutos de las 20 acciones con más volumen inusual. Si la vela es verde, compras cuando supera el máximo de esa vela; si es roja, vendes en corto cuando pierde el mínimo. *Vender en corto* significa apostar a que baja.

| Variante | Operaciones | Aciertos | R medio sin costes | **R medio con costes** | Profit factor | Al año | Peor caída |
|---|---|---|---|---|---|---|---|
| Original (stop pequeño, hasta el cierre) | 44.924 | 15 % | +0,30 | **0,00** | 1,00 | +3,7 % | −86 % |
| Original solo compras | 22.105 | 15 % | +0,30 | **−0,01** | 0,99 | −23 % | −99 % |
| **Agente A** (top 4, stop 1 %, 3R, trailing, cierre 12:20) | 8.340 | 48 % | +0,15 | **+0,03** | 1,06 | **+5,4 %** | **−22 %** |

**Qué significa:**
- **La idea tiene algo de ventaja**, porque sin costes gana +0,15 a +0,30 R. Esto encaja con el estudio publicado (2016-2023).
- **El stop del original es tan pequeño** (10 % del ATR) que cada operación paga mucho en deslizamiento y comisiones, y eso se come toda la ventaja. El *ATR* es el movimiento medio diario de la acción. En la vida real sería todavía peor.
- **La versión del agente A** usa un stop más ancho (1 %) y menos operaciones, así que paga menos costes. Es la única que queda en positivo, aunque por poco.

**Año a año (agente A):** perdió en 2016, 2017, 2019, 2021 y 2022, y ganó en 2018, 2020 y de 2023 a 2026 (+9 %, +17 %, +20 %, +16 %). Los últimos 4 años van bien, pero 5 de 11 años fueron negativos. No es una máquina de dinero.

## 3. ¿Pasa nuestro listón?

En el informe anterior pusimos como listón al menos 200 operaciones y **≥ +0,2 R de media cada año, después de costes**.

| Estrategia | ¿Pasa? |
|---|---|
| Comprar top gainers / huecos | ❌ No (negativa) |
| ORB original | ❌ No (0 R después de costes) |
| ORB agente A | ⚠️ No del todo: +0,03 R. Positivo y con caídas aceptables, pero muy justo |

## 4. Qué propongo ahora (solo demo)

1. **No perseguir las acciones que ya suben mucho.** Los datos dicen que, de media, se pierde.
2. **Probar el ORB del agente A en la cuenta demo** durante 2-3 meses (al menos 40 operaciones). Así veremos si el deslizamiento real es como el supuesto.
3. **Mejoras que se pueden probar en el backtest antes de la demo** (sin gastar nada):
   - Operar solo los días en que el índice va a favor del lado de la operación.
   - Filtrar por motivo: priorizar resultados y compras de empresa, y evitar las que no tienen noticia.
   - Probar el objetivo 4R y otras horas de cierre.
4. Si nada de esto llega a +0,2 R, la conclusión honesta es que **en intradía con datos gratuitos no tenemos ventaja suficiente**. En ese caso conviene centrarse en el agente B (12 meses).

*Datos completos: [informe automático](2026-11-15-backtest-orb-gainers.md) · `backtest/resumen.json` · `backtest/datos/`.*
