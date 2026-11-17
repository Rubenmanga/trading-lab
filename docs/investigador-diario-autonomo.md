# Investigador diario del agente B: modo autónomo

## Qué quedó terminado

La primera versión (PR #63) tenía un validador y una skill de Claude, pero
dependía de una **tarea programada de Claude** para redactar las 3-5 ideas.
Esa tarea no puede ejecutarse cuando se agota la cuota de Claude.

Esta versión añade un motor **determinista y sin IA**:

- GitHub Actions: .github/workflows/investigador-diario.yml, laborables a las
  **08:17, Europe/Madrid** (la hora se ajusta sola al horario de verano).
- Lee investigacion/hoy.md, estado.json, watchlist.csv, entradas.json y
  el libro de predicciones existente. Todos son archivos que ya produce el
  proyecto. **No descarga cotizaciones ni consulta webs externas.**
- Usa los precios publicados en estado.json y marca su hora UTC en el informe.
  Si la carpeta o los precios tienen más de dos días o fecha futura, **falla**
  sin publicar nada. Las ejecuciones fallidas se ven en Actions.
- Elige hasta cinco valores **mencionados en hoy.md**, únicamente cuando
  existen precio, entrada, stop y objetivo coherentes.
- **No inventa niveles**: la calculadora (entradas.json) prevalece sobre el
  límite de la watchlist. Si falta calculadora, usa como **referencia teórica**
  el menor entre el precio observado y el límite de la watchlist, nunca como
  orden de compra. Stop y objetivo deben existir previamente en la watchlist.
- Considera binarios los catalizadores FDA/510(k) cercanos, los avisos de
  riesgos graves y los stops alcanzados. Son «evitar» o «vigilar».
- El modo autónomo **jamás produce «comprar_en_zona»**. No confirma noticias,
  valoraciones ni probabilidades de acierto; por tanto, no puede dar luz verde
  a una operación. El paso final es una revisión humana con fuentes primarias.
- Nunca fuerza tres ideas solo por rellenar una tabla. Si no hay al menos tres
  con datos y niveles válidos, **no escribe informe**.
- Excluye valores que ya aparecieron como PROP- en los últimos 30 días,
  escribe investigacion/propuestas/AAAA-MM-DD.md y usa el validador de
  medio_plazo/propuestas.py para añadirlos **una vez** a predicciones.csv.
- Solo modifica investigacion/propuestas/ y investigacion/predicciones.csv
  cuando se ejecuta desde la rama principal. En los PR ejecuta **solo tests**.

## Cómo usarlo

Tras aprobar y fusionar esta rama en main, GitHub programará la acción
automáticamente los días laborables. Para probarla manualmente:
**GitHub → Actions → Investigador diario sin Claude → Run workflow**.

Para reproducirlo localmente, desde la raíz del repositorio:

~~~bash
PYTHONPATH=src python -m pytest -q tests/test_propuestas.py tests/test_investigador_auto.py
PYTHONPATH=src python -m tradinglab.medio_plazo.investigador_auto
~~~

**Importante:** el generador no sustituye una investigación real, no conoce
la actualidad fuera de los archivos ni garantiza 3-5 candidatos diarios.
Los precios pueden corresponder al último cierre, no ser cotizaciones en
tiempo real. No ejecuta órdenes ni tiene acceso al bróker.

La skill .claude/skills/investigador-diario/SKILL.md sigue disponible como
alternativa manual cuando haya cuota de Claude. Si esa skill genera un informe,
se deben verificar sus datos y ejecutar el validador antes de publicarlo.

## Comprobaciones de aceptación

1. Se ejecutan tests/test_propuestas.py y tests/test_investigador_auto.py.
2. Con hoy.md antiguo se detiene sin tocar el libro.
3. Con menos de tres candidatos elegibles no inventa propuestas.
4. Ante FDA binaria/alerta crítica no propone comprar.
5. El precio de la calculadora prevalece sobre zonas antiguas.
6. Ejecutado dos veces el mismo día no duplica una predicción.
7. Una PR de código no cambia datos ni fusiona en main automáticamente.

## Límite explícito

Esta implementación finaliza **la automatización diaria sin dependencia de
Claude**, pero no transforma las reglas en un analista fundamental autónomo.
Para redactar una tesis nueva contrastada con SEC, FDA, resultados y noticias
en tiempo real se necesitaría otra fase, con un motor de investigación y sus
fuentes verificables. Evitamos simular esa investigación con un algoritmo
que solo lee datos históricos del proyecto.
