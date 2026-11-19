# Rediseño del panel (UX/UI)

**Fecha:** 17-nov-2026. Archivos: `web/index.html`, `web/build.mjs`, `web/test/humo.mjs`. No está en producción hasta que lo apruebes.

## Resumen en 5 líneas

1. **Lo primero que ves ahora es si te puedes fiar de lo que hay debajo**: una franja «Sistema al día / con retraso / parado».
2. **La portada sigue un orden de decisión**: estado → 3 cifras → qué requiere tu atención → ideas del investigador → agenda → los dos agentes.
3. **De 15 pestañas al mismo nivel a 5 secciones**: Hoy · Mis acciones · Ideas · Bot · Más. Los estudios cerrados pasan a «Archivo».
4. **Cada pantalla dice qué clase de información enseña**: hecho, estimación, propuesta de la IA, pasado o demo.
5. **Nuevo sistema visual** sobrio y denso, con las cifras en letra de ancho fijo. Sin librerías nuevas.

## Las preguntas de partida y sus respuestas

| Pregunta | Respuesta | Cómo se refleja |
|---|---|---|
| ¿Qué necesitas saber al abrir? | 1) ¿Los datos son de hoy? 2) ¿Pasa algo con MIS acciones? 3) ¿Hay alguna idea nueva? | Los tres primeros bloques de la portada, en ese orden |
| ¿Qué es secundario? | Ranking completo, laboratorio, estudios antiguos, detalle de fuentes | A un toque, dentro de su sección; nunca en la portada |
| ¿Qué necesita explicación? | Toda cifra calculada (zona de entrada, nota, R, backtest) | Franja de contexto bajo el título de cada pantalla |
| ¿Qué gráficos ayudan a decidir? | Barras de resultado por posición, escala stop-entrada-objetivo, progreso del bot hacia su decisión | Se conservan los dos primeros; se añade el tercero |
| ¿Y cuáles solo ocupaban? | Las 4 cifras grandes de antes (semáforo macro, «avisos: 9») | Sustituidas por 3 cifras que sí cambian lo que haces |
| ¿Qué pasa si un dato falla o es viejo? | Antes: nada visible. Ahora: franja ámbar o roja, punto en la pestaña «Hoy», e ideas marcadas «zona sin confirmar» | `salud()` y `preciosViejos()` en `web/index.html` |
| ¿Demasiado texto? | Sí: las propuestas eran un bloque de Markdown y los avisos repetían titulares | Ideas en tarjetas con 4 cifras; avisos agrupados por empresa, máximo 4 a la vista |
| ¿Se distingue oportunidad, riesgo y señal sin confirmar? | Antes no | Color con significado + etiqueta de evidencia + «sin confirmar» cuando el precio es viejo |

## Lectura por niveles

1. **Esencial** (portada, sin desplazarte): estado del sistema y 3 cifras.
2. **Explicación breve** (portada, al bajar): avisos en una línea, ideas con su motivo, agenda.
3. **Análisis** (un toque): historia de cada acción, lista vigilada, bot.
4. **Evidencia original** (dos toques): informe completo con tabla de fuentes, enlaces a la SEC, registro del bot.

## Navegación

| Antes | Ahora |
|---|---|
| Barra inferior: Hoy · Mis acciones · Ranking · Noticias · Más. Arriba (escritorio): 12 pestañas | Hoy · Mis acciones · **Ideas** (agente B) · **Bot** (agente A) · Más, igual en móvil y escritorio |
| Vigilancia, Marcador y Bot escondidos en «Más» | **Ideas** agrupa Lista vigilada · Ranking · Aciertos · Noticias. **Bot** agrupa Bot en demo · Laboratorio |
| «¿Puede duplicar?» y «¿+500 %?» al mismo nivel que lo diario | En «Más → Archivo», con la fecha del estudio |
| «Salud de las fuentes» al fondo | «Estado del sistema», enlazado desde la franja de arriba |

Las direcciones antiguas siguen funcionando (`#/ranking`, `#/bot`, `#/fuentes`…): ningún enlace guardado se rompe.

## Sistema de diseño

- **Color = significado, nunca adorno.** Verde: bien o a favor. Ámbar: atento o con retraso. Rojo: peligro o parado. Azul: enlace o dato. Violeta: lo propone la IA. Gris: pasado o archivo.
- **Tipografía.** Texto con la letra del sistema (carga instantánea, sin descargas). **Cifras y tickers en letra de ancho fijo**, para que se alineen como en una pantalla de bolsa.
- **Forma.** Tarjetas planas con borde fino, radio de 10 px, sin sombras ni degradados. Listas densas dentro de una sola tarjeta en vez de una tarjeta por elemento.
- **Marca.** «Trading Lab» con un monograma `TL` y la etiqueta fija «SOLO DEMO» en la cabecera.
- **Etiquetas de evidencia** (`.ev`): `HECHO` · `ESTIMACIÓN` · `PROPUESTA IA` · `PASADO` · `DEMO`.
- **Estados.** Sin datos: caja con explicación de cuándo llegarán. Dato viejo: ámbar con las dos fechas (la que hay y la que se esperaba). Parado: rojo con enlace para lanzarlo a mano. Error al dibujar: caja con el mensaje, sin tumbar el resto.
- **Accesibilidad.** Contraste de texto ≥ 4,5:1 en los dos temas, foco visible con teclado, botones de la barra de ≥ 48 px, `aria-current` en la pestaña activa, respeto a «reducir movimiento». Tema oscuro, claro o automático.

## Qué estudié de otras herramientas (principios, no copias)

- **De las plataformas de gráficos profesionales:** cifras en ancho fijo, color reservado para subir/bajar, densidad alta con jerarquía por tamaño y peso.
- **De los paneles de análisis fundamental:** una tabla densa vale más que diez tarjetas; cada cifra con su fecha.
- **De los paneles de estado de servicios:** una sola frase arriba («todo funciona» / «hay incidencias») antes de cualquier detalle.
- No he navegado esas webs en esta sesión (por ahorro de cuota): son principios conocidos de diseño de información, aplicados a tu caso.

## Comprobado

- 15 pantallas × móvil (390 px) y escritorio (1280 px): **sin errores de JavaScript y sin desplazamiento horizontal**.
- Portada revisada en tema oscuro y claro.
- `node web/test/humo.mjs`: datos mínimos, sintaxis y las 5 pestañas.

## Límites y pendientes

- **No probado en un móvil físico** ni con lector de pantalla.
- Las pantallas de detalle (ranking, laboratorio, ficha de empresa) heredan el estilo nuevo, pero **su contenido no se ha reorganizado**. «Lista vigilada» sigue repitiendo avisos largos.
- Faltan gráficos que sí ayudarían: precio histórico por acción y curva del capital demo del bot (no hay datos todavía para el segundo).
- El archivo `web/index.html` sigue siendo uno solo (147 KB).
