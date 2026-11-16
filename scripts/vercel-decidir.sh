#!/usr/bin/env bash
# ¿Despliega Vercel este commit? (exit 1 = sí, exit 0 = no)
# Plan gratis: 100 despliegues/día. Los commits automáticos de datos no despliegan;
# el panel se publica con `publicar-panel.yml` (2 veces al día) o si cambia su código.
case "$VERCEL_GIT_COMMIT_MESSAGE" in *"[panel]"*) echo "Publicación programada: sí"; exit 1;; esac
base="$VERCEL_GIT_PREVIOUS_SHA"
git cat-file -e "${base:-x}^{commit}" 2>/dev/null || base="HEAD^"
if git diff --quiet "$base" HEAD -- web vercel.json scripts/vercel-decidir.sh \
     investigacion/analisis investigacion/propuestas; then
  echo "Solo datos: no se despliega (se publicará en la próxima pasada programada)"; exit 0
fi
echo "Cambia el panel o hay análisis/propuestas nuevas: sí"; exit 1
