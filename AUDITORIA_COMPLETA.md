# Auditoría completa · trading-lab

**Fecha:** 17-nov-2026 (madrugada). **Base:** `main` en el commit `e810765` (incluye los pasos 0-10 de la noche del 16-nov).
**Rama de trabajo:** `claude/project-thread-ikv53s`. Nada de esto está en producción hasta que Ruben lo apruebe.

## Resumen en 5 líneas

1. **La base es razonable y no hay que reconstruirla**: programas en Python que dejan archivos, GitHub Actions que los ejecuta gratis y un panel estático. Coste cero y todo en demo. Eso se conserva.
2. **El fallo más grave no está en el código, sino en que nadie vigila si los automatismos se ejecutan.** GitHub solo ha lanzado **3 ejecuciones programadas en toda la vida del repo**. El bot del corto del hueco **nunca ha operado por horario** (solo 2 pruebas a mano el 15-nov).
3. **Los datos estaban viejos y el panel no lo gritaba**: el 17-nov el ranking y los avisos eran del domingo 15-nov, y la «carpeta del día» decía «REPX está en zona de entrada» con un precio de dos días antes.
4. **Los backtests son honrados pero optimistas en un punto clave**: el del corto del hueco supone un deslizamiento (diferencia entre el precio que ves y el que te dan) de 0,05 %, irreal en acciones que abren +50 %. El resultado real en demo es el único juez; el marcador y la fecha de decisión (15-feb-2027) ya existen y son lo correcto.
5. **Se construyó demasiado deprisa**: 12 PR en una noche sin que nadie pasara las pruebas automáticamente antes de fusionar. No encontré regresiones (139 pruebas pasan), pero no había red de seguridad.

## Cómo se hizo (qué miré y qué no)

- **Sí:** estructura completa, los 14 workflows (disparadores, permisos, secretos), el código del bot y su riesgo, los clientes de eToro y Alpaca, el marcador, los informes de los tres backtests, la carpeta del día, el generador del panel y el panel en móvil (capturas a 390 px), el historial de ejecuciones de GitHub Actions y los PR abiertos.
- **Pruebas iniciales:** `pytest` → **139 pasan** en 69 s. `node web/build.mjs` → construye (150 empresas, 31 informes, 937 hechos). Panel a 390 px: 10 pantallas sin desbordar a lo ancho y sin errores de JavaScript.
- **No:** no leí línea a línea los módulos de puntuación del ranking (`oportunidades.py`, `metricas.py`), ni los datos crudos, ni las skills de terceros. No puedo probar eToro ni Alpaca con claves reales desde aquí. Donde no hay prueba, lo marco como **E · no verificable**.

## Lo que pediste frente a lo que hay de verdad

| Tú dijiste | Lo que hay en el repo | Diferencia |
|---|---|---|
| Agente A: intradía, «1H y 4H» | Opera **dentro del mismo día** con velas de 1 minuto: escanea a las 9:34 de Nueva York, entra a las 9:35 y cierra a las 15:45. No hay nada en 1H ni 4H | Tu descripción era aproximada. Lo construido coincide con lo que acordamos el 15-nov (mismo día, Nasdaq). Si de verdad quieres 1H/4H sería otra estrategia que habría que probar con el pasado antes |
| Agente B: 12 meses | Ranking, expedientes, marcador y entradas con horizonte de 12 meses; el detector x3 mira 3 años | Coincide. El de 2-3 años existe solo como estudio y **no pasó su listón** |
| Solo demo | Cumplido y bien protegido (ver A1) | — |
| Automatismos gratis | 14 workflows de GitHub Actions | Existen, pero **no se están ejecutando por horario con fiabilidad** (ver D1) |
| «Agentes» | No son agentes autónomos: son **programas con reglas fijas** + una sesión de Claude cada mañana (investigador diario). La única IA que decide algo es esa sesión, y solo propone | Conviene llamarlo por su nombre para no confundir automatización con inteligencia |

## Hallazgos

Clases: **A** correcto · **B** funciona pero mejorable · **C** mal diseñado o complejo de más · **D** defectuoso o contra nuestros objetivos · **E** no verificable.

### D · Defectos (lo primero que hay que arreglar)

**D1 · Nadie avisa cuando un automatismo no se ejecuta.**
- *Dónde:* todos los `.github/workflows/*.yml` con `schedule`.
- *Evidencia:* la API de GitHub devuelve **3 ejecuciones de tipo «schedule» en total** (agente-12m el 15-nov, vigilante y noticias el 16-nov a las 23:15 y 23:33). `corto-hueco.yml` tiene 2 ejecuciones, las dos a mano. El 16-nov por la noche `agente-12m` (22:30 y 23:40 UTC) no arrancó.
- *Por qué pasa:* el repo fue privado con el límite de gasto agotado hasta las 23:20 del 16-nov; además GitHub retrasa o se salta ejecuciones programadas. Desde que es público debería mejorar, pero **no está comprobado** (E).
- *Consecuencia:* datos viejos sin aviso, bot que no opera, y la decisión del 15-feb-2027 puede llegar con menos de 40 operaciones solo porque el bot no arrancó.
- *Alternativas:* (1) confiar y mirar a mano; (2) un vigía que mida la edad de cada dato y la enseñe arriba del todo en el panel; (3) un disparador externo de pago o con tu token.
- *Elegida:* la 2. Hecho en este PR: `lab salud` + «Estado del sistema» en la portada del panel, que calcula la edad al abrirlo (funciona aunque GitHub no ejecute nada). La 3 queda descartada por coste y por seguridad.

**D2 · El bot podía dejar una posición abierta sin apuntarla.**
- *Dónde:* `src/tradinglab/intradia/corto_hueco/sesion.py`, función `operar`.
- *Evidencia:* la lista de posiciones abiertas se guardaba **solo al final** del bucle. Si tras abrir un corto fallaba cualquier cosa con la siguiente candidata (eToro devuelve algo raro, corte de red), el programa moría sin apuntar la primera. El cierre de las 15:45 solo cierra lo apuntado.
- *Consecuencia:* un corto vivo toda la noche con solo el stop del 15 %, contra la regla «todo cerrado el mismo día», y sin aviso ni registro.
- *Elegida:* guardar el estado **justo después de cada orden** y aislar los fallos por candidata. Hecho en este PR, con 2 pruebas nuevas.

**D3 · La carpeta del día presentaba precios viejos como si fueran de hoy.**
- *Dónde:* `src/tradinglab/medio_plazo/carpeta_dia.py` → `investigacion/hoy.md`.
- *Evidencia:* `hoy.md` del 16-nov: «REPX a 44,40 $ está en su zona de entrada» con precios del 15-nov 16:27 UTC (en realidad, del cierre del viernes 13). El investigador diario lee **solo** ese archivo para proponer entrada, stop y objetivo.
- *Consecuencia:* propuestas con precio de entrada basadas en un precio que ya no existe. Justo lo contrario de tu prioridad nº 1 (fuentes fiables con fecha).
- *Elegida:* si los precios tienen más de 1 día de bolsa, la carpeta lo dice arriba en grande y marca las zonas de entrada como «sin confirmar». Hecho en este PR, con prueba.

**D4 · Ninguna prueba se ejecutaba antes de fusionar.**
- *Dónde:* no existía ningún workflow de pruebas generales (solo dos parciales dentro de backtests).
- *Consecuencia:* 12 PR fusionados en una noche sin comprobación automática. Un error en `cli.py` rompería a la vez el bot, el ranking y las noticias.
- *Elegida:* `ci.yml`: en cada PR pasa las 142 pruebas, construye el panel y comprueba que arranca sin errores. Gratis (repo público). Hecho en este PR.

### C · Mal diseñado o complejo de más

**C1 · El panel es un solo archivo de 135 KB con 40 pantallas y la portada no prioriza.** `web/index.html`. La portada abría con 4 cifras y luego un texto largo; el estado de los datos estaba escondido en «Más → Fuentes»; había 15 rutas, varias de estudios ya cerrados, al mismo nivel que lo importante. → Rediseño en este PR (ver `REDISENO_UX_UI.md`). No lo reescribo entero: nuevo sistema visual, portada y navegación; las pantallas de detalle se conservan y heredan el estilo.

**C2 · Diez workflows escriben en `main` cada uno por su cuenta** con `git pull --rebase || true; git push`. Si el rebase falla, el `|| true` lo tapa y el `push` falla después: el trabajo se pierde con un error poco claro. Solo tres comparten grupo de concurrencia. → No lo cambio hoy (riesgo de romper lo que funciona el día que arranca el bot); queda en pendientes con la solución: un único paso reutilizable de «guardar en el repo» con reintentos.

**C3 · Restos del principio que confunden:** `dashboard/app.py` (panel antiguo en Streamlit, solo PC), `scripts/*.bat` (Windows) y la dependencia `streamlit` en `pyproject.toml`, cuando no tienes PC. El agente A original (`intradia/sesion.py`, Alpaca + revisor IA) ya no lo lanza ningún workflow. → Se conservan (no borro nada funcional), marcados como «histórico» en el mapa.

**C4 · Se construyó más de lo que se puede validar.** En 3 días: 6 estrategias intradía, ranking de 8 factores, perfiles «duplicar» y «+500 %», radar, vigilante, detector de inflexión, marcador, autopsias. Los backtests dicen que casi nada aporta ventaja (ver B1). El proyecto necesita **menos piezas nuevas y más semanas de datos reales**.

### B · Funciona, pero mejorable

**B1 · Rigor de los backtests (lo bueno y lo flojo).**
- *Bueno:* incluyen costes, comparan contra el universo y contra el azar, el detector de inflexión se ajustó en 2014-20 y se comprobó en 2021+, y los informes dicen claramente cuándo algo **no** funciona (la nota del ranking «aporta poco o nada»: +0,4 % al año; el detector «no pasa el listón»).
- *Flojo 1 · deslizamiento:* `config/laboratorio_intradia.yaml` usa 0,05 % por lado para todo. En una acción pequeña que abre +50 % la horquilla (diferencia entre compra y venta) suele ser de 0,5-2 %. El +0,245 R «como el bot» puede quedarse en nada.
- *Flojo 2 · umbral elegido mirando el resultado:* el «hueco ≥ +50 %, 3 al día» se eligió sobre los mismos 10 años en los que luego se mide. No hay periodo de comprobación aparte, así que la cifra está inflada por construcción (sobreajuste).
- *Flojo 3 · ¿se podía vender en corto?:* el pasado no sabe si eToro dejaba vender cada acción aquel día. El bot real descartará muchas.
- *Flojo 4 · supervivencia (agente B):* solo están las empresas que cotizan hoy. Está avisado en el informe, pero no corregido (no hay fuente gratis de precios de empresas desaparecidas).
- *Decisión:* no «arreglo» cifras históricas. El marcador real en demo manda. Pendiente: repetir el backtest del corto con 0,5 % y 1 % de deslizamiento para tener un rango honrado.

**B2 · El marcador del bot** (`corto_hueco/marcador.py`) está bien pensado: cuenta como −1 R las operaciones que desaparecen (stop supuesto), así no esconde las pérdidas. Mejorable: el resultado es «aproximado» (precio de venta en el momento, no el de ejecución real de eToro).

**B3 · Regla de fuentes** (`medio_plazo/regla_fuentes.py`): una web desconocida cuenta como nivel 1 (oficial). Es una puerta abierta, pero la alternativa simple (desconocida = nivel 3) rechazaría las notas de prensa en la web de cada empresa, que son fuente legítima. → Pendiente: lista de dominios de empresa por ticker en el expediente.

**B4 · Código duplicado menor:** seis funciones `_num` y tres lectores de CSV repartidos. No causa fallos hoy. No lo toco (cambiar por cambiar es riesgo sin beneficio).

**B5 · La calculadora de entrada** usa probabilidades de escenarios que escribe Claude en cada `tesis.md`. Son opiniones, no frecuencias medidas. El panel debe llamarlas «supuestos» hasta que el marcador de aciertos tenga un año de historia.

**B6 · Instrucciones (`CLAUDE.md`)** desfasadas: no listaba `laboratorio-demo.yml`, `radar-resultados.yml` ni `vigilante-intradia.yml`, y no tenía protocolo de verificación. → Actualizado en este PR (ver `MEJORA_CONTINUA.md`).

### A · Correcto y justificado (se conserva)

- **A1 · Solo demo, bien blindado.** eToro: lista blanca de rutas con `/demo/` y rechazo de cualquier ruta con `/real` (`corto_hueco/etoro.py`). Alpaca: `paper=True` fijo y URL de paper fija. Pruebas en `tests/test_seguridad.py`. Los secretos solo viven en GitHub; no hay ninguna clave en el repo.
- **A2 · El riesgo es código sin IA y manda** (`corto_hueco/riesgo.py`): 1 % por operación, máximo 3 al día, 10 % por posición, 30 % en total, freno si la cuenta cae un 10 %.
- **A3 · Arquitectura de coste cero**: Python + archivos en git + panel estático. Sin base de datos ni servidor que mantener. Para un solo usuario es lo correcto.
- **A4 · Registro con motivo** de cada decisión del bot (`registro.csv` + un `.md` por día) y libro de predicciones que solo añade (no se puede maquillar el pasado).
- **A5 · Gasto cero real**: la lectura con Haiku está apagada (`ia.activar: false`) y no hay ninguna otra llamada de pago.
- **A6 · Decisión fijada de antemano** para el bot (15-feb-2027: <40 operaciones o <+0,1 R → apagar). Es la mejor práctica del proyecto.

### E · No verificable con lo que tengo

- **E1** · Que el cron de GitHub vaya a lanzar hoy el bot a las 15:02-15:34. Solo se sabrá hoy. El panel nuevo lo enseñará.
- **E2** · Que eToro acepte de verdad las órdenes de corto del bot (las pruebas del 15-nov fueron ensayos sin orden, en domingo).
- **E3** · Que alguna estrategia sea rentable en el futuro. Ningún backtest lo demuestra.
- **E4** · El panel en un móvil físico (lo he probado en un navegador a tamaño de móvil, no en tu teléfono).

### Otros trabajos en paralelo que he visto (para que no choquen)

- **PR #69** (borrador, rama `audit/reingenieria-ux-20261116`, otro asistente): otra auditoría con los **mismos nombres de documento** que este PR. Coincido con sus hallazgos sobre supervivencia y fechas por fuente; no detectó D1, D2 ni D3. Su cambio en la regla de fuentes (desconocida = nivel 3) tiene el problema descrito en B3. **No se pueden fusionar los dos**: elige uno (recomiendo este y cerrar el #69).
- **PR #71** (borrador): un «agente C» de EUR/USD con MT5 y Haiku. Choca con dos acuerdos tuyos (sin forex; gasto cero) y con el hallazgo C4. No lo toco; decídelo tú.
- **PR #13 y #44**: abiertos desde hace días y ya superados. Convendría cerrarlos.

## Notas iniciales (antes de los cambios)

Escala: 0 inservible · 5 funciona a medias · 10 sólido y comprobado.

| Dimensión | Nota | Por qué (evidencia) |
|---|---|---|
| Calidad arquitectónica | 6 | Simple y de coste cero (A3), pero todo cuelga de un cron que casi no se ha ejecutado (D1) y 10 workflows escriben en `main` sin orden (C2) |
| Calidad y mantenibilidad del código | 5 | 139 pruebas y módulos pequeños; panel de 135 KB en un archivo (C1), sin CI (D4), restos sin uso (C3) |
| Fiabilidad de los datos | 4 | Fuentes primarias bien elegidas, pero datos de 2 días mostrados como actuales (D3) y sin control de frescura |
| Rigor en la validación financiera | 5 | Costes, comparación con azar y conclusiones honradas; deslizamiento irreal, umbral sobreajustado y supervivencia (B1) |
| Experiencia visual UX/UI | 5 | Coherente y con colores con significado; portada sin jerarquía y 15 rutas al mismo nivel (C1) |
| Experiencia móvil | 6 | No desborda y tiene barra inferior; mucho texto seguido y tablas largas |
| Seguridad y gestión del riesgo | 7 | Demo blindado (A1) y riesgo sin IA (A2); el fallo D2 podía dejar un corto sin cerrar |
| Automatización y observabilidad | 3 | 14 workflows pero 3 ejecuciones programadas en total y ningún aviso de fallo (D1) |
| Claridad de la información | 5 | Lenguaje sencillo y ayuda; no distingue bien hecho / supuesto / propuesta ni dato fresco / viejo |
| Facilidad de evolución futura | 5 | Fácil añadir un módulo; difícil tocar el panel o un workflow sin romper otro |

Las notas de después están en `CAMBIOS_REALIZADOS.md`.

## Prioridades

1. **Hoy:** comprobar en el panel si el bot arrancó a las 15:02-15:34 (E1). Si no, lanzarlo a mano o aceptar que el cron de GitHub no sirve para algo con hora exacta.
2. **Esta semana:** no construir nada nuevo. Dejar que se acumulen datos reales y mirar el estado del sistema cada día.
3. **Después:** rango honrado del backtest del corto (B1), ordenar la escritura de los workflows (C2), dominios de empresa en la regla de fuentes (B3).
