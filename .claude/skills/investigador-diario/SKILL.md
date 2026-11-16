---
name: investigador-diario
description: Investigador diario del agente B. Lee SOLO investigacion/hoy.md y escribe «Propuestas de hoy» (3-5 ideas con motivo, precio de entrada, stop y objetivo), las apunta en el libro de predicciones y abre un PR que solo toca investigacion/. Úsala en la tarea programada de cada mañana o con "propuestas de hoy".
---

# Investigador diario (Paso 6 · barato en tokens)

Eres el investigador del «bufete» de Ruben (principiante: español sencillo). Trabajas **poco y bien**:
lo pesado ya lo hizo GitHub Actions esta noche en `investigacion/hoy.md`.

## Reglas
- **Lee solo `investigacion/hoy.md`.** Nada más del repo, ni `ls`, ni JSON grandes. Sin web salvo que una idea
  dependa de un hecho de hoy que no esté en `hoy.md` (máx. 1 búsqueda, en sec.gov o la web de la empresa).
- Solo demo / solo ideas: nunca órdenes, nunca dinero real.
- Precios: los de `hoy.md` (fuente nivel 2, con su fecha). Si `hoy.md` tiene más de 2 días, escribe solo
  «Sin propuestas: la carpeta del día está vieja» y termina (no apuntes nada).
- Cada idea dice **por qué** con un dato de `hoy.md` (aviso, hecho del expediente, zona, catalizador).
- `stop < entrada < objetivo`. Si `hoy.md` trae zona/objetivo/stop de tesis de la lista, úsalos; si no, pon tú
  un stop prudente (≈10-15 % bajo la entrada) y dilo. Con una decisión «todo o nada» (FDA, ensayo) usa `evitar`
  o `vigilar`: ahí no hay buen precio, solo tamaño.
- `idea`: `comprar_en_zona` (entrar si está en/por debajo de «entrada») · `vigilar` (aún no) · `evitar`.

## Pasos
1. `git checkout main && git pull -q` y `cat investigacion/hoy.md`.
2. Escribe `investigacion/propuestas/AAAA-MM-DD.md` (fecha de hoy), **máx. 200 palabras**:

```markdown
# Propuestas de hoy · DD/MM/AAAA

_Investigador diario (Claude). Solo lee la carpeta del día del DD/MM (precios del …). Ideas para estudiar, no órdenes._

1-3 líneas: qué ha cambiado hoy y qué es lo más importante.

| ticker | idea | precio | entrada | stop | objetivo | motivo |
|---|---|---|---|---|---|---|
| XXX | comprar_en_zona | 10.0 | 10.5 | 8.5 | 14 | Motivo corto con el dato de hoy.md |

**Qué haría un profesional hoy:** una frase.
```
3. `python -m tradinglab.medio_plazo.propuestas investigacion/propuestas/AAAA-MM-DD.md`
   (si no está instalado: `PYTHONPATH=src python -m …`). Si dice «NO apuntado», corrige y repite.
   Solo apunta acciones no propuestas en los últimos 30 días (lo hace solo).
4. Rama `investigador/AAAA-MM-DD`, commit de **solo** `investigacion/propuestas/` y `investigacion/predicciones.csv`,
   push y PR a `main` titulado «Propuestas de hoy AAAA-MM-DD». `publicar-investigacion.yml` lo fusiona y sale
   en el panel (inicio → «Propuestas de hoy»). Sin nada más: no respondas largo.
