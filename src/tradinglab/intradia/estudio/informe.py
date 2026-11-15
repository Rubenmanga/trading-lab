"""Paso 3: junta los CSV de todos los años y escribe el resumen (JSON) y un informe en Markdown."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def _pct(x: float | None, dec: int = 1) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.{dec}f} %".replace(".", ",")


def _num(x, dec: int = 2) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{dec}f}".replace(".", ",")


def stats_ops(df: pd.DataFrame) -> dict:
    if df.empty:
        return dict(operaciones=0)
    R = df["R"]
    gan, per = R[R > 0].sum(), -R[R < 0].sum()
    return dict(operaciones=int(len(df)), aciertos=float((R > 0).mean()), R_medio=float(R.mean()),
                R_mediana=float(R.median()), R_total=float(R.sum()),
                profit_factor=float(gan / per) if per > 0 else None,
                salidas={k: int(v) for k, v in df["motivo"].value_counts().items()})


def cartera(ops: pd.DataFrame, fechas: list[str], c: dict) -> dict:
    """Resultado en % de una cartera: cada operación arriesga `riesgo_pct` del capital
    (tamaño = riesgo / distancia al stop), con tope de apalancamiento total del día."""
    if ops.empty:
        return {}
    o = ops.copy()
    o["peso"] = (c["riesgo_pct"] / o["riesgo_pct"].clip(lower=0.05))
    if c.get("exposicion_max"):
        o["peso"] = o["peso"].clip(upper=c["exposicion_max"])
    tot = o.groupby("fecha")["peso"].transform("sum")
    o["peso"] *= np.minimum(1.0, c["apalancamiento_max"] / tot)
    o["contrib"] = o["peso"] * o["ret_pct"] / 100
    dia = o.groupby("fecha")["contrib"].sum().reindex(sorted(set(fechas) | set(o["fecha"])), fill_value=0.0)
    curva = (1 + dia).cumprod()
    anios = max((pd.Timestamp(dia.index[-1]) - pd.Timestamp(dia.index[0])).days / 365.25, 1 / 252)
    dd = float((curva / curva.cummax() - 1).min())
    por_anio = (1 + dia).groupby(dia.index.str[:4]).prod() - 1
    return dict(rentabilidad_total=float(curva.iloc[-1] - 1), cagr=float(curva.iloc[-1] ** (1 / anios) - 1) if anios >= 0.5 else None,
                sharpe=float(dia.mean() / dia.std() * math.sqrt(252)) if dia.std() > 0 else None,
                max_caida=dd, por_anio={k: float(v) for k, v in por_anio.items()},
                curva_mensual={k: float(v) for k, v in curva.groupby(curva.index.str[:7]).last().items()})


def estudio_gainers(g: pd.DataFrame, subida_min: float) -> dict:
    if g.empty:
        return {}
    G = g[g["sube_dia"] >= subida_min]
    D = g[g["hueco"] >= 0.10]
    dias = g["fecha"].nunique()
    hora = pd.to_datetime(G["hora_maximo"], format="%H:%M").dt.hour * 60 + pd.to_datetime(G["hora_maximo"], format="%H:%M").dt.minute
    out = dict(
        dias=int(dias), top_gainers=int(len(G)), por_dia=float(len(G) / max(dias, 1)),
        visibles_apertura_5=float((G["hueco"] >= 0.05).mean()), visibles_apertura_10=float((G["hueco"] >= 0.10).mean()),
        visibles_0900_5=float((G["pm_hueco_0900"].fillna(0) >= 0.05).mean()),
        visibles_0900_10=float((G["pm_hueco_0900"].fillna(0) >= 0.10).mean()),
        maximo_antes_10=float((hora < 600).mean()), maximo_10_12=float(((hora >= 600) & (hora < 720)).mean()),
        maximo_tras_12=float((hora >= 720).mean()),
        huecos10=int(len(D)), huecos10_acaban_15=float((D["sube_dia"] >= subida_min).mean()) if len(D) else None,
        huecos10_cierran_bajo_apertura=float((D["apertura_a_cierre"] < 0).mean()) if len(D) else None,
        huecos10_apertura_cierre_mediana=float(D["apertura_a_cierre"].median()) if len(D) else None,
    )
    estr = {}
    for nombre, sub in {"todas (hueco ≥ 10 %)": D,
                        "precio < 5 $": D[D["cierre_ant"] < 5], "precio 5-20 $": D[(D["cierre_ant"] >= 5) & (D["cierre_ant"] < 20)],
                        "precio ≥ 20 $": D[D["cierre_ant"] >= 20],
                        "hueco 10-20 %": D[D["hueco"] < 0.20], "hueco 20-50 %": D[(D["hueco"] >= 0.20) & (D["hueco"] < 0.50)],
                        "hueco ≥ 50 %": D[D["hueco"] >= 0.50]}.items():
        s = sub.dropna(subset=["c0935_a_cierre"])
        if not len(s):
            continue
        r = s.dropna(subset=["reglasA_R"])
        estr[nombre] = dict(n=int(len(s)), comprar_0935_hasta_cierre_media=float(s["c0935_a_cierre"].mean()),
                            comprar_0935_hasta_cierre_mediana=float(s["c0935_a_cierre"].median()),
                            comprar_0935_gana=float((s["c0935_a_cierre"] > 0).mean()),
                            reglasA_R_medio=float(r["reglasA_R"].mean()) if len(r) else None,
                            reglasA_aciertos=float((r["reglasA_R"] > 0).mean()) if len(r) else None)
    out["huecos10_estrategias"] = estr
    if "motivo" in g:
        mot = {}
        for nombre, sub in {"top gainers": G, "huecos ≥ 10 %": D}.items():
            s = sub.dropna(subset=["motivo"])
            if len(s):
                mot[nombre] = {k: dict(n=int(len(x)), peso=float(len(x) / len(s)),
                                       apertura_a_cierre_media=float(x["apertura_a_cierre"].mean()),
                                       reglasA_R_medio=float(x["reglasA_R"].mean()) if x["reglasA_R"].notna().any() else None)
                               for k, x in s.groupby("motivo")}
        out["motivos"] = mot
    return out


def generar(carpeta: Path, cfg: dict) -> dict:
    g = pd.concat([pd.read_csv(f, converters={"simbolo": str}) for f in sorted(carpeta.glob("gainers-*.csv*"))], ignore_index=True) \
        if list(carpeta.glob("gainers-*.csv*")) else pd.DataFrame()
    o = pd.concat([pd.read_csv(f, converters={"simbolo": str}) for f in sorted(carpeta.glob("orb-*.csv*"))], ignore_index=True) \
        if list(carpeta.glob("orb-*.csv*")) else pd.DataFrame()
    fechas = sorted(set(g["fecha"]) if len(g) else set())
    res = dict(periodo=[fechas[0], fechas[-1]] if fechas else [], gainers=estudio_gainers(g, cfg["gainers"]["subida_min"]),
               orb={})
    for nombre in cfg["orb"]["variantes"]:
        sub = o[o["variante"] == nombre] if len(o) else o
        if sub is None or sub.empty:
            continue
        por_anio = {a: stats_ops(x) for a, x in sub.groupby(sub["fecha"].str[:4])}
        res["orb"][nombre] = dict(total=stats_ops(sub), compras=stats_ops(sub[sub["lado"] == "compra"]),
                                  ventas=stats_ops(sub[sub["lado"] == "venta"]), por_anio=por_anio,
                                  cartera=cartera(sub, fechas, cfg["cartera"][nombre]))
    return res


def markdown(res: dict, fecha: str) -> str:
    g, orb = res.get("gainers", {}), res.get("orb", {})
    per = " a ".join(res.get("periodo", [])) or "—"
    L = [f"# Backtest intradía: ORB y top gainers · datos de {per}", "",
         "*Informe automático (lo genera GitHub Actions con datos de Alpaca). La lectura en sencillo la añade Claude aparte.*", ""]
    if g:
        L += ["## Top gainers (suben ≥ +15 % en el día)", "",
              f"- Días estudiados: **{g['dias']}** · top gainers: **{g['top_gainers']}** (**{_num(g['por_dia'], 1)} al día**).",
              f"- Ya abrían con hueco ≥ +5 %: **{_pct(g['visibles_apertura_5'])}** · ≥ +10 %: **{_pct(g['visibles_apertura_10'])}**.",
              f"- A las 9:00 (premercado) ya subían ≥ +5 %: **{_pct(g['visibles_0900_5'])}** · ≥ +10 %: **{_pct(g['visibles_0900_10'])}**.",
              f"- Hora del máximo del día: antes de las 10:00 **{_pct(g['maximo_antes_10'])}**, 10-12 h **{_pct(g['maximo_10_12'])}**, después **{_pct(g['maximo_tras_12'])}** (hora de NY).",
              "", "### Las que abren con hueco ≥ +10 % (lo que se puede ver a tiempo)", "",
              f"- Casos: **{g['huecos10']}**. Acaban el día ≥ +15 %: **{_pct(g['huecos10_acaban_15'])}**. "
              f"Cierran por debajo de su apertura: **{_pct(g['huecos10_cierran_bajo_apertura'])}**. "
              f"Mediana apertura→cierre: **{_pct(g['huecos10_apertura_cierre_mediana'])}**.", "",
              "| Grupo | Casos | Comprar 9:35 y vender al cierre (media) | Mediana | % que gana | Reglas agente A (R medio) | % aciertos |",
              "|---|---|---|---|---|---|---|"]
        for k, v in g.get("huecos10_estrategias", {}).items():
            L.append(f"| {k} | {v['n']} | {_pct(v['comprar_0935_hasta_cierre_media'])} | {_pct(v['comprar_0935_hasta_cierre_mediana'])} | "
                     f"{_pct(v['comprar_0935_gana'], 0)} | {_num(v['reglasA_R_medio'])} | {_pct(v['reglasA_aciertos'], 0)} |")
        for grupo, mot in g.get("motivos", {}).items():
            L += ["", f"### Motivo según los titulares · {grupo} (muestra)", "",
                  "| Motivo | Casos | Peso | Apertura→cierre (media) | Reglas agente A (R medio) |", "|---|---|---|---|---|"]
            for k, v in sorted(mot.items(), key=lambda x: -x[1]["n"]):
                L.append(f"| {k} | {v['n']} | {_pct(v['peso'], 0)} | {_pct(v['apertura_a_cierre_media'])} | {_num(v['reglasA_R_medio'])} |")
    for nombre, v in orb.items():
        t, c = v["total"], v.get("cartera", {})
        L += ["", f"## ORB · variante «{nombre}»", "",
              f"- Operaciones: **{t['operaciones']}** · aciertos **{_pct(t.get('aciertos'), 0)}** · R medio **{_num(t.get('R_medio'), 3)}** · "
              f"profit factor **{_num(t.get('profit_factor'))}**.",
              f"- Solo compras: R medio {_num(v['compras'].get('R_medio'), 3)} ({v['compras']['operaciones']} ops) · "
              f"solo ventas: R medio {_num(v['ventas'].get('R_medio'), 3)} ({v['ventas']['operaciones']} ops).",
              f"- Cartera: rentabilidad total **{_pct(c.get('rentabilidad_total'), 0)}**, anual **{_pct(c.get('cagr'))}**, "
              f"Sharpe **{_num(c.get('sharpe'))}**, peor caída **{_pct(c.get('max_caida'))}**.", "",
              "| Año | Operaciones | Aciertos | R medio | Rentabilidad cartera |", "|---|---|---|---|---|"]
        for a, s in v["por_anio"].items():
            L.append(f"| {a} | {s['operaciones']} | {_pct(s.get('aciertos'), 0)} | {_num(s.get('R_medio'), 3)} | "
                     f"{_pct(c.get('por_anio', {}).get(a))} |")
    L += ["", f"_Generado el {fecha}. Costes incluidos: deslizamiento y coste por acción en cada lado. "
              "R = lo ganado o perdido en veces lo arriesgado (−1 R = saltó el stop)._"]
    return "\n".join(L) + "\n"


def guardar(res: dict, salida: Path, fecha: str) -> Path:
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = salida.parent / f"{fecha}-backtest-orb-gainers.md"
    md.write_text(markdown(res, fecha), encoding="utf-8")
    return md
