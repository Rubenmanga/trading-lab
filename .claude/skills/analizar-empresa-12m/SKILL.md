---
name: analizar-empresa-12m
description: Análisis a fondo de una empresa para invertir a 12 meses (agente B) con un equipo de analistas (fundamental, catalizadores y noticias, sentimiento, técnico), un debate alcista contra bajista y un gestor de riesgo; guarda el informe y actualiza la lista de vigilancia. Úsala con "analiza TICKER".
---

# Analizar una empresa a 12 meses (agente B)

Estructura de roles adaptada de **TauricResearch/TradingAgents** (Apache-2.0): varios analistas,
debate alcista/bajista y un gestor de riesgo que decide. Aquí cada rol lo haces tú (o un subagente si
Ruben lo pide) en la misma sesión de Claude; no se usa ninguna API de pago.

## 0 · Datos de partida
- `lab medio ficha TICKER` → precio, capitalización, objetivos de analistas, valoración, caja/deuda,
  próximos resultados, cambios de recomendación y titulares. Si algún dato falta o parece raro,
  contrástalo en la web (informe trimestral 10-Q/10-K en SEC EDGAR, nota de prensa de resultados,
  presentación a inversores).
- Si ya existe un informe previo en `investigacion/analisis/`, léelo y di qué ha cambiado.

## 1 · Equipo de analistas (cada uno escribe su sección, con datos y fuentes)
1. **Analista fundamental**: negocio en 3 frases; ventas, márgenes y beneficio de los últimos 4-8
   trimestres; caja frente a gasto (¿cuántos meses de caja?, ¿necesitará ampliar capital?); deuda;
   valoración frente a empresas parecidas (PER futuro, precio/ventas, EV/EBITDA).
2. **Analista de catalizadores y noticias**: lista de catalizadores de los próximos 12 meses **con
   fecha aproximada** (resultados, lanzamientos, ensayos clínicos y decisiones FDA si es biotech,
   contratos, regulación, macro del sector) y qué pasa si salen bien o mal. Noticias recientes importantes.
3. **Analista de expectativas y analistas**: nº de analistas, objetivo medio/alto/bajo, tendencia de
   revisiones (¿suben o bajan objetivos y previsiones de beneficio?), y **si el precio ya descuenta
   lo bueno**: compara lo que el mercado espera con lo que necesitaría pasar para llegar al objetivo.
4. **Analista de sentimiento**: compras/ventas de directivos (insiders), posiciones cortas, interés
   institucional, tono en foros/redes (con prudencia).
5. **Analista técnico** (solo para el momento de entrada): tendencia, soportes y resistencias claros,
   media de 200 sesiones, volumen.

## 2 · Debate (2 rondas)
- **Investigador alcista**: el mejor argumento para comprar, respondiendo al bajista con datos.
- **Investigador bajista**: el mejor argumento en contra (dilución, competencia, catalizador que falla,
  valoración exigente, liquidez), respondiendo al alcista.
Escribe ambos de verdad, sin hacer trampas a favor de uno.

## 3 · Gestor de riesgo y decisión
Decide y justifica en lenguaje sencillo:
- `veredicto`: `comprar_en_zona` | `vigilar` | `descartar`
- `conviccion` 1-5
- `zona_entrada_max`: precio por debajo del cual compensa entrar (con margen frente al objetivo)
- `precio_objetivo_12m`: tu objetivo propio (no copies sin más el de los analistas)
- `stop_tesis`: precio o hecho que demostraría que la tesis está equivocada
- tamaño orientativo: con la skill `position-sizer` (p. ej. arriesgar ≤ 1% de la cartera hasta el stop de tesis);
  en small caps, ninguna posición mayor del 5% de la cartera.
- escenarios: bueno / base / malo con precio y probabilidad aproximada.

## 4 · Guardar
1. Informe en `investigacion/analisis/TICKER-AAAA-MM-DD.md` con secciones: Resumen (5 líneas para leer
   en el móvil), Analistas (1-5), Debate, Decisión, Fuentes (enlaces).
2. Añade o actualiza la fila de `investigacion/watchlist.csv` (columnas: ticker, empresa, sector,
   fecha_analisis, veredicto, conviccion, precio_analisis, zona_entrada_max, precio_objetivo_12m,
   stop_tesis, proximo_catalizador, fecha_catalizador [AAAA-MM-DD], informe).
3. Opcional: registra la tesis con la skill `trader-memory-core` para seguir su ciclo de vida.

## Reglas
- Este agente **no compra**. Solo analiza y avisa. Si Ruben quiere probar una compra, que sea en la
  cuenta demo y decidida por él.
- Separa siempre hechos (con fuente) de opiniones. Si no sabes algo, dilo.
