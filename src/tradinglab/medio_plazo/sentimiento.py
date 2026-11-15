"""Sentimiento de titulares de noticias (en inglés) con una lista de palabras PROPIA (sin licencias raras,
sin modelos pesados ni APIs de pago).

No es tan fino como un modelo de IA, pero sirve para dos cosas útiles:
  1. Ver de un vistazo si las noticias del último mes son buenas, malas o neutras.
  2. Cazar titulares de alarma (ampliación de capital, investigación, "going concern"...) que el análisis
     profundo tiene que leer sí o sí.
La IA (Claude) lee los titulares completos en el análisis profundo; esto solo es un primer filtro.
"""
from __future__ import annotations

import re

# (expresión, peso). Peso positivo = buena noticia para el accionista; negativo = mala.
POSITIVAS = [
    (r"\bbeats?\b", 2), (r"\btops? (estimates|expectations)\b", 2), (r"\braises? (guidance|outlook|forecast)\b", 3),
    (r"\bupgrade[sd]?\b", 2), (r"\b(price target|pt) (raised|increased|boosted)\b", 2), (r"\braises? .*price target\b", 2),
    (r"\brecord (revenue|sales|quarter|results)\b", 2), (r"\bfda approv", 3), (r"\bapprov(al|ed|es)\b", 1),
    (r"\bpositive (data|results|topline)\b", 3), (r"\bmet (its )?primary endpoint\b", 3), (r"\bbreakthrough\b", 1),
    (r"\b(wins?|awarded|secures?) .*(contract|order|deal)\b", 2), (r"\bpartnership\b", 1), (r"\bbuyback\b", 2),
    (r"\brepurchase\b", 2), (r"\bacquired by\b", 2), (r"\bto be acquired\b", 2), (r"\bdividend (increase|hike)\b", 2), (r"\b(raises?|increases?|boosts?) .*dividend\b", 2),
    (r"\boutperform\b", 1), (r"\bstrong (demand|growth|results)\b", 1), (r"\bexpands?\b", 1),
]
NEGATIVAS = [
    (r"\bmiss(es|ed)?\b", -2), (r"\bcuts? (guidance|outlook|forecast)\b", -3), (r"\blowers? (guidance|outlook)\b", -3),
    (r"\bdowngrade[sd]?\b", -2), (r"\b(price target|pt) (cut|lowered|reduced)\b", -2), (r"\blowers? .*price target\b", -2),
    (r"\bpublic offering\b", -3), (r"\b(stock|share|equity) offering\b", -3), (r"\bpriced? .*offering\b", -3),
    (r"\bat-the-market\b", -2), (r"\bdilut", -2), (r"\bgoing concern\b", -4), (r"\bdelist", -4),
    (r"\b(sec|doj|ftc) (probe|investigation|subpoena)\b", -3), (r"\binvestigation\b", -2), (r"\bclass action\b", -2),
    (r"\blawsuit\b", -1), (r"\bcomplete response letter\b", -4), (r"\bcrl\b", -3), (r"\bclinical hold\b", -4),
    (r"\bfail(s|ed)? to meet\b", -3), (r"\bdiscontinue[sd]?\b", -2), (r"\bhalts?\b", -2), (r"\brecall\b", -2),
    (r"\bresign(s|ed|ation)?\b", -1), (r"\blayoffs?\b", -1), (r"\bbankruptcy\b", -4), (r"\bchapter 11\b", -4),
    (r"\bshort seller\b", -2), (r"\brestate", -3), (r"\bmaterial weakness\b", -3), (r"\bdelay(s|ed)?\b", -1),
    (r"\bunderperform\b", -1), (r"\b(cuts?|suspends?|slashes) .*dividend\b", -2), (r"\bsell rating\b", -2), (r"\bplunges?\b", -1), (r"\btumbles?\b", -1),
]
# Titulares que hay que leer siempre (aunque el resto de noticias sean buenas).
ALARMAS = {
    "ampliación de capital": r"\b(public|stock|share|equity|registered direct) offering\b|\bpriced? .*offering\b|\bat-the-market\b",
    "duda sobre la continuidad (going concern)": r"\bgoing concern\b",
    "posible exclusión de bolsa": r"\bdelist",
    "investigación o demanda": r"\b(sec|doj|ftc) (probe|investigation|subpoena)\b|\bclass action\b",
    "rechazo o parón de la FDA": r"\bcomplete response letter\b|\bclinical hold\b|\bcrl\b",
    "quiebra": r"\bbankruptcy\b|\bchapter 11\b",
    "problemas contables": r"\brestate|\bmaterial weakness\b",
}
# Titulares de bufetes que anuncian demandas colectivas genéricas: ruido, no cuentan.
RUIDO = r"(shareholder alert|investor alert|reminds investors|law firm|lawsuit filed|rosen law|pomerantz|levi & korsinsky|bragar|faruqi|glancy|kessler topaz|schall law)"


def puntuar_titular(t: str) -> int:
    t = (t or "").lower()
    if re.search(RUIDO, t):
        return 0
    return sum(p for r, p in POSITIVAS + NEGATIVAS if re.search(r, t))


def sentimiento(titulares: list[str]) -> dict:
    """Devuelve nota de -100 (muy malas) a +100 (muy buenas), nº de titulares y alarmas encontradas."""
    vistos, puntos, alarmas = set(), [], []
    for t in titulares:
        k = (t or "").strip().lower()[:90]
        if not k or k in vistos:
            continue
        vistos.add(k)
        puntos.append(puntuar_titular(t))
        if not re.search(RUIDO, k):
            for nombre, r in ALARMAS.items():
                if re.search(r, t.lower()) and nombre not in alarmas:
                    alarmas.append(nombre)
    if not puntos:
        return dict(sent_nota=None, sent_titulares=0, sent_alarmas=[])
    con_senal = [p for p in puntos if p]
    nota = 0.0
    if con_senal:
        # media acotada a ±4 por titular, escalada a ±100, y suavizada si hay pocos titulares con señal
        media = sum(max(-4, min(4, p)) for p in con_senal) / len(con_senal) / 4 * 100
        nota = media * min(1.0, len(con_senal) / 3)
    etiqueta = "buenas" if nota >= 20 else ("malas" if nota <= -20 else "neutras")
    return dict(sent_nota=round(nota), sent_etiqueta=etiqueta, sent_titulares=len(puntos),
                sent_positivos=sum(1 for p in puntos if p > 0), sent_negativos=sum(1 for p in puntos if p < 0),
                sent_alarmas=alarmas)


def aplicar(filas: list[dict]) -> int:
    """Calcula el sentimiento con las noticias ya descargadas (Finnhub + Alpaca) de cada fila."""
    n = 0
    for f in filas:
        x = f.get("extra") or {}
        tit = [i.get("titulo") for i in (x.get("noticias_alpaca") or []) + (x.get("noticias") or []) if i.get("titulo")]
        if not tit:
            continue
        s = sentimiento(tit)
        x.update(s)
        f["extra"] = x
        for a in s["sent_alarmas"]:
            texto = f"Noticia reciente: {a} (leer antes de decidir)"
            if texto not in f.setdefault("banderas", []):
                f["banderas"].append(texto)   # aviso visible, sin restar puntos (solo se mira en las mejores)
        n += 1
    return n
