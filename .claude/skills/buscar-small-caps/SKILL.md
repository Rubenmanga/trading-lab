---
name: buscar-small-caps
description: Busca small caps de EE. UU. de todos los sectores con buenas perspectivas a 12 meses según los analistas (agente B), combinando investigación sectorial en la web con el cribado `lab medio cribado`. Úsala cuando Ruben pida ideas nuevas de inversión a medio plazo.
---

# Buscar small caps con potencial a 12 meses (agente B)

**No es solo biotecnología.** El universo son empresas pequeñas (300 M$ - 2.000 M$ de capitalización)
de **cualquier sector** en el que los analistas esperen buenos resultados en los próximos 12 meses.
Biotech con un ensayo de Fase 3 es un ejemplo de catalizador, no el foco.

## Paso 1 · ¿Qué sectores ven bien los analistas a 12 meses?
Busca en la web (fuentes gratuitas: notas de perspectivas anuales de bancos y gestoras, encuestas de
FactSet/LSEG sobre crecimiento de beneficios por sector, artículos de Reuters/Bloomberg/CNBC, informes de
ETFs sectoriales). Para cada sector apunta:
- crecimiento de beneficios esperado (y si las previsiones suben o bajan),
- motivos (tipos de interés, ciclo, regulación, demanda, tecnología),
- si las small caps de ese sector se benefician en particular.
Si ayuda, usa también `market-environment-analysis` para el contexto general del mercado.

Guarda el resumen en `investigacion/sectores-AAAA-MM-DD.md` y pon los 3-5 sectores mejor valorados en
`config/medio_plazo.yaml -> cribado.sectores_prioritarios` usando los nombres de sector de Yahoo
(Technology, Healthcare, Industrials, Financial Services, Consumer Cyclical, Consumer Defensive, Energy,
Basic Materials, Communication Services, Utilities, Real Estate).

## Paso 2 · Cribado con datos
Ejecuta `lab medio cribado`. Genera `investigacion/candidatos.csv` con small caps que tienen al menos
N analistas y un precio objetivo medio bastante por encima del precio actual. Los sectores prioritarios
salen primero, pero **no descartes** buenos candidatos de otros sectores.

## Paso 3 · Primera criba cualitativa (rápida)
De los candidatos, elige 5-10 para analizar a fondo. Descarta rápido los que tengan:
- riesgo de quiebra o ampliaciones de capital constantes (mucha dilución),
- un objetivo de analistas muy viejo o de un solo analista optimista,
- un potencial que se explique solo porque la acción se ha hundido por un problema grave.
Valora que haya **catalizadores con fecha** en 12 meses: resultados, lanzamientos, aprobaciones
(FDA u otras), contratos, cambios regulatorios, ventas de activos, entrada en índices...

## Paso 4 · Siguiente paso
Para cada elegida, aplica la skill `analizar-empresa-12m`. Explica a Ruben la selección en lenguaje
sencillo, recordando que las small caps se mueven mucho y tienen más riesgo.
