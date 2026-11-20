"""Agente C: segunda batería de doce hipótesis EUR/USD M5.

Solo investigación: NINGUNA señal puede usarse para enviar órdenes.
Parámetros congelados el 17-11-2026 antes de iniciar pruebas plurianuales.
Al usar datos BID/ASK reales calculamos spread, SL/TP, slippage, comisiones y gap.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

PIP = 0.0001
NAMES = (
    "dema_band", "trend_continuation", "range_zfade", "swing_failure",
    "inside_bar", "impulse_fade", "impulse_follow", "micro_pullback",
    "tokyo_post_fix", "london_post_fix", "ecb_post_fix", "pre_london_fix",
)
RR = {
    "range_zfade": 1.25, "swing_failure": 1.25, "impulse_fade": 1.25,
    "tokyo_post_fix": 1.4, "london_post_fix": 1.4, "ecb_post_fix": 1.4,
    "pre_london_fix": 1.4, "dema_band": 1.6, "micro_pullback": 1.6,
    "trend_continuation": 1.8, "inside_bar": 1.8, "impulse_follow": 1.8,
}


def prepare(data: pd.DataFrame) -> pd.DataFrame:
    f = data.copy()
    f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True)
    f = f.sort_values("timestamp").reset_index(drop=True)
    required = ("open", "high", "low", "close", "spread_pips")
    if f["timestamp"].duplicated().any() or f[list(required)].isna().any().any():
        raise ValueError("Datos con nulos o timestamps duplicados")
    if not ((f.low <= f.open) & (f.low <= f.close) &
            (f.high >= f.open) & (f.high >= f.close) &
            (f.spread_pips > 0)).all():
        raise ValueError("OHLC o spreads inválidos")
    c, h, l, o = f.close, f.high, f.low, f.open
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    f["atr"] = tr.rolling(14, min_periods=14).mean()
    f["atrlong"] = tr.rolling(100, min_periods=100).mean()
    for span in (12, 48, 144):
        f[f"ema{span}"] = c.ewm(span=span, adjust=False).mean()
    for window in (12, 24):
        f[f"hi{window}"] = h.shift(1).rolling(window).max()
        f[f"lo{window}"] = l.shift(1).rolling(window).min()
    f["z48"] = (c-c.rolling(48).mean())/c.rolling(48).std(ddof=0)
    f["eff24"] = (c-c.shift(24)).abs()/c.diff().abs().rolling(24).sum()
    fast = c.ewm(span=5, adjust=False).mean()
    slow = c.ewm(span=12, adjust=False).mean()
    f["dema5"] = 2*fast-fast.ewm(span=5, adjust=False).mean()
    f["dema12"] = 2*slow-slow.ewm(span=12, adjust=False).mean()
    f["candle_size"] = (c-o).abs()
    f["wick_up"] = h-np.maximum(o,c)
    f["wick_down"] = np.minimum(o,c)-l
    f["rvol"] = f.atr/f.atrlong
    ny = f.timestamp.dt.tz_convert("America/New_York")
    mins = ny.dt.hour*60+ny.dt.minute
    # Dos horas + 10 minutos de margen antes del rollover, sin fin de semana.
    f["allowed"] = ~((mins >= 16*60+45-130)&(mins < 18*60+15)) & (ny.dt.dayofweek < 5)
    london = f.timestamp.dt.tz_convert("Europe/London")
    tokyo = f.timestamp.dt.tz_convert("Asia/Tokyo")
    frankfurt = f.timestamp.dt.tz_convert("Europe/Berlin")
    f["london_h"], f["london_m"] = london.dt.hour, london.dt.minute
    f["tokyo_h"], f["tokyo_m"] = tokyo.dt.hour, tokyo.dt.minute
    f["frank_h"], f["frank_m"] = frankfurt.dt.hour, frankfurt.dt.minute
    return f


def signals(f: pd.DataFrame) -> pd.DataFrame:
    """Señales exclusivas de velas CERRADAS; nunca se inspecciona t+1."""
    z = pd.DataFrame(index=f.index)
    c,o,h,l,a = f.close,f.open,f.high,f.low,f.atr
    trendup = (f.ema12>f.ema48)&(f.ema48>f.ema144)
    trenddown = (f.ema12<f.ema48)&(f.ema48<f.ema144)
    volok = (f.rvol.between(.60,2.0)) & (f.spread_pips<1.2)
    def set_sign(long, short):
        ans = pd.Series(0, index=f.index, dtype="int8")
        ans.loc[long if not isinstance(long,bool) else pd.Series(long,index=f.index)] = 1
        ans.loc[short if not isinstance(short,bool) else pd.Series(short,index=f.index)] = -1
        return ans
    gap = (f.dema5-f.dema12)/a
    z["dema_band"] = set_sign((gap>.16)&(gap.shift(1)<=.16)&(c>f.ema48)&volok,
                              (gap<-.16)&(gap.shift(1)>=-.16)&(c<f.ema48)&volok)
    z["trend_continuation"] = set_sign(
        trendup&(c>f.hi12)&(c.shift(1)<=f.hi12.shift(1))&volok,
        trenddown&(c<f.lo12)&(c.shift(1)>=f.lo12.shift(1))&volok)
    z["range_zfade"] = set_sign(
        (f.z48.shift(1)<-1.6)&(f.z48>f.z48.shift(1))&(c>o)&(f.eff24<.30)&volok,
        (f.z48.shift(1)>1.6)&(f.z48<f.z48.shift(1))&(c<o)&(f.eff24<.30)&volok)
    z["swing_failure"] = set_sign(
        (l<f.lo24)&(c>f.lo24)&(c>o)&(f.candle_size<1.2*a)&volok,
        (h>f.hi24)&(c<f.hi24)&(c<o)&(f.candle_size<1.2*a)&volok)
    inside = (h.shift(1)<h.shift(2))&(l.shift(1)>l.shift(2))
    z["inside_bar"] = set_sign(inside&(c>h.shift(2))&(c>f.ema48)&volok,
                                inside&(c<l.shift(2))&(c<f.ema48)&volok)
    z["impulse_fade"] = set_sign(
        (f.wick_down>1.4*a)&(c>o)&(f.wick_up<.5*a)&volok,
        (f.wick_up>1.4*a)&(c<o)&(f.wick_down<.5*a)&volok)
    z["impulse_follow"] = set_sign(
        (f.candle_size.shift(1)>1.4*a.shift(1))&(c.shift(1)>o.shift(1))&(c>h.shift(1))&volok,
        (f.candle_size.shift(1)>1.4*a.shift(1))&(c.shift(1)<o.shift(1))&(c<l.shift(1))&volok)
    pos,neg = c.diff().gt(0),c.diff().lt(0)
    z["micro_pullback"] = set_sign(
        pos.shift(1).rolling(3).sum().eq(3)&neg&trendup&volok,
        neg.shift(1).rolling(3).sum().eq(3)&pos&trenddown&volok)
    # Estructura macro publicada, pero nunca se asume que sobreviva a comisiones.
    z["tokyo_post_fix"] = set_sign((f.tokyo_h==9)&(f.tokyo_m==55)&volok, False)
    z["london_post_fix"] = set_sign((f.london_h==16)&(f.london_m==0)&volok, False)
    z["ecb_post_fix"] = set_sign((f.frank_h==14)&(f.frank_m==15)&volok, False)
    z["pre_london_fix"] = set_sign(False,(f.london_h==15)&(f.london_m==0)&volok)
    z.loc[:200, :] = 0
    z.loc[~f.allowed,:] = 0
    return z


def simulate(f: pd.DataFrame, signals_df: pd.DataFrame, *, cost_multiplier: float = 1.0) -> dict:
    """Stops conservadores; next-open y BID/ASK aproximado por OHLC.

    Cada estrategia opera de forma independiente sin posiciones simultáneas
    dentro de ella. Reportar cada una por separado, no sumar como cartera real.
    """
    if not (1 <= cost_multiplier <= 3):
        raise ValueError("Coste multiplicador fuera de 1..3")
    spread=f.spread_pips.to_numpy(float)
    ts=f.timestamp.to_numpy()
    open_=f.open.to_numpy(float)
    hi=f.high.to_numpy(float)
    lo=f.low.to_numpy(float)
    atr=f.atr.to_numpy(float)
    delta=np.diff(ts).astype("timedelta64[m]").astype(int)
    out={}
    for name in signals_df:
        raw=signals_df[name].to_numpy(np.int8)
        rows=[]
        i=201
        while i < len(f)-25:
            side=int(raw[i])
            if not side or delta[i]!=5 or spread[i+1]>1.2:
                i+=1
                continue
            stop_pips=float(np.clip(1.25*atr[i]/PIP,4.,30.))
            if not np.isfinite(stop_pips) or stop_pips<4*spread[i+1]:
                i+=1
                continue
            start=i+1
            entry=open_[start]+side*(spread[start]/2 + 0.15*cost_multiplier)*PIP
            stop=entry-side*stop_pips*PIP
            target=entry+side*RR[name]*stop_pips*PIP
            exit_price=None;why=""
            for k in range(start,min(len(f),start+25)):
                if k>start and delta[k-1]!=5:
                    exit_price=open_[k]-side*(spread[k]/2+0.15*cost_multiplier)*PIP
                    why="gap"
                    break
                if k==start+24:
                    exit_price=open_[k]-side*(spread[k]/2+0.15*cost_multiplier)*PIP
                    why="120min"
                    break
                half=spread[k]*PIP/2
                adverse=lo[k]-half if side==1 else hi[k]+half
                favorable=hi[k]-half if side==1 else lo[k]+half
                hit_stop=adverse<=stop if side==1 else adverse>=stop
                hit_take=favorable>=target if side==1 else favorable<=target
                if hit_stop:
                    exit_price=min(stop,open_[k]-half) if side==1 else max(stop,open_[k]+half)
                    exit_price-=side*0.15*cost_multiplier*PIP
                    why="stop"
                    break
                if hit_take:
                    exit_price=target-side*0.15*cost_multiplier*PIP
                    why="target"
                    break
            if exit_price is None:
                break
            pips=side*(exit_price-entry)/PIP-0.25*cost_multiplier
            rows.append([ts[start],ts[k],pips/stop_pips,pips,why,side])
            i=k+1
        out[name]=pd.DataFrame(rows, columns=["start","end","R","pips","reason","side"])
    return out


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"operations":0, "expectancy_R":None,"profit_factor":None,
                "win_rate":None,"total_R":0,"max_dd_R":None}
    r=df.R.to_numpy(float)
    wins=r[r>0];loss=r[r<0]
    cum=np.cumsum(r)
    dd=np.maximum.accumulate(np.r_[0.,cum])[1:]-cum
    return {"operations":len(r),"expectancy_R":round(float(r.mean()),5),
            "profit_factor":round(float(wins.sum()/-loss.sum()),5) if len(loss) else None,
            "win_rate":round(float((r>0).mean()),5),
            "total_R":round(float(r.sum()),4),"max_dd_R":round(float(dd.max()),4)}


def evaluate(csv_path: str, *, cost_multiplier: float = 1.0,
             start_valid: str | None = None, end_valid: str | None = None) -> dict:
    """Subset por rango de fecha de entrada, usando 200 barras previas calentamiento."""
    f=prepare(pd.read_csv(csv_path))
    z=signals(f)
    out={}
    trades=simulate(f,z,cost_multiplier=cost_multiplier)
    for name,t in trades.items():
        if start_valid is not None:
            t=t[t.start>=pd.to_datetime(start_valid,utc=True)]
        if end_valid is not None:
            t=t[t.start<pd.to_datetime(end_valid,utc=True)]
        out[name]=summarize(t)
    return {"source":str(csv_path),"bars":len(f),"date_start":str(f.timestamp.iloc[0]),
            "date_end":str(f.timestamp.iloc[-1]),"cost_multiplier":cost_multiplier,
            "strategies":out, "status":"EXPLORATORY_RESEARCH_NOT_APPROVED"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--output",default="investigacion/fx/research-v2.json")
    parser.add_argument("--cost-multiplier",type=float,default=1)
    parser.add_argument("--start-valid",default=None)
    parser.add_argument("--end-valid",default=None)
    args=parser.parse_args()
    output=evaluate(args.csv,cost_multiplier=args.cost_multiplier,
                    start_valid=args.start_valid,end_valid=args.end_valid)
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,indent=2),encoding="utf-8")
    print(json.dumps(output,indent=2))


if __name__=="__main__":
    main()
