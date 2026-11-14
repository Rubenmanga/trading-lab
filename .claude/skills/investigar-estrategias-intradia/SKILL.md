---
name: investigar-estrategias-intradia
description: Investiga y prueba estrategias intradía con backtests públicos para el mercado que elija Ruben, las re-prueba con `lab intradia backtest` y propone cuál enchufar en el agente A. Úsala cuando haya que elegir o cambiar la estrategia intradía.
---

# Investigar estrategias intradía (agente A)

El agente A tiene un "hueco" para la estrategia (`src/tradinglab/intradia/estrategias/`). Esta skill
sirve para elegir qué poner ahí con datos, no con intuición.

## Condiciones fijas que debe cumplir la estrategia
- Acciones o ETFs de EE. UU. (Alpaca demo no tiene forex). Ventana 15:30-18:30 de Madrid
  (9:30-12:30 de Nueva York), todo cerrado antes del final.
- Stop 1% y objetivo 3R o 4R (configurable). **Ojo**: un 3% de recorrido en 3 horas es raro en
  índices grandes (SPY, QQQ). Busca valores/ETFs con suficiente movimiento intradía (rango medio
  diario ATR% ≥ 2-3%) o estrategias que dependan del trailing stop, y dilo claramente en el informe.

## Pasos
1. Pregunta (si no lo sabes) en qué mercado/valores quiere centrarse Ruben.
2. Busca en la web estrategias intradía con **backtests publicados y reglas exactas** (rotura del rango
   de apertura/ORB, VWAP, gap and go, momentum de apertura...). Prioriza estudios con muchas operaciones,
   costes incluidos y periodos largos. Desconfía de vídeos sin datos.
3. Para las 2-3 mejores, escribe la clase en `estrategias/` (hereda de `Estrategia`, devuelve `Senal` o `None`,
   sin mirar velas futuras) y regístrala en `estrategias/__init__.py`. Añade un test.
4. Re-pruébalas con `lab intradia backtest --dias 60` (y más días si se puede) cambiando
   `estrategia.nombre`. La skill `backtest-expert` de tradermonty no está copiada aquí; aplica sus ideas:
   suficientes operaciones (≥ 100), costes, varias épocas de mercado, no sobreajustar parámetros.
5. Escribe un informe en `investigacion/estrategias/AAAA-MM-DD-<nombre>.md` con resultados
   (operaciones, % acierto, profit factor, R medio, máxima caída) y una recomendación en lenguaje sencillo.
6. La IA (revisor) **no** se puede probar con backtest: se mide después en modo sombra en la demo.

Ideas de arquitectura de backtest y "cuenta sombra" tomadas de HKUDS/Vibe-Trading (MIT).
