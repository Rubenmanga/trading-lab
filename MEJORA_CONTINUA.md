# Mejora continua: cómo se trabaja en este repo

**Fecha:** 17-nov-2026. Para Claude y para cualquier otro asistente. Las reglas operativas cortas están en `CLAUDE.md`; aquí está el porqué.

## Resumen en 5 líneas

1. Todo cambio sigue **Evidencia → Hipótesis → Alternativas → Decisión → Implementación → Prueba → Revisión**.
2. **«Funciona» solo se dice con una prueba ejecutada**; si no se pudo probar, se escribe «no verificado».
3. **Un PR, una cosa**, y ningún PR de código se fusiona sin que pasen las pruebas automáticas (`ci.yml`).
4. Antes de construir algo nuevo hay que poder responder: **¿qué decisión de Ruben mejora y cómo sabremos si no sirve?**
5. Cada estrategia tiene **un listón fijado antes** de ver los resultados y una fecha para apagarla.

## Qué falló en la forma de trabajar (auditoría del 17-nov)

| Qué pasó | Por qué | Regla que lo evita |
|---|---|---|
| 12 PR fusionados en una noche | Hilos en paralelo, cada uno «terminaba» al fusionar | Regla 3 y 8 |
| Se dio por hecho que los cron funcionaban | Se comprobó el código, no las ejecuciones | Regla 2: comprobar el efecto, no la intención |
| Propuestas con precios de dos días antes | Nadie miraba la fecha del dato de entrada | Regla 5 |
| Tres estudios grandes en tres días (duplicar, +500 %, radar) | Cada petición se convirtió en un módulo nuevo | Regla 4 |
| Backtest con umbral elegido sobre los mismos datos | No había protocolo de validación escrito | Regla 6 |
| Instrucciones desfasadas en `CLAUDE.md` | Se añadían piezas sin actualizar el mapa | Regla 9 |

## El protocolo

**1. Evidencia.** Antes de opinar, mirar: el archivo, la ejecución real (`actions_list`), la fecha del dato. Citar ruta o identificador.

**2. Hecho, estimación o propuesta.** En cada informe y en cada respuesta a Ruben, distinguir:
- **Hecho:** tiene fuente primaria y fecha.
- **Estimación:** sale de un cálculo con supuestos. Se dicen los supuestos.
- **Propuesta:** opinión de la IA. Se apunta en `predicciones.csv` para comprobarla después.
- **Pasado:** resultado de un backtest. Nunca se escribe en futuro.

**3. Alternativas.** Para toda decisión que cueste más de una hora o cambie cómo usa Ruben el proyecto: al menos «no hacer nada», «lo mínimo» y «lo completo», con coste y riesgo de cada una. Para un arreglo pequeño basta una línea.

**4. Pregunta de entrada para piezas nuevas.** ¿Qué decisión mejora? ¿Con qué número sabremos en N semanas que no sirve? Si no hay respuesta, no se construye: se anota como idea.

**5. Frescura.** Todo programa o sesión que use un precio comprueba su fecha. Más de 1 día de bolsa: se avisa y **no** se propone precio de entrada con él.

**6. Validación de estrategias (listón mínimo para pasar a demo).**
- Reglas y umbrales fijados con una parte de los datos y **comprobados en otra** que no se ha mirado.
- Costes realistas: comisión, horquilla y deslizamiento **según el tipo de acción** (no un 0,05 % para todo).
- Comparación con el azar y con «no hacer nada» (el índice).
- Al menos 100 operaciones en la parte de comprobación y resultado positivo en la mayoría de los años.
- Límites escritos: supervivencia, si se podía operar de verdad, datos que faltan.
- Listón y fecha de apagado **escritos antes** de empezar la demo (como el del bot: 15-feb-2027).
- Una estrategia que no pasa se queda como «informativa». No se retoca hasta que pase.

**7. Prueba.** Tras tocar código: las pruebas de ese módulo. Tras tocar el panel: `node web/build.mjs && node web/test/humo.mjs` y capturas a 390 px si cambia algo visible. Tras tocar un workflow: lanzarlo a mano una vez (`workflow_dispatch`) y leer el resultado.

**8. Revisión antes de fusionar.** Releer el diff completo como si fuera de otro. Buscar: qué rompe si falla la red, qué pasa con el archivo vacío, qué pasa si se ejecuta dos veces. Código → PR con las pruebas en verde y el visto bueno de Ruben si cambia lo que él ve o cómo opera el bot. Datos (`investigacion/`) → se publican solos, como hasta ahora.

**9. Dejarlo dicho.** Actualizar el mapa de `CLAUDE.md` en el mismo PR. Decir a Ruben qué se probó, qué no y qué queda.

## Comprobaciones automáticas (gratis)

| Qué | Dónde | Cuándo |
|---|---|---|
| 149 pruebas de Python | `.github/workflows/ci.yml` → `pytest` | Cada PR que toque código, config, panel o workflows |
| El panel se construye y su JavaScript es válido | `ci.yml` → `web/test/humo.mjs` | Igual |
| Fuentes y fecha del precio en cada análisis | `publicar-investigacion.yml` → `lab medio regla-fuentes` | Cada PR de `investigacion/` |
| ¿Se ejecutó cada automatismo? | Panel → «Estado del sistema» | Al abrir el panel |
| ¿Acertaron las propuestas? | `marcador.yml` → panel «Aciertos» | Cada viernes |
| ¿Cumple el bot lo que decía el pasado? | `lab corto marcador` → panel «Bot» | Cada día de bolsa |

## Si un automatismo falla (recuperación)

1. Abrir el panel → «Estado del sistema». Dice cuál, desde cuándo y qué fecha se esperaba.
2. **Un día de retraso:** esperar a la siguiente pasada. Festivo en EE. UU.: es normal.
3. **Parado (dos citas perdidas):** pedir a Claude «lanza a mano el automatismo parado». Claude usa `actions_run_trigger` sobre el workflow indicado y comprueba después que la fecha cambia.
4. **Falla al ejecutarse** (no es que no arranque): Claude lee el registro de esa ejecución, arregla en una rama, PR con pruebas.
5. **El bot dejó algo abierto:** el aviso (issue de GitHub) lo dice. `lab corto cerrar` con el workflow a mano (acción `cerrar`, ensayo `false`). Si no cierra, cerrarlo en la web de eToro demo.
6. Si un workflow no arranca por horario tres días seguidos: es hora de la opción siguiente de `DECISIONES_ARQUITECTURA.md` (decisión 2).

## Conflictos entre instrucciones (resueltos)

- **«Plan corto y esperar el OK» frente a «trabaja con autonomía»:** el plan previo sigue siendo obligatorio para trabajo grande **salvo** que Ruben pida expresamente ejecutar (como en esta auditoría). Siempre en rama; nunca fusionar a `main` cambios de código o de panel sin su visto bueno.
- **«Ruben deja que Claude fusione los PR» frente a «quiere ver los cambios antes»:** los PR que **solo** tocan `investigacion/` se publican solos. Todo lo demás espera su OK.
- **«Cada token cuenta» frente a «no recortes calidad»:** se ahorra en lecturas a ciegas y repeticiones, no en comprobar. Una prueba ejecutada nunca es un gasto recortable.
- **«Regla 4: decisiones en `data/lab.db`»:** desfasada. El bot actual registra en `investigacion/corto-hueco/registro.csv`. Corregido en `CLAUDE.md`.
