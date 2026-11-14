# Buscador de oportunidades a 12 meses · 14-nov-2026

## Resumen (5 líneas)
1. El buscador ha puntuado **1.145 small caps** de EE. UU. de todos los sectores en 8 factores, y he revisado las **12 mejores**, eligiendo por tipo de oportunidad.
2. Tras una revisión rápida descarto 3 (KMDA, PUBM y JAKK) y paso a fondo las **3 finalistas** más claras: **REPX, PGY y DCTH**.
3. **REPX** (petróleo, Texas): **comprar en zona ≤ 46 $**. Objetivo 58 $, stop 36 $. Crece un 30 % y está muy barata; depende del crudo.
4. **PGY** (préstamos con IA): **comprar en zona ≤ 17,5 $**. Objetivo 25 $, stop 12,5 $. Muy barata, pero muy volátil. **DCTH** (salud): **vigilar**; comprar solo ≤ 17 $ tras su subida del +36 %.
5. Contexto: la Fed (banco central de EE. UU.) subió tipos en septiembre y puede volver a hacerlo en diciembre, y las small caps han bajado un 9 % desde agosto. Por eso los tamaños son pequeños (3-4 % cada una) y **todo es para la cuenta demo**.

## Cómo se ha hecho
- **Ranking**: `investigacion/ranking.json`, del 14-nov a las 22:19 UTC y completo (1.158 de 1.171 descargadas). Factores con su peso: calidad 15, crecimiento 15, valoración 15, revisiones de analistas 20, directivos 5, momento 10, catalizadores 5 y solidez 15. Se suman datos de Finnhub (recomendaciones, compras/ventas de directivos, noticias) y Alpaca (noticias).
- **Revisión rápida** (unos minutos por empresa): noticias, últimos resultados, ampliaciones de capital y riesgos de un solo evento.
- **Análisis a fondo** (skill `analizar-empresa-12m`): 4 analistas, nota GARP de 100 puntos, debate alcista y bajista, plan con precios y debate de riesgo.

## Las 12 candidatas
| Puesto | Ticker | Sector | Tipo | Nota | Precio | Subida según analistas | Revisión rápida |
|---|---|---|---|---|---|---|---|
| 1 | **REPX** | Energía | GARP | 75,6 | 44,40 $ | +28 % (3 analistas) | ✅ **Finalista** |
| 2 | IRWD | Salud | Calidad barata | 72,1 | 4,83 $ | +28 % (4) | ✅ Pasa. PER futuro ≈ 3 y guía subida, pero depende de un solo producto (Linzess), al que le vencen patentes, y cambia de CEO el 1-ene. Reserva |
| 3 | ASC | Industria (petroleros) | Calidad barata | 71,2 | 19,52 $ | +23 % (2) | ✅ Pasa. Es muy cíclica (fletes) y la siguen solo 2 analistas |
| 4 | AII | Finanzas (seguros) | Calidad barata | 70,9 | 27,92 $ | +10 % (4) | ⚪ No revisada a fondo: subida baja y riesgo de huracanes, igual que HRTG |
| 5 | **DCTH** | Salud | Crecimiento fuerte | 70,0 | 20,55 $ | +39 % (5) | ✅ **Finalista** |
| 6 | OPRT | Finanzas (préstamos) | GARP | 69,4 | 11,73 $ | +15 % (4) | ✅ Pasa. Prestamista para clientes con peor historial de crédito: si viene una crisis, sufre. Guía subida |
| 7 | HRTG | Finanzas (seguros) | Calidad barata | 69,2 | 33,68 $ | +26 % (2) | ✅ Pasa. Riesgo de huracanes en Florida |
| 8 | **PGY** | Tecnología (fintech) | Calidad barata | 69,1 | 16,87 $ | +75 % (11) | ✅ **Finalista** |
| 10 | DFIN | Tecnología | Líder en tendencia | 68,7 | 68,13 $ | +11 % (3) | ✅ Pasa, pero con poca subida |
| 16 | HIPO | Finanzas (seguros de hogar) | Crecimiento fuerte | 67,4 | 37,21 $ | +18 % (4) | ✅ Pasa. Guía subida, pero PER futuro de 37 y riesgo de catástrofes |
| 25 | KMDA | Salud | GARP | 65,5 | 8,09 $ | +70 % (4) | ❌ **Descartada**: registró en septiembre la posibilidad de emitir 50 M$ en acciones (riesgo de dilución), un consejero vendió ~200.000 acciones y se va el director financiero |
| 17 | PUBM | Tecnología (publicidad) | Líder en tendencia | 67,1 | 20,61 $ | +8 % (11) | ❌ **Descartada**: ya ha subido un 112 %, tiene pérdidas, un 9,8 % más de acciones y solo +8 % de subida |
| 21 | JAKK | Consumo (juguetes) | GARP | 66,0 | 35,93 $ | +35 % (2) | ❌ **Descartada por ahora**: el WSJ publicó que Mattel podría querer comprarla. Ese rumor mueve el precio y no tiene que ver con el negocio |

**Por qué estas 3 finalistas**: son las mejores de tres tipos distintos (GARP, calidad barata y crecimiento fuerte) y de tres sectores distintos (energía, fintech y salud), así no repiten el mismo riesgo. IRWD queda como reserva.

## Las 3 finalistas, a fondo
| | REPX | PGY | DCTH |
|---|---|---|---|
| Qué hace | Extrae petróleo en el Pérmico | Aprueba préstamos con IA para bancos | Quimioterapia dirigida solo al hígado |
| Veredicto | **Comprar en zona** | **Comprar en zona** | **Vigilar** |
| Precio al analizar | 44,40 $ | 16,87 $ | 20,55 $ |
| Comprar hasta | 46 $ | 17,5 $ | 17 $ |
| Objetivo 12 m | 58 $ (+31 %) | 25 $ (+48 %) | 27 $ (+31 %) |
| Stop de tesis | 36 $ | 12,5 $ | 13 $ |
| Nota GARP | 71 | 66 | 62 |
| Convicción | 3/5 | 3/5 | 3/5 |
| Tamaño máximo | 4 % | 3 % | 3 % |
| Riesgo principal | Precio del crudo | Crisis de crédito y volatilidad | Precio ya alto y un 4.º trimestre más flojo |
| Próximo catalizador | Guía de 2027 (~mar-2027) | Resultados (~28-ene-2027) | Resultados (~mar-2027) |
| Informe | [REPX](analisis/REPX-2026-11-14.md) | [PGY](analisis/PGY-2026-11-14.md) | [DCTH](analisis/DCTH-2026-11-14.md) |

Todas se han añadido a la lista de vigilancia (`investigacion/watchlist.csv`). Las alertas diarias avisarán si el precio entra en la zona de compra o toca el stop.

## Qué vigilar
- **Fed, 9-10 de diciembre**: si sube tipos, las small caps (sobre todo PGY y OPRT) pueden caer. Sería una oportunidad para comprar en zona, sin prisa.
- **Precio del petróleo**: si el WTI baja de 60 $, se revisa REPX.
- **DCTH**: esperar un retroceso hacia 16-17 $ o la guía de marzo.
- **IRWD (reserva)**: si el nuevo CEO confirma la guía en enero, pasarla a fondo.

> Esto es investigación para aprender, no una recomendación de inversión. Practica solo en la **cuenta demo**.
