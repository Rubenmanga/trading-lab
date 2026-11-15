# ¿Se puede anticipar qué acciones serán las que más suben del día? · Investigación del 15-nov-2026

**Resumen en 5 líneas**
1. Las 8-10 acciones que suben un +15 % a +70 % cada día casi siempre tienen **una noticia detrás** (resultados, FDA, compra de la empresa, contrato) o son acciones **muy pequeñas y con pocas acciones en circulación** que se disparan con poco dinero, a veces por manipulación.
2. **Adivinarlas la noche antes es casi imposible:** son ~0,2 % de las ~5.000 acciones de EE. UU. La mayoría de esas noticias salen **por la noche o antes de abrir**, así que nadie las sabe con antelación (salvo quien usa información privilegiada, que es ilegal).
3. Lo que **sí** se puede medir gratis es **detectarlas pronto**: entre las 10:00 y las 15:30 de Madrid (premercado de EE. UU.) ya se ven subiendo, con mucho volumen y una noticia. La pregunta real no es «¿cuál subirá?», sino «**si la compro a primera hora, ¿gano de media?**».
4. La evidencia es dura: muchas de estas acciones **se dan la vuelta** en el mismo día o los siguientes; el 97 % de los que hacen *day trading* durante más de un año pierde dinero; y hay muchas trampas (ampliaciones de capital, *pump & dump*).
5. Mi propuesta: **no arriesgar nada todavía**. Primero un **diario automático** de los top gainers (por qué subieron), luego un **backtest** con 5 años de datos gratis de Alpaca, y solo si sale rentable tras costes, un **escáner en la cuenta demo** del agente A. Te pido el visto bueno antes de construirlo.

---

## 1. Tu idea, en números
Tu planteamiento es: «si acierto 1 o 2 a la semana y reparto el dinero, voy ganando poco a poco». Tiene sentido, pero depende de **cuánto pierdes con las que fallan**. Lo importante no es acertar, sino la **esperanza matemática** (lo que ganas de media por operación, contando las buenas y las malas):

> Esperanza = (% de aciertos × lo que ganas cuando aciertas) − (% de fallos × lo que pierdes cuando fallas) − costes

Ejemplo sencillo: compras 5 candidatas al día, 25 a la semana, con 100 € en cada una.

| Escenario | Aciertos | Ganancia media si acierta | Pérdida media si falla | Resultado semanal |
|---|---|---|---|---|
| Optimista | 2 de 25 | +30 € | −3 € | 60 − 69 = **−9 €** |
| Con stop estricto | 2 de 25 | +30 € | −1,5 € | 60 − 35 = **+25 €** |
| Realista en estas acciones | 2 de 25 | +20 € (no vendes en el máximo) | −5 € (el stop salta con deslizamiento) | 40 − 115 = **−75 €** |

*Deslizamiento* = la diferencia entre el precio al que querías vender y el precio al que de verdad vendes. En acciones que se mueven un 10 % en minutos, un stop del 1 % puede ejecutarse al −3 % o −5 %.

Conclusión: **la idea solo funciona si las que fallan pierden muy poco**. Y justo en estas acciones es donde más difícil es perder poco. Por eso hay que medirlo con datos antes de jugarse un euro.

---

## 2. ¿Por qué suben tanto en un día?
Estos son los motivos habituales, de más a menos «limpios»:

| Motivo | Qué pasa | Subida típica | ¿Se sabe antes? |
|---|---|---|---|
| **Compra de la empresa (fusión/adquisición)** | Otra empresa anuncia que la compra pagando más que el precio actual (la *prima*). En biotech, la prima mediana fue del **42 % en 2025** y del **53 % en el 1.er semestre de 2026** ([Gibson Dunn](https://www.gibsondunn.com/wp-content/uploads/2026/07/Biopharma-M_A-Mid-Cap-Public-Target-Market-Survey.pdf)). | +20 % a +100 % | **No.** Se anuncia sin aviso, normalmente antes de abrir. |
| **Resultados trimestrales** | La empresa gana o vende mucho más de lo esperado, o sube sus previsiones. | +10 % a +40 % | **La fecha sí** (calendario de resultados), **la dirección no**: puede subir o bajar. |
| **FDA / datos de ensayos (biotech)** | Aprueban un fármaco o un ensayo sale bien. Es un *catalizador binario*: sale bien o mal, sin término medio. | +30 % a +300 % | **La fecha a veces** (la fecha PDUFA, que es el día límite de la FDA para decidir). Los datos de ensayos, casi nunca. |
| **Contrato o acuerdo grande** | Contrato con el Gobierno, una gran tecnológica, licencia de un fármaco… | +15 % a +100 % | No. |
| **Temas de moda** | La empresa anuncia algo relacionado con IA, cripto, cuántica, drones… y el público se lanza. | +20 % a +500 % | No, y suele acabar mal. |
| **Short squeeze** | Mucha gente había apostado a la baja (*vendido en corto*, es decir, venden acciones prestadas para recomprarlas más baratas). Una buena noticia les obliga a recomprar a la vez y el precio se dispara. | +20 % a +200 % | El *short interest* (cuánto está vendido en corto) se publica, pero **no dice cuándo** estallará. |
| **Poco *free float*** | El *free float* son las acciones que se pueden comprar y vender libremente. Si solo hay 2-5 millones, con muy poco dinero el precio se mueve muchísimo. | +30 % a +1.000 % | El float se conoce; el día de la subida, no. |
| **Contagio (*sympathy*)** | Sube una empresa y se arrastran las parecidas del mismo sector. | +10 % a +40 % | Se ve en directo, minutos después de la primera. |
| **Manipulación (*pump & dump*)** | Alguien compra barato, lo promociona en redes o WhatsApp y vende a los que entran tarde. Bloomberg calcula que afectó a **~1/4 de las empresas más pequeñas de Nasdaq desde 2023**, sobre todo de Asia ([The Star / Bloomberg, jul-2026](https://www.thestar.com.my/business/business-news/2026/07/25/foreign-microcap-ipos-dry-up-in-us)). Ejemplo: QMMM subió casi un 1.000 % en tres semanas y la SEC suspendió su cotización. | +50 % a +1.000 % | No. Y quien entra tarde pierde casi todo. |

**Patrón común:** casi todas las del top diario son **pequeñas** (menos de 2.000 M$, muchas por debajo de 300 M$), **baratas** (a menudo por debajo de 10 $), con **mucho volumen de repente** (5 a 50 veces su volumen normal) y con **una noticia publicada después del cierre o antes de abrir**.

---

## 3. Lo que dice la evidencia sobre si es predecible

**a) Antes de la noticia: no.** Un mercado como el de EE. UU. incorpora las noticias en segundos. Si se pudiera saber la víspera qué empresa van a comprar, sería información privilegiada (ilegal). Lo único que se puede anticipar son las **fechas** (resultados, FDA), no **hacia dónde** irá el precio.

**b) Después de la noticia: a veces sigue, muchas veces se da la vuelta.**
- Un estudio de Concretum Group (2012-2026, acciones de EE. UU.) apostaba **en contra** de las acciones que abrían con huecos muy grandes, porque tienden a darse la vuelta durante el día. Funcionó muy bien hasta 2022 y **desde entonces pierde**, porque demasiada gente hace lo mismo ([Concretum](https://concretumgroup.substack.com/p/identifying-stocks-to-fade)). Lección: **ni comprar ni vender estas acciones es una ventaja segura**, y lo que funciona deja de funcionar.
- El llamado **efecto MAX**: las acciones que han tenido una subida diaria enorme el último mes **rinden peor de media** en los meses siguientes. La gente paga de más por la «lotería» ([Bali, Cakici y Whitelaw y estudios posteriores](https://www.uni-trier.de/fileadmin/fb4/prof/BWL/FIN/Files/Maxing_out.pdf)).
- Los inversores particulares compran sobre todo las acciones que **llaman la atención** (noticias, volumen enorme, subidas extremas) y eso no les sale bien de media ([Barber y Odean, «All That Glitters»](https://ideas.repec.org/a/oup/rfinst/v21y2008i2p785-818.html)).
- La excepción más estudiada: tras **resultados muy buenos** de verdad, la acción tiende a seguir subiendo algo durante semanas (*deriva tras resultados*). Es la subida «más sana» de la lista.

**c) Hacer esto a diario es muy difícil para un particular.** En Brasil, de los que hicieron *day trading* más de 300 días, **el 97 % perdió dinero** y solo el 0,4-0,5 % ganó más que el sueldo de un cajero de banco ([Chague, De-Losso y Giovannetti, 2019](https://quantpedia.com/retail-day-trading-is-an-uphill-battle/)).

**d) Las trampas típicas de estas acciones:**
- **Ampliación de capital (dilución):** muchas empresas pequeñas aprovechan la subida para **emitir acciones nuevas** y venderlas. Al día siguiente (o esa misma tarde) la acción puede caer un 20-40 %. Se ve en la SEC con formularios **S-1, S-3, 424B** o en anuncios de «*registered direct offering*».
- **Paradas de cotización (*halts*):** si sube o baja muy rápido, la bolsa la congela 5 minutos. No puedes vender mientras está parada, y el stop no te protege.
- **Huecos y deslizamiento:** el stop del 1 % del agente A puede saltar al −5 %.
- **Spread enorme:** la diferencia entre el precio de compra y el de venta puede ser del 1-2 %. Pierdes eso nada más entrar.

**Veredicto honesto:** «predecir» 1 o 2 por semana **antes** de que suban no es realista. Lo que sí se puede intentar es **detectarlas en el premercado y comprobar con datos si existe alguna regla que gane de media** entrando a primera hora con un stop estricto. Puede que la respuesta sea «no hay ninguna»; eso también es un buen resultado, porque te ahorra perder dinero.

---

## 4. Qué señales previas se pueden medir gratis

| Señal | Qué es | Fuente gratis |
|---|---|---|
| **Hueco en premercado** (*gap*) | Cuánto sube antes de abrir respecto al cierre de ayer. Ej.: +12 % a las 9:00 de NY. | Alpaca (barras de 1 minuto con horario extendido; en el plan gratis, con 15 min de retraso) |
| **Volumen relativo** (*RVOL*) | Volumen del premercado comparado con lo normal. Un RVOL de 10 = 10 veces más de lo habitual. | Alpaca |
| **Noticia con hora** | Titular, hora y ticker. Si no hay noticia, peor señal (posible manipulación). | API de noticias de Alpaca (Benzinga, incluida gratis), Finnhub, SEC (8-K) |
| **Calendario de resultados** | Quién presenta resultados hoy antes de abrir o ayer al cierre. | Finnhub (calendario gratis) |
| **Calendario FDA** | Fechas PDUFA y congresos médicos. | Webs públicas de calendarios FDA, notas de prensa (con WebSearch) |
| **Free float y acciones en circulación** | Cuántas acciones se negocian. Menos de 10-20 M = se mueve mucho. | SEC (10-Q), Yahoo vía GitHub Actions |
| **Short interest** | % de acciones vendidas en corto. Más del 20 % = posible *squeeze*. | FINRA (cada dos semanas), volumen corto diario de FINRA |
| **Riesgo de dilución** | ¿Tiene un S-3 o un ATM (programa para vender acciones poco a poco) activo? ¿Poca caja? | SEC EDGAR |
| **Sentimiento en redes** | Cuánto se habla del ticker. | Difícil gratis y fácil de manipular; lo dejaría para el final |

**Ojo con las horas (Madrid):** el premercado va de 10:00 a 15:30; la sesión normal de 15:30 a 22:00. El agente A ya opera de 15:35 a 17:30, justo la franja en que más se mueven estas acciones. **Revolut** permite operar en premercado (4:00-9:30 NY) si activas el «horario extendido», pero solo con órdenes limitadas y acciones enteras ([ayuda de Revolut](https://help.revolut.com/en-FI/help/wealth/stocks/trading-stocks/when-can-i-trade/what-is-extended-market-hours/)). Para practicar seguimos en **Alpaca demo**, nunca con dinero real.

**Un detalle importante:** la lista de «más revalorizadas» que ves en Revolut se calcula **durante el día**. Cuando una acción aparece ahí, normalmente **ya ha subido**. Entrar en ese momento es comprar a quien entró antes.

---

## 5. Método propuesto para probarlo sin arriesgar nada
Todo con coste cero (GitHub Actions + claves de Alpaca demo + Finnhub gratis), todo en la nube y sin tocar el agente de 12 meses. Encaja en el **agente A (intradía)**.

### Fase 1 · Diario automático de top gainers (2-4 semanas, pasivo)
- Cada día al cierre, GitHub Actions guarda las **50 que más suben** (el «screener de movers» de Alpaca) con su precio, volumen, capitalización, float y **las noticias del día** de cada una.
- Clasifica el motivo (resultados, FDA, fusión, contrato, sin noticia…) y si había **hueco en premercado** a las 9:00 de NY.
- Resultado: un informe semanal en el panel que responde con **datos reales** a «¿por qué suben?» y «¿cuántas se veían ya en el premercado?».

### Fase 2 · Backtest con datos históricos (una vez)
*Backtest* = probar una regla con datos del pasado como si la hubieras seguido.
- Descargar de Alpaca las velas diarias y de 1 minuto (incluido premercado) de **2021 a 2026** de todas las acciones de EE. UU., **incluidas las que dejaron de cotizar** (si no, el resultado sale demasiado bonito: es el *sesgo de supervivencia*).
- Preguntas que responde:
  1. De las que acaban el día a **+15 % o más**, ¿cuántas ya subían **+5 % / +10 %** a las 9:00 de NY con RVOL alto? (¿se pueden detectar a tiempo?)
  2. De todas las que cumplen la señal a las 9:00 (no solo las ganadoras), ¿cuántas acaban subiendo y cuántas se dan la vuelta? (esto evita engañarse mirando solo las que salieron bien)
  3. Si se compran a las 9:35 con **stop del 1 %, objetivo 3R y trailing stop** (las reglas del agente A), **¿qué esperanza da tras costes**, *spread* y deslizamiento realista?
  4. ¿Qué filtros mejoran el resultado? (con noticia vs. sin noticia, float, precio, motivo, sin riesgo de dilución)
- **Criterio para seguir, fijado de antemano:** al menos 200 operaciones en el histórico, esperanza positiva tras costes (≥ +0,2 R por operación, donde *R* = lo que arriesgas en cada una) y que funcione **en cada año** por separado, no solo en uno bueno.

### Fase 3 · Escáner diario en la cuenta demo (4-8 semanas)
Solo si la fase 2 sale bien:
- A las 9:00-9:25 de NY (15:00-15:25 Madrid), un escáner publica en el panel las **3-5 candidatas** del día con su motivo, y un aviso al móvil.
- El agente A las opera **en la demo de Alpaca**, con las reglas de riesgo de siempre (riesgo 0,5 % por operación, stop, cierre forzado). El revisor IA lee la noticia y puede **frenar**, nunca forzar una entrada. Todo queda registrado con su motivo.
- Tras al menos **40 operaciones** en demo, comparamos con el backtest. Si se parecen, tendremos algo real. Si no, se descarta.

### Lo que **no** haría
- Comprar acciones que suben **sin noticia** o que son salidas a bolsa recientes de empresas diminutas: es el terreno del *pump & dump*.
- Perseguir lo que ya aparece en el top de Revolut a media sesión.
- Usar dinero real antes de terminar las tres fases.

---

## 6. Siguiente paso
Si te parece bien, empiezo por la **Fase 1 (diario automático)**, que es pequeña y no opera nada, y preparo la **Fase 2 (backtest)** en paralelo. Las dos necesitan código nuevo en el repo, así que te pediré que revises el pull request antes de que entre.

*Esto es investigación para aprender, no una recomendación de compra. Solo cuenta demo.*

**Fuentes:** [Concretum Group: acciones para «fadear»](https://concretumgroup.substack.com/p/identifying-stocks-to-fade) · [Quantpedia sobre Chague et al.](https://quantpedia.com/retail-day-trading-is-an-uphill-battle/) · [Barber y Odean (2008)](https://ideas.repec.org/a/oup/rfinst/v21y2008i2p785-818.html) · [«Maxing out» (efecto MAX)](https://www.uni-trier.de/fileadmin/fb4/prof/BWL/FIN/Files/Maxing_out.pdf) · [Gibson Dunn, primas en biopharma](https://www.gibsondunn.com/wp-content/uploads/2026/07/Biopharma-M_A-Mid-Cap-Public-Target-Market-Survey.pdf) · [The Star / Bloomberg, microcaps y pump & dump](https://www.thestar.com.my/business/business-news/2026/07/25/foreign-microcap-ipos-dry-up-in-us) · [Alpaca: movers](https://docs.alpaca.markets/reference/movers-1) · [Alpaca: datos de mercado](https://docs.alpaca.markets/docs/about-market-data-api) · [Alpaca: noticias](https://docs.alpaca.markets/docs/historical-news-data) · [Revolut: horario extendido](https://help.revolut.com/en-FI/help/wealth/stocks/trading-stocks/when-can-i-trade/what-is-extended-market-hours/)
