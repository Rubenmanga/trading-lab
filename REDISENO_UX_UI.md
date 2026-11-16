# REDISENO_UX_UI · Sistema de experiencia
**Problema base:** la portada anterior mezclaba KPIs, propuestas, gráficos, avisos, posiciones y resultados; mostraba una sola fecha general. El usuario debía inferir por sí mismo qué mirar primero, qué estaba desactualizado y qué era una hipótesis.

## Jerarquía de información que se implementa
1. **Qué merece atención hoy**: accesos directos a revisar alertas, radar, laboratorio y fuentes.
2. **Estado de las fuentes**: fecha propia, dato presente/retrasado/ausente/fecha inválida. Sin datos ≠ cero alertas.
3. **Riesgos/eventos**: hasta cuatro avisos y cinco eventos próximos, con contexto. Un evento no pronostica un resultado.
4. **Agentes separados**: A = investigación intradía y paper; B = investigación de 12 meses sin órdenes.
5. **Explorar en profundidad**: vistas existentes, resultados, gráficos, diario e informes accesibles sin borrar funcionalidad.

## Sistema visual
- Diseño sobrio, tipografía del sistema, énfasis mediante espacio y jerarquía, no por tarjetas de distintos colores.
- Azul para acciones de navegación, ámbar para revisar/retraso, rojo para ausencia o peligro; siempre palabra junto al color.
- Componentes propios `tl-*` en `web/decision-center.css`; tamaño de lectura estable; separaciones claras; fondo oscuro/claro heredado.
- Móvil: una columna para paneles y bloques críticos, dos columnas para procedencia; escritorio dos paneles y cuatro fuentes.
- Botones y enlaces grandes, foco visible y movimiento reducido respetado.
- El menú de escritorio cambia el lenguaje técnico opaco por **Centro / Radar / Laboratorio / Bot demo / Mi cartera / Noticias / Fuentes / Archivo y ayuda**. El menú móvil conserva cinco destinos esenciales.

## Principios de visualización por tipo
- **Activos:** precio + fecha + fuente; nivel de entrada/stop/objetivo como **escenarios**, no garantías; catalizador verificable y condición de invalidación.
- **Estrategias:** resultados netos de costes, nº operaciones, distribución de R, drawdown, benchmark, sensibilidad y separación dentro/fuera de muestra. No presentar «semaforo verde» como «ganará».
- **Paper:** estado de orden, entrada/salida, costes y justificación; no confundir P&L de backtest con dinero real.
- **Agentes:** hipótesis, hechos verificados, descartes y último dato. Una skill no es un agente activo por sí sola.
- **Datos ausentes:** explicitar ausencia/retraso y enlace al origen. Nunca usar «0» para indicar una métrica desconocida.

## Lo hecho y lo pendiente
**Real:** nueva portada estructural, navegación, sistema CSS separado y contrato de procedencia con tests. **Pendiente:** refactorizar fichas/tablas secundarias, estados de cada workflow en tiempo real, test visual a 360/390/768/1280 px, teclado y lectores de pantalla, pruebas de usabilidad y escalas gráficas con grandes muestras. No se han realizado capturas de navegador ni se ha certificado UX móvil.

## Validación de UX (antes de merge final)
- A 390 px: sin scroll horizontal de página, fechas y etiquetas legibles, enlaces accesibles con dedo.
- Datos faltantes: aviso explícito, jamás apariencia de fiabilidad por defecto.
- Navegación: los cinco destinos móviles llevan a su vista; todos los módulos anteriores siguen localizables.
- En desktop: la información crítica aparece primero y el detalle no es requisito para comprender estado y riesgo.
- Con teclado: foco visible, menús recorribles, sin elementos interactivos exclusivos de hover.
- En pruebas: JS sin dependencias de red, documento HTML sintácticamente correcto y compilación del panel sin credenciales.

**Límite:** no se compararon directamente herramientas comerciales en captura ni se copiaron sus diseños; se usan principios generales de lectura por niveles y terminal financiero.
