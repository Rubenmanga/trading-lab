# Cambios realizados · auditoría del 17-nov-2026

**Rama:** `claude/project-thread-ikv53s` (parte de `main` en `e810765`). **Estado:** en un PR, **sin fusionar y sin publicar**. Espera el visto bueno de Ruben.
Este archivo es el punto de relevo: quien continúe (Claude u otro asistente) empieza por «Pendiente».

## Resumen en 5 líneas

1. Auditoría escrita con evidencia (`AUDITORIA_COMPLETA.md`): 4 defectos, 4 problemas de diseño, 6 mejoras y 6 aciertos.
2. Arreglados los 4 defectos: el bot ya no puede perder una posición abierta, la carpeta del día avisa de precios viejos, hay pruebas automáticas en cada PR y el panel enseña si cada automatismo se ejecutó.
3. Panel rediseñado: estado del sistema arriba, 5 secciones, ideas en tarjetas, etiquetas de evidencia, nuevo sistema visual.
4. Instrucciones (`CLAUDE.md`, skill del investigador) y método (`MEJORA_CONTINUA.md`) actualizados.
5. **No se ha tocado** ningún dato histórico, ninguna estrategia, ningún horario de workflow ni tu cartera. Todo sigue en demo.

## Qué cambia para ti

- Al abrir el panel verás primero **si los datos son de hoy**. Si algo no se ejecutó, sale en ámbar o rojo con la fecha.
- Abajo hay 5 botones: **Hoy · Mis acciones · Ideas · Bot · Más**.
- Las ideas del investigador salen en tarjetas con precio, entrada, stop y objetivo. Si el precio es viejo, pone «zona sin confirmar».
- Cada pantalla dice si lo que enseña es un hecho, una estimación, una propuesta de la IA o un resultado del pasado.

## Archivos

| Archivo | Qué | Por qué |
|---|---|---|
| `src/tradinglab/intradia/corto_hueco/sesion.py` | Guarda el estado tras **cada** orden; un fallo con una candidata no tumba el resto; si eToro no da la cartera, no abre y lo apunta | Hallazgo D2 |
| `tests/test_corto_hueco.py` | +2 pruebas (fallo en la 2.ª candidata; sin cartera) | Demostrar D2 arreglado |
| `src/tradinglab/medio_plazo/carpeta_dia.py` | Aviso «PRECIOS VIEJOS» si tienen más de 1 día de bolsa; zonas «sin confirmar»; fuera la nota caducada del Paso 8 | Hallazgo D3 |
| `tests/test_carpeta_dia.py` | +1 prueba | D3 |
| `.claude/skills/investigador-diario/SKILL.md` | Comprueba dos fechas (la de la carpeta y la de los precios) antes de proponer | D3 |
| `.github/workflows/ci.yml` (nuevo) | `pytest` completo + construir panel + prueba de humo en cada PR | Hallazgo D4 |
| `web/test/humo.mjs` (nuevo) | Prueba del panel sin navegador ni dependencias | D4 |
| `web/build.mjs` | Lista `salud`: última fecha real de 7 automatismos; la imprime al construir | Hallazgo D1 |
| `web/index.html` | Rediseño (ver `REDISENO_UX_UI.md`): tokens, cabecera, navegación, portada, «Más», «Estado del sistema», contexto por pantalla | C1 y D1 |
| `CLAUDE.md` | Sección «Cómo se trabaja», mapa al día, 4 workflows que faltaban, regla 4 corregida | B6 |
| `AUDITORIA_COMPLETA.md`, `DECISIONES_ARQUITECTURA.md`, `REDISENO_UX_UI.md`, `MEJORA_CONTINUA.md`, este archivo (nuevos) | Entregables | — |

## Pruebas ejecutadas

| Prueba | Antes | Después |
|---|---|---|
| `python -m pytest -q` | 139 pasan (146 con el Paso 8 de `main`) | **149 pasan**, 68 s |
| `node web/build.mjs` | Construye | Construye e imprime la fecha de cada automatismo |
| `node web/test/humo.mjs` | No existía | **OK** |
| Panel en navegador, 390 px y 1280 px | 10 pantallas sin errores | **15 pantallas × 2 tamaños: 0 errores de JavaScript, 0 desbordes** |
| Tema claro | — | Portada revisada |

**No verificado (dicho claro):** que el bot arranque hoy por horario; que eToro acepte una orden real de la demo; el panel en un móvil físico; `ci.yml` ejecutándose en GitHub (se verá al abrir el PR).

## Notas antes y después

| Dimensión | Antes | Después | Por qué cambia (o no) |
|---|---|---|---|
| Calidad arquitectónica | 6 | 6 | No cambia la estructura: sigue dependiendo del cron de GitHub |
| Calidad y mantenibilidad del código | 5 | 6 | CI y 10 pruebas más; el panel sigue en un solo archivo |
| Fiabilidad de los datos | 4 | 5 | Ahora se **ve** cuándo un dato es viejo; no llega más fresco por ello |
| Rigor en la validación financiera | 5 | 5 | Sin cambios en backtests; solo protocolo escrito para los próximos |
| Experiencia visual UX/UI | 5 | 7 | Jerarquía, navegación y sistema visual nuevos; detalle sin reorganizar |
| Experiencia móvil | 6 | 7 | Menos texto, listas densas, 5 botones; sin probar en teléfono real |
| Seguridad y gestión del riesgo | 7 | 8 | Cerrado el hueco de la posición sin apuntar (D2) |
| Automatización y observabilidad | 3 | 5 | Los fallos ya se detectan y se enseñan; el cron sigue sin demostrar que funciona |
| Claridad de la información | 5 | 7 | Etiquetas de evidencia y avisos de frescura |
| Facilidad de evolución futura | 5 | 6 | CI, mapa al día y protocolo; falta trocear el panel y ordenar workflows |

Son notas de juicio técnico con la evidencia citada, no mediciones.

## Pendiente (por orden)

1. **Ruben:** mirar la vista previa y decir si se fusiona. Decidir qué hacer con el PR #69 (otra auditoría con los mismos nombres de archivo: no se pueden fusionar los dos) y con los PR #13, #44 y #71.
2. **Hoy 15:02-15:34 (España):** comprobar si el bot arrancó solo. Si no, lanzarlo a mano y apuntarlo. Si falla tres días, aplicar la decisión 2 de `DECISIONES_ARQUITECTURA.md`.
3. **Backtest del corto del hueco con deslizamiento de 0,5 % y 1 %** (`config/laboratorio_intradia.yaml` → `costes.desliz_pct`, workflow `laboratorio-intradia.yml` en modo `pasado`) para tener un rango honrado. No sustituir el resultado actual: añadirlo.
4. **Ordenar la escritura de los workflows en `main`** (C2): un paso común de «guardar» con reintentos y sin `|| true`.
5. **Trocear `web/index.html`** en 4-5 archivos por sección, sin framework.
6. **Reorganizar las pantallas de detalle** (Lista vigilada repite avisos; ranking y laboratorio muy largos).
7. **Regla de fuentes** (B3): dominios de empresa por ticker para que «web desconocida» deje de contar como oficial.
8. **Etiqueta de evidencia dato a dato** (hoy es por pantalla).
9. Limpieza opcional: quitar `streamlit` de las dependencias (acelera instalaciones) si Ruben confirma que no usará el panel de PC.

## Cómo deshacerlo

Todo está en una rama. Si no convence, basta con cerrar el PR: `main` no cambia. Si ya se hubiera fusionado, `git revert` del commit de fusión devuelve el panel y el código al estado anterior; no hay migraciones de datos.
