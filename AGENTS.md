# AGENTS.md · Instrucciones para agentes de código (incluido Codex)
## Contexto
Trading Lab es un laboratorio de aprendizaje e investigación financiera, con agente A de intradía/paper y B de investigación a ~12 meses. Python en `src/tradinglab/`, datos versionados en `investigacion/`, panel estático en `web/`. Léase `CLAUDE.md` como mapa de archivos, pero este documento aplica también a agentes distintos de Claude.

## Prioridad de seguridad
1. Solo demo/paper. Prohibido permitir dinero real o cambiar a endpoints live.
2. Sin servicios o APIs de pago sin autorización. No revelar secrets ni registrar credenciales.
3. No borrar ni reescribir datos financieros históricos sin copia y plan de reversión.
4. La cartera del usuario está **fuera de alcance de la auditoría actual** por instrucción explícita.
5. `main` es la referencia estable: cambios en ramas independientes y PR sin auto-merge para código. No despliegues de producción.
6. No atribuir validez predictiva a un backtest sesgado, sin OOS o sin costes. Hechos, estimaciones y escenarios por separado.

## Método de trabajo
Seguir `MEJORA_CONTINUA.md`: evidencia → hipótesis → alternativas → decisión → implementación → test → revisión adversarial. Verificar archivos, nombres, SHA, fuentes y fechas. Si no se dispone de pruebas, escribir «No verificable».

Comprobar al menos:
- `python -m pytest -q tests/`
- `node --test web/test/*.test.cjs`
- `node web/build.mjs`
- GitHub Actions e inspección visual móvil si el cambio toca UX.

## Conflictos de instrucciones
`CLAUDE.md` recomienda plan breve y aguardar confirmación para tareas grandes. Esta misión tiene permiso **expreso** para ejecutar mejoras reversibles en rama sin otra confirmación. **No** hay permiso de merge, operaciones live, pago, despliegue productivo ni cambios de cartera. Si una instrucción posterior del usuario cambia el alcance, prevalece para ese alcance.

## Información
Priorizar fuentes oficiales SEC/FDA/ClinicalTrials.gov y fecha de disponibilidad. Dominios desconocidos **no** se presumen oficiales. No confundir compilación del panel con precio de mercado en vivo. Mantener costes, divulgación de límites y fuentes en cada resultado.
