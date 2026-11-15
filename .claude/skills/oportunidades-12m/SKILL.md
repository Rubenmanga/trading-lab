---
name: oportunidades-12m
description: Buscador de oportunidades a 12 meses (agente B) de principio a fin - lee el ranking multifactor diario de todas las small caps de EE. UU., elige las mejores por tipo de oportunidad, hace una revisión rápida de descarte y lanza el análisis profundo (analizar-empresa-12m) de las 3-5 finalistas. Úsala con "busca oportunidades", "qué hay hoy", "dame las mejores small caps" o "busca nuevas small caps".
---

# Buscador de oportunidades a 12 meses (agente B)

Embudo completo. Las dos primeras etapas las hace el programa cada día (GitHub Actions); tú haces las tres últimas.

```
 ~1.100 small caps de EE. UU. (300 M$ - 2.000 M$, líquidas, todos los sectores)
   │  1. puntuación de 8 factores + banderas rojas            (programa, cada día)
   ▼
 ranking.json (top 150) · ranking_detalle.json (top 40 con todas las métricas)
   │  2. elegir 10-12 por carril, con tope por sector          (tú)
   ▼
 revisión rápida de descarte (10 min por empresa)              (tú)
   │  3. quedarse con 3-5 finalistas
   ▼
 análisis profundo: analizar-empresa-12m                       (tú)
   │  4. GARP 100 puntos + equipo TradingAgents + plan de entrada
   ▼
 informe + lista de vigilancia + avisos diarios automáticos
```

## Paso 0 · Contexto de mercado (rápido)
- Mira la fecha de `investigacion/ranking.json` (campo `actualizado`). Si tiene más de 3 días, dilo.
- Lee el **semáforo macro** (`macro` en `ranking.json`: diferencial high yield, curva de tipos, condiciones
  financieras de FRED e IWM frente a su media de 200 días). En rojo: menos finalistas, entradas escalonadas y más
  margen de seguridad. Dilo en la primera línea del informe.
- Lee `investigacion/validacion.md` (¿acierta el ranking?). Si el top lleva meses sin batir a la mediana, dilo y
  apóyate más en el análisis profundo que en la nota.
- Contexto general en 5 líneas con la skill `market-environment-analysis` (¿mercado alcista o bajista?,
  ¿small caps a favor?). Es la "M" de CANSLIM: en mercado bajista, sé más exigente con la entrada.
- Si hay `investigacion/sectores-*.md` reciente úsalo; si no, investiga qué sectores ven bien los analistas
  (como en `buscar-small-caps`, paso 1).

## Paso 1 · Leer el ranking
`investigacion/ranking.json` → `filas` ordenadas por `nota`. Cada fila tiene:
- `factores` (0-100, cuanto más mejor; 50 = en la media): calidad, crecimiento, valoracion, revisiones,
  insiders, momentum, catalizadores, solidez. Se comparan con todo el universo; calidad y valoración con su sector.
- `banderas` (rojas, ya restadas en la nota), `carril` (tipo de oportunidad), `senales` técnicas.
- Métricas clave: potencial según analistas, PER futuro, revisiones del BPA a 90 días, dilución, meses de caja...
- **SEC EDGAR** (gratis, para todas): `sec_registro_180d` (S-1/S-3: pueden vender acciones nuevas),
  `sec_colocacion_90d` (424B: colocación hecha), `sec_13d_180d` / `sec_13g_180d` (fondos >5 %),
  `sec_retraso_365d` (cuentas tarde), `sec_documentos` (enlaces). Ya restan/suman en la nota.
- **ClinicalTrials.gov** (solo salud): `ensayos_clave_12m` y `ensayos` (fase 2/3 con resultados en 12 meses).
- **Cortos**: `cortos_flotante`, `cortos_cambio_1m_pct`, `dias_para_cubrir`.
- **Tono de noticias** (top 60, en `extra`): `sent_nota` (−100 a 100) y `sent_alarmas` (ampliación, FDA,
  investigación...). Una alarma obliga a leer esa noticia antes de seguir.
Para más detalle de las 40 primeras: `investigacion/ranking_detalle.json`.

> **Ahorro de tokens:** estos JSON pesan cientos de KB. No los abras enteros: saca solo lo que necesitas con
> `jq` (p. ej. `jq '.filas[:40][] | {ticker,nota,carril,sector,potencial_analistas_pct,banderas}' investigacion/ranking.json`)
> o empieza por la tabla corta `investigacion/ranking.md`.

## Paso 2 · Elegir 10-12 candidatas (diversificadas)
Idea de los "carriles" del screener GARP de tradermonty: no dejes que un solo estilo llene la lista.
- Hasta 3 de **GARP**, 2 de **Crecimiento fuerte**, 2 de **Calidad barata**, 2 de **Giro: previsiones
  mejorando**, 2 de **Líder en tendencia**; completa con las de más nota.
- **Máximo 3 por sector.** Prioriza los sectores favorecidos, pero no descartes los demás.
- Excluye: notas con cobertura de datos < 0,5 (`cobertura_total`), o con bandera de caja < 12 meses.

## Paso 3 · Revisión rápida de descarte (10 min por empresa)
Para cada candidata, con WebFetch de `stockanalysis.com/stocks/TICKER/` y una WebSearch de noticias:
1. ¿Por qué ha bajado/subido? ¿Hay una noticia que explique un "potencial" enorme (fraude, ensayo fallido,
   pérdida de un cliente, OPA ya anunciada)? → si sí, descarta.
2. ¿Ampliación de capital en marcha? (SEC: S-3, 424B, ATM en los últimos 6 meses) → penaliza o descarta.
3. ¿El crecimiento es orgánico o por compras? ¿Un solo cliente > 30%?
4. ¿Hay al menos un catalizador con fecha en 12 meses?
Escribe una línea por empresa: "pasa" o "descartada porque...".

## Paso 4 · Análisis profundo de 3-5 finalistas
Aplica la skill **`analizar-empresa-12m`** a cada finalista (todas sus fases: TradingAgents + GARP + plan de
entrada + debate de riesgo + gestor). Si Ruben lo pide o hay muchas, puedes usar un subagente por empresa.

## Paso 5 · Informe del buscador
Guarda `investigacion/oportunidades-AAAA-MM-DD.md`:
1. **Resumen (5 líneas)**: contexto de mercado, cuántas empresas se miraron y las finalistas con su veredicto.
2. Tabla de las 10-12 candidatas: nota, carril, factores clave, "pasa/descartada y por qué".
3. Tabla de finalistas: calificación (Comprar/Sobreponderar/Mantener/Infraponderar/Vender), zona de entrada,
   objetivo, stop de tesis, convicción, nota GARP, enlace al informe.
4. Qué vigilar esta semana (resultados, catalizadores).
Actualiza `investigacion/watchlist.csv`. PR que toque solo `investigacion/` → se publica solo.

## Reglas
- El agente no compra. Español sencillo; explica los términos.
- El ranking es un **filtro**, no una recomendación: una nota alta solo significa "merece análisis".
- Sé honesto con lo que no se puede verificar gratis.
