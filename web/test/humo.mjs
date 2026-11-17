// Prueba de humo del panel, sin navegador ni dependencias: `node web/build.mjs && node web/test/humo.mjs`.
// Comprueba que el panel generado tiene los datos que la portada necesita y que su JavaScript no tiene errores de sintaxis.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const DIST = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "dist");
const fallos = [];
const ok = (cond, msg) => { if (!cond) fallos.push(msg); };

const datos = JSON.parse(fs.readFileSync(path.join(DIST, "datos.json"), "utf8"));
for (const k of ["construido", "salud", "watchlist", "cartera", "expedientes", "predicciones", "informes", "corto"]) ok(k in datos, `falta «${k}» en datos.json`);
ok(Array.isArray(datos.salud) && datos.salud.length >= 5, "el estado del sistema debe listar al menos 5 automatismos");
for (const s of datos.salud || []) ok(s.id && s.nombre && Array.isArray(s.dias) && typeof s.hora === "number", `automatismo mal descrito: ${JSON.stringify(s).slice(0, 80)}`);
// Nada de claves ni secretos en lo que se publica.
const crudo = fs.readFileSync(path.join(DIST, "datos.json"), "utf8");
ok(!/(api[_-]?key|secret|token)["']?\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}/i.test(crudo), "datos.json parece contener una clave");

const html = fs.readFileSync(path.join(DIST, "index.html"), "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
ok(scripts.length >= 1, "index.html no tiene script");
for (const s of scripts) { try { new vm.Script(s); } catch (e) { fallos.push(`JavaScript del panel con error de sintaxis: ${e.message}`); } }
for (const ruta of ["#/", "#/cartera", "#/ideas", "#/agente-a", "#/mas"]) ok(html.includes(`href="${ruta}"`), `falta la pestaña ${ruta}`);
ok(/viewport/.test(html), "falta la etiqueta viewport (móvil)");

if (fallos.length) { console.error("PANEL: FALLA\n- " + fallos.join("\n- ")); process.exit(1); }
console.log(`PANEL: OK (${datos.salud.length} automatismos, ${scripts.length} script, ${(html.length / 1024).toFixed(0)} KB)`);
