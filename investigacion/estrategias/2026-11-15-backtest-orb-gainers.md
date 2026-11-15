# Backtest intradía: ORB y top gainers · datos de 2016-01-19 a 2021-12-31

*Informe automático (lo genera GitHub Actions con datos de Alpaca). La lectura en sencillo la añade Claude aparte.*

## Top gainers (suben ≥ +15 % en el día)

- Días estudiados: **1501** · top gainers: **21475** (**14,3 al día**).
- Ya abrían con hueco ≥ +5 %: **49,1 %** · ≥ +10 %: **28,7 %**.
- A las 9:00 (premercado) ya subían ≥ +5 %: **38,6 %** · ≥ +10 %: **24,4 %**.
- Hora del máximo del día: antes de las 10:00 **11,3 %**, 10-12 h **16,4 %**, después **72,3 %** (hora de NY).

### Las que abren con hueco ≥ +10 % (lo que se puede ver a tiempo)

- Casos: **14548**. Acaban el día ≥ +15 %: **42,3 %**. Cierran por debajo de su apertura: **62,1 %**. Mediana apertura→cierre: **-2,5 %**.

| Grupo | Casos | Comprar 9:35 y vender al cierre (media) | Mediana | % que gana | Reglas agente A (R medio) | % aciertos |
|---|---|---|---|---|---|---|
| todas (hueco ≥ 10 %) | 14548 | -1,0 % | -1,4 % | 41 % | -0,25 | 34 % |
| precio < 5 $ | 2433 | 0,1 % | -1,5 % | 42 % | -0,46 | 29 % |
| precio 5-20 $ | 4569 | -0,5 % | -1,0 % | 43 % | -0,26 | 35 % |
| precio ≥ 20 $ | 7546 | -1,6 % | -1,6 % | 40 % | -0,18 | 34 % |
| hueco 10-20 % | 10772 | -0,3 % | -1,0 % | 43 % | -0,25 | 35 % |
| hueco 20-50 % | 3020 | -2,4 % | -3,0 % | 37 % | -0,24 | 32 % |
| hueco ≥ 50 % | 756 | -5,1 % | -10,5 % | 29 % | -0,34 | 24 % |

### Motivo según los titulares · top gainers (muestra)

| Motivo | Casos | Peso | Apertura→cierre (media) | Reglas agente A (R medio) |
|---|---|---|---|---|
| sin noticia | 300 | 48 % | 16,0 % | 0,14 |
| resultados | 135 | 22 % | 14,7 % | 0,28 |
| otra noticia | 122 | 19 % | 16,5 % | 0,25 |
| FDA o ensayo | 32 | 5 % | 9,9 % | 0,02 |
| fusión o compra | 21 | 3 % | 6,7 % | -0,08 |
| contrato o acuerdo | 11 | 2 % | 10,8 % | 0,26 |
| cripto/IA/moda | 4 | 1 % | 10,0 % | -0,54 |
| ampliación de capital | 2 | 0 % | 10,4 % | 0,83 |

### Motivo según los titulares · huecos ≥ 10 % (muestra)

| Motivo | Casos | Peso | Apertura→cierre (media) | Reglas agente A (R medio) |
|---|---|---|---|---|
| sin noticia | 169 | 36 % | -2,9 % | -0,41 |
| resultados | 137 | 29 % | 2,7 % | -0,09 |
| otra noticia | 91 | 20 % | -4,5 % | -0,16 |
| FDA o ensayo | 36 | 8 % | -3,1 % | -0,23 |
| fusión o compra | 18 | 4 % | 2,2 % | -0,30 |
| contrato o acuerdo | 11 | 2 % | -5,7 % | -0,13 |
| ampliación de capital | 2 | 0 % | -10,7 % | -1,18 |
| cripto/IA/moda | 2 | 0 % | -4,8 % | -1,12 |

## ORB · variante «original»

- Operaciones: **24651** · aciertos **11 %** · R medio **-0,524** · profit factor **0,56**.
- Solo compras: R medio -0,512 (12207 ops) · solo ventas: R medio -0,535 (12444 ops).
- Cartera: rentabilidad total **-100 %**, anual **-87,0 %**, Sharpe **-7,81**, peor caída **-100,0 %**.

| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |
|---|---|---|---|---|
| 2016 | 3920 | 13 % | -0,413 | -75,9 % |
| 2017 | 4037 | 11 % | -0,720 | -84,7 % |
| 2018 | 4116 | 10 % | -0,539 | -83,6 % |
| 2019 | 4084 | 12 % | -0,545 | -82,6 % |
| 2020 | 4236 | 11 % | -0,425 | -92,6 % |
| 2021 | 4258 | 10 % | -0,501 | -93,0 % |

## ORB · variante «original_solo_compras»

- Operaciones: **12207** · aciertos **11 %** · R medio **-0,512** · profit factor **0,57**.
- Solo compras: R medio -0,512 (12207 ops) · solo ventas: R medio — (0 ops).
- Cartera: rentabilidad total **-100 %**, anual **-88,9 %**, Sharpe **-5,50**, peor caída **-100,0 %**.

| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |
|---|---|---|---|---|
| 2016 | 1998 | 13 % | -0,332 | -76,6 % |
| 2017 | 1995 | 11 % | -0,703 | -86,4 % |
| 2018 | 2032 | 10 % | -0,548 | -89,5 % |
| 2019 | 2075 | 12 % | -0,607 | -87,4 % |
| 2020 | 2004 | 12 % | -0,294 | -86,3 % |
| 2021 | 2103 | 9 % | -0,579 | -96,5 % |

## ORB · variante «agente_a»

- Operaciones: **4597** · aciertos **38 %** · R medio **-0,254** · profit factor **0,60**.
- Solo compras: R medio -0,284 (2141 ops) · solo ventas: R medio -0,229 (2456 ops).
- Cartera: rentabilidad total **-95 %**, anual **-39,0 %**, Sharpe **-6,02**, peor caída **-94,7 %**.

| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |
|---|---|---|---|---|
| 2016 | 711 | 42 % | -0,194 | -29,3 % |
| 2017 | 745 | 42 % | -0,209 | -32,4 % |
| 2018 | 778 | 43 % | -0,157 | -26,7 % |
| 2019 | 775 | 39 % | -0,217 | -34,6 % |
| 2020 | 788 | 35 % | -0,282 | -42,8 % |
| 2021 | 800 | 29 % | -0,453 | -59,8 % |

_Generado el 2026-11-15. Costes incluidos: deslizamiento y coste por acción en cada lado. R = lo ganado o perdido en veces lo arriesgado (−1 R = saltó el stop)._
