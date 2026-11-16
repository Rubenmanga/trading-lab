"""¿Presentó resultados la empresa justo antes de abrir? Fuente oficial y gratis: la SEC.

Cuando una empresa de EE. UU. publica resultados trimestrales, presenta un formulario 8-K con el punto
2.02 («Results of Operations and Financial Condition»). La SEC apunta la hora exacta a la que lo recibe.
Marcamos un día D como «día de resultados» de una acción si ese 8-K llegó entre las 15:30 NY del día
de bolsa anterior y las 9:30 NY de D (resultados de la tarde anterior o de esa madrugada).

Límites (para no engañarnos):
- Solo empresas con ticker ACTUAL en la SEC: las deslistadas no se pueden marcar (columna `con_cik`).
- Las extranjeras que presentan 6-K (no 8-K) quedan fuera.
- Nada mira el futuro: un aviso que llega después de las 9:30 no cuenta para ese día.
"""
from __future__ import annotations

import json
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from ...medio_plazo.fuentes_publicas import _get, _ua, mapa_cik

ZIP_SEC = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
API_SEC = "https://data.sec.gov/submissions/CIK{cik}.json"
NY = "America/New_York"


def filas_8k(bloque: dict) -> list[str]:
    """Horas de recepción (texto tal cual) de los 8-K con el punto 2.02 de un bloque de la SEC."""
    formas, items, horas = bloque.get("form") or [], bloque.get("items") or [], bloque.get("acceptanceDateTime") or []
    return [h for f, it, h in zip(formas, items, horas) if f in ("8-K", "8-K/A") and "2.02" in str(it)]


def _bloques(js: dict) -> tuple[dict, list[str]]:
    """El JSON principal trae lo reciente en filings.recent y el nombre de los archivos con lo antiguo."""
    if "filings" in js:
        return js["filings"].get("recent") or {}, [f["name"] for f in js["filings"].get("files") or []]
    return js, []


def eventos_desde_zip(ruta_zip: str | Path, ciks: set[str]) -> pd.DataFrame:
    """Lee del archivo masivo de la SEC solo las empresas que interesan."""
    filas = []
    with zipfile.ZipFile(ruta_zip) as z:
        nombres = set(z.namelist())
        for cik in sorted(ciks):
            principal = f"CIK{cik}.json"
            if principal not in nombres:
                continue
            reciente, extra = _bloques(json.loads(z.read(principal)))
            horas = filas_8k(reciente)
            for n in extra:
                if n in nombres:
                    horas += filas_8k(_bloques(json.loads(z.read(n)))[0])
            filas += [(cik, h) for h in horas]
    return pd.DataFrame(filas, columns=["cik", "aceptado"])


def eventos_api(ciks: set[str], pausa: float = 0.15) -> pd.DataFrame:
    """Para pocos días (cuenta sombra): un pedido por empresa, por debajo del límite de 10/s de la SEC."""
    filas = []
    for cik in sorted(ciks):
        js = _get(API_SEC.format(cik=cik)) or {}
        filas += [(cik, h) for h in filas_8k(_bloques(js)[0])]
        time.sleep(pausa)
    return pd.DataFrame(filas, columns=["cik", "aceptado"])


def a_hora_ny(aceptado: pd.Series) -> pd.Series:
    """Pasa las horas de la SEC a hora de Nueva York.

    La SEC escribe las horas con una «Z» (UTC), pero no está claro que siempre lo sean. Se decide mirando
    los datos: los resultados se publican sobre todo a las 16-17 h y a las 6-8 h de Nueva York. Si las
    horas tal cual se amontonan ahí, ya son de Nueva York; si se amontonan 4-5 horas después, son UTC."""
    t = pd.to_datetime(aceptado.astype(str).str.replace("Z", "", regex=False), errors="coerce")
    h = t.dt.hour
    como_ny = h.isin([6, 7, 8, 16, 17]).mean()
    como_utc = h.isin([10, 11, 12, 13, 20, 21, 22]).mean()
    if como_utc > como_ny:
        return t.dt.tz_localize("UTC").dt.tz_convert(NY)
    return t.dt.tz_localize(NY, ambiguous="NaT", nonexistent="NaT")


def marcar(cands: pd.DataFrame, eventos: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    """Devuelve (fecha, simbolo, con_cik, resultados, hora_aviso) para cada fila de las candidatas."""
    base = cands[["fecha", "simbolo"]].drop_duplicates().copy()
    base["cik"] = base["simbolo"].map(lambda s: mapa.get(str(s).upper()) or mapa.get(str(s).upper().replace(".", "-")))
    base["con_cik"] = base["cik"].notna()
    base["resultados"], base["hora_aviso"] = False, ""
    if eventos.empty:
        return base.drop(columns="cik")
    ev = eventos.assign(ny=a_hora_ny(eventos["aceptado"])).dropna(subset=["ny"])
    # Día de bolsa anterior a cada fecha (con los días que tenemos; si solo hay uno, el laborable anterior)
    dias = sorted(base["fecha"].unique())
    previo = {d: (dias[i - 1] if i else (pd.Timestamp(d) - pd.offsets.BDay(1)).strftime("%Y-%m-%d"))
              for i, d in enumerate(dias)}
    por_cik = {c: g["ny"].sort_values().tolist() for c, g in ev.groupby("cik")}
    for i, f in base[base["con_cik"]].iterrows():
        horas = por_cik.get(f["cik"])
        if not horas:
            continue
        ini = pd.Timestamp(f"{previo[f['fecha']]} 15:30", tz=NY)
        fin = pd.Timestamp(f"{f['fecha']} 09:30", tz=NY)
        dentro = [h for h in horas if ini < h <= fin]
        if dentro:
            base.at[i, "resultados"] = True
            base.at[i, "hora_aviso"] = dentro[-1].strftime("%Y-%m-%d %H:%M")
    return base.drop(columns="cik")


def descargar_zip(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(ZIP_SEC, headers={"User-Agent": _ua()})
    with urllib.request.urlopen(req, timeout=600) as r, open(destino, "wb") as f:
        while trozo := r.read(1 << 20):
            f.write(trozo)
    return destino


def calcular(cands: pd.DataFrame, zip_local: Path | None = None) -> pd.DataFrame:
    """Marca las candidatas. Con muchos días usa el archivo masivo (1 descarga); con pocos, la API."""
    mapa = mapa_cik()
    if not mapa:
        raise RuntimeError("La SEC no ha devuelto la lista de tickers (¿falta SEC_USER_AGENT?)")
    ciks = {mapa[s] for s in cands["simbolo"].astype(str).str.upper().unique() if s in mapa}
    if cands["fecha"].nunique() > 5:
        z = zip_local or descargar_zip(Path("datos_estudio") / "submissions.zip")
        ev = eventos_desde_zip(z, ciks)
    else:
        ev = eventos_api(ciks)
    out = marcar(cands, ev, mapa)
    print(f"SEC: {len(ciks)} empresas con ticker actual, {len(ev)} avisos de resultados (8-K 2.02); "
          f"{out['con_cik'].mean():.0%} de las filas con CIK, {int(out['resultados'].sum())} días de resultados")
    return out


def unir(cands: pd.DataFrame, marcas: pd.DataFrame | None) -> pd.DataFrame:
    """Añade a las candidatas las columnas `resultados` y `con_cik` (False si no hay marcas)."""
    if marcas is None or marcas.empty:
        return cands.assign(resultados=False, con_cik=False)
    m = marcas[["fecha", "simbolo", "resultados", "con_cik"]]
    out = cands.drop(columns=[c for c in ("resultados", "con_cik") if c in cands], errors="ignore").merge(
        m, on=["fecha", "simbolo"], how="left")
    out["resultados"] = out["resultados"].fillna(False).astype(bool)
    out["con_cik"] = out["con_cik"].fillna(False).astype(bool)
    return out


def leer(ruta: str | Path) -> pd.DataFrame:
    return pd.read_csv(ruta, keep_default_na=False, na_values=[""]) if Path(ruta).exists() else pd.DataFrame()
