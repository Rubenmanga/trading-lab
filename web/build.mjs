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
if (seguimiento) for (const t of Object.keys(seguimiento.empresas || {})) seguimiento.empresas[t].texto = leer("investigacion/seguimiento", `${t}.md`) || "";
let estado = null;
try { estado = JSON.parse(leer("investigacion", "estado.json") || "null"); } catch { estado = null; }

const datos = {
  construido: new Date().toISOString(),
  watchlist: csv(leer("investigacion", "watchlist.csv")),
  candidatos: csv(leer("investigacion", "candidatos.csv")),
  estado,
  seguimiento,
  ranking,
  // Perfil «¿puede duplicar?»: el informe más reciente (o la lista provisional si aún no hay informe).
  duplicar: (markdowns("investigacion/duplicar", "INFORME")[0] || markdowns("investigacion/duplicar", "PROVISIONAL")[0] || null),
  informes: [
    ...markdowns("investigacion/analisis").map((d) => ({ ...d, clase: "Empresa" })),
    ...markdowns("investigacion", "oportunidades").map((d) => ({ ...d, clase: "Buscador" })),
    ...markdowns("investigacion", "sectores").map((d) => ({ ...d, clase: "Sectores" })),
    ...markdowns("investigacion", "repaso").map((d) => ({ ...d, clase: "Repaso" })),
    ...markdowns("diario").map((d) => ({ ...d, clase: "Diario intradía" })),
  ],
};

fs.rmSync(DIST, { recursive: true, force: true });
fs.mkdirSync(DIST, { recursive: true });
fs.writeFileSync(path.join(DIST, "datos.json"), JSON.stringify(datos));
fs.copyFileSync(path.join(RAIZ, "web", "index.html"), path.join(DIST, "index.html"));
fs.cpSync(path.join(RAIZ, "web", "vendor"), path.join(DIST, "vendor"), { recursive: true });
console.log(`Panel listo: ${datos.ranking ? datos.ranking.filas.length : 0} en ranking, ${datos.watchlist.length} en vigilancia, ${datos.candidatos.length} candidatos, ${datos.informes.length} informes.`);
