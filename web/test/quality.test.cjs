const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Q = require("../quality.js");
const ROOT = path.resolve(__dirname, "../..");
const cuando = Date.parse("2026-11-16T22:00:00Z");

test("fechas ausentes o inválidas nunca aparecen como recientes", () => {
  assert.equal(Q.evaluarFecha(null, cuando).codigo, "sin_datos");
  assert.equal(Q.evaluarFecha("cualquier cosa", cuando).codigo, "fecha_invalida");
  assert.equal(Q.evaluarFecha("2026-11-17T12:00:00Z", cuando).codigo, "fecha_invalida");
});
test("fecha de solo día no se presenta como una hora exacta", () => {
  const v = Q.evaluarFecha("2026-11-16", cuando);
  assert.equal(v.codigo, "reciente");
  assert.equal(v.fecha, "2026-11-16");
});
test("el retraso se evalúa sobre el dato, no sobre la hora del build", () => {
  const d = { construido: "2026-11-16T21:00:00Z", ranking: { actualizado: "2026-11-12T20:00:00Z" } };
  const r = Q.resumen(d, cuando);
  assert.equal(r.fuentes.find(x => x.id === "ranking").codigo, "retrasado");
  assert.equal(r.sinDatos, 3);
});
test("sin datos no es lo mismo que cero alertas", () => {
  assert.equal(Q.resumen({}, cuando).avisos, null);
  assert.equal(Q.resumen({ estado: { alertas: [] } }, cuando).avisos, 0);
});
test("el panel sigue siendo JavaScript válido y contiene el centro de decisiones", () => {
  const html = fs.readFileSync(path.join(ROOT, "web/index.html"), "utf8");
  const code = html.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1];
  assert.ok(code, "script principal");
  assert.doesNotThrow(() => new vm.Script(code));
  assert.match(html, /function portada\(\)/);
  assert.match(html, /quality\.js/);
  assert.match(html, /decision-center\.css/);
  assert.match(html, /hoyDetalle\(\)/);
});
test("el compilador publica todas las dependencias locales del panel", () => {
  const code = fs.readFileSync(path.join(ROOT, "web/build.mjs"), "utf8");
  for (const name of ["quality.js", "decision-center.css", "datos.json", "index.html"]) {
    assert.ok(code.includes(name), name);
  }
});
