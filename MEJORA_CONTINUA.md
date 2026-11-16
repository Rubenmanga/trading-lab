# MEJORA_CONTINUA · Protocolo de trabajo verificable

## Secuencia obligatoria
**Evidencia → Hipótesis → Alternativas → Decisión → Implementación → Prueba → Revisión adversarial.**

1. **Evidencia.** Identificar commit, archivo y líneas, estado de GitHub Actions, fecha y procedencia de los datos. Si no se verifica: «No verificable».
2. **Hipótesis falsable.** Decir qué error se espera reducir y cómo podría observarse una regresión.
3. **Alternativas.** Mantener, refactorizar o sustituir. Puntuar riesgo, complejidad, coste, beneficio y reversibilidad.
4. **Decisión.** Registrar por qué se eligió, qué queda fuera de alcance y quién puede autorizar operaciones o pagos.
5. **Implementación.** Rama aislada desde SHA conocido; cambios reversibles, nada de borrar historial ni operaciones real-money.
6. **Prueba.** Tests unitarios y de integración sin red + CI; si hay proveedor externo, prueba controlada y logs, no inferencias.
7. **Revisión adversarial.** Buscar contraejemplos, sesgos, leakage, información futura, estado vacío, fechas falsas, riesgos de configuración y regresiones de móvil.

## Contratos financieros innegociables
- Una empresa con objetivo de analistas +500 % no equivale a oportunidad. Probabilidad y pérdida potencial pesan lo mismo.
- Separar **hechos**, **hipótesis**, **escenarios**, **señales demo** y **acciones descartadas**.
- No llamar «validada» una estrategia con P&L positivo in-sample. Exigir embargo de información futura, universo del día, delistings, spreads, comisiones, impacto, deslizamiento, retardo de datos, fuera de muestra y control de múltiples pruebas.
- Predefinir benchmarks, reglas de cartera y condiciones de parada antes de mirar el resultado. Congelar parámetros y registrar versión de dataset y código.
- Si falta dato crítico, señalar «sin datos» y bloquear conclusión. No rellenar con número aparentemente preciso.
- Un informe de SEC u oficial no demuestra que el precio reaccionará como se espera. Diferenciar riesgo de evento y tesis.

## Fallos operativos y recuperación
- Cada workflow debe registrar fecha UTC, SHA, run ID, origen de datos, resultado y estado de error, idealmente en artefacto independiente.
- Si falla la descarga: conservar último dataset con marca «antiguo», no reemplazar silenciosamente por array vacío.
- Si falla el proveedor o un cálculo: no emitir señal nueva basada en estado incompleto; reintentar de forma acotada, registrar causa.
- Si falla un push de Git: no ignorar el fallo con `|| true` salvo que se establezca explícitamente un protocolo de reconciliación.
- Tras cambios: ejecutar `node --test web/test/*.test.cjs`, `node web/build.mjs`, `python -m pytest -q tests/` y revisar GitHub Actions. No asumir que son pruebas end-to-end.

## Tres roles de revisión
- **Arquitecto:** defiende solo decisiones con beneficio medible y reversibilidad.
- **Auditor:** intenta refutar los supuestos financieros, de seguridad y de UX. Exige evidencia externa.
- **Integrador:** conserva lo útil, incorpora correcciones con tests y deja pendientes conocidos sin ocultar.

## Criterios de cierre de una PR
- Contrato paper/demostración sin cambios.
- Al menos un test de regresión por defecto corregido, y CI completo verde.
- Sin falsificar estado de fuentes, probabilidad, precio o resultados.
- Si cambia UI, comprobar móvil real; si no se pudo, declarar «no verificado».
- Documentación y límites actualizados; rama lista para revisar, **sin fusionar a main automáticamente**.
- No se promueve código con resultados financieros «superiores» si solo se optimizó sobre los mismos datos.

## Excepciones de instrucciones
`CLAUDE.md` recomienda detenerse por aprobación tras un plan grande para ahorrar tokens. La autorización **explícita** de ejecutar autónomamente en rama para esta misión prevalece para cambios reversibles; no se interpreta como permiso de merge, trading live, servicios de pago ni borrados. La solicitud posterior deja la cartera personal **fuera de alcance**. Codex y asistentes nuevos deben seguir `AGENTS.md`.

## Control de coste de las automatizaciones
Los cambios editoriales no desencadenan descargas masivas. Las PR ejecutan primero tests sin consultar cotizaciones. La lógica de recálculo y publicación de datos queda reservada a ejecución programada, manual o a cambios relevantes del motor.
