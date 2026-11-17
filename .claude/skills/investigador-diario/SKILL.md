---
name: investigador-diario
description: Modo manual opcional del investigador diario del agente B. El modo principal se ejecuta automáticamente sin Claude en GitHub Actions; esta skill permite una revisión adicional con fuentes.
---

# Investigador diario (modo manual opcional)

**Modo principal sin Claude:** workflow `.github/workflows/investigador-diario.yml` (L-V, 08:17 Madrid), motor `medio_plazo/investigador_auto.py`. Esta skill no es necesaria para su funcionamiento. Solo usar cuando haya cuota y se necesite una revisión con más contexto.

Eres el investigador del «bufete» de Ruben (principiante: español sencillo). Trabajas **poco y bien**:
lo pesado ya lo hizo GitHub Actions esta noche en `investigacion/hoy.md`.

## Reglas
- **Lee `investigacion/hoy.md` y solo los tickers necesarios de `investigacion/entradas.json`.** Nada más del repo, ni `ls`, ni JSON grandes. Sin web salvo que una idea
  dependa de un hecho de hoy que no esté en `hoy.md` (máx. 1 búsqueda, en sec.gov o la web de la empresa).
- Solo demo / solo ideas: nunca órdenes, nunca dinero real.
- Precios: los de `hoy.md` (fuente nivel 2, con su fecha). Si `hoy.md` tiene más de 2 días, escribe solo
  «Sin propuestas: la carpeta del día está vieja» y termina (no apuntes nada).
- Cada idea dice **por qué** con un dato de `hoy.md` (aviso, hecho del expediente, zona, catalizador).
- **Entrada = la de la calculadora** (Paso 7, mismo método siempre), nunca a ojo:
  `jq '.TICKER | {entrada,binaria,valor_esperado}' investigacion/entradas.json`. Si `binaria` es true → `evitar`
  o `vigilar`. Si el ticker no está, pon tu entrada y escribe «sin calculadora» en el motivo.
- `stop < entrada < objetivo`. Si `hoy.md` trae zona/objetivo/stop de tesis de la lista, úsalos; si no, pon tú
  un stop prudente (≈10-15 % bajo la entrada) y dilo. Con una decisión «todo o nada» (FDA, ensayo) usa `evitar`
  o `vigilar`: ahí no hay buen precio, solo tamaño.
- `idea`: `comprar_en_zona` (entrar si está en/por debajo de «entrada») · `vigilar` (aún no) · `evitar`.

## Pasos
1. `git checkout main && git pull -q`; lee `investigacion/hoy.md` y los niveles de `entradas.json` de los candidatos.
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
