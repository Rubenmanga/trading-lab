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
   inversores. Finviz no deja leerse. Anota fecha y fuente de cada dato (regla de fuentes, Fase 6): caja, deuda y
   acciones, del 10-Q/10-K de la SEC, no de webs intermediarias.
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
a 12 meses y escenarios bueno/base/malo con probabilidad, en una tabla `| Escenario | Probabilidad | Precio a 12 meses | Por qué |`
(probabilidades que sumen 100 %). **La zona de entrada máxima NO se elige a ojo**: sale de la calculadora
(`lab medio entrada TICKER`, Paso 7: el más bajo entre la regla 3 a 1 y el valor esperado −15 %). Copia los
escenarios en `investigacion/expedientes/TICKER/tesis.md`, ejecútala y usa su precio; si dice «todo o nada»,
no hay precio de entrada: decide solo el tamaño (pequeño). Tamaño con la skill `position-sizer`
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
   Debate de riesgo · Decisión final · Qué cambiaría la tesis · **Tabla de fuentes** (al final, obligatoria).

   **Regla de fuentes** (la comprueba una máquina: sin ella el informe no se publica):
   - Primero fuentes oficiales (**nivel 1**): SEC (10-Q, 10-K, 8-K, Form 4), FDA, ClinicalTrials.gov,
     nota de prensa o web de la empresa. **Nivel 2** = datos de mercado (Alpaca, Finnhub, Yahoo, Nasdaq,
     o los ficheros de `investigacion/` que deja GitHub Actions). **Nivel 3** = webs intermediarias
     (stockanalysis, MarketBeat, TipRanks, Investing, prensa…): solo diciéndolo y **nunca para precio ni caja**.
   - Cada dato importante, una fila con fuente (enlace o fichero) y fecha AAAA-MM-DD del dato.
   - Fila `precio` obligatoria, de como mucho 2 días de bolsa antes del informe. Al menos una fila de nivel 1.
   - Plantilla (copia y rellena; la columna `nivel` es opcional y no puede decir mejor nivel que la web):
     ```
     ## Tabla de fuentes
     | dato | valor | fuente | fecha | nivel |
     |---|---|---|---|---|
     | precio | 4,10 $ | investigacion/ranking.json | 2026-11-20 | 2 |
     | caja | 50 M$ | [10-Q](https://www.sec.gov/...) | 2026-09-30 | 1 |
     | deuda | 20 M$ | [10-Q](https://www.sec.gov/...) | 2026-09-30 | 1 |
     | acciones en circulación | 30 M | [10-Q](https://www.sec.gov/...) | 2026-11-05 | 1 |
     | próximo catalizador | FDA 22-nov | [nota de prensa](https://www.globenewswire.com/...) | 2026-10-01 | 1 |
     | objetivo de analistas | 8 $ | https://stockanalysis.com/... (intermediaria) | 2026-11-20 | 3 |
     ```
   - Antes del PR: `lab medio regla-fuentes investigacion/analisis/TICKER-AAAA-MM-DD.md` (o
     `PYTHONPATH=src python -m tradinglab.medio_plazo.regla_fuentes RUTA`) debe decir «pasa».
2. Fila en `investigacion/watchlist.csv` (columnas: ticker, empresa, sector, fecha_analisis, veredicto,
   conviccion, precio_analisis, zona_entrada_max (= precio de la calculadora), precio_objetivo_12m, stop_tesis, proximo_catalizador,
   fecha_catalizador [AAAA-MM-DD], informe).
3. Registra la tesis con `trader-memory-core` si Ruben lleva diario.
4. Desde la nube: PR que toque **solo** `investigacion/` → se publica solo en el panel.

## Reglas
- El agente **no compra**. Solo analiza y avisa; si Ruben quiere practicar, en la cuenta demo.
- Hechos con fuente y fecha; opiniones marcadas como tales; lo no verificado, dicho.
- Explica cada término técnico la primera vez (Ruben está aprendiendo).
