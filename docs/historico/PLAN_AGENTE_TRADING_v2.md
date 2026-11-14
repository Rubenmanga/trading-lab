# Plan v2: agente de trading (versión sencilla, rápida y 24/7)

*14 nov 2026 · Sustituye al plan v1 en lo que pediste: lenguaje simple, demo en días, funcionar sin tu PC y verlo desde el móvil.*

> Regla fija: **solo cuenta demo / simulada**. Ningún paso toca dinero real.

## Mini-glosario
- **Demo**: cuenta con dinero ficticio, pero con precios y reglas reales. Ideal para aprender sin riesgo.
- **Backtest**: probar una estrategia con datos del pasado.
- **Stop / objetivo**: precio en el que la operación se cierra con pérdida limitada (stop) o con la ganancia prevista (objetivo).
- **Modo sombra**: la IA da su opinión pero **no bloquea nada**; solo se apunta qué habría hecho. Así mides si sirve sin arriesgar.
- **VPS**: un ordenador alquilado en internet que está siempre encendido. Tu agente vive ahí.
- **Prop firm / FTMO**: empresa que te da una cuenta grande si superas una prueba con reglas de pérdida máxima. Es opcional y va al final; por ahora nos da igual.

## 1. Cómo conseguir demo en DÍAS, no meses
Lo que no se puede acortar es **saber si el agente da dinero** (eso exige cientos de operaciones). Pero **ver el agente funcionando en demo** sí es cuestión de días. Por eso separamos las dos cosas:

| Qué | Cuándo | Para qué |
|---|---|---|
| Esqueleto funcionando con broker simulado | **Hoy** (ya está hecho, carpeta `skeleton`) | Ver el flujo completo y el registro de decisiones |
| Subirlo a un VPS + panel web | Días 1–3 | Que funcione sin tu PC y lo veas en el móvil |
| Conectar a cuenta demo real de un bróker | Días 3–7 (cuando elijamos mercado/bróker) | Operaciones demo con precios reales |
| IA en modo sombra | Desde que haya señales | Empezar a recoger datos de si la IA acierta |
| Conclusiones serias | Semanas después | Decidir si el agente aporta |

Para ir rápido mientras aprendes: **mucha actividad en poco tiempo**. Estrategias en gráficos de 15 min a 1 hora generan varias señales al día, y con 2–3 símbolos tendrás decenas de señales por semana. Aun así, con 100+ señales (unas 3–5 semanas) ya hay algo que mirar; con menos es azar.

## 2. Sin PC encendido y con móvil/tablet
Sí es posible. Se hace con un VPS y un panel web:

```
   VPS (siempre encendido)                     Tu móvil / tablet
 ┌───────────────────────────┐             ┌──────────────────┐
 │ Agente (Python)           │             │ Navegador        │
 │ Base de datos (SQLite)    │ ──HTTPS──▶  │ → panel web      │
 │ Panel web (Streamlit)     │             │   (con contraseña)│
 └─────────────┬─────────────┘             └──────────────────┘
               │ órdenes demo
               ▼
        Bróker (cuenta DEMO)
```

**Qué VPS depende del bróker** (esto es lo único que condiciona la elección):
- **Bróker con API web (p. ej. OANDA practice, Alpaca paper):** vale un VPS Linux pequeño (~5 €/mes). Es lo más barato y sencillo.
- **MetaTrader 5 (lo que usan FTMO y muchas prop firms):** la conexión con Python solo funciona en **Windows**, así que hace falta un VPS Windows (~15–25 €/mes). Más caro, pero es el que necesitarás si algún día haces la prueba de FTMO.

Recomendación: empezar con el esqueleto en un VPS Linux con broker simulado/API web para validar el flujo, y pasar a Windows+MT5 solo si decides ir hacia FTMO.

Seguridad del panel: contraseña obligatoria, acceso por HTTPS, y las claves (API de Claude, bróker) en un archivo `.env` en el VPS, nunca en el código.

## 3. Estrategias: investigación aparte
Como indicas, no elegimos estrategia ahora. Cuando decidas mercado se lanza una investigación que busque estrategias con backtests públicos, y se re-probará cada una con datos propios (con costes) antes de usarla. El esqueleto no depende de ninguna: el módulo de estrategia se conecta después.

## 4. Qué hay ya construido (carpeta `skeleton`)
- Flujo completo de las 4 capas: reglas → IA rápida → orquestador → ejecución.
- Guardián de riesgo sin IA: corte de pérdida diaria, máximo de operaciones al día y cálculo de tamaño para arriesgar solo un % fijo por operación.
- Modo `sombra` / `veto` de la IA en `config.yaml`; si la IA falla, por defecto se frena.
- Broker simulado y registro de **cada** decisión con su motivo.
- Panel web básico (solicitudes, pasadas, frenadas, motivos).
- Probado: una señal de ejemplo recorre todo el flujo y queda registrada.

Aún **no** hay: estrategia real, datos de mercado, titulares, calendario económico, conexión a bróker demo ni gráficos de acierto de la IA. Son los siguientes pasos.

## 5. Próximos pasos (en orden)
1. **Elegir mercado** (tú) → lanzamos la investigación de estrategias.
2. **Elegir bróker demo** (según mercado): decide si el VPS es Linux o Windows.
3. Conectar datos de precio y un conector de bróker demo.
4. Añadir calendario económico (regla "no operar cerca de noticias importantes") y fuente de titulares.
5. Desplegar en VPS + panel con contraseña.
6. Activar la IA en modo sombra y medir.
7. Más adelante, y solo si los datos lo justifican: veto real, comparación con/sin agente y, si quieres, prop firm.

## 6. Lo que sigo diciéndote con honestidad
- La IA mejora decisiones solo si las estrategias ya funcionan; no convierte una estrategia mala en buena.
- La IA no se puede probar con datos históricos (ya "conoce" lo que pasó); solo hacia delante, en demo.
- En demo no hay miedo ni deslizamientos reales: los resultados reales pueden ser peores.
