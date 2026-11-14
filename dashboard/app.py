"""Panel web. Se abre con:  lab panel   (o  streamlit run dashboard/app.py)"""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data" / "lab.db"

st.set_page_config(page_title="Trading Lab (demo)", layout="wide")
st.title("Trading Lab · solo cuenta demo")


def tabla(sql):
    if not DB.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB) as con:
        try:
            return pd.read_sql(sql, con)
        except Exception:  # noqa: BLE001
            return pd.DataFrame()


t1, t2, t3 = st.tabs(["Intradía", "Medio plazo (12 meses)", "Backtests"])

with t1:
    origenes = tabla("SELECT DISTINCT origen FROM decisiones ORDER BY id DESC")
    if origenes.empty:
        st.info("Aún no hay datos. Prueba en la terminal:  lab intradia demo")
    else:
        origen = st.selectbox("¿Qué quieres ver?", origenes["origen"].tolist(),
                              help="sesion-* = sesiones en vivo · demo/backtest = pruebas")
        dec = tabla(f"SELECT * FROM decisiones WHERE origen='{origen}' ORDER BY id DESC")
        ops = tabla(f"SELECT * FROM operaciones WHERE origen='{origen}' ORDER BY id")
        cerradas = ops[ops["pnl"].notna()] if not ops.empty else ops
        c = st.columns(5)
        c[0].metric("Señales", len(dec))
        c[1].metric("Ejecutadas", int((dec.resultado == "PASADA").sum()))
        c[2].metric("Frenadas", int((dec.resultado == "FRENADA").sum()))
        c[3].metric("Resultado $", f"{cerradas['pnl'].sum():+.2f}" if not cerradas.empty else "0")
        c[4].metric("% acierto", f"{(cerradas['pnl'] > 0).mean() * 100:.0f}%" if not cerradas.empty else "-")
        if not cerradas.empty:
            st.subheader("Curva de resultados (operaciones cerradas)")
            st.line_chart(cerradas["pnl"].cumsum().reset_index(drop=True))
        st.subheader("Operaciones")
        st.dataframe(ops, width="stretch", hide_index=True)
        st.subheader("Cada decisión y por qué")
        st.dataframe(dec[["ts", "simbolo", "lado", "resultado", "capa", "motivo", "ia_veredicto", "ia_motivo"]],
                     width="stretch", hide_index=True)

with t2:
    wl = RAIZ / "investigacion" / "watchlist.csv"
    st.subheader("Lista de vigilancia")
    if wl.exists() and wl.stat().st_size > 0:
        df = pd.read_csv(wl)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Vacía. Pide a Claude: 'usa la skill buscar-small-caps' y luego 'analizar-empresa-12m'.")
    st.subheader("Últimas alertas")
    al = tabla("SELECT ts, ticker, tipo, mensaje FROM alertas ORDER BY id DESC LIMIT 50")
    st.dataframe(al, width="stretch", hide_index=True) if not al.empty else st.caption("Sin alertas. Ejecuta: lab medio alertas")
    cand = RAIZ / "investigacion" / "candidatos.csv"
    if cand.exists():
        st.subheader("Candidatos del último cribado")
        st.dataframe(pd.read_csv(cand), width="stretch", hide_index=True)
    informes = sorted((RAIZ / "investigacion" / "analisis").glob("*.md"), reverse=True)
    if informes:
        st.subheader("Informes de análisis")
        elegido = st.selectbox("Informe", [p.name for p in informes])
        st.markdown((RAIZ / "investigacion" / "analisis" / elegido).read_text(encoding="utf-8"))

with t3:
    bt = tabla("SELECT ts, estrategia, simbolos, desde, hasta, n_operaciones, aciertos_pct, profit_factor, pnl, "
               "max_drawdown_pct FROM backtests ORDER BY id DESC")
    st.dataframe(bt, width="stretch", hide_index=True) if not bt.empty else st.info("Sin backtests todavía.")
