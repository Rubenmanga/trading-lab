# Backtest intradía: ORB y top gainers · datos de 2016-01-19 a 2026-11-13

*Informe automático (lo genera GitHub Actions con datos de Alpaca). La lectura en sencillo la añade Claude aparte.*

## Top gainers (suben ≥ +15 % en el día)

- Días estudiados: **2723** · top gainers: **58960** (**21,7 al día**).
- Ya abrían con hueco ≥ +5 %: **46,8 %** · ≥ +10 %: **28,2 %**.
- A las 9:00 (premercado) ya subían ≥ +5 %: **40,4 %** · ≥ +10 %: **24,7 %**.
- Hora del máximo del día: antes de las 10:00 **10,4 %**, 10-12 h **17,0 %**, después **72,6 %** (hora de NY).

### Las que abren con hueco ≥ +10 % (lo que se puede ver a tiempo)

- Casos: **37522**. Acaban el día ≥ +15 %: **44,3 %**. Cierran por debajo de su apertura: **60,8 %**. Mediana apertura→cierre: **-2,5 %**.

| Grupo | Casos | Comprar 9:35 y vender al cierre (media) | Mediana | % que gana | Reglas agente A (R medio) | % aciertos |
|---|---|---|---|---|---|---|
| todas (hueco ≥ 10 %) | 37522 | -1,0 % | -1,4 % | 42 % | -0,23 | 34 % |
| precio < 5 $ | 7807 | 0,0 % | -1,8 % | 42 % | -0,41 | 30 % |
| precio 5-20 $ | 12285 | -0,5 % | -1,0 % | 44 % | -0,19 | 36 % |
| precio ≥ 20 $ | 17430 | -1,8 % | -1,6 % | 41 % | -0,16 | 35 % |
| hueco 10-20 % | 27176 | -0,4 % | -1,0 % | 44 % | -0,23 | 36 % |
| hueco 20-50 % | 7961 | -1,4 % | -2,6 % | 40 % | -0,18 | 33 % |
| hueco ≥ 50 % | 2385 | -5,9 % | -11,3 % | 29 % | -0,37 | 24 % |

### Motivo según los titulares · top gainers (muestra)

| Motivo | Casos | Peso | Apertura→cierre (media) | Reglas agente A (R medio) |
|---|---|---|---|---|
| sin noticia | 571 | 48 % | 16,2 % | 0,19 |
| otra noticia | 252 | 21 % | 17,7 % | 0,41 |
| resultados | 218 | 18 % | 13,3 % | 0,30 |
| FDA o ensayo | 75 | 6 % | 13,5 % | -0,07 |
| fusión o compra | 28 | 2 % | 11,5 % | -0,16 |
| contrato o acuerdo | 24 | 2 % | 6,2 % | 0,18 |
| cripto/IA/moda | 12 | 1 % | 9,7 % | -0,09 |
| ampliación de capital | 6 | 1 % | 16,9 % | 0,15 |

### Motivo según los titulares · huecos ≥ 10 % (muestra)

| Motivo | Casos | Peso | Apertura→cierre (media) | Reglas agente A (R medio) |
|---|---|---|---|---|
| sin noticia | 302 | 37 % | -3,8 % | -0,46 |
| resultados | 220 | 27 % | 1,9 % | -0,08 |
| otra noticia | 159 | 20 % | -3,0 % | -0,02 |
| FDA o ensayo | 69 | 9 % | -3,6 % | -0,37 |
| fusión o compra | 24 | 3 % | 4,0 % | -0,29 |
| contrato o acuerdo | 22 | 3 % | -6,9 % | 0,03 |
| cripto/IA/moda | 9 | 1 % | -10,8 % | -0,49 |
| ampliación de capital | 5 | 1 % | 7,9 % | -1,20 |

## ORB · variante «original»

- Operaciones: **44924** · aciertos **15 %** · R medio **0,001** · profit factor **1,00** · R medio **sin costes** 0,301 (la diferencia es lo que se comen deslizamiento y comisiones).
- Solo compras: R medio -0,010 (22105 ops) · solo ventas: R medio 0,012 (22819 ops).
- Cartera: rentabilidad total **49 %**, anual **3,7 %**, Sharpe **0,29**, peor caída **-86,4 %**.

| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |
|---|---|---|---|---|
| 2016 | 3920 | 17 % | -0,025 | -12,9 % |
| 2017 | 4037 | 15 % | -0,214 | -40,7 % |
| 2018 | 4116 | 15 % | 0,050 | 11,9 % |
| 2019 | 4084 | 17 % | 0,044 | 6,0 % |
| 2020 | 4236 | 15 % | -0,061 | -53,5 % |
| 2021 | 4258 | 14 % | 0,018 | 15,1 % |
| 2022 | 4234 | 16 % | 0,039 | 24,9 % |
| 2023 | 4140 | 13 % | -0,146 | -45,1 % |
| 2024 | 4125 | 14 % | 0,017 | 19,7 % |
| 2025 | 4079 | 14 % | 0,128 | 125,2 % |
| 2026 | 3695 | 17 % | 0,180 | 145,1 % |

## ORB · variante «original_solo_compras»

- Operaciones: **22105** · aciertos **15 %** · R medio **-0,010** · profit factor **0,99** · R medio **sin costes** 0,296 (la diferencia es lo que se comen deslizamiento y comisiones).
- Solo compras: R medio -0,010 (22105 ops) · solo ventas: R medio — (0 ops).
- Cartera: rentabilidad total **-94 %**, anual **-23,2 %**, Sharpe **-0,15**, peor caída **-99,3 %**.

| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |
|---|---|---|---|---|
| 2016 | 1998 | 17 % | 0,044 | -14,8 % |
| 2017 | 1995 | 15 % | -0,269 | -54,4 % |
| 2018 | 2032 | 14 % | -0,058 | -50,4 % |
| 2019 | 2075 | 17 % | 0,014 | -17,5 % |
| 2020 | 2004 | 15 % | 0,071 | -32,2 % |
| 2021 | 2103 | 13 % | -0,052 | -27,1 % |
| 2022 | 2013 | 14 % | -0,100 | -54,1 % |
| 2023 | 2074 | 13 % | -0,168 | -59,6 % |
| 2024 | 2017 | 14 % | -0,019 | -4,5 % |
| 2025 | 1975 | 13 % | 0,155 | 39,7 % |
| 2026 | 1819 | 17 % | 0,310 | 195,7 % |

## ORB · variante «agente_a»

- Operaciones: **8340** · aciertos **48 %** · R medio **0,030** · profit factor **1,06** · R medio **sin costes** 0,154 (la diferencia es lo que se comen deslizamiento y comisiones).
- Solo compras: R medio -0,001 (3999 ops) · solo ventas: R medio 0,058 (4341 ops).
- Cartera: rentabilidad total **77 %**, anual **5,4 %**, Sharpe **0,63**, peor caída **-21,9 %**.

| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |
|---|---|---|---|---|
| 2016 | 711 | 48 % | -0,034 | -6,1 % |
| 2017 | 745 | 49 % | -0,068 | -12,1 % |
| 2018 | 778 | 51 % | 0,053 | 10,4 % |
| 2019 | 775 | 47 % | -0,033 | -6,6 % |
| 2020 | 788 | 51 % | 0,151 | 33,9 % |
| 2021 | 800 | 45 % | -0,050 | -10,0 % |
| 2022 | 777 | 46 % | -0,014 | -3,0 % |
| 2023 | 755 | 48 % | 0,049 | 9,3 % |
| 2024 | 765 | 50 % | 0,086 | 17,3 % |
| 2025 | 758 | 49 % | 0,098 | 19,9 % |
| 2026 | 688 | 48 % | 0,087 | 15,7 % |

_Generado el 2026-11-15. Costes incluidos: deslizamiento y coste por acción en cada lado. R = lo ganado o perdido en veces lo arriesgado (−1 R = saltó el stop)._
