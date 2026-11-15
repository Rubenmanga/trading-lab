"""Perfil "¿puede duplicar?" del agente B (12 meses).

Es el mismo agente B con otros parámetros (config/perfil_duplicar.yaml). Reutiliza, sin cambiarlos:
  - oportunidades.universo()   → universo de Yahoo (gratis) con el tamaño/liquidez del perfil
  - oportunidades.enriquecer() → metricas.empresa(): las mismas ~90 métricas por empresa
  - oportunidades.puntuar()    → la misma nota de 8 factores y banderas rojas
  - fuentes_extra.completar()  → Finnhub (recomendaciones, insiders, noticias) y noticias de Alpaca
Añade lo que pide Ruben y el agente normal no mira:
  - precio en EUROS (cambio EUR/USD del día), objetivo > +100 % con 10+ analistas
  - tendencia trimestral: cuántos trimestres seguidos mejora la empresa
  - riesgo de dilución (meses de caja, acciones nuevas en 12 meses, deuda frente a caja)
  - grandes inversores: % de fondos, los 10 mayores fondos y compras de directivos
Los catalizadores (ensayos Fase 2/3, FDA, lanzamientos) los revisa después la skill `duplicar-12m` con la web.

Resultados en investigacion/duplicar/ (no toca el ranking normal).
    python -m tradinglab.perfiles.duplicar
"""
from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..common.config import cargar, ruta
from ..common.db import ahora
from ..medio_plazo import oportunidades


def _n(x):
    try:
        x = float(x)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def _reintentos(f, intentos=4):
    for i in range(intentos):
        try:
            return f()
        except Exception:  # noqa: BLE001
            if i == intentos - 1:
                raise
            time.sleep(4 * (i + 1))


def cambio_eur_usd() -> float:
    import yfinance as yf
    h = yf.Ticker("EURUSD=X").history(period="5d")["Close"].dropna()
    return float(h.iloc[-1])


def objetivo_analistas(t: str) -> dict:
    """Pasada rápida: solo lo necesario para el filtro de analistas (1 llamada por empresa)."""
    import yfinance as yf
    i = _reintentos(lambda: yf.Ticker(t).info) or {}
    p = _n(i.get("currentPrice")) or _n(i.get("regularMarketPrice"))
    o = _n(i.get("targetMeanPrice"))
    return dict(ticker=t, precio=p, analistas=_n(i.get("numberOfAnalystOpinions")), objetivo_medio=o,
                potencial_analistas_pct=(o / p - 1) * 100 if o and p else None, sector=i.get("sector"),
                empresa=i.get("longName") or i.get("shortName"))


# ---------------------------------------------------------------- añadidos del perfil
def _serie(df, nombres):
    if df is None or getattr(df, "empty", True):
        return None
    for n in nombres:
        if n in df.index:
            s = df.loc[n]
            s = s[sorted(s.index)]  # de más antiguo a más reciente
            return [[str(k)[:10], _n(v)] for k, v in s.items() if _n(v) is not None]
    return None


def racha_mejora(serie) -> int:
    """Trimestres seguidos (desde el último hacia atrás) en que la cifra mejora."""
    vals = [v for _, v in (serie or [])]
    n = 0
    for antes, despues in zip(reversed(vals[:-1]), reversed(vals[1:])):
        if despues > antes:
            n += 1
        else:
            break
    return n


def trimestres_y_fondos(t: str) -> dict:
    import yfinance as yf
    tk = yf.Ticker(t)
    d: dict = {"errores": []}

    def intenta(nombre, f):
        try:
            return _reintentos(f, 3)
        except Exception as e:  # noqa: BLE001
            d["errores"].append(f"{nombre}: {type(e).__name__}")
            return None

    inc, cf, bs = (intenta("resultados", lambda: tk.quarterly_income_stmt),
                   intenta("flujos", lambda: tk.quarterly_cashflow),
                   intenta("balance", lambda: tk.quarterly_balance_sheet))
    d["trim"] = dict(
        ventas=_serie(inc, ["Total Revenue", "Operating Revenue"]),
        resultado_operativo=_serie(inc, ["Operating Income", "EBIT"]),
        beneficio_neto=_serie(inc, ["Net Income", "Net Income Common Stockholders"]),
        flujo_operativo=_serie(cf, ["Operating Cash Flow"]),
        flujo_libre=_serie(cf, ["Free Cash Flow"]),
        emision_acciones=_serie(cf, ["Issuance Of Capital Stock", "Common Stock Issuance"]),
        caja=_serie(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
        deuda=_serie(bs, ["Total Debt"]),
        acciones=_serie(bs, ["Ordinary Shares Number", "Share Issued"]),
    )
    tr = d["trim"]
    d["rachas"] = {k: racha_mejora(tr[k]) for k in ("ventas", "resultado_operativo", "beneficio_neto", "flujo_operativo")}
    # "Economía mejorando" = resultado operativo, beneficio neto o flujo operativo (las ventas solas no bastan).
    d["trimestres_mejorando"] = max(d["rachas"]["resultado_operativo"], d["rachas"]["beneficio_neto"],
                                    d["rachas"]["flujo_operativo"])
    caja = tr["caja"][-1][1] if tr["caja"] else None
    deuda = tr["deuda"][-1][1] if tr["deuda"] else 0.0
    fl = [v for _, v in (tr["flujo_libre"] or [])][-2:]
    quema = -sum(fl) / len(fl) if fl else None
    d["caja"], d["deuda"] = caja, deuda
    d["quema_trimestral"] = quema if quema and quema > 0 else 0.0
    d["meses_caja"] = round(caja / quema * 3, 1) if caja and quema and quema > 0 else (999 if caja and quema is not None else None)
    d["deuda_sobre_caja"] = round(deuda / caja, 2) if caja else None
    acc = [v for _, v in (tr["acciones"] or [])]
    d["acciones_nuevas_periodo_pct"] = round((acc[-1] / acc[0] - 1) * 100, 1) if len(acc) >= 2 else None
    try:
        from datetime import date, timedelta
        sh = tk.get_shares_full(start=str(date.today() - timedelta(days=365)))
        if sh is not None and len(sh) > 2:
            d["acciones_nuevas_12m_pct"] = round((float(sh.iloc[-1]) / float(sh.iloc[0]) - 1) * 100, 1)
    except Exception as e:  # noqa: BLE001
        d["errores"].append(f"acciones12m: {type(e).__name__}")
    ih = intenta("fondos", lambda: tk.institutional_holders)
    if ih is not None and not ih.empty:
        d["fondos_top"] = [dict(nombre=str(r.get("Holder")), pct=_n(r.get("pctHeld")),
                                cambio_pct=_n(r.get("pctChange")), fecha=str(r.get("Date Reported"))[:10])
                           for _, r in ih.head(10).iterrows()]
    return d


def evaluar(f: dict, c: dict, usd_por_eur: float) -> dict:
    """Comprueba cada criterio de Ruben y explica por qué pasa o falla (sin relajar nada)."""
    p = f.get("precio")
    f["precio_eur"] = round(p / usd_por_eur, 2) if p else None
    d = f.get("duplicar", {})
    dil = c["dilucion"]
    acc12 = d.get("acciones_nuevas_12m_pct")
    if acc12 is None:
        acc12 = f.get("dilucion_1a_pct")
    meses = d.get("meses_caja")
    res = {
        "precio_5_25_eur": (bool(f["precio_eur"] and c["precio_eur_min"] <= f["precio_eur"] <= c["precio_eur_max"]),
                            f"{f['precio_eur']} €"),
        "objetivo_100_10_analistas": (bool((f.get("analistas") or 0) >= c["analistas_min"]
                                           and (f.get("potencial_analistas_pct") or 0) > c["potencial_min_pct"]),
                                      f"+{(f.get('potencial_analistas_pct') or 0):.0f} % con {(f.get('analistas') or 0):.0f} analistas"),
        "economia_mejorando": ((d.get("trimestres_mejorando") or 0) >= c["trimestres_mejorando_min"],
                               f"{d.get('trimestres_mejorando')} trimestres seguidos mejorando {d.get('rachas')}"),
        "poca_dilucion": (bool(meses is not None and meses >= dil["meses_caja_min"]
                               and (acc12 is not None and acc12 <= dil["acciones_nuevas_12m_max_pct"])
                               and (d.get("deuda_sobre_caja") is not None and d["deuda_sobre_caja"] <= dil["deuda_sobre_caja_max"])),
                          f"caja para {meses} meses, acciones nuevas 12m {acc12} %, deuda/caja {d.get('deuda_sobre_caja')}"),
    }
    f["criterios"] = {k: {"cumple": v[0], "dato": v[1]} for k, v in res.items()}
    f["criterios_cumplidos"] = sum(v[0] for v in res.values())
    f["cumple_todo"] = f["criterios_cumplidos"] == len(res)
    return f


def ejecutar(cfg: dict, desde_universo: bool = False) -> dict:
    c, lc = cfg["criterios"], cfg["lista_corta"]
    usd_por_eur = cambio_eur_usd()
    pmin, pmax = c["precio_eur_min"] * usd_por_eur, c["precio_eur_max"] * usd_por_eur
    m = lc["margen_precio"]
    print(f"Cambio: 1 € = {usd_por_eur:.4f} $ → rango {pmin:.2f}-{pmax:.2f} $", flush=True)

    previo = ruta("investigacion", "duplicar", "universo.csv")
    if desde_universo and previo.exists():
        # Reutiliza la pasada rápida anterior (así Yahoo no nos corta por pedir demasiado).
        import csv
        rapidas = []
        for r in csv.DictReader(open(previo, encoding="utf-8")):
            rapidas.append(dict(ticker=r["ticker"], empresa=r["empresa"], sector=r["sector"] or None,
                                precio=_n(r["precio_usd"]), analistas=_n(r["analistas"]),
                                objetivo_medio=_n(r["objetivo_medio"]), potencial_analistas_pct=_n(r["potencial_pct"])))
        base, fallos = rapidas, 0
        print(f"Pasada rápida reutilizada: {len(rapidas)} empresas", flush=True)
    else:
        base = oportunidades.universo(cfg)          # mismo universo que el agente B, con el tamaño del perfil
        base = [b for b in base if b.get("precio") and pmin * (1 - m) <= b["precio"] <= pmax * (1 + m)]
        print(f"Universo con precio cerca de 5-25 €: {len(base)}", flush=True)
        rapidas, fallos = [], 0
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(objetivo_analistas, b["ticker"]) for b in base]
            for k, fu in enumerate(as_completed(futs), 1):
                try:
                    rapidas.append(fu.result())
                except Exception:  # noqa: BLE001
                    fallos += 1
                time.sleep(0.25)  # sin prisa: si se va rápido, Yahoo bloquea el resto
                if k % 200 == 0:
                    print(f"  ... {k}/{len(base)} (fallos {fallos})", flush=True)
    corta = [r for r in rapidas if (r["analistas"] or 0) >= lc["analistas_min"]
             and (r["potencial_analistas_pct"] or 0) >= lc["potencial_min_pct"]
             and r["precio"] and pmin * (1 - m) <= r["precio"] <= pmax * (1 + m)]
    print(f"Lista corta (≥{lc['potencial_min_pct']} % con ≥{lc['analistas_min']} analistas): {len(corta)}", flush=True)
    rapida_de = {r["ticker"]: r for r in corta}

    # Análisis completo con las métricas, la nota y las fuentes extra del agente B.
    filas = oportunidades.enriquecer([r["ticker"] for r in corta], hilos=1, pausa=1.0)
    for f in filas:
        # Si Yahoo falló en algún bloque, se completa con la pasada rápida (nunca se descarta en silencio).
        for k, v in rapida_de.get(f["ticker"], {}).items():
            if f.get(k) is None:
                f[k] = v
        f["duplicar"] = trimestres_y_fondos(f["ticker"])
        time.sleep(1.0)
    if filas:
        oportunidades.puntuar(filas, cfg["oportunidades"].get("pesos"), min_sector=5)
    for f in filas:
        evaluar(f, c, usd_por_eur)
    filas.sort(key=lambda f: (-f["criterios_cumplidos"], -(f.get("nota") or 0)))
    from ..medio_plazo import fuentes_extra
    extra = fuentes_extra.completar(filas, top=cfg["oportunidades"].get("extra_top", 40)) \
        if (fuentes_extra.hay_finnhub() or fuentes_extra.hay_alpaca()) else {}
    universo_csv = sorted(rapidas, key=lambda r: -(r["potencial_analistas_pct"] or -999))
    return dict(actualizado=ahora(), usd_por_eur=round(usd_por_eur, 4), rango_usd=[round(pmin, 2), round(pmax, 2)],
                universo=len(base), con_objetivo=len(rapidas), fallos=fallos, lista_corta=len(filas),
                criterios=c, fuentes_extra=extra, filas=filas, universo_filas=universo_csv)


def _limpio(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, dict):
        return {k: _limpio(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_limpio(x) for x in v]
    return v


def guardar(res: dict) -> str:
    carpeta = ruta("investigacion", "duplicar")
    carpeta.mkdir(parents=True, exist_ok=True)
    cab = {k: v for k, v in res.items() if k not in ("filas", "universo_filas")}
    with open(carpeta / "resultado.json", "w", encoding="utf-8") as fh:
        json.dump(cab | {"filas": [_limpio(f) for f in res["filas"]]}, fh, ensure_ascii=False, indent=0, default=str)
    with open(carpeta / "universo.csv", "w", encoding="utf-8") as fh:  # noqa: SIM115
        fh.write("ticker,empresa,sector,precio_usd,analistas,objetivo_medio,potencial_pct\n")
        for r in res["universo_filas"]:
            fh.write(",".join("" if r.get(k) is None else (f"{r[k]:.2f}" if isinstance(r[k], float) else
                                                         '"' + str(r[k]).replace('"', "'") + '"')
                              for k in ("ticker", "empresa", "sector", "precio", "analistas", "objetivo_medio",
                                        "potencial_analistas_pct")) + "\n")
    with open(carpeta / "resultado.md", "w", encoding="utf-8") as fh:
        fh.write("# Perfil «¿puede duplicar?» · datos automáticos\n\n")
        fh.write(f"_Actualizado {res['actualizado']} · 1 € = {res['usd_por_eur']} $ · universo {res['universo']} · "
                 f"con datos {res['con_objetivo']} · lista corta {res['lista_corta']}_\n\n")
        fh.write("| Ticker | Precio € | Analistas | Potencial | Trim. mejorando | Meses de caja | Acc. nuevas 12m | Fondos % | Nota agente B | Criterios |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for f in res["filas"]:
            d = f["duplicar"]
            fh.write(f"| {f['ticker']} | {f['precio_eur']} | {f.get('analistas') or 0:.0f} | "
                     f"+{f.get('potencial_analistas_pct') or 0:.0f} % | {d.get('trimestres_mejorando')} | {d.get('meses_caja')} | "
                     f"{d.get('acciones_nuevas_12m_pct')} | {(f.get('instituciones_pct') or 0) * 100:.0f} | {f.get('nota')} | "
                     f"{f['criterios_cumplidos']}/4{' ✅' if f['cumple_todo'] else ''} |\n")
    return str(carpeta)


def main():
    import sys
    cfg = cargar("perfil_duplicar")
    res = ejecutar(cfg, desde_universo="--desde-universo" in sys.argv)
    print("Guardado en", guardar(res))
    for f in res["filas"][:25]:
        print(f"  {f['ticker']:6} {f['precio_eur']}€ {f['criterios_cumplidos']}/4 "
              + " ".join(f"{k}={'sí' if v['cumple'] else 'NO'}" for k, v in f["criterios"].items()))


if __name__ == "__main__":
    main()
