"""Expediente por acción (Paso 1 de la revisión del 16-nov-2026). Archivero SIN IA.

Para cada empresa que sigues (cartera abierta + lista de noticias + lista de vigilancia) guarda en
`investigacion/expedientes/TICKER/`:
- `eventos.csv`: un hecho por línea, con su fuente (enlace), la fecha de la fuente y cómo reaccionó el precio
  a 1, 5 y 20 sesiones. Solo se AÑADEN líneas; nunca se borran. Lo único que se rellena después son las
  reacciones que aún no se podían medir (un evento de ayer todavía no tiene reacción a 20 sesiones).
- `tesis.md`: plantilla para escribir por qué interesa y qué la rompería. Se crea una vez y no se pisa.

Fuentes (gratis): SEC EDGAR `submissions` (documentos oficiales con fecha) y precios diarios de Yahoo.
Reacción = cierre N sesiones después ÷ cierre de la sesión anterior al evento − 1, en %.
"""
from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from pathlib import Path

from ..common.config import ruta

COLUMNAS = ["fecha", "tipo", "resumen", "fuente_url", "fecha_fuente", "precio_antes",
            "reaccion_1d", "reaccion_5d", "reaccion_20d"]
REACCIONES = {"reaccion_1d": 1, "reaccion_5d": 5, "reaccion_20d": 20}
DIAS = 365

# Apartados de un 8-K (aviso oficial de hecho relevante) → tipo de evento.
ITEMS_8K = {
    "2.02": ("resultados", "Resultados del trimestre (8-K 2.02)"),
    "1.01": ("contrato", "Contrato o acuerdo importante (8-K 1.01)"),
    "2.01": ("contrato", "Compra o venta de un negocio (8-K 2.01)"),
    "3.02": ("ampliacion", "Venta de acciones nuevas sin registro (8-K 3.02)"),
    "5.02": ("directivos", "Cambio de directivos o consejeros (8-K 5.02)"),
    "3.01": ("aviso", "Aviso de la bolsa por incumplir requisitos (8-K 3.01)"),
    "1.03": ("aviso", "Quiebra o suspensión de pagos (8-K 1.03)"),
    "4.02": ("aviso", "Cuentas anteriores no fiables (8-K 4.02)"),
}
FORMAS = {
    "10-K": ("cuentas", "Cuentas anuales (10-K)"),
    "10-Q": ("cuentas", "Cuentas del trimestre (10-Q)"),
    "20-F": ("cuentas", "Cuentas anuales (20-F)"),
    "S-1": ("ampliacion", "Registro para vender acciones nuevas (S-1)"),
    "S-3": ("ampliacion", "Registro para vender acciones nuevas (S-3)"),
    "S-3ASR": ("ampliacion", "Registro para vender acciones nuevas (S-3ASR)"),
    "F-3": ("ampliacion", "Registro para vender acciones nuevas (F-3)"),
    "424B4": ("ampliacion", "Colocación de acciones: precio final (424B4)"),
    "424B5": ("ampliacion", "Colocación de acciones (424B5)"),
    "SC 13D": ("grandes_inversores", "Inversor activista pasa del 5 % (13D)"),
    "SCHEDULE 13D": ("grandes_inversores", "Inversor activista pasa del 5 % (13D)"),
    "SC 13G": ("grandes_inversores", "Fondo grande pasa del 5 % (13G)"),
    "SCHEDULE 13G": ("grandes_inversores", "Fondo grande pasa del 5 % (13G)"),
    "NT 10-K": ("aviso", "Cuentas anuales presentadas tarde (NT 10-K)"),
    "NT 10-Q": ("aviso", "Cuentas del trimestre presentadas tarde (NT 10-Q)"),
}


# ------------------------------------------------------------------ qué empresas se siguen
def seguidas(cfg: dict | None = None) -> dict[str, str]:
    """{ticker: grupo}. Cartera abierta (mi_cartera.csv) + lista de noticias + lista de vigilancia.
    Las materias primas (oro, divisas) no tienen documentos en la SEC y se dejan fuera."""
    lc = (cfg or {}).get("lista_noticias") or {}
    materias = {t.upper() for t in (lc.get("materias_primas") or {})}
    out: dict[str, str] = {}

    def add(t, grupo):
        t = (t or "").strip().upper()
        if t and t not in materias and t not in out:
            out[t] = grupo
    try:
        with open(ruta("config", "mi_cartera.csv"), newline="", encoding="utf-8") as fh:
            for f in csv.DictReader(fh):
                if (f.get("estado") or "").strip() == "abierta":
                    add(f.get("ticker"), "cartera")
    except FileNotFoundError:
        pass
    for t in lc.get("empresas") or {}:
        add(t, "cartera")
    try:
        with open(ruta("investigacion", "watchlist.csv"), newline="", encoding="utf-8") as fh:
            for f in csv.DictReader(fh):
                add(f.get("ticker"), "vigilancia")
    except FileNotFoundError:
        pass
    return out


# ------------------------------------------------------------------ eventos de la SEC
def eventos_sec(sub: dict, hoy: date | None = None, dias: int = DIAS) -> list[dict]:
    """Documentos de la SEC del último año → eventos. Los Form 4 (compras/ventas de directivos) se juntan
    por día para no llenar el expediente de líneas repetidas."""
    hoy = hoy or date.today()
    rec = ((sub or {}).get("filings") or {}).get("recent") or {}
    cik = str(int(sub.get("cik") or 0)) if sub.get("cik") else ""
    col = {k: rec.get(k) or [] for k in ("form", "filingDate", "accessionNumber", "primaryDocument", "items")}
    out, form4 = [], {}
    for i, fo in enumerate(col["form"]):
        fe = col["filingDate"][i] if i < len(col["filingDate"]) else ""
        try:
            d = date.fromisoformat(fe)
        except ValueError:
            continue
        if not 0 <= (hoy - d).days <= dias:
            continue
        acc = col["accessionNumber"][i] if i < len(col["accessionNumber"]) else ""
        doc = col["primaryDocument"][i] if i < len(col["primaryDocument"]) else ""
        url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
               if cik and acc and doc else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}")
        f = (fo or "").upper().strip()
        if f == "4":
            g = form4.setdefault(fe, dict(n=0, url=url))
            g["n"] += 1
            continue
        if f == "8-K":
            items = [x.strip() for x in str(col["items"][i] if i < len(col["items"]) else "").split(",") if x.strip()]
            conocidos = [ITEMS_8K[x] for x in items if x in ITEMS_8K]
            if conocidos:
                tipo = conocidos[0][0]
                resumen = "; ".join(r for _, r in conocidos)
            else:
                tipo, resumen = "8k", "Aviso oficial de hecho relevante (8-K" + (" " + ",".join(items) if items else "") + ")"
            out.append(dict(fecha=fe, tipo=tipo, resumen=resumen, fuente_url=url, fecha_fuente=fe))
        elif f in FORMAS:
            tipo, resumen = FORMAS[f]
            out.append(dict(fecha=fe, tipo=tipo, resumen=resumen, fuente_url=url, fecha_fuente=fe))
    for fe, g in form4.items():
        n = g["n"]
        out.append(dict(fecha=fe, tipo="directivos_form4",
                        resumen=f"{n} aviso{'s' if n > 1 else ''} de compra/venta de directivos (Form 4)",
                        fuente_url=g["url"], fecha_fuente=fe))
    return out


# ------------------------------------------------------------------ precio
def _pct(a, b):
    return round((a / b - 1) * 100, 2) if a and b else None


def reacciones(fecha: str, velas: list[dict]) -> dict:
    """precio_antes = cierre de la última sesión ANTES del día del evento; reacción N = cierre de la sesión N
    contando desde el día del evento (1 = ese mismo día o el siguiente hábil). Vacío si aún no hay datos."""
    fechas = [v["fecha"] for v in velas]
    j = next((k for k, f in enumerate(fechas) if f >= fecha), None)
    out = {"precio_antes": None, **{c: None for c in REACCIONES}}
    if j is None or j == 0:
        return out
    base = velas[j - 1]["cierre"]
    out["precio_antes"] = round(base, 4)
    for c, n in REACCIONES.items():
        if j - 1 + n < len(velas):
            out[c] = _pct(velas[j - 1 + n]["cierre"], base)
    return out


def movimientos(velas: list[dict], ticker: str, hoy: date | None = None, dias: int = DIAS,
                umbral_pct: float = 8.0, sigmas: float = 2.5) -> list[dict]:
    """Días en que el precio se movió mucho más de lo normal (≥ 8 % y ≥ 2,5 veces su movimiento típico)."""
    hoy = hoy or date.today()
    desde = (hoy - timedelta(days=dias)).isoformat()
    out = []
    for k in range(21, len(velas)):
        cambios = [velas[i]["cierre"] / velas[i - 1]["cierre"] - 1 for i in range(k - 20, k) if velas[i - 1]["cierre"]]
        if not cambios or not velas[k - 1]["cierre"] or velas[k]["fecha"] < desde:
            continue
        m = sum(cambios) / len(cambios)
        sd = math.sqrt(sum((c - m) ** 2 for c in cambios) / len(cambios)) or 1e-9
        c = velas[k]["cierre"] / velas[k - 1]["cierre"] - 1
        if abs(c) * 100 >= umbral_pct and abs(c) >= sigmas * sd:
            vol = velas[k].get("volumen") or 0
            vm = sum(velas[i].get("volumen") or 0 for i in range(k - 20, k)) / 20
            extra = f", volumen x{vol / vm:.1f} su media" if vm else ""
            out.append(dict(fecha=velas[k]["fecha"], tipo="movimiento",
                            resumen=f"{'Sube' if c > 0 else 'Cae'} {abs(c) * 100:.1f} % en un día "
                                    f"({abs(c) / sd:.1f} veces lo normal{extra})",
                            fuente_url=f"https://finance.yahoo.com/quote/{ticker}/history/",
                            fecha_fuente=velas[k]["fecha"]))
    return out


# ------------------------------------------------------------------ archivo (solo añadir)
def _clave(e: dict) -> tuple:
    return (e.get("fecha"), e.get("tipo"), e.get("fuente_url"))


def leer(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def fusionar(previos: list[dict], nuevos: list[dict], velas: list[dict]) -> tuple[list[dict], int]:
    """Mantiene TODAS las líneas previas, añade las nuevas y rellena reacciones vacías. Devuelve (filas, añadidas)."""
    vistos = {_clave(e) for e in previos}
    filas = [dict(e) for e in previos]
    añadidas = 0
    for e in nuevos:
        if _clave(e) not in vistos:
            vistos.add(_clave(e))
            filas.append({c: e.get(c, "") for c in COLUMNAS})
            añadidas += 1
    if velas:
        for f in filas:
            if any(f.get(c) in (None, "") for c in ("precio_antes", *REACCIONES)):
                r = reacciones(f["fecha"], velas)
                for c, v in r.items():
                    if f.get(c) in (None, "") and v is not None:
                        f[c] = v
    filas.sort(key=lambda f: (f.get("fecha") or "", f.get("tipo") or ""), reverse=True)
    return filas, añadidas


def escribir(path: Path, filas: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        for f in filas:
            w.writerow({c: ("" if f.get(c) is None else f.get(c)) for c in COLUMNAS})


def plantilla_tesis(ticker: str, grupo: str, vig: dict | None = None) -> str:
    v = vig or {}
    lineas = [f"# {ticker} · tesis", "",
              f"- Grupo: {grupo}. Línea de tiempo con fuentes en `eventos.csv` (se actualiza sola cada día de bolsa).",
              ]
    if v:
        lineas += [f"- Último análisis: {v.get('fecha_analisis')} → **{v.get('veredicto')}** "
                   f"(convicción {v.get('conviccion')}/5). Informe: `{v.get('informe')}`",
                   f"- Zona de entrada máx.: {v.get('zona_entrada_max')} $ · objetivo 12 m: {v.get('precio_objetivo_12m')} $ "
                   f"· la tesis se rompe por debajo de {v.get('stop_tesis')} $",
                   f"- Próximo catalizador: {v.get('proximo_catalizador')} ({v.get('fecha_catalizador')})"]
    lineas += ["", "## Por qué interesa", "_(pendiente)_", "", "## Qué la rompería", "_(pendiente)_", "",
               "## Escenarios y precio de entrada",
               "_(rellena la tabla; `lab medio entrada` calcula el precio. Si está vacía, copia la del último informe)_", ""]
    return "\n".join(lineas)


def _watchlist() -> dict[str, dict]:
    try:
        with open(ruta("investigacion", "watchlist.csv"), newline="", encoding="utf-8") as fh:
            return {(f.get("ticker") or "").upper(): f for f in csv.DictReader(fh)}
    except FileNotFoundError:
        return {}


def indice(resumen: dict[str, dict], hoy: date) -> str:
    total = sum(r["eventos"] for r in resumen.values())
    nuevos = sum(r["añadidas"] for r in resumen.values())
    sin = [t for t, r in resumen.items() if r.get("error")]
    out = [f"# Expedientes por acción ({hoy.isoformat()})", "",
           f"1. {len(resumen)} empresas seguidas, {total} hechos guardados en total.",
           f"2. Hoy se han añadido {nuevos} hechos nuevos.",
           "3. Cada hecho trae su fuente (SEC o Yahoo), su fecha y cómo reaccionó el precio a 1, 5 y 20 sesiones.",
           f"4. Sin datos hoy: {', '.join(sin) if sin else 'ninguna'}.",
           "5. Los expedientes solo crecen: nada se borra. Es información, no una recomendación.", "",
           "| Empresa | Grupo | Hechos | Último hecho |", "|---|---|---|---|"]
    for t, r in sorted(resumen.items()):
        out.append(f"| [{t}]({t}/eventos.csv) | {r['grupo']} | {r['eventos']} | {r.get('ultimo') or '—'} |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ ejecutar
def ejecutar(cfg: dict | None = None, tickers: list[str] | None = None, carpeta: Path | None = None,
             fuente_sec=None, fuente_velas=None, hoy: date | None = None) -> dict[str, dict]:
    """Actualiza los expedientes. `fuente_sec(tickers)->{t: submissions}` y `fuente_velas(t)->velas` se pueden
    cambiar (los tests usan datos falsos)."""
    hoy = hoy or date.today()
    carpeta = carpeta or ruta("investigacion", "expedientes")
    grupos = seguidas(cfg)
    if tickers:
        grupos = {t.upper(): grupos.get(t.upper(), "manual") for t in tickers}
    if fuente_sec is None:
        fuente_sec = _submissions
    if fuente_velas is None:
        from .seguimiento import velas_yahoo

        def fuente_velas(t):
            return velas_yahoo(t, "2y")
    subs = {}
    try:
        subs = fuente_sec(list(grupos)) or {}
    except Exception as e:  # noqa: BLE001
        print(f"SEC no disponible: {e}")
    vig = _watchlist()
    resumen = {}
    for t, grupo in grupos.items():
        velas, error = [], None
        try:
            velas = fuente_velas(t) or []
        except Exception as e:  # noqa: BLE001
            error = f"precios: {type(e).__name__}"
        nuevos = eventos_sec(subs[t], hoy) if subs.get(t) else []
        if not subs.get(t):
            error = (error + "; " if error else "") + "sin datos de la SEC"
        nuevos += movimientos(velas, t, hoy)
        path = carpeta / t / "eventos.csv"
        filas, añadidas = fusionar(leer(path), nuevos, velas)
        if filas:
            escribir(path, filas)
        tes = carpeta / t / "tesis.md"
        if not tes.exists():
            tes.parent.mkdir(parents=True, exist_ok=True)
            tes.write_text(plantilla_tesis(t, grupo, vig.get(t)), encoding="utf-8")
        resumen[t] = dict(grupo=grupo, eventos=len(filas), añadidas=añadidas,
                          ultimo=(f"{filas[0]['fecha']} · {filas[0]['resumen']}" if filas else None),
                          error=error if not filas or not velas else None)
    if not tickers:
        (carpeta / "README.md").write_text(indice(resumen, hoy), encoding="utf-8")
    return resumen


def _submissions(tickers: list[str]) -> dict[str, dict]:
    import time

    from .fuentes_publicas import SEC_SUBMISSIONS, _get, mapa_cik
    ciks = mapa_cik()
    out = {}
    for t in tickers:
        cik = ciks.get(t) or ciks.get(t.replace(".", "-"))
        if cik:
            sub = _get(SEC_SUBMISSIONS.format(cik=cik))
            if sub:
                out[t] = sub
            time.sleep(0.15)  # muy por debajo del límite de 10 pedidos/s de la SEC
    return out
