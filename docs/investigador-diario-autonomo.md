# Investigador diario con IA: descubrimiento y memoria de riesgo

## Objetivo

El prototipo sin IA fue descartado: no investigaba realmente la jornada y
simplemente reordenaba los datos. Se sustituye por un flujo con IA **obligatoria**.
La tarea solo puede publicarse si una petición de IA ha respondido correctamente.

No se depende del límite semanal de mensajes de Claude. Para ejecutar la IA
desde GitHub Actions se usa **Gemini 2.5 Flash-Lite**, con posibilidad de usar
otro modelo de Gemini configurándolo mediante INVESTIGADOR_GEMINI_MODELO.

## Cómo funciona

Cada laborable a las **08:17 Europe/Madrid**:

1. Verifica que la carpeta del día, los precios y el ranking tengan fecha reciente.
   Si están desactualizados se detiene, sin presentar precios antiguos como actuales.
2. Examina hasta 150 compañías del ranking, no solo la watchlist. Reserva
   prioridad a nombres nuevos, fuera de las acciones conocidas.
3. Consulta noticias RSS recientes en varios sectores, con la fuente, título
   y fecha, para detectar cambios que todavía no han llegado al seguimiento.
4. Consulta la SEC EDGAR (hasta 16 empresas) para identificar formularios
   recientes. La existencia del formulario es un hecho; su contenido NO se
   considera confirmado por el mero título. Si EDGAR falla, queda registrado.
5. En biotecnológicas, consulta ClinicalTrials.gov para los NCT disponibles
   en el ranking. Se consideran cambios materiales un nuevo resultado
   publicado o una fecha principal REAL de terminación. Una modificación
   administrativa no cuenta.
6. Envía un dossier compacto, con sus fechas, riesgos, indicadores y URLs,
   al modelo de IA para que seleccione 0-8 casos. El modelo debe diferenciar
   oportunidades reales, pruebas incompletas y riesgos que desaconsejan comprar.
7. Valida cada ticker y cada ID de fuente: ninguna fuente inventada entra
   en el informe. Compara precio, escenarios y riesgos del proyecto; la IA
   NO puede aprobar una compra sin regla 2,5 a 1, entrada calculada y evidencia
   oficial reciente. Las entradas de nuevas acciones sin tesis pasan a vigilar.
8. Publica el informe largo en investigacion/investigador/AAAA-MM-DD.md.
   Si hay al menos tres casos con entrada, stop y objetivo válidos, también
   prepara investigacion/propuestas/AAAA-MM-DD.md y apunta esas predicciones
   en predicciones.csv sin repeticiones. No rellena la lista por obligación.

## Qué ocurre cuando dice evitar

investigacion/investigador/estado_ia.json conserva los tickers descartados.

- Una empresa marcada **evitar** sale de la selección prioritaria diaria.
- Ni una mejor nota, ni un nuevo titular, ni una subida del precio la
  reactivan automáticamente.
- Solo vuelve a la evaluación al observar un hecho primario **nuevo**
  y material: formulario SEC relevante (8-K, 10-Q, 10-K, 6-K, 20-F,
  ampliación S-3/424B5, 13D) o una novedad clínica importante en
  ClinicalTrials.gov (resultados o fin principal real).
- La reactivación significa **reabrir su expediente**, no pasar a comprar.
- La memoria se conserva entre días y se versiona en GitHub.

Este primer clasificador de cambios materiales se basa en metadatos de
formularios y ensayos. Un anuncio regulatorio que no aparezca en estas
fuentes podría necesitar una revisión manual adicional: la cobertura
automática no es exhaustiva.

## Configuración mínima (acción del propietario)

1. Crear una API key de Gemini en Google AI Studio:
   https://aistudio.google.com/app/apikey
2. En el repositorio GitHub: Settings > Secrets and variables > Actions >
   New repository secret. Nombre exacto: GEMINI_API_KEY. Introducir allí
   la clave; **nunca** en el chat ni en un commit.
3. Para una identificación apropiada ante SEC, configurar el secreto
   SEC_USER_AGENT con organización y correo de contacto válido.
4. Aprobar y fusionar la PR para activar la tarea programada.
5. Verificar en GitHub > Actions > Investigador diario IA >
   Run workflow para la primera ejecución real.

La API de Gemini dispone de nivel gratuito para modelos elegibles sujeto
a cuotas y disponibilidad. No se habilita facturación de pago por código.
Si falta la clave, se alcanza el límite, la API falla o la respuesta no
cumple las reglas, **GitHub Actions marca error y no publica análisis
falso**. No se puede verificar una respuesta Gemini real sin configurar
el secreto en el repositorio.

## Pruebas

En la raíz del proyecto:

~~~bash
PYTHONPATH=src python -m pytest -q tests/test_propuestas.py tests/test_investigador_ia.py
~~~

Las pruebas emulan las llamadas al modelo y las fuentes. Cubren novedades,
fuentes fabricadas, estados evitar, reactivación por SEC/ClinicalTrials.gov,
prevención de compra sin escenarios, frescura e idempotencia.

## Límites de calidad

La IA NO sustituye una due diligence profunda. Debe distinguir lo que está
documentado de los rumores o de un simple título, contrastar la rentabilidad
frente a la pérdida y marcar incertidumbre. El modelo no tiene por sí solo
acceso garantizado al texto completo del 10-Q, nota de prensa o ensayo;
una oportunidad destacada requiere análisis oficial más profundo antes de
cualquier operación. El sistema es solo demo y no manda órdenes al bróker.
