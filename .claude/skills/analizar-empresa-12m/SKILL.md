---
name: analizar-empresa-12m
description: Análisis profundo de UNA small cap para invertir a 12 meses (agente B). Combina el método GARP de tradermonty (nota de 100 puntos + calidad de datos + KPI por sector), el equipo completo de TradingAgents (4 analistas, debate alcista/bajista, jefe de investigación, trader, debate de riesgo a 3 voces, gestor) y las skills de entrada y tamaño. Guarda el informe y actualiza la lista de vigilancia. Úsala con "analiza TICKER" o desde `oportunidades-12m`.
---

# Análisis profundo a 12 meses (agente B)

No es un resumen de datos: es una **decisión de inversión defendible**. Sigue todas las fases en orden.
Lee antes las referencias que se citan (están en `references/`).

## Fase 0 · Punto de partida (5 min)
1. Busca la empresa en `investigacion/ranking.json` (solo su fila: `jq '.filas[] | select(.ticker=="TICKER")' investigacion/ranking.json`) (lo genera GitHub Actions cada día): puesto, nota, los 8
   factores, carril, banderas rojas y señales técnicas. Es tu **hipótesis inicial**: explica por qué el
   buscador la ha subido y qué hay que confirmar o desmentir.
2. Si hay informe previo en `investigacion/analisis/`, léelo y di qué ha cambiado.
3. Datos que faltan: en la nube la terminal no llega a webs de bolsa; usa **WebFetch** con
   `stockanalysis.com/stocks/TICKER/` (`forecast/`, `statistics/`, `financials/?p=quarterly`,
   `financials/cash-flow-statement/?p=quarterly`, `financials/balance-sheet/?p=quarterly`), **SEC EDGAR**
   (`https://data.sec.gov/submissions/CIK##########.json` → 10-Q/10-K/8-K/Form 4/S-3/424B) y la web de
   inversores. Finviz no deja leerse. Anota fecha y fuente de cada dato.
   El ranking ya trae resumidos los documentos de la SEC (`sec_*`, `sec_documentos` con enlaces), los ensayos
   clínicos (`ensayos`) y el tono de los titulares (`extra.sent_*`): úsalos como punto de partida y ábrelos.
   Biotech: confirma cada ensayo en `clinicaltrials.gov/study/NCT...` y busca la fecha PDUFA (decisión de la FDA)
   con WebSearch en las notas de prensa de la empresa (no hay calendario oficial gratis de la FDA).

## Fase 1 · Equipo de analistas (TradingAgents)
Sigue `references/tradingagents-roles.md`, roles 1-4. Cada analista escribe su sección con una **tabla final**.
- **Fundamental**: aplica `references/tradermonty/research-checklist.md` y los KPI del sector de
  `references/tradermonty/sector-kpis.md`. Imprescindible: crecimiento por acción, FCF y FCF − SBC, dilución,
  caja/deuda, ROIC, márgenes, valoración frente a 3+ comparables (PER futuro, EV/ventas, EV/EBITDA, rentab. FCF).
- **Mercado/técnico**: `references/tradermonty/vcp_methodology.md` y `pead_strategy.md` + campos técnicos del ranking.
- **Noticias y catalizadores**: catalizadores con fecha a 12 meses; `scenario_playbooks.md`.
- **Sentimiento**: directivos (Form 4), cortos (y si suben: `cortos_cambio_1m_pct`), fondos >5 % (13D/13G), institucionales (`institutional_interpretation_framework.md`),
  revisiones y cambios de recomendación.
También revisa CANSLIM (`canslim_methodology.md`) como lista rápida: C, A, N, S, L, I, M.

## Fase 2 · Nota GARP de 100 puntos (tradermonty)
Puntúa con `references/tradermonty/scoring-rubric.md`, secciones 2 y 3:
- **Nota de inversión** (A crecimiento 20 · B valoración 20 · C calidad financiera 15 · D calidad de FCF y
  beneficios 15 · E ventaja competitiva 10 · F asignación de capital/SBC/dilución 10 · G catalizador/riesgo 10).
- **Nota de calidad de datos** (0-100): cuánto de lo anterior está verificado con fuente primaria.
- Puertas de calidad (sección "Formal eligibility"): SBC-adjusted FCF yield ≥ 3% o EV/FCF ≤ 30x, ROIC ≥ 8%,
  deuda neta/EBITDA ≤ 3x, dilución ≤ 5%/año, ≥ 15% de subida en el caso bajo. Small caps en crecimiento
  pueden no cumplir alguna: dilo y baja la convicción, no lo escondas.
- Valoración **sin suponer que el múltiplo sube**: subida con múltiplo constante a 12-24 meses y prueba de
  estrés con el múltiplo un 20% más bajo.

## Fase 3 · Debate alcista vs bajista (2 rondas) → Jefe de investigación
Roles 5-7 de `tradingagents-roles.md`. Debate de verdad, respondiendo punto por punto. El jefe elige una de:
Comprar / Sobreponderar / Mantener / Infraponderar / Vender, sin refugiarse en "Mantener".

## Fase 4 · Plan del trader
Rol 8: zona de entrada máxima (precio), entrada escalonada, **señal técnica de confirmación** (tendencia fase 2,
base VCP, hueco PEAD que se mantiene o vuelta sobre la MA50), stop de tesis (precio y hecho), objetivo propio
a 12 meses y escenarios bueno/base/malo con probabilidad. Tamaño con la skill `position-sizer`
(riesgo ≤ 1% de la cartera hasta el stop; ninguna small cap > 5%).

## Fase 5 · Debate de riesgo (agresivo, prudente, neutral) → Gestor de cartera
Roles 9-10. Decisión final con la escala de 5 niveles y su traducción a la lista:
Comprar/Sobreponderar → `comprar_en_zona`, Mantener → `vigilar`, Infraponderar/Vender → `descartar`.
Antes de terminar, pasa la skill `pre-trade-discipline-gate` mentalmente: ¿hay plan, tamaño y stop?

## Fase 6 · Guardar
1. `investigacion/analisis/TICKER-AAAA-MM-DD.md` con este orden:
   **Resumen (5 líneas, español sencillo)** · Tarjeta de decisión (calificación, zona, objetivo, stop,
   convicción, nota GARP, nota de datos, carril) · Por qué lo encontró el buscador (factores) ·
   Analistas 1-4 (con tablas) · Nota GARP desglosada · Debate · Jefe de investigación · Plan del trader ·
   Debate de riesgo · Decisión final · Qué cambiaría la tesis · Fuentes (enlaces con fecha).
2. Fila en `investigacion/watchlist.csv` (columnas: ticker, empresa, sector, fecha_analisis, veredicto,
   conviccion, precio_analisis, zona_entrada_max, precio_objetivo_12m, stop_tesis, proximo_catalizador,
   fecha_catalizador [AAAA-MM-DD], informe).
3. Registra la tesis con `trader-memory-core` si Ruben lleva diario.
4. Desde la nube: PR que toque **solo** `investigacion/` → se publica solo en el panel.

## Reglas
- El agente **no compra**. Solo analiza y avisa; si Ruben quiere practicar, en la cuenta demo.
- Hechos con fuente y fecha; opiniones marcadas como tales; lo no verificado, dicho.
- Explica cada término técnico la primera vez (Ruben está aprendiendo).
