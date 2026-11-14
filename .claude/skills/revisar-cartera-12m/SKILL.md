---
name: revisar-cartera-12m
description: Repaso periódico (semanal) de la lista de vigilancia del agente B - ejecuta las alertas, revisa catalizadores próximos y tesis caducadas, y resume qué hacer. Úsala con "revisa mi lista" o en el repaso semanal.
---

# Repaso de la lista de vigilancia (agente B)

1. Ejecuta `lab medio alertas` (actualiza `investigacion/alertas.md`).
2. Para cada alerta:
   - **ZONA DE ENTRADA**: comprueba en la web que no haya salido una noticia que rompa la tesis antes
     de decir "está en zona". Recuerda que no compramos automáticamente.
   - **TESIS EN PELIGRO**: busca el motivo de la caída; si la tesis se rompe, cambia el veredicto a
     `descartar` en `investigacion/watchlist.csv` y explica por qué.
   - **CATALIZADOR CERCA**: resume qué se espera y qué pasaría en cada caso.
   - **OBJETIVO ALCANZADO** o **REVISAR ANÁLISIS**: vuelve a aplicar `analizar-empresa-12m`.
3. Escribe un resumen corto (para leer en el móvil) en `investigacion/repaso-AAAA-MM-DD.md`.
