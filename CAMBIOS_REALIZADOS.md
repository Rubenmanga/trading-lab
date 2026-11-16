# CAMBIOS_REALIZADOS · revisión de 16-11-2026
**Trabajo sobre:** `audit/reingenieria-ux-20261116`.
**Estado original preservado:** `main` @ `dda9c07bd3c7fff258d3a1713e2275c7d09b2cd5`.
**Autorización:** modificar la rama, no mergear ni desplegar a producción; no usar dinero real ni servicios de pago. Cartera fuera de alcance.

## Entregas verificables
1. `web/index.html`: nueva portada de decisión, priorización de alertas y agenda, estados de datos, explicación de A/B y detalle histórico plegable; navegación y contexto para vistas secundarias. Se conserva el código anterior de vistas.
2. `web/decision-center.css`: lenguaje visual sobrio, legibilidad y estructura responsive, foco y movimiento reducido.
3. `web/quality.js`: contrato puro para fecha y antigüedad; detecta datos ausentes, retraso y fecha futura.
4. `web/build.mjs`: genera `schema_version`, fechas por fuente, y copia los assets nuevos a `web/dist/`.
5. `web/test/quality.test.cjs`: pruebas de estados de datos, sintaxis JavaScript de la UI y publicación del build.
6. `.github/workflows/verificacion-reingenieria.yml`: CI web + pytest sin secretos ni operaciones.
7. `src/tradinglab/medio_plazo/regla_fuentes.py` y `tests/test_regla_fuentes.py`: dominios desconocidos ya no son oficiales por defecto; fechas inválidas/futuras reportadas sin excepción.
8. `src/tradinglab/backtest12m/informe.py` y `tests/test_backtest12m.py`: advertencia clara de límite estadístico y no validación; se retira especulación optimista sobre quintiles.
9. `AGENTS.md`, `CLAUDE.md` y documentación de auditoría, arquitectura, UX y calidad.
10. `.github/workflows/backtest-12m.yml`: no recalcular históricos al cambiar solo el informe y no publicar sin sus cuatro tramos de precios.
11. `.github/workflows/agente-12m.yml`: validar pull requests con tests sin descargar mercado ni publicar datos de prueba.

## Resultados ejecutados
- **Commit 15d30d3:** GitHub Actions `Verificación de reingeniería`, trabajos `web` y `python` completados con `success`: sintaxis Node, tests JS, compilador del panel, artefactos y suite de pytest.
- **Commit 2a195414:** fuente e informe financiero; CI general `43974533119` exitoso. **Commit 2e814f0:** control del workflow histórico; CI `43975415410` exitoso. **Commit 14b7a50:** pruebas de PR del agente B sin descargas; comprobar checks finales. Un backtest histórico innecesariamente lanzado se canceló al introducir la nueva regla.
- No se han validado providers remotos, operaciones eToro/Alpaca con credenciales, ejecución en móvil real, Vercel en producción ni calidad financiera fuera de muestra. **No** declarar lo contrario.
- Se han mantenido los históricos y no se han reescrito métricas existentes.

## Revisión adversarial
- **Arquitecto:** conservar Python/Vercel estático, añadir capa de decisión y CI.
- **Auditor:** un mensaje de «datos actualizados» no prueba que los proveedores estén sanos; un aviso de backtest no elimina sesgo; HTML sigue monolítico; sin prueba de navegador.
- **Integrador:** etiquetas de *fecha declarada* en vez de «datos verificados»; mensaje «exploratorio/no validado»; pruebas de fuente y sintaxis; pendientes escritos sin presentarlos como completados.

## Pendientes ordenados
**P0:** reconstrucción del universo histórico con delistings y benchmark coherente; protocolo de walk-forward y cobertura de datos. No activar señal financiera basándose en este backtest.
**P1:** prueba en navegador móvil/escritorio y accesibilidad; revisar cálculo y dibujo de estados sin datos; contratos de cliente de bróker paper.
**P2:** extraer el resto de UI a módulos, observar workflows y controlar conflictos de escritura/push.
**Fuera de alcance:** cartera del usuario a petición expresa; no se modificó ni se propone acción sobre ella.

## Criterio de aceptación
Se considera **avance implementado**, no reconstrucción completa. Propuesta de revisión sujeta a aprobación humana. Conservar la rama como punto reversible y hacer merge **solo** tras visto bueno explícito.
