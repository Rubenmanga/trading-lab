# Decisiones de arquitectura

**Fecha:** 17-nov-2026. Acompaña a `AUDITORIA_COMPLETA.md`. Aquí solo van las decisiones grandes: qué hay, qué alternativas miré y cuál elijo.

## Resumen en 5 líneas

1. **Se mantiene la arquitectura** (Python + archivos en git + GitHub Actions + panel estático). No hay motivo comprobado para cambiar de tecnología.
2. **Se añade lo que faltaba alrededor**: vigilancia de que las cosas se ejecutan, pruebas antes de fusionar y avisos de datos viejos.
3. **El panel se rediseña sin cambiar de framework**: mismo HTML sin dependencias, nuevo sistema visual, portada y navegación.
4. **No se reconstruye ningún motor** (ranking, backtests, bot): funcionan y tienen pruebas. Sus debilidades son de método (supuestos), no de código.
5. **Regla nueva: congelar la construcción.** Durante unas semanas vale más acumular datos reales que añadir piezas.

## Cómo es hoy (comprobado en el repo)

```
GitHub Actions (14 workflows, cron)          Sesión de Claude (L-V por la mañana)
        │ ejecuta `lab …` (Python)                    │ lee solo investigacion/hoy.md
        ▼                                             ▼
  investigacion/*.json|csv|md  ◄──────────────  propuestas + predicciones.csv
        │ (todo se guarda como archivos en git)
        ▼
  web/build.mjs → web/dist/datos.json + index.html → Vercel (2 veces al día)

  Agente A (bot):  Alpaca (precios) → escáner → riesgo (código fijo) → eToro DEMO → registro.csv
  Agente B:        Yahoo + SEC + FRED → ranking → alertas → carpeta del día → investigador (IA) → marcador
```

- **Separación A/B:** real. No comparten código de decisión ni datos; solo `common/` (configuración y horario).
- **«Agentes»:** A es un programa de reglas (sin IA). B es un programa de reglas más una sesión diaria de Claude que solo propone.
- **Base de datos:** no hay. `data/lab.db` (SQLite) es del agente A original y ya no se usa en la nube.

## Decisión 1 · Arquitectura general

| | 1. Mantener y reforzar | 2. Refactorizar subsistemas | 3. Reconstruir (servidor + base de datos) |
|---|---|---|---|
| Qué sería | Lo actual + vigía, CI y avisos de frescura | Unificar escritura de workflows, partir el panel en módulos | Supabase o similar + servidor siempre encendido + panel con framework |
| Complejidad | Baja | Media | Alta |
| Fiabilidad | Media (depende del cron de GitHub) | Media-alta | Alta si se mantiene bien |
| Coste | 0 € | 0 € | 0-25 €/mes y horas de mantenimiento |
| Mantenible por alguien que no programa | Sí (todo son archivos legibles) | Sí | No |
| Adecuación (1 usuario, móvil, demo) | Alta | Alta | Excesiva |

**Elegida: 1 ahora, 2 por partes después.** La 3 resuelve problemas que no tenemos (muchos usuarios, tiempo real) y rompe «gasto cero» y «entendible». El único punto débil serio de la 1 es el cron de GitHub; se ataca midiéndolo (decisión 2), no cambiando todo.

## Decisión 2 · Qué hacer con un cron que no se ejecuta

| | A. Fiarse | B. Medir y enseñar (elegida) | C. Disparador externo | D. Servidor propio |
|---|---|---|---|---|
| Coste | 0 | 0 | 0, pero un token tuyo en un servicio ajeno | 4-6 €/mes |
| Detecta fallos | No | Sí, al abrir el panel | Los evita en parte | Los evita |
| Riesgo | Datos viejos sin saberlo | Ninguno nuevo | Seguridad del token | Coste y mantenimiento |

**Elegida: B.** `web/build.mjs` extrae la última fecha real de 7 automatismos y `web/index.html` calcula el retraso en tu navegador. Si tras una o dos semanas el bot sigue sin arrancar a su hora, la siguiente opción es **mover solo el bot** a una tarea programada de Claude que lance el workflow a mano (gratis, ya hay una para el investigador). D queda descartada mientras todo sea demo.

## Decisión 3 · El panel

| | 1. Parchear el HTML actual | 2. Mismo HTML, nuevo sistema de diseño (elegida) | 3. Reescribir con un framework (React, Svelte…) |
|---|---|---|---|
| Riesgo de romper pantallas | Bajo | Medio (controlado con prueba de humo y capturas) | Alto: 40 pantallas que rehacer |
| Peso en el móvil | 135 KB | 147 KB | 150-300 KB + paso de compilación |
| Mejora de uso | Poca | Grande donde importa (portada, navegación, frescura) | Grande, pero a un coste que no compensa |
| Dependencias nuevas | 0 | 0 | Muchas |

**Elegida: 2.** Un framework no haría el panel más útil; lo que fallaba era la jerarquía de la información, no la tecnología. **Pendiente honesto:** el archivo sigue siendo único y grande. El siguiente paso razonable es partirlo en 4-5 archivos `.js` por sección (sin framework).

## Decisión 4 · Dónde vive el estado del bot

Hoy el bot guarda su estado (`estado.json`, `registro.csv`) como commits en `main`. Alternativas: caché de Actions (se borra a los 7 días sin uso), una base de datos gratis (otra dependencia), o seguir en git. **Se mantiene en git**: es auditable, tiene historial y no cuesta nada. Se corrige el fallo real (guardar tras cada orden, hallazgo D2).

## Decisión 5 · Qué NO se toca y por qué

- **Motores de ranking y backtest:** sus límites están en los supuestos (deslizamiento, supervivencia), no en fallos de programación. «Arreglar» las cifras sin datos mejores sería maquillarlas.
- **Los 10 workflows que escriben en `main` (C2):** unificarlos es correcto, pero hacerlo el mismo día que el bot arranca por primera vez es un riesgo innecesario. Va a pendientes.
- **Restos del principio (Streamlit, `.bat`, agente A original):** no molestan y borrar no es reversible para ti. Se marcan como histórico.
- **Tu cartera (`config/mi_cartera.csv`):** no se toca.

## Revisión adversarial (qué le critiqué a mi propia propuesta)

| Crítica del auditor | Respuesta del integrador |
|---|---|
| «El vigía solo mira fechas dentro de archivos; si un programa escribe la fecha pero falla a medias, sale verde» | Cierto. Para el bot se usa la última fila del registro de decisiones (no la fecha del marcador). Para el ranking queda el aviso `provisional` que ya existía. Documentado como límite |
| «No conoce los festivos de EE. UU.: dará falsos retrasos» | Aceptado y dicho en la propia pantalla. Un falso ámbar 9 días al año es preferible a no avisar |
| «El aviso de precios viejos se genera al crear `hoy.md`; si `hoy.md` no se regenera, el aviso no aparece» | Por eso hay dos barreras: la skill del investigador comprueba las dos fechas, y el panel marca las ideas como «zona sin confirmar» calculándolo al abrir |
| «El rediseño añade 12 KB y deja el monolito» | Sí. Se prioriza lo que ve el usuario; el troceo queda como pendiente nº 1 de código |
| «Las etiquetas hecho/estimación están puestas por pantalla, no por dato» | Es una primera capa barata. Etiquetar dato a dato exige que cada programa guarde el tipo de evidencia; pendiente |
| «La prueba de humo no abre un navegador» | En CI comprueba datos y sintaxis (rápido, sin dependencias). La comprobación con navegador real se hace en la sesión (30 pantallas, móvil y escritorio, sin errores ni desbordes) y queda descrita en `MEJORA_CONTINUA.md` |
