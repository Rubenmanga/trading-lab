# DECISIONES_ARQUITECTURA · ADR
Fecha: 2026-11-16. Compromisos: solo demo/paper, coste de infraestructura cercano a cero, uso desde móvil, fuentes verificables, no romper datos históricos ni main.

## Mapa técnico real
```text
GitHub Actions (horarios / manual)
  ├─ Agente A → Python intradia → simulación y brokers demo → logs/CSV
  └─ Agente B → Python medio_plazo + SEC/mercado → ranking/tesis/alertas
               ↓
       investigacion/*.json|csv|md (Git)
               ↓
         web/build.mjs
               ↓
     web/dist/ (HTML/JS/CSS/datos.json)
               ↓
       Vercel (lectura estática)

PC: SQLite data/lab.db → dashboard/app.py (Streamlit, distinto del panel Vercel)
```

## ADR-001 · Conservar el stack y refactorizar
| Criterio | Mantener sin cambios | Refactor selectivo **elegido** | Reescribir con SPA+API |
|---|---|---|---|
| Complejidad | Baja al principio | Baja-media | Alta |
| Confiabilidad | Bugs conocidos | Tests de regresión | Riesgo alto de migración |
| Coste fijo | Muy bajo | Muy bajo | Hosting y mantenimiento adicionales |
| Mantenibilidad | Monolito | Modularización progresiva | Nuevas dependencias |
| Rendimiento y móvil | Densidad difícil | Priorización y responsive | Potencial sin demostrar |
| Ajuste al objetivo | Parcial | Mejor relación beneficio/riesgo | Desproporcionado hoy |

Se mantiene `web/index.html` y todas las rutas. Se añaden `web/quality.js`, `web/decision-center.css` y pruebas. Solo extraeremos vistas a módulos una vez que la navegación esté cubierta.

## ADR-002 · La frescura de datos tiene contrato propio
`web/build.mjs` añade `schema_version: 2` y `procedencia` (ranking/alertas/noticias/laboratorio). `web/quality.js` evalúa fechas de **cada fuente**, no confunde tiempo de publicación con cotización de mercado. Ventanas de antigüedad aproximadas, **no certificación de precios en vivo**. Falta estado real del workflow.

## ADR-003 · Conservar separación de agentes y barreras paper
Agente A puede simular órdenes, incluyendo clientes REST demo con URL permitida. Agente B investiga y genera alertas, no ejecuta órdenes. No unificar funciones ni permitir live a cambio de simplicidad. Nunca convertir una recomendación en una orden sin reglas fijas y consentimiento expreso.

## ADR-004 · Fuente oficial no equivale a dominio desconocido
La heurística anterior concedía nivel 1 a todo dominio no listado. En una auditoría de evidencia, «sin verificar» **no es** «oficial». El control clasifica un dominio desconocido como nivel 3 hasta revisión de su legitimidad. Una nota de empresa publicada en dominio nuevo requiere verificación antes de tratarse como primaria. Prueba de URL con `sec.gov` contenido en dominio ajeno incluida.

## ADR-005 · La simulación histórica no valida por sí sola
`backtest12m/informe.py` advierte claramente que las tasas medidas no son probabilidades de futuro. **No** se inventa un retorno por delisting ni se retocan datasets sin fuentes. Bloqueo de uso como señal validada hasta reconstruir universo histórico, precios de salida, splits, dividendos, costes, censura y OOS.

## ADR-006 · Calidad en CI
`.github/workflows/verificacion-reingenieria.yml`: tests de datos/JS, compilación estática y pytest. Solo lectura y validación; no hace trades, no usa claves ni servicios de pago. Un CI verde es una comprobación parcial, no auditoría funcional de mercados.

## Decisiones explícitamente pospuestas
- Backtest financiero completo point-in-time por falta de información suficiente: no crear rendimientos simulados para rellenar huecos.
- Centralizar workflows o cambiar proveedores sin medir fallos, límites y cobertura.
- Reconstruir el panel con framework JS, solo justificable si el refactor incremental fracasa en pruebas de experiencia.
- Cartera personal: fuera de alcance por instrucción expresa.

## ADR-007 · Medir censura antes de corregir el motor
Añadir `auditar_cobertura_cartera()` sin alterar la cartera simulada: permite conocer la fracción de posiciones sin cotización del fin de trimestre. No se asignan pérdidas ficticias a delistings ni se recomputan históricos sin sus eventos corporativos. Se mantiene el estado «NO VALIDADO» aunque la cobertura aparente sea completa.
