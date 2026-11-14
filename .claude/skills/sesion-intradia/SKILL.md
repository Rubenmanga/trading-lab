---
name: sesion-intradia
description: Prepara, lanza y supervisa la sesión de trading intradía (agente A) en la cuenta demo de Alpaca durante la ventana horaria, y al terminar escribe el diario. Úsala cuando Ruben diga "arranca la sesión", "empieza a operar" o similar.
---

# Sesión intradía (agente A)

Objetivo: que la sesión del día corra sin sustos y que al final quede todo cerrado y apuntado.

## Antes de empezar
1. Lee `config/intradia.yaml` y resume a Ruben en 3 líneas: broker (simulado o alpaca), estrategia,
   valores, horario en hora de Madrid, riesgo por operación y modo de la IA.
2. Si `broker: alpaca`, ejecuta `lab intradia comprobar`. Si la bolsa está cerrada (festivo, fin de semana),
   dilo y no sigas.
3. Si `estrategia.nombre` es `ejemplo_cruce_medias`, recuérdale que es solo de prueba.
4. Si quiere contexto, usa la skill `market-environment-analysis` para describir el estado del mercado
   (riesgo alto / bajo) en lenguaje sencillo.

## Durante
- Lanza `lab intradia sesion` (en una terminal aparte; tarda hasta la hora de cierre forzado).
- Cada cierto tiempo puedes leer `data/lab.db` (tablas `decisiones` y `operaciones`) para contar
  qué está pasando. No toques la configuración mientras corre.
- Si Ruben quiere parar ya: `Ctrl+C` en esa terminal (cierra todo) o `lab intradia cerrar-todo`.

## Después
1. Comprueba en Alpaca/BD que no queda nada abierto. Si queda algo: `lab intradia cerrar-todo`.
2. Ejecuta `lab diario` y después aplica la skill `diario-operaciones`.

## Reglas fijas
- Solo cuenta demo (paper). Nunca cambies `ALPACA_PAPER` ni `modo_cuenta`.
- Nada se queda abierto de un día para otro.
- No cambies stop, objetivo ni tamaños a mano durante la sesión.
