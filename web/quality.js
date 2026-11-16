/* Contrato de transparencia para el panel. No depende de APIs externas. */
(function (root) {
  "use strict";
  const HORA = 3600000;
  function evaluarFecha(valor, ahora = Date.now(), maxHoras = 84) {
    if (typeof valor !== "string" || !valor.trim()) return { codigo: "sin_datos", fecha: null, edadHoras: null };
    const soloDia = /^\d{4}-\d{2}-\d{2}$/.test(valor);
    const momento = Date.parse(soloDia ? valor + "T23:59:59Z" : valor);
    if (!Number.isFinite(momento)) return { codigo: "fecha_invalida", fecha: valor, edadHoras: null };
    if (momento - ahora > 4 * HORA) return { codigo: "fecha_invalida", fecha: valor, edadHoras: null };
    const edad = Math.max(0, (ahora - momento) / HORA);
    return { codigo: edad > maxHoras ? "retrasado" : "reciente", fecha: valor, edadHoras: Math.round(edad) };
  }
  function calidad(datos, ahora = Date.now()) {
    const fuentes = [
      { id: "ranking", nombre: "Radar 12 meses", fecha: datos?.ranking?.actualizado, maxHoras: 84, ruta: "#/ranking" },
      { id: "alertas", nombre: "Alertas de precios", fecha: datos?.estado?.actualizado, maxHoras: 84, ruta: "#/vigilancia" },
      { id: "noticias", nombre: "Seguimiento de noticias", fecha: datos?.seguimiento?.lista?.fecha, maxHoras: 108, ruta: "#/seguimiento" },
      { id: "laboratorio", nombre: "Laboratorio intradía", fecha: datos?.lab?.actualizado, maxHoras: 108, ruta: "#/lab" },
    ];
    return fuentes.map(({ maxHoras, ...f }) => ({ ...f, ...evaluarFecha(f.fecha, ahora, maxHoras) }));
  }
  function resumen(datos, ahora = Date.now()) {
    const f = calidad(datos, ahora);
    const sinDatos = f.filter(x => x.codigo === "sin_datos" || x.codigo === "fecha_invalida");
    const retrasadas = f.filter(x => x.codigo === "retrasado");
    const alertas = datos?.estado?.alertas;
    return { fuentes: f, sinDatos: sinDatos.length, retrasadas: retrasadas.length,
      avisos: Array.isArray(alertas) ? alertas.length : null,
      actualizado: datos?.construido || null };
  }
  const api = Object.freeze({ evaluarFecha, calidad, resumen });
  root.TradingLabQuality = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
