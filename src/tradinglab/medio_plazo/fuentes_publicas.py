"""Fuentes públicas GRATIS y SIN CLAVE para el agente B (12 meses).

  - SEC EDGAR (registro oficial de EE. UU.): qué documentos ha presentado cada empresa.
      · S-1 / S-3 = "registro" para poder vender acciones nuevas (posible dilución).
      · 424B4 / 424B5 = folleto de una colocación de acciones que ya se está haciendo.
      · 13D = un inversor (a menudo activista) declara más del 5 % y quiere influir.
      · 13G = un fondo declara más del 5 % como inversión pasiva.
      · NT 10-K / NT 10-Q = aviso de que presentará las cuentas tarde (mala señal).
  - ClinicalTrials.gov (EE. UU.): ensayos clínicos de fase 2 y 3 de cada empresa de salud cuyo resultado
    principal se espera en los próximos 12 meses (catalizadores clásicos en biotech).
  - FRED (Reserva Federal de St. Louis): semáforo macro para small caps.

Funcionan desde GitHub Actions (no desde el contenedor de Claude en la nube, que tiene la red cortada).
Todo falla "en silencio": si una fuente no responde, el buscador sigue sin esos datos.
Las funciones `resumen_*`, `leer_csv_fred` y `semaforo_macro` son puras (sin internet) para poder probarlas.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

# La SEC pide un "User-Agent" que identifique quién pregunta. Se puede cambiar con el secreto SEC_USER_AGENT.
# Ojo: la SEC rechaza los User-Agent que contienen "bot" o que no tienen forma "Nombre email".
UA_DEFECTO = "TradingLab Research noreply@github.com"
ULTIMO_ERROR: dict = {}


def _ua() -> str:
    return os.getenv("SEC_USER_AGENT") or UA_DEFECTO


def _get(url: str, json_: bool = True, intentos: int = 3, cab: dict | None = None):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _ua(), "Accept-Encoding": "identity",
                                                       **(cab or {})})
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode("utf-8", errors="replace")
                return json.loads(txt) if json_ else txt
        except urllib.error.HTTPError as e:
            ULTIMO_ERROR[urllib.parse.urlparse(url).netloc] = f"HTTP {e.code}"
            if e.code == 404:
                return None
            time.sleep(3 * (i + 1) if e.code in (429, 403, 503) else 1)
        except Exception as e:  # noqa: BLE001
            ULTIMO_ERROR[urllib.parse.urlparse(url).netloc] = type(e).__name__
            time.sleep(2 * (i + 1))
    return None


def _fecha(s: str | None) -> date | None:
    """'2026-11-14', '2026-11' o '2026' → fecha (a mitad de mes / año si falta el día)."""
    if not s:
        return None
    try:
        p = s[:10].split("-")
        if len(p) == 3:
            return date(int(p[0]), int(p[1]), int(p[2]))
        if len(p) == 2:
            return date(int(p[0]), int(p[1]), 15)
        return date(int(p[0]), 6, 30)
    except (ValueError, IndexError):
        return None


# ------------------------------------------------------------------ SEC EDGAR
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"

REGISTRO = ("S-1", "S-3", "S-3ASR", "F-1", "F-3", "S-1/A", "S-3/A")
COLOCACION = ("424B4", "424B5", "424B1")


def _es(form: str, *tipos: str) -> bool:
    return form.upper().strip() in tipos


def resumen_sec(sub: dict, hoy: date | None = None) -> dict:
    """Resume la lista de documentos recientes de una empresa (JSON de data.sec.gov/submissions)."""
    hoy = hoy or date.today()
    rec = ((sub or {}).get("filings") or {}).get("recent") or {}
    formas, fechas = rec.get("form") or [], rec.get("filingDate") or []
    acc, doc = rec.get("accessionNumber") or [], rec.get("primaryDocument") or []
    cik = str(int(sub.get("cik") or 0)) if sub.get("cik") else ""
    out = dict(sec_registro_180d=0, sec_colocacion_90d=0, sec_13d_180d=0, sec_13g_180d=0, sec_form4_90d=0,
               sec_retraso_365d=0, sec_8k_30d=0)
    destacados = []
    for i, (fo, fe) in enumerate(zip(formas, fechas)):
        d = _fecha(fe)
        if d is None:
            continue
        dias = (hoy - d).days
        if dias < 0 or dias > 365:
            continue
        f = (fo or "").upper().strip()
        tipo = None
        if f in REGISTRO and dias <= 180:
            out["sec_registro_180d"] += 1
            tipo = "Registro para vender acciones (" + f + ")"
        elif f in COLOCACION and dias <= 90:
            out["sec_colocacion_90d"] += 1
            tipo = "Colocación de acciones (" + f + ")"
        elif f in ("SC 13D", "SCHEDULE 13D") and dias <= 180:
            out["sec_13d_180d"] += 1
            tipo = "Inversor activista >5 % (13D)"
        elif f in ("SC 13G", "SCHEDULE 13G") and dias <= 180:
            out["sec_13g_180d"] += 1
            tipo = "Fondo grande >5 % (13G)"
        elif f == "4" and dias <= 90:
            out["sec_form4_90d"] += 1
        elif f in ("NT 10-K", "NT 10-Q"):
            out["sec_retraso_365d"] += 1
            tipo = "Cuentas presentadas tarde (" + f + ")"
        elif f == "8-K" and dias <= 30:
            out["sec_8k_30d"] += 1
        if tipo and len(destacados) < 8:
            url = None
            if cik and i < len(acc) and i < len(doc) and acc[i]:
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc[i].replace('-', '')}/{doc[i]}"
            destacados.append(dict(fecha=fe, tipo=tipo, url=url))
    out["sec_grandes_inversores_180d"] = out["sec_13d_180d"] + out["sec_13g_180d"]
    out["sec_documentos"] = destacados
    return out


def mapa_cik() -> dict[str, str]:
    d = _get(SEC_TICKERS) or {}
    return {str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10) for v in d.values() if v.get("ticker")}


def datos_sec(tickers: list[str], hilos: int = 4, pausa: float = 0.5) -> dict[str, dict]:
    """Un pedido por empresa. 4 hilos x 2 por segundo = 8/s, por debajo del límite de 10/s de la SEC."""
    ciks = mapa_cik()
    if not ciks:
        return {}
    hoy = date.today()

    def uno(t):
        cik = ciks.get(t.upper()) or ciks.get(t.upper().replace(".", "-"))
        if not cik:
            return t, None
        sub = _get(SEC_SUBMISSIONS.format(cik=cik))
        time.sleep(pausa)
        return t, (resumen_sec(sub, hoy) if sub else None)
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        return {t: r for t, r in ex.map(uno, tickers) if r}


# ------------------------------------------------------------------ ClinicalTrials.gov
CT_API = "https://clinicaltrials.gov/api/v2/studies"
CT_ESTADOS = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING"
_SUFIJOS = r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|lp|holdings?|group|n\.?v|s\.?a|ag|se)\b\.?"


def nombre_simple(empresa: str | None) -> str:
    """'Oric Pharmaceuticals, Inc.' → 'oric pharmaceuticals'."""
    s = (empresa or "").lower().replace("&", " and ")
    s = re.sub(r"[,()]", " ", s)
    s = re.sub(_SUFIJOS, " ", s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 \-]", " ", s)).strip()


def resumen_ensayos(estudios: list[dict], empresa: str, hoy: date | None = None, dias: int = 365) -> dict:
    """Ensayos de fase 2/3 del propio patrocinador con fecha de resultado principal entre hace 30 días y +12 meses."""
    hoy = hoy or date.today()
    mio = nombre_simple(empresa)
    activos, clave_12m = 0, []
    for e in estudios or []:
        ps = e.get("protocolSection") or {}
        lider = nombre_simple(((ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}).get("name"))
        if not mio or not lider or not (lider.startswith(mio) or mio.startswith(lider)):
            continue   # otro patrocinador con nombre parecido
        activos += 1
        fases = (ps.get("designModule") or {}).get("phases") or []
        if not any(f in ("PHASE2", "PHASE3") for f in fases):
            continue
        st = ps.get("statusModule") or {}
        fecha_txt = (st.get("primaryCompletionDateStruct") or {}).get("date")
        d = _fecha(fecha_txt)
        if d is None or not (-30 <= (d - hoy).days <= dias):
            continue
        ide = ps.get("identificationModule") or {}
        clave_12m.append(dict(nct=ide.get("nctId"), titulo=(ide.get("briefTitle") or "")[:160],
                              fase="/".join(f.replace("PHASE", "F") for f in fases), fecha=fecha_txt,
                              estado=st.get("overallStatus")))
    clave_12m.sort(key=lambda x: x["fecha"] or "")
    return dict(ensayos_activos=activos, ensayos_clave_12m=len(clave_12m), ensayos=clave_12m[:8])


def datos_ensayos(empresas: dict[str, str], pausa: float = 0.35) -> dict[str, dict]:
    """empresas = {ticker: nombre}. Solo para empresas del sector salud."""
    out, hoy = {}, date.today()
    for t, nombre in empresas.items():
        q = nombre_simple(nombre)
        if len(q) < 3:
            continue
        params = {"query.lead": q, "filter.overallStatus": CT_ESTADOS, "pageSize": 100,
                  "fields": "NCTId,BriefTitle,Phase,PrimaryCompletionDate,OverallStatus,LeadSponsorName"}
        r = _get(f"{CT_API}?{urllib.parse.urlencode(params)}", cab={"Accept": "application/json"})
        time.sleep(pausa)
        if r is not None:
            out[t] = resumen_ensayos(r.get("studies") or [], nombre, hoy)
    return out


# ------------------------------------------------------------------ FRED (macro)
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={desde}"
SERIES_MACRO = {
    "BAMLH0A0HYM2": "Diferencial del crédito de riesgo (high yield), %",
    "T10Y2Y": "Curva de tipos (10 años menos 2 años), puntos",
    "NFCI": "Condiciones financieras (Fed de Chicago; >0 = más duras que la media)",
}


def leer_csv_fred(txt: str) -> list[tuple[date, float]]:
    out = []
    for linea in (txt or "").splitlines()[1:]:
        p = linea.strip().split(",")
        if len(p) < 2:
            continue
        d = _fecha(p[0])
        try:
            v = float(p[1])
        except ValueError:
            continue   # "." = sin dato ese día
        if d:
            out.append((d, v))
    return out


def _valor_hace(serie: list[tuple[date, float]], dias: int) -> float | None:
    if not serie:
        return None
    objetivo = serie[-1][0] - timedelta(days=dias)
    antes = [v for d, v in serie if d <= objetivo]
    return antes[-1] if antes else None


def semaforo_macro(series: dict[str, list[tuple[date, float]]], iwm: dict | None = None) -> dict:
    """Verde / ámbar / rojo para small caps. Orientativo: NO cambia la nota de las empresas."""
    ind = []

    def add(clave, nombre, valor, hace3m, estado, explicacion):
        ind.append(dict(clave=clave, nombre=nombre, valor=None if valor is None else round(valor, 2),
                        cambio_3m=None if (valor is None or hace3m is None) else round(valor - hace3m, 2),
                        estado=estado, explicacion=explicacion))
    hy = series.get("BAMLH0A0HYM2") or []
    if hy:
        v, a = hy[-1][1], _valor_hace(hy, 91)
        est = "verde" if v < 4 else ("ambar" if v < 5.5 else "rojo")
        if a is not None and v - a > 0.75 and est != "rojo":
            est = "ambar" if est == "verde" else "rojo"
        add("BAMLH0A0HYM2", SERIES_MACRO["BAMLH0A0HYM2"], v, a, est,
            "Lo que cobran de más las empresas con deuda arriesgada. Si sube deprisa, el dinero huye del riesgo "
            "y las small caps (que dependen más del crédito) suelen sufrir.")
    cu = series.get("T10Y2Y") or []
    if cu:
        v, a = cu[-1][1], _valor_hace(cu, 91)
        add("T10Y2Y", SERIES_MACRO["T10Y2Y"], v, a, "ambar" if v < 0 else "verde",
            "Si es negativa (curva invertida) históricamente ha avisado de recesión con 1-2 años de antelación.")
    nf = series.get("NFCI") or []
    if nf:
        v, a = nf[-1][1], _valor_hace(nf, 91)
        add("NFCI", SERIES_MACRO["NFCI"], v, a, "verde" if v < 0 else ("ambar" if v < 0.3 else "rojo"),
            "Mide si es fácil o difícil conseguir financiación. Negativo = fácil, bueno para empresas pequeñas.")
    if iwm and iwm.get("precio") and iwm.get("ma200"):
        dist = (iwm["precio"] / iwm["ma200"] - 1) * 100
        add("IWM", "Small caps (Russell 2000, IWM) frente a su media de 200 días, %", dist, None,
            "verde" if dist > 0 else ("ambar" if dist > -5 else "rojo"),
            "Por encima de la media de 200 días = tendencia de fondo alcista para las small caps.")
    rojos = sum(1 for i in ind if i["estado"] == "rojo")
    ambar = sum(1 for i in ind if i["estado"] == "ambar")
    if not ind:
        glob, txt = None, "Sin datos macro hoy."
    elif rojos >= 2 or (rojos == 1 and ambar >= 2):
        glob, txt = "rojo", "Ambiente difícil para small caps: entrar con menos dinero y exigir más margen de seguridad."
    elif rojos == 1 or ambar >= 2:
        glob, txt = "ambar", "Ambiente mixto: ir con cuidado y escalonar las compras."
    else:
        glob, txt = "verde", "Ambiente favorable para small caps."
    return dict(estado=glob, resumen=txt, indicadores=ind,
                fecha=max((s[-1][0] for s in series.values() if s), default=None))


def datos_macro() -> dict:
    desde = (date.today() - timedelta(days=400)).isoformat()
    series = {}
    for sid in SERIES_MACRO:
        txt = _get(FRED_CSV.format(id=sid, desde=desde), json_=False)
        series[sid] = leer_csv_fred(txt) if txt else []
    iwm = None
    try:
        import yfinance as yf
        c = yf.Ticker("IWM").history(period="15mo", interval="1d", auto_adjust=True)["Close"]
        if len(c) >= 200:
            iwm = dict(precio=float(c.iloc[-1]), ma200=float(c.tail(200).mean()))
    except Exception:  # noqa: BLE001
        pass
    r = semaforo_macro(series, iwm)
    if r.get("fecha"):
        r["fecha"] = r["fecha"].isoformat()
    return r


# ------------------------------------------------------------------ todo junto
def completar(filas: list[dict], cfg: dict | None = None) -> dict:
    """Añade a cada fila los datos de SEC y (salud) ensayos ANTES de puntuar. Devuelve un resumen."""
    cfg = cfg or {}
    res: dict = {}
    if cfg.get("sec", True):
        t0 = time.monotonic()
        sec = datos_sec([f["ticker"] for f in filas])
        for f in filas:
            if f["ticker"] in sec:
                f.update(sec[f["ticker"]])
        res["sec_empresas"] = len(sec)
        res["sec_segundos"] = round(time.monotonic() - t0)
        if not sec and ULTIMO_ERROR.get("www.sec.gov"):
            res["sec_error"] = ULTIMO_ERROR["www.sec.gov"]
    if cfg.get("ensayos", True):
        salud = {f["ticker"]: f.get("empresa") for f in filas if f.get("sector") == "Healthcare" and f.get("empresa")}
        t0 = time.monotonic()
        ens = datos_ensayos(salud)
        for f in filas:
            if f["ticker"] in ens:
                f.update(ens[f["ticker"]])
        res["ensayos_empresas"] = len(ens)
        res["ensayos_con_catalizador"] = sum(1 for v in ens.values() if v["ensayos_clave_12m"])
        res["ensayos_segundos"] = round(time.monotonic() - t0)
    return res
