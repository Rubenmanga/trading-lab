---
name: diario-operaciones
description: Completa el diario del día del agente intradía (diario/AAAA-MM-DD.md) con una reflexión sencilla - qué funcionó, qué no, si la IA acertó en modo sombra y qué aprender. Úsala al terminar cada sesión.
---

# Diario de operaciones (agente A)

Inspirada en las skills de diario y revisión de tradermonty/claude-trading-skills (MIT).

1. Si no existe, ejecuta `lab diario` para generar `diario/AAAA-MM-DD.md` con los datos del día.
2. Lee el archivo y `data/lab.db` (tablas `decisiones` y `operaciones`).
3. Sustituye "_Pendiente._" por una reflexión breve y en lenguaje sencillo:
   - Resultado del día y comparación con el límite de pérdida diaria.
   - ¿Se respetaron las reglas? (horario, stop, nada abierto al final)
   - **IA en modo sombra**: en las señales que la IA habría frenado, ¿acertó? (¿esa operación perdió?)
     Lleva la cuenta acumulada: aciertos y fallos de la IA en todos los diarios.
   - Una lección concreta (no generalidades).
4. Una vez por semana: resume la semana en `diario/semana-AAAA-WW.md` (operaciones, % acierto,
   R medio, mayor pérdida, aciertos de la IA).
