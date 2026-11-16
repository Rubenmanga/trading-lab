"""Libro de predicciones + marcador (Paso 3 de la revisión del 16-nov-2026). Sin IA y gratis.

- `investigacion/predicciones.csv` es el LIBRO: cada análisis deja una línea con fecha, veredicto,
  precio, zona de entrada, objetivo y stop. Solo se AÑADE: nunca se cambia ni se borra una línea
  (así nadie puede «retocar» una predicción después de ver el resultado).
- El marcador compara cada predicción con lo que hizo el precio y con el índice de small caps (IWM)
  en el mismo tiempo, y dice si va acertando. Con pocas predicciones, lo dice: es poco concluyente.
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

RAIZ = Path(__file__).resolve().parents[3]
LIBRO = RAIZ / "investigacion" / "predicciones.csv"
SALIDA = RAIZ / "investigacion" / "marcador"
INDICE = "IWM"  # fondo que copia al índice Russell 2000 (small caps de EE. UU.)
MIN_SESIONES = 5  # antes de 5 días de bolsa no se puntúa: sería ruido
COLUMNAS = ["id", "fecha", "ticker", "informe", "veredicto", "conviccion", "probabilidad", "precio",
            "zona_entrada_max", "objetivo", "stop_tesis", "fecha_revision", "nota"]
# Veredictos que apuestan a que la acción lo hará MEJOR que el índice; el resto («vigilar», «no comprar»)
# aciertan si esperar no costó nada (la acción no batió al índice o tocó el stop).
ALCISTAS = {"comprar", "comprar_en_zona", "mantener"}


def _f(x) -> float | None:
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def leer(path: Path = LIBRO) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def sincronizar(watchlist: list[dict], path: Path = LIBRO) -> int:
    """Apunta en el libro los análisis nuevos de watchlist.csv. Solo añade líneas al final."""
    ya = {r["id"] for r in leer(path)}
    nuevas = []
    for w in watchlist:
        pid = f"{w.get('ticker')}-{w.get('fecha_analisis')}"
        if not w.get("ticker") or not w.get("fecha_analisis") or pid in ya:
            continue
        ya.add(pid)
        f = date.fromisoformat(w["fecha_analisis"])
        nuevas.append(dict(id=pid, fecha=w["fecha_analisis"], ticker=w["ticker"], informe=w.get("informe", ""),
                           veredicto=w.get("veredicto", ""), conviccion=w.get("conviccion", ""), probabilidad="",
                           precio=w.get("precio_analisis", ""), zona_entrada_max=w.get("zona_entrada_max", ""),
                           objetivo=w.get("precio_objetivo_12m", ""), stop_tesis=w.get("stop_tesis", ""),
                           fecha_revision=(f + timedelta(days=365)).isoformat(), nota="apuntada desde watchlist.csv"))
    if nuevas:
        nuevo = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
            if nuevo:
                w.writeheader()
            w.writerows(nuevas)
    return len(nuevas)


def _cierre_hasta(velas: list[dict], dia: str) -> float | None:
    previas = [v["cierre"] for v in velas if v["fecha"] <= dia]
    return previas[-1] if previas else None


def puntuar(p: dict, velas: list[dict], velas_idx: list[dict], hoy: date) -> dict:
    """Una predicción frente a lo ocurrido. Devuelve rentabilidad, la del índice, la diferencia y el resultado."""
    precio, obj, stop, zona = _f(p.get("precio")), _f(p.get("objetivo")), _f(p.get("stop_tesis")), _f(p.get("zona_entrada_max"))
    fin = min(hoy.isoformat(), p.get("fecha_revision") or "9999")
    tras = [v for v in velas if p["fecha"] < v["fecha"] <= fin]
    out = dict(id=p["id"], ticker=p["ticker"], fecha=p["fecha"], veredicto=p.get("veredicto", ""),
               conviccion=p.get("conviccion", ""), informe=p.get("informe", ""), precio=precio, objetivo=obj,
               stop=stop, fecha_revision=p.get("fecha_revision", ""), sesiones=len(tras), motivo="", toco_zona=False)
    base_idx = _cierre_hasta(velas_idx, p["fecha"])
    if not precio or not tras or not base_idx:
        return {**out, "estado": "abierta", "resultado": "pronto", "explicacion": "Aún no hay precios después del análisis."}
    salida, dia_fin = tras[-1]["cierre"], tras[-1]["fecha"]
    for v in tras:  # ¿tocó antes el stop o el objetivo? Si los dos el mismo día, cuenta el stop (lo prudente).
        if zona and v["minimo"] <= zona:
            out["toco_zona"] = True
        if stop and v["minimo"] <= stop:
            salida, dia_fin, out["motivo"] = min(v.get("apertura") or stop, stop), v["fecha"], "stop"
            break
        if obj and v["maximo"] >= obj:
            salida, dia_fin, out["motivo"] = max(v.get("apertura") or obj, obj), v["fecha"], "objetivo"
            break
    idx_fin = _cierre_hasta(velas_idx, dia_fin) or base_idx
    ret, ret_idx = (salida / precio - 1) * 100, (idx_fin / base_idx - 1) * 100
    exceso = ret - ret_idx
    cerrada = bool(out["motivo"]) or hoy.isoformat() >= (p.get("fecha_revision") or "9999")
    alcista = p.get("veredicto", "") in ALCISTAS
    if out["motivo"] == "objetivo":
        acierto = alcista
    elif out["motivo"] == "stop":
        acierto = not alcista
    else:
        acierto = exceso > 0 if alcista else exceso <= 0
    sesiones = sum(1 for v in tras if v["fecha"] <= dia_fin)
    if sesiones < MIN_SESIONES and not out["motivo"]:
        resultado = "pronto"
    else:
        resultado = "acierto" if acierto else "fallo"
    if out["motivo"] == "objetivo":
        expl = "Llegó al precio objetivo."
    elif out["motivo"] == "stop":
        expl = "Tocó el precio donde la tesis se rompe (stop)."
    elif alcista:
        expl = f"{'Bate' if exceso > 0 else 'No bate'} al índice de small caps por {abs(exceso):.1f} puntos."
    else:
        expl = (f"Esperar no costó nada: va {abs(exceso):.1f} puntos peor que el índice." if exceso <= 0
                else f"Se escapó: va {exceso:.1f} puntos mejor que el índice sin haberla comprado.")
    return {**out, "estado": "cerrada" if cerrada else "abierta", "resultado": resultado, "explicacion": expl,
            "sesiones": sesiones, "hasta": dia_fin, "precio_final": round(salida, 4),
            "rent_pct": round(ret, 2), "rent_indice_pct": round(ret_idx, 2), "exceso_pct": round(exceso, 2)}


def _veredicto_muestra(n: int) -> str:
    if n == 0:
        return "Todavía no hay ninguna predicción con tiempo suficiente para puntuarla."
    if n < 10:
        return f"Solo {n} predicciones puntuadas: es muy poco, cualquier porcentaje puede ser suerte."
    if n < 30:
        return f"{n} predicciones puntuadas: empieza a decir algo, pero sigue siendo poco concluyente."
    return f"{n} predicciones puntuadas: ya es una muestra razonable."


def resumir(filas: list[dict]) -> dict:
    hechas = [f for f in filas if f["resultado"] in ("acierto", "fallo")]
    con_precio = [f for f in filas if f.get("exceso_pct") is not None]
    acierta = lambda fs: round(100 * sum(f["resultado"] == "acierto" for f in fs) / len(fs)) if fs else None  # noqa: E731
    calib = []
    for c in sorted({f["conviccion"] for f in filas if f["conviccion"]}):
        g = [f for f in hechas if f["conviccion"] == c]
        calib.append(dict(conviccion=c, n=len(g), aciertos_pct=acierta(g)))
    alc = [f for f in con_precio if f["veredicto"] in ALCISTAS]
    return dict(total=len(filas), puntuadas=len(hechas), cerradas=sum(f["estado"] == "cerrada" for f in filas),
                pronto=sum(f["resultado"] == "pronto" for f in filas), aciertos=sum(f["resultado"] == "acierto" for f in hechas),
                aciertos_pct=acierta(hechas), muestra=_veredicto_muestra(len(hechas)),
                exceso_medio_todas=round(mean(f["exceso_pct"] for f in con_precio), 2) if con_precio else None,
                exceso_medio_compras=round(mean(f["exceso_pct"] for f in alc), 2) if alc else None,
                n_compras=len(alc), calibracion=calib)


def informe_md(res: dict, filas: list[dict], hoy: date) -> str:
    s = lambda x: "—" if x is None else f"{x:+.1f} %"  # noqa: E731
    pct = "—" if res["aciertos_pct"] is None else f"{res['aciertos_pct']} %"
    lin = [f"# Marcador de aciertos · {hoy.isoformat()}", "", "**Resumen (5 líneas)**",
           f"1. Predicciones en el libro: {res['total']} (puntuadas: {res['puntuadas']}; aún pronto: {res['pronto']}).",
           f"2. Aciertos: {res['aciertos']} de {res['puntuadas']} ({pct}).",
           f"3. Si se hubieran comprado todas, irían {s(res['exceso_medio_todas'])} frente al índice de small caps (IWM).",
           f"4. {res['muestra']}",
           "5. Regla: el libro solo se amplía; las predicciones no se cambian después de ver el resultado.", "",
           "| Acción | Fecha | Veredicto | Precio | Ahora | Acción % | IWM % | Diferencia | Resultado |",
           "|---|---|---|---|---|---|---|---|---|"]
    for f in sorted(filas, key=lambda f: (f["fecha"], f["ticker"])):
        lin.append(f"| {f['ticker']} | {f['fecha']} | {f['veredicto']} | {f['precio'] or '—'} | {f.get('precio_final', '—')} | "
                   f"{s(f.get('rent_pct'))} | {s(f.get('rent_indice_pct'))} | {s(f.get('exceso_pct'))} | {f['resultado']} |")
    lin += ["", "Cómo se puntúa: «comprar» y «mantener» aciertan si la acción bate al IWM o llega al objetivo; "
            "«vigilar» acierta si esperar no costó nada (no batió al IWM o tocó el stop). Antes de "
            f"{MIN_SESIONES} sesiones de bolsa se marca «pronto». Información, no consejo."]
    return "\n".join(lin) + "\n"


def ejecutar(hoy: date | None = None, velas_de=None, libro: Path = LIBRO, salida: Path = SALIDA) -> dict:
    hoy = hoy or date.today()
    from . import watchlist
    añadidas = sincronizar(watchlist.leer(), libro)
    preds = leer(libro)
    if velas_de is None:
        from .seguimiento import velas_yahoo
        velas_de = lambda t: velas_yahoo(t, "2y")  # noqa: E731
    cache: dict[str, list] = {}

    def velas(t):
        if t not in cache:
            try:
                cache[t] = velas_de(t) or []
            except Exception as e:  # noqa: BLE001 - una acción sin datos no para el resto
                print(f"AVISO {t}: {e}")
                cache[t] = []
        return cache[t]

    idx = velas(INDICE)
    filas = [puntuar(p, velas(p["ticker"]), idx, hoy) for p in preds]
    res = resumir(filas)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "marcador.json").write_text(json.dumps(dict(actualizado=hoy.isoformat(), indice=INDICE, resumen=res, filas=filas),
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "marcador.md").write_text(informe_md(res, filas, hoy), encoding="utf-8")
    return dict(añadidas=añadidas, **res)
