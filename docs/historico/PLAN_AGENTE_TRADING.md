# Plan: agente de trading por capas

*Versión 1 · 14 nov 2026 · basado en el dashboard del vídeo "Creo una estrategia con Claude para que opere por mí"*

> Regla de oro de este proyecto: **nada toca dinero real** hasta que el sistema haya pasado backtest, demo y modo sombra con criterios medibles. Todo lo de abajo empieza en cuenta demo / paper trading.

---

## 1. Qué hace el agente del vídeo

Un pipeline de 4 capas por cada señal que genera una estrategia:

| Capa | Quién | Latencia | Qué hace |
|---|---|---|---|
| 1. Reglas | Código, sin IA | milisegundos | Mira precio, tendencia, calendario, volatilidad. Lo traduce a palabras ("volatilidad alta"). Deja pasar siempre, **salvo si el día ya pierde demasiado**. |
| 2. IA rápida | Haiku | ~1 s | Lee titulares: ¿mueve el símbolo? ¿bueno o malo? ¿y el mercado? Si duda, sube a la capa 3. |
| 3. Orquestador | Claude (modelo grande) | segundos | Revisa las dudas y decide **dejar pasar o frenar** (frena si hay titulares en contra o el mercado no acompaña). |
| 4. Ejecución | Código | — | Si pasa: orden al bróker con stop y objetivo. Si frena: no manda nada. Siempre apunta qué decidió y por qué. |

Lo comparan con dos retos FTMO de 10.000 $ con las mismas estrategias: uno con agente y otro sin él. El dashboard enseña solicitudes / pasan / frenadas, aciertos y fallos de cada decisión, a qué horas frena más y cuántos titulares lee.

## 2. Lo que está bien pensado

- **La IA solo puede vetar, no inventar operaciones.** Las entradas salen de estrategias con reglas; la IA es un filtro. Es el diseño correcto: limita el daño que puede hacer un LLM que alucina.
- **Coste y latencia escalonados.** Reglas gratis y rápidas primero, modelo barato después, modelo caro solo cuando hay duda.
- **Control de riesgo determinista** (pérdida diaria) que no depende de la IA.
- **Todo queda registrado con su motivo.** Sin esto no se puede medir si la IA aporta algo.
- **Grupo de control** (misma estrategia sin agente). Es la única forma honesta de medir el valor del filtro.

## 3. Debilidades y riesgos

### 3.1 Los resultados del vídeo no demuestran nada (todavía)
Mirando los números de la captura:
- Son **4 días de trading** y solo **15 de 44 decisiones están cerradas**; 29 siguen abiertas.
- **Sin agente va mejor**: +204 $ frente a +129 $. Con las abiertas valoradas al corte, el agente va **−75 $** por detrás.
- El "decidió mejor +37,86 $" cuenta solo las 15 cerradas. Con 8 aciertos y 7 fallos es indistinguible del azar.

Para saber si el filtro aporta hacen falta **cientos de señales** y varias semanas, no 4 días. No es una crítica al creador (es un experimento en curso), pero no hay que copiar el diseño pensando que ya está validado.

### 3.2 La capa de IA no se puede backtestear de verdad
Un LLM "sabe" lo que pasó después de muchos titulares históricos (fuga de información del futuro). Si le das un titular de 2024, su juicio está contaminado. **La capa de IA solo se puede validar hacia delante** (forward testing en demo). Las estrategias sí se backtestean; el filtro no.

### 3.3 Sobreajuste
- Ajustar parámetros de la estrategia hasta que el backtest quede bonito.
- Ajustar los prompts de la IA mirando qué trades salieron bien la semana pasada.
- Antídoto: separar datos in-sample / out-of-sample, walk-forward, pocos parámetros, y congelar prompts durante cada periodo de prueba.

### 3.4 Latencia
Entre señal y orden pueden pasar 2–10 s (Haiku + Claude). Para estrategias de intradía en M15/H1 da igual; para scalping o entradas en noticias es un problema serio. → Usar estrategias de marco temporal medio, y que la capa 4 **recalcule precio, stop y tamaño justo antes de enviar** (y descarte si el precio se ha movido más de X).

### 3.5 Coste y calidad de las noticias
- Feeds de titulares en tiempo real buenos son de pago; los gratis llegan tarde o son ruido.
- Coste de LLM: cada señal = 1 llamada a Haiku + a veces 1 a Claude. Es barato por señal, pero hay que **registrar tokens por llamada** desde el día 1 para conocer el coste real.
- Titulares ≠ noticias. El calendario económico (NFP, IPC, tipos) es más útil y más fiable que interpretar titulares sueltos, y es determinista: va en la capa 1.

### 3.6 Reglas de la prop firm (FTMO u otra)
Valores típicos del reto FTMO de 10k (**verificar en su web, cambian**):
- Objetivo fase 1: +10 % (1.000 $); fase 2: +5 %.
- Pérdida diaria máxima: 5 % (500 $), cuenta con flotante y según hora del servidor.
- Pérdida máxima total: 10 % (1.000 $).
- Mínimo de días de trading.
- Restricciones al operar alrededor de noticias de alto impacto en cuentas financiadas (según tipo de cuenta) y prohibición de prácticas como HFT, arbitraje de latencia o copiar operaciones idénticas entre cuentas.

Implicación: nuestra capa de riesgo debe ser **más estricta** que la de la prop firm (p. ej. cortar a −3 % diario, no a −5 %), contar el flotante, y bloquear operaciones X minutos antes/después de noticias de alto impacto.

### 3.7 Riesgos operativos
Desconexiones de MT5, órdenes duplicadas, el PC que se apaga o se actualiza, la API del LLM caída. Regla: **si algo falla, no se opera** (fail-closed), y todas las posiciones llevan stop en el servidor del bróker desde el primer momento.

## 4. Arquitectura propuesta

Igual que el vídeo, con dos cambios: el riesgo va **también al final** (guardián independiente) y la IA tiene un **modo sombra**.

```
 Datos (MT5: velas, ticks, cuenta)     Calendario económico     Titulares
            │                                  │                    │
            ▼                                  │                    │
 [Estrategias]  → genera SEÑAL (símbolo, dirección, entrada, stop, objetivo)
            │
            ▼
 [1. Reglas y contexto]  determinista, ms
    - filtros de mercado: tendencia, ATR, spread, sesión
    - calendario: ¿noticia de alto impacto en ±X min? → frena
    - riesgo pre-trade: pérdida del día, nº operaciones, exposición por divisa
            │
            ▼
 [2. Analista rápido (Haiku)]  ~1 s, salida JSON estricta
    - relevancia, sentimiento, confianza, "dudo: sí/no"
            │ (solo si duda o señal de alto riesgo)
            ▼
 [3. Orquestador (Claude)]  segundos, salida JSON: PASA / FRENA + motivo
            │
            ▼
 [4. Guardián de riesgo + ejecución]  determinista
    - recalcula tamaño (riesgo fijo % por operación), revalida precio y límites
    - envía orden con SL/TP en el servidor
            │
            ▼
 [Registro]  SQLite: señal, contexto, respuestas IA, tokens, decisión, resultado
            │
            ▼
 [Dashboard]  pasan/frenadas, acierto del filtro, coste, P&L con vs sin agente
```

Principios:
- La IA **nunca** abre operaciones, cambia el tamaño ni mueve stops. Solo dice PASA o FRENA.
- Si la IA no responde a tiempo o devuelve algo inválido → configurable (frenar por defecto).
- **Modo sombra**: la IA decide y se registra, pero la operación se ejecuta igual. Así medimos "qué habría pasado si hubiera frenado" con todas las señales, sin necesitar dos cuentas.

## 5. Stack recomendado (por defecto)

| Pieza | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.11+ | Ecosistema de trading y SDK de Anthropic. |
| Bróker / ejecución | **MetaTrader 5 en cuenta demo** + paquete `MetaTrader5` de Python | FTMO y la mayoría de prop firms usan MT5; la librería funciona en Windows (tu PC). Demo gratis. |
| Datos de precio | Histórico de MT5 (`copy_rates_range`) | Mismo feed que el que ejecuta: sin diferencias de datos. |
| Backtest | `backtesting.py` o `vectorbt` | Rápidos, suficientes para estrategias de reglas. |
| Calendario económico | Feed de Forex Factory / Finnhub / similar | Para la regla de "no operar cerca de noticias". |
| Titulares | Empezar con RSS/API gratuita (Finnhub, RSS de medios); pagar solo si el filtro demuestra valor | No gastar en datos antes de validar. |
| IA | API de Anthropic: Haiku como analista rápido, Sonnet/Opus como orquestador, con salidas JSON validadas | Igual que el vídeo. |
| Registro | SQLite | Cero mantenimiento, fácil de consultar. |
| Dashboard | Streamlit (fase 4) | Rápido de montar. |
| Configuración | `config.yaml` + `.env` para claves (nunca en el código) | |

Alternativas si no quieres MT5: **Alpaca paper** (acciones/cripto EE. UU.), **Interactive Brokers paper**, **OANDA practice** (forex). Cambia la capa 4 y los datos; el resto es igual.

## 6. Hoja de ruta por fases

Cada fase tiene un criterio de salida. No se pasa a la siguiente sin cumplirlo.

### Fase 0 · Definir (unos días)
- Mercado y símbolos (p. ej. EURUSD, GBPUSD, XAUUSD, US100).
- 1–2 estrategias con reglas escritas en papel: entrada, stop, objetivo, marco temporal, horario.
- Reglas de riesgo: riesgo por operación (0,25–0,5 %), corte diario (−3 %), máximo de operaciones/día, exposición máxima.
- **Salida:** documento de estrategia y `config.yaml` de riesgo.

### Fase 1 · Estrategia sin IA + backtest (1–2 semanas)
- Descargar histórico de MT5 (≥3 años), backtest con spread y comisiones.
- Walk-forward / out-of-sample.
- **Salida:** expectativa positiva tras costes en datos que no se usaron para ajustar, y drawdown compatible con las reglas FTMO. Si no la tiene, se cambia de estrategia (la IA no arregla una estrategia perdedora).

### Fase 2 · Motor en demo, solo reglas (2–4 semanas)
- Capas 1 y 4 + registro, corriendo en MT5 demo.
- Comprobar que lo que pasa en demo se parece al backtest (deslizamiento, horarios, fallos).
- **Salida:** semanas sin errores operativos, guardián de riesgo probado (incluido el corte diario).

### Fase 3 · IA en modo sombra (4–8 semanas)
- Añadir capas 2 y 3. Deciden y se registran, pero no bloquean.
- Medir: de las que habría frenado, ¿cuántas perdían de verdad? ¿Cuánto P&L habría ahorrado o perdido? Coste en tokens por señal.
- Prompts congelados durante el periodo.
- **Salida:** ≥100 señales con evidencia de que frenar mejora el resultado neto de costes. Si no, se descarta o se rediseña el filtro.

### Fase 4 · IA con veto real en demo + dashboard (4+ semanas)
- Dos cuentas demo en paralelo, con y sin agente (como el vídeo), y el dashboard.
- **Salida:** la versión con agente mantiene la mejora y respeta las reglas de la prop firm.

### Fase 5 · Prop firm
- Prueba gratuita / trial de la prop firm con el sistema completo.
- Solo después, y si tú lo decides, un reto de pago. Revisar antes las reglas vigentes sobre EAs y noticias.

## 7. Primer paso concreto

1. **Tú:** abrir una cuenta demo de MT5 (en FTMO trial o cualquier bróker) e instalar MetaTrader 5 en el PC. Decirme mercado, símbolos y si ya tienes alguna estrategia (aunque sea manual).
2. **Yo:** creo en esta carpeta el esqueleto del proyecto:
   ```
   trading-claude/
     config/      config.yaml (riesgo, símbolos), .env.example
     data/        descarga de histórico desde MT5
     strategies/  estrategia 1 (reglas)
     backtest/    backtest con costes + informe
     risk/        guardián de riesgo (corte diario, tamaño de posición)
     execution/   conector MT5 (solo demo; se niega a operar en cuenta real)
     agents/      analista (Haiku) y orquestador (Claude) — fase 3
     storage/     SQLite de decisiones
   ```
   y dejo funcionando la descarga de datos + el backtest de una estrategia simple de ejemplo (p. ej. ruptura del rango asiático en EURUSD M15), para tener la base de la Fase 1.

## 8. Preguntas abiertas

- ¿Qué mercado? (forex, índices, oro, acciones, cripto)
- ¿Objetivo final es pasar un reto FTMO u otra prop firm, o cuenta propia?
- ¿Tienes ya una estrategia que operes a mano, o partimos de cero?
- ¿Cuánto tiempo puede estar encendido el PC? (si no, habría que pensar en un VPS más adelante)
