---
name: duplicar-12m
description: Perfil «¿puede duplicar?» del agente B (12 meses). Mismo buscador y mismo análisis profundo, con los criterios de Ruben (objetivo de analistas > +100 % con 10+ analistas, precio 5-25 €, 2+ trimestres mejorando, poca dilución, grandes inversores, catalizadores a 12 meses). Úsala con "busca acciones que puedan duplicar" o "pasa el perfil duplicar".
---

# Perfil «¿puede duplicar?» (agente B con otros parámetros)

Es el agente de 12 meses de siempre. Lo único distinto son los criterios (`config/perfil_duplicar.yaml`)
y dónde se guarda (`investigacion/duplicar/`). **No cambies `config/medio_plazo.yaml` ni el ranking normal.**

## Paso 1 · Datos automáticos (GitHub Actions)
`python -m tradinglab.perfiles.duplicar` (workflow "Perfil duplicar"). Reutiliza `oportunidades.universo`,
`enriquecer` (metricas.empresa), `puntuar` (nota de 8 factores) y `fuentes_extra` (Finnhub, Alpaca), y añade:
precio en euros, racha de trimestres mejorando, meses de caja, acciones nuevas en 12 meses, deuda/caja y los
10 mayores fondos. Resultado: `investigacion/duplicar/resultado.json` (grande: léelo con `jq`, o mejor el `.md`) / `.md` y `universo.csv`.

## Paso 2 · Lo que el código no puede ver (web)
Para las que cumplen los 4 criterios automáticos y las 5-8 que más se acercan:
1. **Comprueba los números** en `stockanalysis.com/stocks/TICKER/forecast/` (número de analistas y objetivo).
   Yahoo a veces cuenta mal: si no coincide, dilo y usa el dato más prudente.
2. **Catalizadores a 12 meses** con fecha: ensayos Fase 2/3 (clinicaltrials.gov, notas de prensa), fechas
   PDUFA de la FDA, lanzamientos y ventas de producto, contratos. Sin catalizador claro → no es finalista.
3. **Dilución**: en SEC EDGAR busca S-3, 424B (ampliaciones), programas ATM ("at-the-market") y warrants
   del último año. Un ATM abierto o warrants baratos suben el riesgo aunque la caja sea alta.
4. **Grandes inversores**: % de fondos, fondos especializados (en biotech: RA Capital, Baker Bros, Perceptive,
   Deep Track, Avoro…), formularios 13D/13G y compras de directivos (Form 4).
5. Para las finalistas, análisis profundo con `analizar-empresa-12m` (versión resumida si son varias).

## Paso 3 · Informe
`investigacion/duplicar/INFORME-AAAA-MM-DD.md`: resumen de 5 líneas, cambio EUR/USD usado, tabla de
finalistas, casi-candidatas con el criterio que falla, ficha de cada finalista y el aviso de riesgo.

## Reglas
- **No relajar criterios en silencio.** Si nadie cumple todo, se dice y se enseñan las más cercanas.
- Un objetivo de +100 % suele significar mucho riesgo (resultado binario de un ensayo, empresa castigada).
  Recuérdalo siempre y propone tamaño pequeño (skill `position-sizer`). El agente no compra nada.
