// Construye el panel web (solo lectura) a partir de los archivos del repo.
// Sin dependencias: lo ejecuta Vercel en cada cambio de la rama main (`node web/build.mjs`).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(RAIZ, "web", "dist");
const leer = (...p) => { try { return fs.readFileSync(path.join(RAIZ, ...p), "utf8"); } catch { return null; } };

function csv(texto) {
  if (!texto) return [];
  const filas = []; let fila = [], campo = "", comillas = false;
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i];
    if (comillas) {
      if (c === '"' && texto[i + 1] === '"') { campo += '"'; i++; }
      else if (c === '"') comillas = false;
      else campo += c;
    } else if (c === '"') comillas = true;
    else if (c === ",") { fila.push(campo); campo = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && texto[i + 1] === "\n") i++;
      fila.push(campo); campo = "";
      if (fila.some((x) => x !== "")) filas.push(fila);
      fila = [];
    } else campo += c;
  }
  fila.push(campo); if (fila.some((x) => x !== "")) filas.push(fila);
  const [cab, ...resto] = filas;
  return cab ? resto.map((f) => Object.fromEntries(cab.map((k, i) => [k.trim(), (f[i] ?? "").trim()]))) : [];
}

function markdowns(carpeta, tipo) {
  const dir = path.join(RAIZ, carpeta);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".md") && (!tipo || f.startsWith(tipo)))
    .map((f) => {
      const texto = fs.readFileSync(path.join(dir, f), "utf8");
      const titulo = (texto.match(/^#\s+(.+)$/m) || [, f.replace(/\.md$/, "")])[1];
      const fecha = (f.match(/(\d{4}-\d{2}-\d{2})/) || [, ""])[1];
      return { id: `${carpeta}/${f}`, archivo: f, titulo, fecha, texto };
    })
    .sort((a, b) => b.fecha.localeCompare(a.fecha) || a.archivo.localeCompare(b.archivo));
}

let ranking = null;
try { ranking = JSON.parse(leer("investigacion", "ranking.json") || "null"); } catch { ranking = null; }
let seguimiento = null;
try { seguimiento = JSON.parse(leer("investigacion", "seguimiento.json") || "null"); } catch { seguimiento = null; }
if (seguimiento) for (const t of Object.keys(seguimiento.empresas || {})) { seguimiento.empresas[t].texto = leer("investigacion/seguimiento", `${t}.md`) || ""; seguimiento.empresas[t].notas = leer("investigacion/seguimiento", `${t}-notas.md`) || ""; }
// La lista de noticias guarda memoria interna (titulares vistos, etc.) que el panel no necesita.
for (const g of ["empresas", "materias_primas"]) for (const e of Object.values(seguimiento?.lista?.[g] || {})) { delete e.vistos; delete e.sec_vistos; delete e.anterior; delete e.avisados; }
// Laboratorio intradía (agente A): estrategias en cuenta sombra, resumen calculado por GitHub Actions.
let lab = null;
try { lab = JSON.parse(leer("investigacion/laboratorio", "resumen.json") || "null"); } catch { lab = null; }
let estado = null;
try { estado = JSON.parse(leer("investigacion", "estado.json") || "null"); } catch { estado = null; }

// Bot del corto del hueco (agente A, eToro DEMO): registro de decisiones y unos pocos parámetros de su config.
const cfgCorto = {};
for (const l of (leer("config", "corto_hueco.yaml") || "").split("\n")) {
  const m = l.match(/^([a-z_]+):\s*"?([^"#]+?)"?\s*(#.*)?$/);
  if (m) cfgCorto[m[1]] = isNaN(+m[2]) ? m[2] : +m[2];
}
delete cfgCorto.modo_cuenta;

// Mis acciones reales (config/mi_cartera.csv). Ruben aceptó (16-nov-2026) que el panel muestre cantidades e importes:
// no hay claves ni datos de acceso, solo posiciones. Si algún día quiere ocultarlos, quitar `cantidad` e `importe_eur` aquí.
const num0 = (x) => (x === "" || x == null || isNaN(+x) ? null : +x);
const cartera = csv(leer("config", "mi_cartera.csv")).map((r) => ({
  ticker: r.ticker, broker: r.broker, moneda: r.moneda, estado: r.estado || "abierta",
  precio_entrada: num0(r.precio_medio), cantidad: num0(r.cantidad), importe_eur: num0(r.importe_eur),
  // Ventas (estado «vendida»): fecha, precio, dinero neto que entró y comisión.
  fecha_venta: r.fecha_venta || null, precio_venta: num0(r.precio_venta), neto_venta: num0(r.neto_venta), comision_venta: num0(r.comision_venta),
}));

// Expediente por acción (paso 2): una sola línea de tiempo por empresa, juntando lo que ya se guarda.
// Fuentes: investigacion/expedientes/T/eventos.csv (SEC y Yahoo, con enlace), el historial diario de la lista
// de noticias, los titulares guardados y los informes del vigilante. Solo lectura: no se toca ningún archivo.
function expedientes() {
  const out = {};
  const poner = (t, e) => { (out[t] ||= []).push(e); };
  const dirE = path.join(RAIZ, "investigacion", "expedientes");
  if (fs.existsSync(dirE)) for (const t of fs.readdirSync(dirE)) {
    for (const r of csv(leer("investigacion/expedientes", t, "eventos.csv")))
      poner(t, { f: r.fecha, tipo: r.tipo, txt: r.resumen, url: r.fuente_url, r1: num0(r.reaccion_1d), r5: num0(r.reaccion_5d), r20: num0(r.reaccion_20d), de: /sec\.gov/.test(r.fuente_url) ? "SEC" : /yahoo/.test(r.fuente_url) ? "Yahoo" : "" });
  }
  // Historial diario: solo los días con algo que contar (no los «movimiento normal»).
  for (const r of csv(leer("investigacion/seguimiento", "lista-historial.csv")))
    if (r.grande === "1" || (r.porque && !/^Movimiento normal/.test(r.porque)))
      poner(r.ticker, { f: r.fecha, tipo: "dia", txt: `${+r.cambio_pct > 0 ? "Sube" : "Baja"} ${Math.abs(+r.cambio_pct)} % (cierre ${r.cierre}). ${r.porque}`, de: "Seguimiento" });
  for (const g of ["empresas", "materias_primas"]) for (const [t, e] of Object.entries(seguimiento?.lista?.[g] || {}))
    for (const n of e.titulares || []) poner(t, { f: n.fecha, tipo: "noticia", txt: n.titulo, url: n.url, de: n.fuente || "", imp: !!n.importante });
  const dirV = path.join(RAIZ, "investigacion", "vigilante");
  if (fs.existsSync(dirV)) for (const a of fs.readdirSync(dirV)) {
    const m = a.match(/^([A-Z.]+)-(\d{4}-\d{2}-\d{2})\.md$/); if (!m) continue;
    const lineas = (leer("investigacion/vigilante", a) || "").split("\n").filter((l) => /^[245]\. /.test(l)).map((l) => l.slice(3).replace(/\*\*/g, ""));
    poner(m[1], { f: m[2], tipo: "vigilante", txt: lineas.join(" "), id: `investigacion/vigilante/${a}`, de: "Vigilante" });
  }
  for (const t of Object.keys(out)) {
    const vistos = new Set();
    out[t] = out[t].filter((e) => e.f && !vistos.has(e.f + e.tipo + (e.url || e.txt)) && vistos.add(e.f + e.tipo + (e.url || e.txt)))
      .sort((a, b) => b.f.localeCompare(a.f));
  }
  return out;
}

const datos = {
  construido: new Date().toISOString(),
  watchlist: csv(leer("investigacion", "watchlist.csv")),
  candidatos: csv(leer("investigacion", "candidatos.csv")),
  estado,
  seguimiento,
  ranking,
  cartera,
  expedientes: expedientes(),
  // Paso 3: libro de predicciones (solo añadir) y su puntuación frente al índice de small caps (IWM).
  predicciones: csv(leer("investigacion", "predicciones.csv")),
  propuestas: markdowns("investigacion/propuestas").slice(0, 7),
  // Paso 7: calculadora del precio de entrada (3 escenarios de cada tesis.md).
  entradas: (() => { try { return JSON.parse(leer("investigacion", "entradas.json") || "{}"); } catch { return {}; } })(),
  marcador: (() => { try { return JSON.parse(leer("investigacion/marcador", "marcador.json") || "null"); } catch { return null; } })(),
  lab,
  lab_demo: csv(leer("investigacion/laboratorio/demo", "registro.csv")),
  corto: { registro: csv(leer("investigacion/corto-hueco", "registro.csv")), config: cfgCorto,
    // Paso 9: marcador del bot (real frente al backtest) y fecha de decisión.
    marcador: (() => { try { return JSON.parse(leer("investigacion/corto-hueco", "marcador.json") || "null"); } catch { return null; } })() },
  historial_lista: csv(leer("investigacion/seguimiento", "lista-historial.csv")).map(({ porque, ...r }) => r),
  // Perfil «¿puede duplicar?»: el informe más reciente (o la lista provisional si aún no hay informe).
  duplicar: (markdowns("investigacion/duplicar", "INFORME")[0] || markdowns("investigacion/duplicar", "PROVISIONAL")[0] || null),
  // Investigación «+500 %»: objetivos de analistas que multiplican por 6 (el informe más reciente).
  quintuplicar: (markdowns("investigacion/quintuplicar", "INFORME")[0] || null),
  informes: [
    ...markdowns("investigacion/analisis").map((d) => ({ ...d, clase: "Empresa" })),
    ...markdowns("investigacion/propuestas").map((d) => ({ ...d, clase: "Investigador diario" })),
    ...markdowns("investigacion/quintuplicar", "INFORME").map((d) => ({ ...d, clase: "+500 %" })),
    ...markdowns("investigacion", "oportunidades").map((d) => ({ ...d, clase: "Buscador" })),
    ...markdowns("investigacion", "sectores").map((d) => ({ ...d, clase: "Sectores" })),
    ...markdowns("investigacion", "repaso").map((d) => ({ ...d, clase: "Repaso" })),
    ...markdowns("investigacion", "validacion").map((d) => ({ ...d, clase: "¿Acierta el ranking?" })),
    ...markdowns("investigacion/vigilante").map((d) => ({ ...d, clase: "Vigilante" })),
    ...markdowns("investigacion/corto-hueco").map((d) => ({ ...d, clase: "Corto del hueco" })),
    ...markdowns("investigacion/laboratorio", "INFORME").map((d) => ({ ...d, fecha: d.fecha || lab?.actualizado || "", clase: "Laboratorio intradía" })),
    ...markdowns("investigacion/estrategias").map((d) => ({ ...d, clase: "Intradía (agente A)" })),
    ...markdowns("investigacion/backtest-12m", "INFORME").map((d) => ({ ...d, clase: "Backtest 12 meses" })),
    ...markdowns("diario").map((d) => ({ ...d, clase: "Diario intradía" })),
  ],
};

fs.rmSync(DIST, { recursive: true, force: true });
fs.mkdirSync(DIST, { recursive: true });
fs.writeFileSync(path.join(DIST, "datos.json"), JSON.stringify(datos));
fs.copyFileSync(path.join(RAIZ, "web", "index.html"), path.join(DIST, "index.html"));
fs.cpSync(path.join(RAIZ, "web", "vendor"), path.join(DIST, "vendor"), { recursive: true });
console.log(`Panel listo: ${datos.ranking ? datos.ranking.filas.length : 0} en ranking, ${datos.watchlist.length} en vigilancia, ${datos.candidatos.length} candidatos, ${datos.informes.length} informes, ${Object.values(datos.expedientes).flat().length} hechos en ${Object.keys(datos.expedientes).length} expedientes.`);
