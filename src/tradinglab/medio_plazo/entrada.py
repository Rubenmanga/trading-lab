"""Calculadora del precio de entrada (Paso 7 de la revisión del 16-nov-2026).

Siempre el mismo método, sin IA: con los mismos datos sale siempre el mismo precio.

Datos: la tabla de escenarios de `investigacion/expedientes/TICKER/tesis.md` (sección
«## Escenarios y precio de entrada»): malo, normal y bueno, cada uno con su probabilidad y el precio
que tendría la acción en 12 meses. Si la tabla está vacía, se copia la del último informe
`investigacion/analisis/TICKER-*.md` (diciendo de cuál sale).

Cálculo:
- valor esperado = media de los tres precios ponderada por su probabilidad;
- regla 1 (3 a 1): lo que ganas si sale «normal» ≥ 3 veces lo que pierdes si sale «malo»
  → precio ≤ (normal + 3·malo) / 4;
- regla 2 (margen): precio ≤ valor esperado · (1 − 15 %);
- precio de entrada = el más bajo de los dos, redondeado hacia abajo al céntimo.
En apuestas «todo o nada» (decisión de la FDA, un ensayo) no hay precio bueno: se avisa y se decide el tamaño.

Salidas: el bloque de resultado dentro de `tesis.md` (solo cambia si cambian los datos) e
`investigacion/entradas.json` (para el panel, la carpeta del día y el investigador diario).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from ..common.config import ruta

RATIO = 3          # ganar al menos 3 veces lo que se puede perder
MARGEN = 0.15      # comprar al menos un 15 % por debajo del valor esperado
UMBRAL_BINARIA = 0.25  # si el caso malo vale ≤ 25 % del normal, parece «todo o nada»
SECCION = "## Escenarios y precio de entrada"
INI, FIN = "<!-- entrada:inicio -->", "<!-- entrada:fin -->"
NOMBRES = {"malo": "malo", "bajista": "malo", "base": "normal", "normal": "normal", "medio": "normal",
           "bueno": "bueno", "alcista": "bueno"}
TABLA_VACIA = ["| escenario | probabilidad | precio en 12 meses | qué tiene que pasar |", "|---|---|---|---|",
               "| malo | | | |", "| normal | | | |", "| bueno | | | |", "",
               "Tipo: normal _(pon «binaria» si todo depende de un solo hecho, p. ej. una decisión de la FDA)_"]


def _num(txt: str) -> float | None:
    """'95-100 $' → 97.5 · '5,5 $' → 5.5 · '45 %' → 45. Sin número → None."""
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", txt or "")]
    if not nums:
        return None
    return (nums[0] + nums[1]) / 2 if len(nums) >= 2 and re.search(r"\d\s*[-–]\s*\d", txt) else nums[0]


def leer_tabla(texto: str) -> dict[str, dict]:
    """Busca una tabla con columnas escenario / probabilidad / precio y devuelve {malo|normal|bueno: {...}}."""
    lineas = texto.splitlines()
    for i, ln in enumerate(lineas):
        cab = [c.strip().lower() for c in ln.strip().strip("|").split("|")]
        if not ln.strip().startswith("|") or not any("escenario" in c for c in cab) \
                or not any("prob" in c for c in cab):
            continue
        ce = next(k for k, c in enumerate(cab) if "escenario" in c)
        cp = next(k for k, c in enumerate(cab) if "prob" in c)
        cv = next((k for k, c in enumerate(cab) if "precio" in c or "valor" in c), None)
        if cv is None:
            continue
        out = {}
        for fila in lineas[i + 2:]:
            if not fila.strip().startswith("|"):
                break
            celdas = [c.strip() for c in fila.strip().strip("|").split("|")]
            if len(celdas) <= max(ce, cp, cv):
                continue
            nombre = NOMBRES.get(re.sub(r"[^a-záéíóú]", "", celdas[ce].lower()))
            prob, precio = _num(celdas[cp]), _num(celdas[cv])
            if nombre and prob is not None and precio is not None:
                motivo = celdas[3] if len(celdas) > 3 and 3 not in (ce, cp, cv) else ""
                out[nombre] = {"prob": prob, "precio": precio, "motivo": motivo}
        if out:
            return out
    return {}


def calcular(esc: dict[str, dict], binaria: bool = False) -> dict:
    """El método fijo. Devuelve el resultado o {'error': ...} si faltan datos."""
    if set(esc) != {"malo", "normal", "bueno"}:
        return {"error": "faltan escenarios (hacen falta malo, normal y bueno)"}
    probs = {k: v["prob"] for k, v in esc.items()}
    total = sum(probs.values())
    if total <= 1.0001:  # vienen como 0,25 en vez de 25 %
        probs = {k: p * 100 for k, p in probs.items()}
        total *= 100
    if abs(total - 100) > 1:
        return {"error": f"las probabilidades suman {total:g} %, tienen que sumar 100 %"}
    m, n, b = (esc[k]["precio"] for k in ("malo", "normal", "bueno"))
    if not m <= n <= b:
        return {"error": "los precios tienen que ir de menor a mayor: malo ≤ normal ≤ bueno"}
    ve = sum(probs[k] / 100 * esc[k]["precio"] for k in esc)
    regla1 = (n + RATIO * m) / (RATIO + 1)
    regla2 = ve * (1 - MARGEN)
    binaria = binaria or (n > 0 and m <= UMBRAL_BINARIA * n)
    r = {"malo": m, "normal": n, "bueno": b,
         "prob_malo": round(probs["malo"], 1), "prob_normal": round(probs["normal"], 1),
         "prob_bueno": round(probs["bueno"], 1),
         "valor_esperado": round(ve, 2), "regla_3a1": round(regla1, 2), "regla_margen": round(regla2, 2),
         "binaria": binaria}
    r["entrada"] = None if binaria else math.floor(min(regla1, regla2) * 100) / 100
    r["manda"] = None if binaria else ("3 a 1" if regla1 <= regla2 else "margen")
    return r


def _f(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def bloque(r: dict, origen: str) -> str:
    """Texto en español sencillo con el cálculo paso a paso (va dentro de tesis.md)."""
    if "error" in r:
        return "\n".join([INI, f"**Calculadora:** no se puede calcular: {r['error']}.", FIN])
    pm, pn, pb = r["prob_malo"], r["prob_normal"], r["prob_bueno"]
    lin = [INI, f"**Resultado de la calculadora** (`lab medio entrada`, mismo método siempre; escenarios: {origen})", "",
           f"1. **Valor esperado** (la media pesada por probabilidad): {pm:g} % × {_f(r['malo'])} + "
           f"{pn:g} % × {_f(r['normal'])} + {pb:g} % × {_f(r['bueno'])} = **{_f(r['valor_esperado'])} $**",
           f"2. **Regla 3 a 1** (si sale normal ganas 3 veces lo que pierdes si sale malo): "
           f"({_f(r['normal'])} + 3 × {_f(r['malo'])}) / 4 = {_f(r['regla_3a1'])} $",
           f"3. **Regla del margen** (15 % por debajo del valor esperado): "
           f"{_f(r['valor_esperado'])} × 0,85 = {_f(r['regla_margen'])} $"]
    if r["binaria"]:
        lin += ["", "⚠️ **Apuesta «todo o nada»**: el caso malo hunde la acción. No hay un precio de entrada bueno; "
                "lo que se decide es **cuánto** arriesgar (poco)."]
    else:
        lin += ["", f"**Precio de entrada: ≤ {_f(r['entrada'])} $** (el más bajo de los dos; manda la regla "
                f"{'3 a 1' if r['manda'] == '3 a 1' else 'del margen'})."]
    return "\n".join(lin + [FIN])


def _seccion(texto: str) -> tuple[int, int]:
    """Posición (inicio, fin) del cuerpo de la sección de escenarios; (-1, -1) si no existe."""
    i = texto.find(SECCION)
    if i < 0:
        return -1, -1
    ini = i + len(SECCION)
    j = texto.find("\n## ", ini)
    return ini, (j if j >= 0 else len(texto))


def _informe(ticker: str, carpeta: Path) -> Path | None:
    cand = sorted(carpeta.glob(f"{ticker}-*.md"))
    con_tabla = [p for p in cand if leer_tabla(p.read_text(encoding="utf-8"))]
    return con_tabla[-1] if con_tabla else None


def procesar(ticker: str, inv: Path) -> dict | None:
    """Lee (o siembra) los escenarios de un ticker, calcula y reescribe el bloque de tesis.md."""
    tes = inv / "expedientes" / ticker / "tesis.md"
    if not tes.exists():
        return None
    texto = tes.read_text(encoding="utf-8")
    ini, fin = _seccion(texto)
    if ini < 0:
        texto = texto.rstrip("\n") + "\n\n" + SECCION + "\n"
        ini, fin = _seccion(texto)
    cuerpo = texto[ini:fin]
    sin_bloque = re.sub(re.escape(INI) + r".*?" + re.escape(FIN), "", cuerpo, flags=re.S)
    esc = leer_tabla(sin_bloque)
    origen = "tabla de esta tesis"
    tiene_tabla = bool(re.search(r"^\|\s*escenario", sin_bloque, flags=re.I | re.M))
    if not esc and not tiene_tabla:  # sembrar desde el último informe con tabla de escenarios
        inf = _informe(ticker, inv / "analisis")
        if inf:
            esc = leer_tabla(inf.read_text(encoding="utf-8"))
            origen = f"copiados de `investigacion/analisis/{inf.name}`"
            filas = TABLA_VACIA[:2] + [
                f"| {k} | {_f(esc[k]['prob']).replace(',00', '')} % | {_f(esc[k]['precio'])} $ | {esc[k]['motivo']} |"
                for k in ("malo", "normal", "bueno") if k in esc] + TABLA_VACIA[5:]
            sin_bloque = f"_Escenarios {origen} (cámbialos aquí si hay hechos nuevos)._\n\n" + "\n".join(filas)
        else:
            sin_bloque = "\n".join(TABLA_VACIA)
    else:
        m = re.search(r"copiados de `[^`]+`", sin_bloque)
        origen = m.group(0) if m else origen
    binaria = bool(re.search(r"^tipo:\s*binaria", sin_bloque, flags=re.I | re.M))
    r = calcular(esc, binaria) if esc else {"error": "la tabla de escenarios está vacía"}
    nuevo = "\n" + sin_bloque.strip("\n") + "\n\n" + bloque(r, origen) + "\n"
    final = texto[:ini] + nuevo + ("\n" + texto[fin:].lstrip("\n") if fin < len(texto) else "")
    if final != tes.read_text(encoding="utf-8"):
        tes.write_text(final, encoding="utf-8")
    return {**r, "ticker": ticker, "origen": origen} if esc else None


def ejecutar(tickers: list[str] | None = None, base: Path | None = None) -> dict[str, dict]:
    inv = base or Path(ruta("investigacion"))
    carpeta = inv / "expedientes"
    todos = tickers or sorted(p.name for p in carpeta.iterdir() if (p / "tesis.md").exists()) if carpeta.exists() else []
    salida = inv / "entradas.json"
    try:
        previas = json.loads(salida.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previas = {}
    res = {}
    for t in todos:
        r = procesar(t.upper(), inv)
        if r:
            res[t.upper()] = r
    previas = {k: v for k, v in previas.items() if k not in {t.upper() for t in todos}} if tickers else {}
    previas.update(res)
    salida.write_text(json.dumps(dict(sorted(previas.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return res


def main(argv: list[str]) -> int:
    res = ejecutar([a.upper() for a in argv] or None)
    if not res:
        print("Sin escenarios: rellena la tabla de «Escenarios y precio de entrada» en investigacion/expedientes/TICKER/tesis.md")
        return 0
    for t, r in res.items():
        if "error" in r:
            print(f"{t}: no se puede calcular ({r['error']})")
        elif r["binaria"]:
            print(f"{t}: todo o nada → sin precio de entrada (decide el tamaño). Valor esperado {_f(r['valor_esperado'])} $")
        else:
            print(f"{t}: entrada ≤ {_f(r['entrada'])} $ · valor esperado {_f(r['valor_esperado'])} $ "
                  f"(regla 3 a 1 {_f(r['regla_3a1'])} $, margen {_f(r['regla_margen'])} $)")
    return 0
