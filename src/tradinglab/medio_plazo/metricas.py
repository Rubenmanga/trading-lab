"""Recogida de datos de UNA empresa para el buscador de oportunidades (agente B).

Fuente: Yahoo Finance vía yfinance (gratis; funciona desde GitHub Actions, no desde el contenedor de
Claude en la nube). Cada bloque va en su propio try: si Yahoo no da un dato, se queda en None y el
buscador lo trata como "sin dato" (puntúa neutro y baja la cobertura).

Las métricas siguen las ideas de los profesionales que usamos como referencia:
- GARP / us-undervalued-growth-screener (tradermonty, MIT): crecimiento por acción, valoración futura,
  calidad de caja, dilución y SBC, apalancamiento.
- CANSLIM (tradermonty, MIT): beneficios actuales y anuales, cerca de máximos, fuerza relativa.
- VCP de Minervini y PEAD (tradermonty, MIT): señales técnicas de entrada.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone


def _n(x):
    try:
        x = float(x)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def _fila(df, *nombres):
    """Primera fila que exista en un DataFrame de estados financieros de yfinance."""
    if df is None or getattr(df, "empty", True):
        return None
    for n in nombres:
        if n in df.index:
            return df.loc[n]
    return None


def _pct(a, b):
    a, b = _n(a), _n(b)
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1) * 100


def tecnico(hist, ref=None) -> dict:
    """Métricas de precio a partir de velas diarias (DataFrame con Close, High, Low, Volume, Open)."""
    out = {}
    if hist is None or len(hist) < 60:
        return out
    c = hist["Close"].astype(float)
    p = float(c.iloc[-1])
    out["precio"] = p

    def ret(dias, salto=0):
        if len(c) <= dias:
            return None
        fin = c.iloc[-1 - salto] if salto else p
        return (fin / float(c.iloc[-1 - dias]) - 1) * 100

    out["ret_3m"] = ret(63)
    out["ret_6m"] = ret(126)
    out["ret_12m_1m"] = ret(min(252, len(c) - 1), salto=21)  # 12 meses quitando el último (clásico de momentum)
    ma50 = float(c.tail(50).mean())
    ma200 = float(c.tail(200).mean()) if len(c) >= 200 else None
    out["sobre_ma50_pct"] = (p / ma50 - 1) * 100
    out["sobre_ma200_pct"] = (p / ma200 - 1) * 100 if ma200 else None
    alto = float(hist["High"].tail(252).max())
    bajo = float(hist["Low"].tail(252).min())
    out["dist_max52_pct"] = (p / alto - 1) * 100
    out["sobre_min52_pct"] = (p / bajo - 1) * 100
    rend = c.pct_change().dropna()
    out["volatilidad_anual_pct"] = float(rend.tail(126).std() * math.sqrt(252) * 100)
    pico = c.cummax()
    out["max_caida_1a_pct"] = float(((c / pico) - 1).tail(252).min() * 100)
    vol = hist["Volume"].astype(float)
    out["volumen_dolares_medio"] = float((c.tail(50) * vol.tail(50)).mean())
    if ref is not None and len(ref) > 130:
        r = ref.astype(float)
        out["fuerza_relativa_6m"] = (out["ret_6m"] or 0) - (float(r.iloc[-1]) / float(r.iloc[-127]) - 1) * 100

    # Señales de entrada (orientativas, no órdenes):
    # 1) Tendencia "fase 2" de Minervini: precio > MA50 > MA200 y MA200 subiendo.
    ma200_antes = float(c.iloc[-221:-21].mean()) if len(c) >= 221 else None
    out["tendencia_fase2"] = bool(ma200 and p > ma50 > ma200 and ma200_antes and ma200 > ma200_antes)
    # 2) Base estrecha tipo VCP: el rango de las últimas 3 semanas es mucho menor que el de 3 meses
    #    y el precio está a menos del 15% de su máximo anual.
    r15 = float(hist["High"].tail(15).max() / hist["Low"].tail(15).min() - 1)
    r63 = float(hist["High"].tail(63).max() / hist["Low"].tail(63).min() - 1)
    out["contraccion_rango"] = r15 / r63 if r63 > 0 else None
    out["base_vcp"] = bool(out["contraccion_rango"] is not None and out["contraccion_rango"] < 0.4
                           and out["dist_max52_pct"] > -15 and out["tendencia_fase2"])
    # 3) Hueco al alza con volumen en los últimos 40 días que se mantiene (idea PEAD: tras buenos
    #    resultados el precio suele seguir subiendo semanas).
    o = hist["Open"].astype(float)
    huecos = []
    for i in range(max(1, len(c) - 40), len(c)):
        gap = (float(o.iloc[i]) / float(c.iloc[i - 1]) - 1) * 100
        vmed = float(vol.iloc[max(0, i - 50):i].mean() or 1)
        if gap >= 5 and float(vol.iloc[i]) >= 2 * vmed:
            huecos.append((i, gap, float(c.iloc[i - 1])))
    if huecos:
        i, gap, antes = huecos[-1]
        out["hueco_reciente_pct"] = round(gap, 1)
        out["hueco_mantenido"] = bool(p > antes * (1 + gap / 200))  # conserva al menos la mitad del hueco
    return out


def empresa(ticker: str, ref_close=None) -> dict:
    """Todas las métricas en bruto de una empresa. Cada bloque falla por separado."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    m: dict = {"ticker": ticker, "errores": []}

    def bloque(nombre, fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            m["errores"].append(f"{nombre}: {type(e).__name__}")

    def info():
        i = t.info or {}
        m.update(
            empresa=i.get("shortName") or i.get("longName"), sector=i.get("sector"), industria=i.get("industry"),
            capitalizacion=_n(i.get("marketCap")), valor_empresa=_n(i.get("enterpriseValue")),
            ventas=_n(i.get("totalRevenue")), crec_ventas=_n(i.get("revenueGrowth")),
            crec_beneficio=_n(i.get("earningsGrowth")), margen_bruto=_n(i.get("grossMargins")),
            margen_operativo=_n(i.get("operatingMargins")), margen_neto=_n(i.get("profitMargins")),
            roe=_n(i.get("returnOnEquity")), roa=_n(i.get("returnOnAssets")),
            fcf=_n(i.get("freeCashflow")), flujo_operativo=_n(i.get("operatingCashflow")),
            ebitda=_n(i.get("ebitda")), caja=_n(i.get("totalCash")), deuda=_n(i.get("totalDebt")),
            per_futuro=_n(i.get("forwardPE")), per=_n(i.get("trailingPE")), peg=_n(i.get("trailingPegRatio")),
            ev_ventas=_n(i.get("enterpriseToRevenue")), ev_ebitda=_n(i.get("enterpriseToEbitda")),
            precio_valor_contable=_n(i.get("priceToBook")), bpa_futuro=_n(i.get("forwardEps")),
            bpa=_n(i.get("trailingEps")), cortos_flotante=_n(i.get("shortPercentOfFloat")),
            insiders_pct=_n(i.get("heldPercentInsiders")), instituciones_pct=_n(i.get("heldPercentInstitutions")),
            analistas=_n(i.get("numberOfAnalystOpinions")), recomendacion_media=_n(i.get("recommendationMean")),
            recomendacion=i.get("recommendationKey"), objetivo_medio=_n(i.get("targetMeanPrice")),
            objetivo_bajo=_n(i.get("targetLowPrice")), objetivo_alto=_n(i.get("targetHighPrice")),
            precio_info=_n(i.get("currentPrice") or i.get("regularMarketPrice")), beta=_n(i.get("beta")),
            tipo=i.get("quoteType"),
            cortos_acciones=_n(i.get("sharesShort")), cortos_mes_antes=_n(i.get("sharesShortPriorMonth")),
            dias_para_cubrir=_n(i.get("shortRatio")),
        )

    def tendencia_bpa():
        # Cuánto han cambiado las previsiones de beneficio por acción (BPA) en 30 y 90 días.
        df = t.eps_trend
        for per, et in (("0y", "anio"), ("+1y", "sig")):
            if df is None or per not in df.index:
                continue
            fila = df.loc[per]
            act, d30, d90 = _n(fila.get("current")), _n(fila.get("30daysAgo")), _n(fila.get("90daysAgo"))
            m[f"bpa_est_{et}"] = act
            if act is not None and d30:
                m[f"rev_bpa_30d_{et}"] = (act - d30) / abs(d30) * 100
            if act is not None and d90:
                m[f"rev_bpa_90d_{et}"] = (act - d90) / abs(d90) * 100

    def revisiones():
        df = t.eps_revisions
        if df is None or df.empty:
            return
        sub = baj = 0
        for per in ("0q", "+1q", "0y", "+1y"):
            if per in df.index:
                sub += _n(df.loc[per].get("upLast30days")) or 0
                baj += _n(df.loc[per].get("downLast30days")) or 0
        m["revisiones_suben_30d"], m["revisiones_bajan_30d"] = sub, baj

    def estimaciones():
        e = t.earnings_estimate
        if e is not None and "+1y" in e.index:
            m["crec_bpa_sig_anio"] = _n(e.loc["+1y"].get("growth"))
            m["crec_bpa_anio"] = _n(e.loc["0y"].get("growth")) if "0y" in e.index else None
        r = t.revenue_estimate
        if r is not None and "+1y" in r.index:
            m["crec_ventas_sig_anio"] = _n(r.loc["+1y"].get("growth"))
            m["crec_ventas_anio"] = _n(r.loc["0y"].get("growth")) if "0y" in r.index else None

    def sorpresas():
        h = t.earnings_history
        if h is None or h.empty or "surprisePercent" not in h.columns:
            return
        s = [_n(x) for x in h["surprisePercent"].tolist()[-4:]]
        s = [x for x in s if x is not None]
        if s:
            m["sorpresa_media"] = sum(s) / len(s) * (100 if max(abs(x) for x in s) < 5 else 1)
            m["sorpresas_positivas"] = sum(1 for x in s if x > 0)

    def cambios_recomendacion():
        ud = t.upgrades_downgrades
        if ud is None or ud.empty:
            return
        desde = datetime.now(timezone.utc) - timedelta(days=90)
        idx = ud.index.tz_localize("UTC") if ud.index.tz is None else ud.index
        rec = ud[idx >= desde]
        acc = rec["Action"].astype(str).str.lower() if "Action" in rec.columns else []
        m["mejoras_90d"] = int((acc == "up").sum()) if len(rec) else 0
        m["rebajas_90d"] = int((acc == "down").sum()) if len(rec) else 0
        if "priceTargetAction" in rec.columns:
            pta = rec["priceTargetAction"].astype(str).str.lower()
            m["objetivos_suben_90d"] = int(pta.str.contains("raise").sum())
            m["objetivos_bajan_90d"] = int(pta.str.contains("lower").sum())

    def insiders():
        # Resumen de Yahoo de los formularios 4 de la SEC de los últimos 6 meses.
        ip = t.insider_purchases
        if ip is None or ip.empty:
            return
        col0 = ip.columns[0]
        filas = {str(r[col0]).strip().lower(): r for _, r in ip.iterrows()}

        def val(clave, col="Shares"):
            for k, r in filas.items():
                if k.startswith(clave):
                    return _n(r.get(col))
            return None
        m["insiders_compras_n"] = val("purchases", "Trans")
        m["insiders_ventas_n"] = val("sales", "Trans")
        m["insiders_neto_pct"] = val("% net shares")
        if m["insiders_neto_pct"] is not None and abs(m["insiders_neto_pct"]) < 1:
            m["insiders_neto_pct"] *= 100

    def cuentas():
        q = t.quarterly_income_stmt
        acc = _fila(q, "Diluted Average Shares", "Basic Average Shares")
        if acc is not None:
            v = [x for x in (_n(a) for a in acc.tolist()) if x]
            if len(v) >= 5:
                m["dilucion_1a_pct"] = _pct(v[0], v[4])
            elif len(v) >= 2:
                m["dilucion_1a_pct"] = _pct(v[0], v[-1])
        ventas_q = _fila(q, "Total Revenue")
        if ventas_q is not None:
            v = [_n(a) for a in ventas_q.tolist()]
            if len(v) >= 5 and v[0] and v[4]:
                m["crec_ventas_ult_trim"] = _pct(v[0], v[4]) / 100
        cf = t.quarterly_cashflow
        fcf = _fila(cf, "Free Cash Flow")
        sbc = _fila(cf, "Stock Based Compensation")
        if fcf is not None:
            v = [_n(a) for a in fcf.tolist()[:4]]
            v = [x for x in v if x is not None]
            if v:
                m["fcf_4t"] = sum(v)
                m["fcf_trim_positivos"] = sum(1 for x in v if x > 0)
        if sbc is not None:
            v = [x for x in (_n(a) for a in sbc.tolist()[:4]) if x is not None]
            if v:
                m["sbc_4t"] = sum(v)

    def calendario():
        cal = t.calendar or {}
        f = cal.get("Earnings Date") or []
        if f:
            m["proximos_resultados"] = str(f[0])[:10]

    def precio():
        h = t.history(period="15mo", interval="1d", auto_adjust=True)
        m.update(tecnico(h, ref_close))

    for nombre, fn in (("info", info), ("tendencia_bpa", tendencia_bpa), ("revisiones", revisiones),
                       ("estimaciones", estimaciones), ("sorpresas", sorpresas),
                       ("recomendaciones", cambios_recomendacion), ("insiders", insiders),
                       ("cuentas", cuentas), ("calendario", calendario), ("precio", precio)):
        bloque(nombre, fn)

    # Derivadas
    cap, caja, deuda = m.get("capitalizacion"), m.get("caja"), m.get("deuda")
    fcf = m.get("fcf_4t", m.get("fcf"))
    if cap and fcf is not None:
        m["rent_fcf_pct"] = fcf / cap * 100
        if m.get("sbc_4t") is not None:
            m["rent_fcf_menos_sbc_pct"] = (fcf - m["sbc_4t"]) / cap * 100
    if caja is not None and fcf is not None and fcf < 0:
        m["meses_de_caja"] = caja / (-fcf / 12)
    if deuda is not None and caja is not None and m.get("ebitda"):
        m["deuda_neta_ebitda"] = (deuda - caja) / m["ebitda"] if m["ebitda"] > 0 else None
    if m.get("cortos_acciones") and m.get("cortos_mes_antes"):
        m["cortos_cambio_1m_pct"] = _pct(m["cortos_acciones"], m["cortos_mes_antes"])
    p = m.get("precio") or m.get("precio_info")
    if p and m.get("objetivo_medio"):
        m["potencial_analistas_pct"] = (m["objetivo_medio"] / p - 1) * 100
    if p and m.get("objetivo_bajo"):
        m["potencial_objetivo_bajo_pct"] = (m["objetivo_bajo"] / p - 1) * 100
    return m
