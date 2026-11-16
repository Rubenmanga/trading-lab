# AUDITORIA_COMPLETA · trading-lab
**Fecha:** 16 de noviembre de 2026. **Base reproducible:** commit `dda9c07bd3c7fff258d3a1713e2275c7d09b2cd5` de `main`. Rama de trabajo: `audit/reingenieria-ux-20261116`.

## Dictamen ejecutivo
No hay justificación suficiente para reconstruir todo el proyecto. El laboratorio contiene piezas útiles: motores Python independientes, conexión **solo demo/paper**, datos con fuentes, pruebas y automatizaciones. Sin embargo, la relación entre una cifra, su procedencia, su fecha y su **fuerza probatoria** estaba insuficientemente clara en el panel. La siguiente prioridad es auditar los backtests contra sesgos de supervivencia, exclusiones de cotización e información posterior al evento.

**Alcance acordado:** el usuario ha solicitado **no intervenir en la cartera personal**; sus datos, visibilidad, almacenamiento y vistas quedan deliberadamente fuera de esta intervención.

## Inventario verificado
- Repositorio base: **394 archivos Git**, ~18,8 MB de contenido registrado. Inventario de rutas completo y lectura dirigida de los módulos de riesgo, simulación, fuentes, publicación, documentación y experiencia web. No se ha hecho lectura exhaustiva línea por línea de cada archivo ni auditoría externa certificada.
- Lenguajes: Python >=3.10 en `pyproject.toml`; HTML/CSS/JavaScript sin framework en `web/`; Node para compilar `web/build.mjs`; YAML para configuración y GitHub Actions.
- **Agente A:** `src/tradinglab/intradia/`. Backtest y simulación local; laboratorio intradía; operaciones ficticias mediante Alpaca paper y eToro demo. `config/intradia.yaml`, `config/laboratorio_intradia.yaml`, `config/corto_hueco.yaml` conservan distinciones de estrategias.
- **Agente B:** `src/tradinglab/medio_plazo/`, sin ejecución de órdenes. Ranking, fuentes SEC, noticias, catalizadores, escenarios, expedientes, marcador de predicciones y `src/tradinglab/backtest12m/`.
- Persistencia: Markdown/CSV/JSON versionados en `investigacion/` y SQLite local en `data/lab.db` (excluida de Git).
- Presentación: `web/build.mjs` genera HTML + `datos.json` estáticos para Vercel; `dashboard/app.py` es otra pantalla local en Streamlit, no un backend de la web pública.
- Automatización: 14 workflows en `.github/workflows/` de la base; hay ejecuciones satisfactorias en GitHub Actions. No equivalen a validación de señales ni disponibilidad real de proveedores.
- Instrucciones: `CLAUDE.md`, `.claude/skills/` y referencia histórica `docs/historico/`. Las skills definen procedimientos, pero no acreditan por sí mismas agentes persistentes.

## Hallazgos, evidencia, consecuencia y alternativa

| ID | Clase | Evidencia | Problema y consecuencia | Alternativa / decisión |
|---|---|---|---|---|
| A1 | A · correcto | `common/alpaca_cliente.py` usa `paper=True`; `intradia/laboratorio/alpaca_demo.py` usa URL paper fija; `intradia/corto_hueco/etoro.py` restringe `/demo/` | Barreras técnicas claras, sin prueba contra todos los fallos externos | **Conservar** y cubrir con tests de contratos antes de cambios de bróker |
| A2 | A · correcto | `pyproject.toml`, `tests/`, `web/build.mjs` | Arquitectura simple y reproducible sin backend de pago | Conservar; ampliar CI |
| B1 | B · mejorable | `web/index.html` superior a 1.100 líneas; concentra navegación, presentación y cálculos | Regresiones y alto coste de mantenimiento | Refactor por capas con pruebas, **no** reescritura total |
| B2 | B · mejorable | Cabecera original `web/index.html` usaba `estado.actualizado` como fecha genérica | Podía aparentar que ranking, noticias y bot estaban sincronizados | **Corregido:** fechas y estados por fuente en portada |
| B3 | B · mejorable | `dashboard/app.py` construye SQL interpolando `origen` obtenido de la propia BD | Patrón frágil si se amplía el origen de datos | Parametrización, prioridad media; no se modificó |
| C1 | C · complejo | Portada inicial `hoy()` con KPIs, propuestas, avisos, cartera, vigilancia, gráficos, calendario, agentes y fuentes encadenados | La información urgente queda mezclada con lo secundario | **Corregido en portada:** decisiones primero, detalle después |
| D1 | D · defecto | `medio_plazo/regla_fuentes.py` clasificaba cualquier dominio desconocido como nivel 1 | Un enlace sin verificabilidad podía hacerse pasar por dato oficial | **Corregido:** desconocido = nivel 3 hasta revisión explícita; prueba nueva |
| D2 | D · riesgo financiero | `backtest12m/motor.py` usa universo de símbolos con precios disponibles hoy; `ret_futuro` utiliza última cotización encontrada si falta el fin de periodo | Sesgo de supervivencia, delisting y censura; rentabilidad histórica potencialmente sesgada | No parchear con -100 % genérico; obtener universe/delistings punto-en-tiempo y predefinir política |
| D3 | D · riesgo financiero | `backtest12m/informe.py` en base concluía `sí aporta` con datos de muestra sesgada y atribuía ventaja probable entre quintiles | Confusión de evidencia exploratoria con validez predictiva | **Corregido:** aviso destacado de «no validado» y lenguaje neutral |
| B4 | B · mejorable | `intradia/estudio/simular.py` presupone camino de la vela en entradas intrabar | El orden real de máximo/mínimo dentro de un minuto no se observa | Comparar contra entradas en vela siguiente y escenario adverso antes de aprobar estrategia |
| B5 | B · mejorable | `medio_plazo/entrada.py` usa probabilidades de escenarios cargadas de archivos | Cálculo replicable, pero probabilidades no necesariamente calibradas | Identificar siempre supuestos y explicar que no son frecuencias estimadas |
| B6 | B · mejorable | Varios workflows hacen commits/push al propio repositorio; otros llevan `git pull --rebase --autostash -q || true` | Fallos/reintentos y carreras difíciles de rastrear | No borrar automatizaciones; añadir run ID, errores visibles y control de conflictos |
| E1 | E · no verificable | No se ha aportado backtest walk-forward ciego con universo histórico completo y exclusiones | **No se puede acreditar una estrategia rentable** | Bloquear conclusiones operativas hasta disponer de evidencias |
| E2 | E · no verificable | No hay prueba directa de todos los proveedores, brókeres, dispositivos y accesibilidad | No certificar integración o UX completa | Validación manual y end-to-end pendientes |

## Evaluación inicial y posterior
Rúbrica de juicio técnico: 0 = inutilizable, 5 = parcialmente útil, 10 = sólido con evidencias técnicas y uso comprobado. Son **notas orientativas**, no rendimiento medido; se indica NV cuando no existe prueba suficiente.

| Dimensión | Inicial | Después | Motivo verificable |
|---|---:|---:|---|
| Arquitectura | 6 | 6 | Separación de dominios útil, frontend concentrado |
| Código/mantenibilidad | 5 | 6 | Módulos de calidad separados y CI, monolito web pendiente |
| Fiabilidad de datos | 5 | 5 | Más controles de origen/fecha; proveedores no auditados extremo a extremo |
| Validación financiera | 4 | 4 | Cambia la prudencia del informe, no el sesgo de datos históricos |
| UX/UI | 5 | 6 | Centro de decisiones y jerarquía de lectura, sin estudio con usuarios |
| Móvil | NV | NV | CSS adaptable, sin inspección visual en dispositivo |
| Seguridad/riesgo de simulación | 6 | 6 | Barreras paper existentes; revisión de bróker no exhaustiva |
| Automatización/observabilidad | 5 | 6 | CI y antigüedad por fuente; logs/alertas de workflows pendientes |
| Claridad de información | 5 | 7 | Estado de fuente explícito, límites del backtest visibles |
| Evolución futura | 5 | 6 | JS puro verificable y arquitectura conservada |

**No se atribuye mejora en rigor estadístico**: cambiar la advertencia no cambia el método de estimación. **Las notas posteriores son provisionales** mientras falten tests visuales y contrastes de mercado.

## Pruebas observadas
- Ejecución inicial de GitHub Actions para la rama: trabajo `web` y suite `python` completados con éxito en el commit `15d30d3`; incluye compilación web y pruebas pytest.
- Correcciones posteriores de fuente e informe: sujetos al nuevo CI de la rama, consignado en `CAMBIOS_REALIZADOS.md`. No se ha ensayado la ejecución de operaciones reales ni publicado en producción.
- Resultados originales no se alteran: no reescribir precios ni rentabilidades históricas para obtener mejores métricas.

## Prioridades
**P0 financiero:** universo histórico completo, delistings, periodos sin dato, pruebas fuera de muestra. Hasta entonces, «investigación exploratoria». **P1:** fecha y procedencia, clasificación conservadora de fuentes, UI que distingue dato/hipótesis/decisión y tests. **P2:** desacoplar vistas, asegurar transacciones entre workflows y registrar trazas con identificadores reproducibles.

## Límites
Los nombres de servicios y calendarios son los configurados en Git; no se han verificado facturas, SLA, calidad de tick ni disponibilidad futura. La revisión no sustituye análisis SEC/FDA por ticker, prueba auditada de estrategias o investigación con usuarios.

## Acción de mitigación posterior al dictamen
Se añadió un indicador cuantitativo de cobertura del backtest (posiciones con/sin precio de trimestre y precios intermedios) sin rellenar retornos, cambiar las curvas o inventar exclusiones. Es evidencia diagnóstica, **no** reconstrucción del universo histórico completo ni aprobación estadística.
