# Trading Lab 🧪 (solo cuenta demo)

Laboratorio para aprender trading con ayuda de Claude, **sin dinero real y sin gastar nada** aparte de
tu suscripción de Claude. Tiene **dos agentes separados**:

| | Agente A · Intradía | Agente B · Medio plazo (12 meses) |
|---|---|---|
| Qué hace | Abre y cierra operaciones **el mismo día** en la cuenta demo de Alpaca | Busca y analiza **small caps de cualquier sector** con buenas perspectivas a 12 meses |
| Cuándo | Con el PC encendido, ~15:30-18:30 (hora de Madrid) | Cuando quieras (también desde el móvil) |
| ¿Opera solo? | Sí, en demo, con reglas fijas de riesgo | **No**: analiza, guarda una lista de vigilancia y avisa |
| Dónde está | `src/tradinglab/intradia/` · `config/intradia.yaml` | `src/tradinglab/medio_plazo/` · `config/medio_plazo.yaml` · `investigacion/` |

> 🔒 **Regla fija:** el código solo se conecta a la cuenta *paper* (demo) de Alpaca. Si en `.env` pone
> otra cosa que `ALPACA_PAPER=true`, o en la configuración otra cosa que `modo_cuenta: demo`, se niega a arrancar.

---

## Mini-glosario

- **Demo / paper trading**: cuenta con dinero ficticio y precios reales.
- **Intradía**: se abre y se cierra en el mismo día. Nada se queda abierto por la noche.
- **Stop loss (SL)**: precio al que se cierra la operación para limitar la pérdida. Aquí, a un **1%** de la entrada.
- **R**: lo que arriesgas en una operación (la distancia hasta el stop). **3:1** significa que el objetivo
  está a 3 veces esa distancia: arriesgas 1 para ganar 3.
- **Trailing stop**: un stop que "persigue" al precio cuando va a tu favor, para proteger lo ganado.
- **Backtest**: probar una estrategia con datos del pasado.
- **Modo sombra**: la IA da su opinión y se apunta, pero **no** bloquea nada. Así medimos si acierta.
- **Small cap**: empresa pequeña en bolsa (aquí, entre 300 y 2.000 millones de dólares).
- **Catalizador**: un evento con fecha que puede mover mucho la acción (resultados, aprobación de un
  producto, un contrato, un ensayo clínico...).
- **Precio objetivo de los analistas**: precio al que los analistas creen que llegará la acción en ~12 meses.

---

## Cómo funciona el agente A (intradía)

```
 Velas de 5 min (Alpaca, gratis)
        │
        ▼
 1. ESTRATEGIA ──► propone "compra SPY a 500"         (hueco enchufable: estrategias/)
        │
        ▼
 2. REGLAS FIJAS ─► ¿en horario? ¿ratio ≥ 3:1? ¿ya hay posición?
        │
        ▼
 3. GESTOR DE RIESGO (sin IA, siempre manda)
        · stop 1% y objetivo 3R (o 4R)
        · corte si el día pierde un 2%
        · máximo 4 operaciones al día y 2 a la vez
        · tamaño para perder solo un 0,5% del capital si salta el stop
        │
        ▼
 4. ANALISTA IA (Claude, con tu suscripción) ─► mira noticias y contexto: "pasa" o "frena"
        · modo sombra: solo opina   · modo veto: puede frenar
        │
        ▼
 5. EJECUCIÓN en Alpaca demo (orden con stop y objetivo ya puestos) + trailing stop
        │
        ▼
 Todo se apunta con su motivo en data/lab.db  →  panel web y diario/
 A la hora de cierre forzado: se cierra TODO.
```

La **estrategia todavía no está elegida**: viene una de ejemplo (`ejemplo_cruce_medias`) solo para comprobar
que la tubería funciona. La elegiremos con la skill `investigar-estrategias-intradia`.

## Cómo funciona el agente B (12 meses)

Un "equipo" de analistas hecho con Claude (idea de TradingAgents):

1. **Buscar** (`buscar-small-caps`): qué sectores esperan los analistas que vayan bien a 12 meses →
   cribado de small caps de EE. UU. con varios analistas y un precio objetivo bastante por encima del actual.
2. **Analizar** (`analizar-empresa-12m`): analista fundamental, de catalizadores y noticias, de expectativas
   (¿el precio ya descuenta lo bueno?), de sentimiento y técnico → **debate alcista contra bajista** →
   **gestor de riesgo** que decide: comprar en zona / vigilar / descartar, con zona de entrada,
   precio objetivo propio y "stop de tesis".
3. **Vigilar** (`lab medio alertas` y `revisar-cartera-12m`): avisa si una empresa entra en su zona de
   entrada, si un catalizador está cerca, si cae bajo el stop de tesis o si el análisis se ha quedado viejo.

Los informes se guardan en `investigacion/` como texto, así los puedes **leer desde el móvil en GitHub**.

---

## Empezar (Windows) · paso a paso

### 1. Instala lo necesario (una vez)
- **Python 3.11 o superior**: https://www.python.org/downloads/ (marca *"Add Python to PATH"* al instalar).
- **Git** o **GitHub Desktop**: https://desktop.github.com/
- **Claude Code** (para el analista IA y las skills): https://claude.com/claude-code . Inicia sesión con tu
  cuenta de Claude (la suscripción que ya pagas). **No** hace falta clave de API.

### 2. Descarga el repo
Con GitHub Desktop: *File → Clone repository → Rubenmanga/trading-lab*. Elige por ejemplo
`C:\Users\JUAN MIGUEL\Documents\Ruben\trading-lab`.

### 3. Instala el proyecto
Doble clic en `scripts\instalar.bat`. Crea un entorno de Python (`.venv`) e instala todo.

### 4. Prueba sin claves (2 minutos)
Doble clic en `scripts\demo.bat`. Hace un backtest con **datos inventados** y abre el panel web en el
navegador. Sirve para ver que todo funciona, **no** para saber si la estrategia gana.

### 5. Crea tu cuenta demo de Alpaca (gratis)
1. Regístrate en https://alpaca.markets (no hace falta ingresar dinero).
2. Entra en https://app.alpaca.markets y asegúrate de estar en **Paper Trading** (arriba a la izquierda).
3. En la página principal, sección **API Keys** → **Generate New Keys**. Copia las dos claves
   (la secreta solo se ve una vez).
4. Abre el archivo `.env` de la carpeta del proyecto con el Bloc de notas y pégalas:
   ```
   ALPACA_API_KEY=PK...
   ALPACA_SECRET_KEY=...
   ALPACA_PAPER=true
   ```
5. Comprueba la conexión: abre una terminal en la carpeta, ejecuta `.venv\Scripts\activate` y luego
   `lab intradia comprobar`.

### 6. Primera sesión intradía
1. En `config/intradia.yaml` cambia `broker: simulado` por `broker: alpaca` (o déjalo en `simulado`
   para usar precios reales pero con una cuenta sombra interna).
2. Hacia las 15:30 de Madrid, doble clic en `scripts\sesion_intradia.bat`. Déjalo abierto: termina solo
   tras el cierre forzado (18:20) y escribe el diario del día.
3. Para verlo: `scripts\panel.bat`. Para parar y cerrar todo ya: `Ctrl+C` en la ventana, o `scripts\cerrar_todo.bat`.

### 7. Activar el analista IA (cuando quieras)
En `config/intradia.yaml`:
```yaml
ia:
  revisor: claude_cli   # usa Claude Code de tu PC, con tu suscripción
  modo: sombra          # primero solo opina; pasaremos a "veto" si demuestra que acierta
```
Cada revisión tarda unos 30-90 segundos y consume parte de tu límite de uso de Claude.

### 8. Agente B
Abre Claude Code en la carpeta del proyecto (`claude`) y escribe, por ejemplo:
- *"Usa la skill buscar-small-caps"*
- *"Analiza ABCD con la skill analizar-empresa-12m"*
- *"Revisa mi lista con revisar-cartera-12m"*

O en la terminal: `lab medio cribado`, `lab medio ficha ABCD`, `lab medio alertas`.

---

## Desde el móvil
- **Leer**: todo lo que generan los agentes (informes en `investigacion/`, diarios en `diario/`) está en
  GitHub; ábrelo desde la app de GitHub o el navegador.
- **Trabajar**: en claude.ai/code (o la app de Claude) puedes abrir una sesión sobre este repo y pedir
  análisis del agente B. Ojo: desde la nube, Yahoo Finance a veces está bloqueado, así que `lab medio ficha`
  puede fallar; Claude completará con búsquedas web.
- El **agente A** necesita tu PC encendido (no hay servidor por ahora). Para no olvidar subir los
  resultados, al terminar la sesión haz *commit* y *push* desde GitHub Desktop.

## Comandos (`lab ...`)
| Comando | Qué hace |
|---|---|
| `lab intradia demo` | Prueba completa con datos inventados (sin claves) |
| `lab intradia comprobar` | Comprueba claves de Alpaca demo y si la bolsa está abierta |
| `lab intradia backtest --dias 60` | Backtest con datos reales del pasado (Alpaca, gratis) |
| `lab intradia sesion` | Sesión en vivo durante la ventana |
| `lab intradia cerrar-todo` | Botón del pánico: cierra todo en la demo |
| `lab diario` | Escribe el diario del día en `diario/` |
| `lab medio cribado` | Busca small caps con potencial según analistas |
| `lab medio ficha TICKER` | Datos de una empresa |
| `lab medio alertas` | Revisa la lista de vigilancia |
| `lab panel` | Panel web (pestañas Intradía, Medio plazo y Backtests) |

## Estructura
```
config/            intradia.yaml · medio_plazo.yaml   ← aquí se ajusta todo
src/tradinglab/
  common/          configuración, base de datos, conexión Alpaca (solo paper), horario
  intradia/        motor, reglas, riesgo, trailing, revisor IA, backtest, sesión, brokers/, estrategias/
  medio_plazo/     datos (yfinance), cribado, lista de vigilancia, alertas
  diario.py · cli.py
.claude/skills/    skills de Claude (propias y de tradermonty)
dashboard/app.py   panel web (Streamlit)
investigacion/     watchlist.csv · candidatos.csv · alertas.md · analisis/ · estrategias/
diario/            diario de cada sesión intradía
scripts/           .bat para Windows (doble clic)
tests/             pruebas automáticas (pytest)
docs/historico/    planes anteriores
```

## Lo que tienes que hacer tú
1. Instalar Python, GitHub Desktop y Claude Code, y clonar el repo (pasos 1-3).
2. Crear la cuenta **paper** de Alpaca y poner las claves en `.env` (paso 5). Nunca compartas ese archivo.
3. Decidir **mercado/valores** para el agente A, para lanzar la investigación de estrategias.
4. Encender el PC en la ventana y lanzar la sesión.

## Siguientes pasos (hoja de ruta)
1. ✅ Esqueleto de los dos agentes, riesgo, Alpaca demo, panel, skills.
2. Elegir mercado → `investigar-estrategias-intradia` → enchufar la estrategia ganadora y hacer backtest real.
3. Semanas de demo con la IA en **modo sombra** (mínimo ~100 señales antes de sacar conclusiones).
4. Agente B: primera ronda de `buscar-small-caps` y análisis de 5-10 empresas.
5. Más adelante, si hace falta: servidor siempre encendido (VPS), avisos al móvil.

## Con honestidad
- Con stop 1% y objetivo 3%, en solo 3 horas muchas operaciones acabarán cerradas por el **cierre forzado**
  antes de llegar al objetivo (la demo lo muestra). La estrategia y los valores tendrán que tener
  suficiente movimiento; lo veremos en la investigación.
- La IA no se puede probar con datos del pasado (ya "sabe" lo que pasó): solo hacia delante, en modo sombra.
- En demo no hay miedo ni deslizamientos reales: los resultados reales suelen ser peores.
- Las small caps se mueven mucho y pueden caer con fuerza. Ninguna posición debería ser grande.

## Licencias de terceros
Ver [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md): skills de tradermonty (MIT), estructura de roles de
TradingAgents (Apache-2.0) e ideas de Vibe-Trading (MIT).
