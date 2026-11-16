# Revisión estratégica del proyecto (16-nov-2026)

**Resumen en 5 líneas**
1. El proyecto ha crecido muy rápido a lo ancho (13 automatismos, 2 bots, 6 estrategias) y poco a lo hondo: **nada mide todavía si los análisis aciertan**.
2. La puerta de entrada del agente B (la nota del ranking) **no encuentra las x3-x4**: en el backtest (prueba con el pasado) las mejores notas tenían menos pelotazos que la media (5,4 % frente a 6,2 %).
3. Lo que más acerca al «bufete» no es más código, sino tres piezas: **expediente por acción**, **libro de predicciones con marcador** y **carpeta del día** para el investigador.
4. Para buscar x3-x4 hay que cambiar de pregunta: de «¿qué empresa es buena?» a «**¿en qué empresa acaba de cambiar algo?**» (punto de inflexión), y comprobarlo con el pasado.
5. El agente A (intradía) debe **congelarse**: un solo bot, un marcador y una fecha para decidir si sigue.

> Este documento no cambia código. Es el plan para que hilos más ligeros lo ejecuten paso a paso.

---

## A. Qué está mal planteado o sobra

| Problema | Por qué importa | Qué hacer |
|---|---|---|
| **Se construye más rápido de lo que se comprueba.** 54 cambios en 3 días. | Sin marcador, no se sabe qué parte sirve. | Regla nueva: nada nuevo sin decir antes cómo se medirá. |
| **La nota del ranking busca la «empresa típica buena», no el pelotazo.** Top 20: +10,2 %/año frente a +9,7 % del conjunto. | Tu objetivo son las excepciones; la nota las deja fuera (las x3 tenían *peor* calidad y *más* crecimiento antes de subir). | Mantener el ranking como filtro de seguridad, no como buscador. Añadir un detector de inflexión (idea 4). |
| **El 20 % de la nota y el perfil «duplicar» dependen de los precios objetivo de los analistas.** | No se puede probar con el pasado (el historial es de pago) y los objetivos suelen ir por detrás del precio. | Bajarlo a dato informativo hasta que las fotos diarias que ya se guardan den 6-12 meses de historia. |
| **El «precio de entrada» sale del criterio de cada análisis**, sin método fijo. | Dos análisis de la misma empresa pueden dar zonas distintas. | Calcularlo siempre igual, con escenarios (idea 5). |
| **El registro está repartido** en 6 sitios (`seguimiento/`, `vigilante/`, `watchlist.csv`, `historico/`, `alertas.md`, avisos de GitHub). | Tu prioridad n.º 3 (registro de todo por acción) no se cumple: no hay un sitio donde leer la historia de una empresa. | Un expediente por acción (idea 1). |
| **Algunos análisis usaron webs intermediarias con datos viejos.** | Choca con tu prioridad n.º 1. | Regla de fuentes con fecha y comprobación automática (idea 3). |
| **Agente A: 10 años de datos dicen que solo una estrategia gana, y poco** (corto del hueco: +0,11 a +0,24 R, bajando con los años, y en la vida real muchas de esas acciones no se pueden vender en corto). | Cada estrategia nueva que se prueba aumenta el riesgo de «sobreajuste» (encontrar por casualidad algo que funcionó en el pasado y no se repite). | Congelar (idea 7). |
| **El vigilante guarda un cambio en el repo cada 10 minutos.** | Ensucia el historial y cada cambio puede lanzar una publicación del panel en Vercel (el plan gratis tiene tope diario; comprobar). | Guardar solo cuando haya un evento nuevo y al cierre. |

**Sobra o se puede apagar sin perder nada:** la cuenta sombra diaria de las 5 estrategias que pierden en 10 años; el filtro de 8 puntos (ya es solo informativo); uno de los dos vigilantes (`vigilante-bucle` y `vigilante-intradia` hacen lo mismo); `prueba-etoro.yml`; el perfil «+500 %» como búsqueda aparte (lo sustituye la idea 4). Revisar si la carpeta `dashboard/` se usa.

---

## B. Las 8 ideas, ordenadas por impacto / coste

### 1. Expediente por acción (impacto muy alto · coste bajo)
Una carpeta por empresa en seguimiento: `investigacion/expedientes/TICKER/`.
- `eventos.csv`: una línea por hecho, solo se añade, nunca se borra. Columnas: `fecha, tipo, resumen, fuente_url, fecha_fuente, precio_antes, reaccion_1d, reaccion_5d, reaccion_20d`.
- `tesis.md`: por qué interesa, qué la rompería, escenarios y precio de entrada vigente.
- Tipos de evento: resultados, 8-K (aviso oficial de hecho relevante), Form 4 (compras/ventas de directivos), ampliación de capital (S-3, 424B5), ensayo clínico, FDA, contrato, movimiento anómalo de precio.
- Lo rellena un «archivero» en GitHub Actions, **sin IA**. La página de cada empresa en el panel muestra la línea de tiempo.

Esto cumple tus prioridades 2 y 3 y además responde con datos a tu pregunta de fondo (por qué unas caen y otras suben): cada evento queda con su reacción.

### 2. Libro de predicciones + marcador (impacto muy alto · coste bajo)
Cada análisis termina en predicciones comprobables y con fecha: veredicto, precio de entrada, objetivo, punto donde la tesis se rompe, probabilidad y fecha de revisión. Casi todo existe ya en `watchlist.csv`; falta **no sobrescribirlo** (guardar cada versión) y puntuarlo.
- Un trabajo semanal compara cada predicción con lo ocurrido y con el índice de small caps (IWM).
- Página «Marcador» en el panel: % de aciertos, rentabilidad frente a IWM, y **calibración** (cuando el agente dice «70 % probable», ¿pasa 7 de cada 10 veces?).
- Sirve igual para el agente A (operaciones demo) y para tus compras reales.

Sin esto, dentro de 6 meses seguiremos sin saber si el bufete es bueno.

### 3. Regla de fuentes, comprobada por máquina (impacto alto · coste bajo)
- Todo dato de un informe lleva fuente y fecha. Niveles: **1** = oficial (SEC, FDA, ClinicalTrials.gov, nota de prensa de la empresa); **2** = datos de mercado (Alpaca, Finnhub); **3** = webs intermediarias, solo si se dice y nunca para precio o caja.
- Los informes acaban con una tabla `dato | valor | fuente | fecha`. Una comprobación automática rechaza el informe si falta o si el precio tiene más de 2 días.
- Fuentes gratis y oficiales que aún no se aprovechan:
  - SEC EDGAR `submissions`: lista diaria de todo lo que presenta cada empresa.
  - SEC «Insider Transactions Data Sets»: histórico gratis de compras de directivos desde 2006. **Esto permite probar con el pasado el factor de directivos**, que se daba por imposible.
  - USAspending.gov: contratos públicos (útil para defensa, p. ej. RCAT).
  - FINRA: posiciones cortas, cada 15 días.
  - openFDA y ClinicalTrials.gov v2.
  - RSS de notas de prensa (GlobeNewswire, PR Newswire, BusinessWire).

### 4. Detector de inflexión para buscar x3-x4 (impacto alto · coste medio)
Buscar empresas donde **algo acaba de cambiar**, con las cuentas oficiales que ya se descargan:
- las ventas crecen más deprisa que el trimestre anterior (aceleración);
- el margen bruto mejora;
- los gastos crecen menos que las ventas;
- primer trimestre con caja positiva, o caja para más de 18 meses (no necesita emitir acciones);
- el número de acciones no se dispara (poca dilución);
- extra: 2 o más directivos comprando con su dinero en 30 días.

**Cómo se prueba (decidido antes de mirar):** con el motor de backtest que ya existe. La medida no es la rentabilidad media, sino cuántas x3 en 3 años hay en el 10 % mejor puntuado. Listón: al menos el doble de la base (12 % frente a 6,2 %), ajustando con 2014-2020 y comprobando en 2021-2026. Si no pasa, se descarta y se dice.

Aviso honesto: aun con un buen detector, la mayoría de candidatas no triplicará. Se gana con una **cesta de 10-15 posiciones pequeñas**, cortando las que rompen la tesis y dejando correr las que cumplen.

### 5. Precio de entrada con método (impacto alto · coste bajo)
Para cada empresa, tres escenarios (malo, normal, bueno), cada uno con valor estimado y probabilidad. De ahí sale:
- **valor esperado** = media de los tres ponderada por su probabilidad;
- **precio de entrada** = el más alto que cumple dos condiciones: lo que puedes ganar en el caso normal es al menos 3 veces lo que puedes perder en el malo, y el precio está por debajo del valor esperado con margen.

Se recalcula solo cuando el expediente recibe un evento que cambia un escenario. En apuestas de «todo o nada» (decisión de la FDA), no hay precio de entrada bueno: lo que se decide es el tamaño.

### 6. Carpeta del día + investigador diario barato (impacto alto · coste bajo en tokens)
GitHub Actions prepara cada mañana `investigacion/hoy.md`, corto (menos de una pantalla): eventos nuevos de tus acciones y de la lista de vigilancia, empresas que entran en el detector de inflexión, catalizadores de los próximos 14 días y qué acciones están dentro de su zona de entrada.
Una sesión ligera de Claude lee **solo ese archivo** y escribe «Propuestas de hoy» (máximo 200 palabras, con precio de entrada y motivo). Así el investigador diario cuesta muy poco de tu cuota: lo pesado lo hace Actions y la IA solo razona sobre un resumen.

### 7. Agente A: congelar y poner fecha (impacto medio · coste casi cero)
- Queda solo el bot del corto del hueco en demo, con su marcador (idea 2).
- **Fecha de decisión: 15-feb-2027.** Si hay menos de 40 operaciones o la media es menor de +0,1 R, se apaga.
- Cualquier estrategia nueva: hipótesis escrita antes, una sola prueba, datos partidos en dos mitades. Sin eso, no se prueba.
- Motivo: el tiempo y la cuota que consume el intradía se quitan al agente B, que es donde está tu objetivo de fondo.

### 8. «Autopsias» de resultados (impacto medio · coste bajo)
Tras cada presentación de resultados de una acción en seguimiento, 10 líneas en su expediente: qué se esperaba, qué salió, qué dijo la empresa del futuro (previsión), cuánto había subido antes y cómo reaccionó. Cada trimestre, un resumen de patrones. El radar ya dio la primera lección: superar previsiones y caer ocurre el 42 % de las veces, así que el resultado solo no basta; importa lo que ya estaba «descontado» en el precio.

---

## C. Plan por pasos (para hilos ligeros, uno por paso)

Cada paso es un PR pequeño con sus tests. Orden recomendado:

| Paso | Qué | Dónde | Hecho cuando… |
|---|---|---|---|
| 0 | Limpieza: vigilante guarda solo con evento nuevo y al cierre; apagar el segundo vigilante, la cuenta sombra de estrategias perdedoras y `prueba-etoro.yml` | `.github/workflows/`, `config/laboratorio_intradia.yaml` | Un día de bolsa deja menos de 10 cambios automáticos en el repo |
| 1 | Expediente: formato + archivero SEC (`submissions`) + reacción de precio (Alpaca) para cartera y lista de vigilancia | nuevo `medio_plazo/expediente.py`, `investigacion/expedientes/`, workflow diario | Cada acción seguida tiene `eventos.csv` con los últimos 12 meses y fuente en cada línea |
| 2 | Volcar al expediente lo ya guardado (`seguimiento/`, `vigilante/`, `lista-historial.csv`) y mostrar la línea de tiempo en la página de empresa | `web/build.mjs`, `web/index.html` | El panel muestra la historia de una empresa en una sola página |
| 3 | Libro de predicciones (`investigacion/predicciones.csv`, solo añadir) + puntuador semanal + página «Marcador» | nuevo `medio_plazo/marcador.py`, workflow semanal | Los 13 análisis ya escritos aparecen puntuados frente a IWM |
| 4 | Regla de fuentes: plantilla con tabla de fuentes en la skill `analizar-empresa-12m` + comprobación automática de informes | `.claude/skills/`, `tests/` | Un informe sin tabla de fuentes o con precio viejo no pasa |
| 5 | Carpeta del día `hoy.md` (sin IA) | nuevo `medio_plazo/carpeta_dia.py`, dentro de `agente-12m.yml` | `hoy.md` se genera a diario y cabe en una pantalla del móvil |
| 6 | Investigador diario: sesión ligera programada que lee `hoy.md` y escribe las propuestas | tarea programada de Claude | Una semana de propuestas, cada una apuntada en el libro de predicciones |
| 7 | Calculadora de precio de entrada con escenarios | `medio_plazo/entrada.py`, `tesis.md` | `lab medio entrada TICKER` da el mismo precio siempre con los mismos datos |
| 8 | Detector de inflexión + directivos (datos de la SEC) y su backtest con el listón de la idea 4 | `backtest12m/`, workflow `backtest-12m.yml` | Informe con el resultado: pasa o no pasa el listón del 12 % |
| 9 | Agente A: marcador del bot y recordatorio de la decisión del 15-feb-2027 | `investigacion/corto-hueco/` | El panel muestra operaciones, R medio y la fecha de decisión |
| 10 | Autopsias de resultados: plantilla y primer resumen trimestral | `expedientes/TICKER/` | Primera autopsia escrita tras los próximos resultados de una acción seguida |

**Regla para todos los pasos:** si un paso necesita descargar o calcular mucho, se hace en GitHub Actions y la sesión de Claude solo lee el resumen.

**Los tres primeros que más cambian el proyecto:** pasos 1, 3 y 8.
