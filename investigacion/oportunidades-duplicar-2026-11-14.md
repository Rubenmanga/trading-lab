# ¿Qué acciones podrían duplicar en 12 meses? · Informe del 14-nov-2026

**Resumen en 5 líneas**
1. He revisado **1.474 empresas** de EE. UU. con el mismo agente de 12 meses, pero con tus criterios. Cambio usado: **1 € = 1,105 $**.
2. **64** tienen un precio de 5-25 € y un objetivo de los analistas que más que duplica el precio (con 10 o más analistas).
3. Solo **7** pasan además los filtros de "economía mejorando" y "poco riesgo de dilución": SNDX, LEGN, JANX, KURA, ARVN, ARCT y UEC.
4. Tras leer sus resultados y catalizadores, las más sólidas son **Syndax (SNDX)** y **Legend (LEGN)**, seguidas de **Janux (JANX)** y **Kura (KURA)**.
5. ⚠️ Un objetivo de +100 % casi siempre va unido a **mucho riesgo**: son empresas castigadas o que dependen de ensayos clínicos. Esto no es una orden de compra. Si practicas, hazlo en la cuenta demo y con posiciones pequeñas.

---

## Cómo se ha hecho (y qué es cada criterio)
Es el **mismo agente B** (el de 12 meses): mismo universo de Yahoo, mismas ~90 métricas por empresa, misma nota de 8 factores
y los mismos datos extra de Finnhub y Alpaca. Solo cambian los parámetros (`config/perfil_duplicar.yaml`).

| Criterio | Cómo se mide | Fuente |
|---|---|---|
| Precio 5-25 € | precio en $ ÷ 1,105 | Yahoo (EURUSD=X) |
| Objetivo > +100 % con 10+ analistas | precio objetivo **medio** a 12 meses frente al precio | Yahoo |
| Economía mejorando | resultado operativo, beneficio neto o flujo de caja de las operaciones mejorando **2 trimestres seguidos o más** (las ventas solas no cuentan) | Cuentas trimestrales (Yahoo) |
| Poca dilución | caja para **24 meses o más**, **≤ 10 %** de acciones nuevas en 12 meses y deuda **menor** que la caja. *Dilución* = la empresa emite acciones nuevas y tu trozo de la empresa se hace más pequeño | Balance y nº de acciones (Yahoo) + notas de prensa |
| Grandes inversores | % en manos de fondos, los 10 mayores fondos, compras/ventas de directivos | Yahoo (formularios 13F) y Finnhub |
| Catalizadores a 12 meses | ensayos Fase 2/3, datos en congresos, decisiones de la FDA, ventas de productos | Notas de resultados del 3er trimestre de 2026 |

**No he relajado ningún criterio.** Las que fallan alguno aparecen abajo como "casi", con el criterio que falla.

---

## Las 7 que pasan los 4 filtros automáticos

| # | Empresa (ticker) | Precio € | Analistas | Objetivo medio | Subida esperada | Trim. mejorando | Caja para… | Acciones nuevas 12 m | Nota agente B |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Syndax (SNDX)** · cáncer de sangre | 8,55 | 11 | 35,45 $ | +275 % | 4 (flujo de caja) | 44 meses | 3,4 % | 35 |
| 2 | **Legend Biotech (LEGN)** · terapia CAR-T | 15,84 | 13 | 42,54 $ | +143 % | 2 (beneficio) | 73 meses | 2,5 % | 61 |
| 3 | **Janux (JANX)** · inmunoterapia cáncer | 10,29 | 14 | 33,14 $ | +191 % | 3 (pérdida operativa menor) | > 10 años | 1,7 % | 66 |
| 4 | **Kura Oncology (KURA)** · leucemia | 7,03 | 13 | 32,00 $ | +312 % | 2 (flujo de caja) | 25 meses | 5,6 % | 56 |
| 5 | **Arvinas (ARVN)** · degradadores de proteínas | 6,17 | 13 | 14,00 $ | +105 % | 2 (flujo de caja) | 57 meses | 2,0 % | 59 |
| 6 | **Arcturus (ARCT)** · ARN mensajero | 7,57 | 10 | 23,80 $ | +185 % | 3 (pérdida menor) | 41 meses | −5 % | 48 |
| 7 | **Uranium Energy (UEC)** · minería de uranio | 6,03 | 11 | 15,85 $ | +138 % | 2 (flujo de caja) | 90 meses | 2,6 % (dudoso) | 25 |

*Nota agente B* = la nota 0-100 del buscador normal (calidad, crecimiento, valoración, revisiones, etc.) comparando estas 88 empresas entre sí.

---

## Ficha de cada una (de más a menos convincente)

### 1. Syndax (SNDX) · la que mejor encaja con "economía mejorando"
- **Qué hace:** vende dos medicamentos aprobados: **Revuforj** (leucemia) y **Niktimvo** (enfermedad injerto contra huésped, con Incyte).
- **Tendencia:** ventas del 3er trimestre **83 M$ (+82 % en un año)**; Revuforj +11 % frente al trimestre anterior. La caja que quema baja **4 trimestres seguidos** (de −70 M$ a −27 M$). Pérdida neta 49 M$ (antes 61 M$).
- **Catalizadores 12 meses:** datos nuevos de revumenib en el congreso ASH (diciembre 2026); inicio del ensayo **Fase 2 RAVEN**; **datos de Fase 2** de axatilimab + ruxolitinib en el **1er trimestre de 2027**.
- **Dilución:** 551 M$ de caja y la empresa dice que le basta para llegar a ganar dinero. No hay ampliación anunciada. **Pero** tiene bonos convertibles (≈10 M de acciones posibles) y deuda ligada a royalties.
- **Grandes inversores:** BlackRock 10 %, Kynam Capital 8,9 % (fondo especializado en salud), Goldman Sachs 6,5 %.
- **Riesgos:** su ensayo en fibrosis pulmonar **fracasó en octubre 2026**; patrimonio neto negativo; **21 % de las acciones vendidas a corto** (mucha gente apuesta a que baja).

### 2. Legend Biotech (LEGN) · la más sólida, ya gana dinero
- **Qué hace:** **Carvykti**, terapia CAR-T contra el mieloma (con Johnson & Johnson).
- **Tendencia:** ventas de Carvykti ≈710 M$ (+36 %); **beneficio operativo de 47 M$** frente a una pérdida de 43 M$ hace un año.
- **Por qué cayó (~28 % tras resultados):** el crecimiento se frena 4 trimestres seguidos, las ventas en EE. UU. no crecieron frente al trimestre anterior y la empresa avisó de que las previsiones de 2027 son optimistas.
- **Catalizadores:** congreso ASH (diciembre), resultados del 4º trimestre, programa LB2501 (CAR-T "in vivo"). El ensayo grande **CARTITUDE-5 se retrasa a 2027 como pronto**.
- **Dilución:** baja. 853 M$ de caja, poca deuda.
- **Grandes inversores:** Fidelity 12,5 %, Deerfield 4,2 % (especialista en salud).
- **Riesgo:** competencia de los anticuerpos biespecíficos y de otro CAR-T (anito-cel).

### 3. Janux (JANX) · vale menos que el dinero que tiene en el banco
- **Qué hace:** inmunoterapias "TRACTr" contra el cáncer de próstata (JANX007, JANX014) y autoinmunes (JANX011).
- **Dato clave:** **946 M$ de caja** frente a ~696 M$ de valor en bolsa. Quema muy poco (pérdida de 22 M$ en el trimestre).
- **Catalizadores:** primeros datos de JANX011 (9-nov-2026), **más datos de Fase 1b de JANX007 en el 1er semestre de 2027**. Ojo: aún no está en Fase 2/3.
- **Grandes inversores:** **RA Capital 18 %** (uno de los fondos biotech más conocidos), BlackRock 10 %, Fidelity 4 %. Los directivos han **comprado** en neto.
- **Riesgos:** UBS bajó la recomendación y el objetivo a 15 $ por datos "mixtos" de JANX007. El objetivo medio (33 $) puede estar desfasado.

### 4. Kura Oncology (KURA)
- **Qué hace:** **Komzifti** (ziftomenib), aprobado para un tipo de leucemia, con Kyowa Kirin.
- **Tendencia:** ventas de Komzifti **13,9 M$ (+53 % frente al trimestre anterior)**; pacientes nuevos +30 %.
- **Catalizadores:** 8 presentaciones en ASH (dic.), inicio de estudio de registro de darlifarnib (1er sem. 2027). La **Fase 3** grande da resultados en **2028** (fuera de los 12 meses). Hitos de Kyowa Kirin por 180 M$.
- **Dilución:** caja 492 M$ ≈ **25 meses** (justo en el límite). Ha firmado un préstamo con Oberland de hasta 300 M$ (deuda, no acciones).
- **Grandes inversores:** BlackRock 11 %, Montanova 9 %, **BVF 9 %** (especialista biotech).

### 5. Arvinas (ARVN) · también cotiza por debajo de su caja
- **Dato clave:** 559 M$ de caja frente a ~447 M$ en bolsa; dice tener dinero hasta el 2º semestre de 2028.
- **Ojo con la "mejora":** solo mejora el flujo de caja porque **ha recortado gastos**; los ingresos han caído a casi cero (solo royalties de Rigel).
- **Catalizadores:** primeros datos de **ARV-393** en linfoma en ASH (12-15 dic. 2026); más datos a mitad de 2027.
- **Inversores:** BlackRock 12 %, Vanguard, D. E. Shaw 5 %, **Pfizer 5 %**.

### 6. Arcturus (ARCT)
- Ingresos del trimestre inflados por un pago único de CSL (12 M$). Caja 185 M$, dinero "para más de dos años".
- **Catalizadores:** datos completos de **ARCT-032 (fibrosis quística) en el 2º trimestre de 2027** y decisión de pasar a Fase 3; Fase 2 de ARCT-2601.
- **Riesgos:** los calendarios **se están retrasando**; empresa pequeña (240 M$); **24 % vendido a corto**. Inversores: ARK 10 %, BlackRock 9 %.

### 7. Uranium Energy (UEC) · la única que no es biotecnológica
- Productor de uranio en EE. UU.: producción del año 229.000 libras (casi el doble), sin deuda, 495 M$ de caja.
- **Catalizadores:** nuevas zonas de producción en Wyoming y Texas, permisos de Sweetwater (marzo-mayo 2027), planta de refinado.
- **Dudas:** el agente B detecta **+14 % de acciones nuevas en un año** (otra fuente dice 2,6 %) y la empresa hizo una ampliación de 15,5 M de acciones en octubre de 2025. Los analistas han **recortado** previsiones más de un 15 % en 90 días. La dejo como la más dudosa.

---

## Casi-candidatas (fallan 1 criterio, salvo BCRX que falla 2)

| Ticker | Precio € | Analistas | Subida | Qué falla |
|---|---|---|---|---|
| NAMS (NewAmsterdam) | 18,23 | 15 | +149 % | Solo 1 trimestre mejorando |
| NRIX (Nurix) | 14,01 | 14 | +116 % | Solo 1 trimestre mejorando |
| CLYM (Climb Bio) | 9,38 | 15 | +174 % | Ningún trimestre mejorando |
| ORIC | 7,11 | 14 | +176 % | 1 trimestre mejorando |
| FTH (Faeth) | 9,08 | 13 | +460 % | 1 trimestre mejorando |
| QBTS (D-Wave) / RGTI (Rigetti) | 8,65 / 8,71 | 17 / 12 | +148 % / +123 % | 1 trimestre mejorando |
| GLXY (Galaxy Digital) | 13,01 | 16 | +138 % | Deuda casi el doble que la caja |
| PL (Planet Labs), ALM (Almonty), PHAT | 12,5 / 7,4 / 5,5 | 10-12 | +119 a +231 % | Más de 10 % de acciones nuevas |
| MARA, CLSK, BTDR, WYFI (bitcoin / centros de datos) | 5-9 | 11-15 | +127 a +264 % | Caja para menos de 24 meses y deuda mayor que la caja |
| OMDA, RSI | 13,0 / 10,7 | 12 / 14 | +88 % / +96 % | Subida esperada menor de +100 % |
| BCRX (BioCryst) | 6,89 | 11 | +169 % | Ningún trimestre mejorando y +22 % de acciones |

La lista completa está en [`resultado.md`](https://github.com/Rubenmanga/trading-lab/blob/main/investigacion/duplicar/resultado.md) (88 empresas analizadas) y [`universo.csv`](https://github.com/Rubenmanga/trading-lab/blob/main/investigacion/duplicar/universo.csv) (las 1.474).

---

## Avisos importantes
- **Datos de Yahoo y notas de prensa** (14-nov-2026). Yahoo a veces se equivoca (por ejemplo, el % de fondos puede salir por encima del 100 % por contar dos veces). Antes de decidir, confirma en la web de la empresa y en la SEC.
- El **objetivo medio de los analistas** tarda en actualizarse: si la acción acaba de caer (LEGN, JANX), puede estar desfasado.
- En biotecnología un ensayo fallido puede hundir la acción un 50-80 % en un día. **No pongas en una sola de estas más de un 1-2 % de la cartera** (skill `position-sizer`).
- El agente **no compra nada**. Si quieres practicar, hazlo en la cuenta demo.

## Siguiente paso posible
Pasar el análisis profundo completo (`analizar-empresa-12m`: debate alcista/bajista, plan de entrada y stop) a SNDX y LEGN, y vigilar JANX y KURA hasta sus datos de diciembre.

## Fuentes (consultadas el 14-nov-2026)
- Datos automáticos: Yahoo Finance (yfinance) en GitHub Actions; Finnhub y Alpaca para recomendaciones y noticias.
- Syndax 3T 2026: [BiopharmaWatch](https://www.biopharmawatch.com/news/SNDX/syndax-reports-q3-2026-results-business-update)
- Legend 3T 2026: [BiopharmaWatch](https://www.biopharmawatch.com/news/LEGN/legend-biotech-q3-2026-results-highlights), [Finviz](https://finviz.com/news/420265/legend-biotechs-big-eps-beat-masks-slowing-carvykti-growth-and-an-effective-guide-down-for-q4-and-2027), [SEC 6-K](https://www.sec.gov/Archives/edgar/data/0001801198/000180119826000026/a991earningsreleaseq32026.htm)
- Janux 3T 2026: [BiopharmaWatch](https://www.biopharmawatch.com/news/JANX/janux-therapeutics-q3-2026-results), [Zacks](https://www.zacks.com/stock/news/2978383/janx-shares-gain-191-in-3-months-heres-what-you-need-to-know), [rebaja de UBS](https://allmind.ai/news/ba89cd8e1c7a286b03bda4c72ab0e075ccfc766be201726660982eba9d656203)
- Kura 3T 2026: [BiopharmaWatch](https://www.biopharmawatch.com/news/KURA/kura-oncology-q3-2026-results-update)
- Arvinas 3T 2026: [BiopharmaWatch](https://www.biopharmawatch.com/news/ARVN/arvinas-reports-q3-2026-results-update)
- Arcturus 3T 2026: [Finviz](https://finviz.com/news/418014/arcturus-beats-on-a-one-time-csl-windfall-but-the-real-story-is-a-bigger-pipeline-with-later-decision-points)
- Uranium Energy año fiscal 2026: [Finviz](https://finviz.com/news/396246/uranium-energy-corp-reports-fiscal-2026-results), [ampliación oct-2025](https://quantisnow.com/i/uranium-energy-corp-announces-launch-of-public-offering-6221616)
