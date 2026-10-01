"""Controlled ablation: one change at a time against the current rules, with a
pre-registered decision rule. Portfolio is marked to market daily; calls are
modelled with Black-Scholes (IV ~ 1.10 x 20-day realized vol at each day,
so IV moves with volatility), theta, bid/ask spread and slippage.

Adopt a candidate only if ALL hold:
  1. explore Sharpe >= incumbent explore Sharpe + 0.10
  2. holdout Sharpe >= incumbent holdout Sharpe   (survives out of sample; veto only)
  3. numeric settings: a neighbouring value also clears rule 1 (plateau, not a spike)
Ranking among qualifiers uses explore Sharpe only.

Usage: PYTHONPATH=.. python ablation.py
"""
from __future__ import annotations

import math
import pickle
from dataclasses import replace
from multiprocessing import Pool

import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm

from common import CACHE, ROOT, SPLIT, load
from src.strategy import Params, _sma_daily_prev, _vwap, simulate

CFG = yaml.safe_load((ROOT / "config.yaml").read_text())["strategies"][0]
POOL = CFG["universe"]["pool"]
EARN = pickle.load(open(CACHE / "earnings.pickle", "rb"))
SPY, QQQ = load("SPY"), load("QQQ")
DATA = {t: load(t) for t in POOL}
COST = 0.0005
MIN_DOLLAR_VOL = 3e8  # 20-day average daily dollar volume

# ------------------------------------------------------------------ daily data
def daily(df):
    g = df.groupby(df.index.normalize())
    d = pd.DataFrame({"close": g["close"].last(), "dv": (df["close"] * df["volume"]).groupby(df.index.normalize()).sum()})
    d.index = d.index.tz_localize(None)
    return d

DAY = {t: daily(df) for t, df in DATA.items()}
SPYD = daily(SPY)
RV = {t: d["close"].pct_change().rolling(20).std() * math.sqrt(252) for t, d in DAY.items()}  # known at that close
RVMED = {t: r.rolling(250, min_periods=60).median() for t, r in RV.items()}

# ------------------------------------------------------------------ universe
def members(mode: str, k: int = 10) -> dict:
    close = pd.DataFrame({t: d["close"] for t, d in DAY.items()})
    dv = pd.DataFrame({t: d["dv"] for t, d in DAY.items()}).rolling(20).mean()
    spy = SPYD["close"]
    out = {}
    for ms in pd.date_range("2024-01-01", "2026-10-01", freq="MS"):
        c, s = close[close.index < ms], spy[spy.index < ms]
        if len(c) < 130:
            continue
        r = c.pct_change()
        vol = r.tail(120).std()
        mom = c.iloc[-1] / c.iloc[-121] - 1
        rs = (c.iloc[-1] / c.iloc[-21] - 1) - (s.iloc[-1] / s.iloc[-21] - 1)
        liquid = dv[dv.index < ms].iloc[-1] >= MIN_DOLLAR_VOL
        ranks = {"vol": vol.rank(ascending=False), "mom": mom.rank(ascending=False),
                 "rs": rs.rank(ascending=False)}
        score = {"vol": ranks["vol"], "mom": ranks["mom"], "rs": ranks["rs"],
                 "volmom": (ranks["vol"] + ranks["mom"]) / 2,
                 "combo": (ranks["vol"] + ranks["mom"] + ranks["rs"]) / 3}[mode]
        score = score[liquid & score.notna()]
        out[(ms.year, ms.month)] = set(score.sort_values().index[:k])
    return out

MEMBERS = {m: members(m) for m in ("vol", "mom", "volmom", "rs", "combo")}

# ------------------------------------------------------------------ regime labels
def regime_series():
    p = Params()
    ema = SPY["close"].ewm(span=21, adjust=False).mean()
    vw = _vwap(SPY, "week")
    a = (ema > vw).astype(int) + (SPY["close"] > _sma_daily_prev(SPY, 50)).astype(int)
    return a.map({2: "bull", 1: "neutral", 0: "bear"}).shift(1)  # known at the signal bar's close

REGIME = regime_series()

# ------------------------------------------------------------------ options model
def bs_call(S, K, T, v, r=0.04):
    T = np.maximum(T, 1e-6)
    d1 = (np.log(S / K) + (r + v * v / 2) * T) / (v * np.sqrt(T))
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d1 - v * np.sqrt(T))


def strike_for(S, T, v, delta, r=0.04):
    return S * np.exp(-norm.ppf(delta) * v * np.sqrt(T) + (r + v * v / 2) * T)


def half_spread(delta, dte):
    hs = {0.65: 0.020, 0.75: 0.015, 0.85: 0.010}[delta]
    return hs + (0.005 if dte < 21 else 0.0)

# ------------------------------------------------------------------ one variant
def run_variant(v: dict) -> dict:
    p = Params(**{**CFG["params"], **v.get("params", {})})
    mem = MEMBERS[v.get("universe", "vol")]
    trades = []
    for t in POOL:
        tr = simulate(DATA[t], p, cost=COST, market=SPY, events=EARN.get(t), market2=QQQ)
        for x in tr:
            et = x["entry_time"]
            if t in mem.get((et.year, et.month), ()):
                x["ticker"] = t
                trades.append(x)
    tr = pd.DataFrame(trades)
    tr["regime"] = [REGIME.asof(e) for e in tr.entry_time]
    if v.get("regime_size"):
        tr["size"] = tr.regime.map(v["regime_size"]).fillna(0.0)
    else:
        tr["size"] = 1.0
    # position weight (fraction of account at entry)
    w = np.full(len(tr), 0.10)
    if v.get("sizing") == "voladj":
        rv0 = np.array([RV[t].asof(e.tz_localize(None).normalize() - pd.Timedelta(days=1))
                        for t, e in zip(tr.ticker, tr.entry_time)])
        med = np.nanmedian(rv0)
        w = 0.10 * np.clip(med / rv0, 0.5, 1.5)
    tr["w"] = w * tr["size"]
    tr = tr[tr.w > 0].reset_index(drop=True)
    opt = v.get("option", {"dte": 38, "delta": 0.65})
    daily_stock, daily_opt, opt_ret = {}, {}, []
    for x in tr.itertuples():
        d = DAY[x.ticker]["close"]
        d0, d1 = x.entry_time.tz_localize(None).normalize(), x.exit_time.tz_localize(None).normalize()
        path = d[(d.index >= d0) & (d.index < d1)]
        prices = [x.entry] + list(path.values) + [x.exit]
        dates = list(path.index) + [d1]
        # stock
        for i, day in enumerate(dates):
            r = prices[i + 1] / prices[i] - 1 - (COST if i == 0 else 0) - (COST if i == len(dates) - 1 else 0)
            daily_stock[day] = daily_stock.get(day, 0.0) + x.w * r
        # call
        rv0 = RV[x.ticker].asof(d0 - pd.Timedelta(days=1))
        med = RVMED[x.ticker].asof(d0 - pd.Timedelta(days=1))
        if not (rv0 > 0) or (med > 0 and rv0 > 2.0 * med):  # abnormal IV: no option trade
            opt_ret.append(np.nan)
            continue
        T0, dl = opt["dte"] / 365, opt["delta"]
        iv0 = 1.10 * rv0
        K = strike_for(x.entry, T0, iv0, dl)
        hs = half_spread(dl, opt["dte"]) + 0.005  # + slippage
        vals = [bs_call(x.entry, K, T0, iv0) * (1 + hs)]
        for i, day in enumerate(dates):
            ivd = 1.10 * RV[x.ticker].asof(day - pd.Timedelta(days=1))
            Td = T0 - (day - d0).days / 365
            vv = bs_call(prices[i + 1], K, Td, ivd if ivd > 0 else iv0)
            vals.append(vv * (1 - hs) if i == len(dates) - 1 else vv)
        scale = x.w / (dl * x.entry)  # same delta exposure as the share position
        for i, day in enumerate(dates):
            daily_opt[day] = daily_opt.get(day, 0.0) + scale * (vals[i + 1] - vals[i])
        opt_ret.append(vals[-1] / vals[0] - 1)
    tr["opt_ret"] = opt_ret
    cal = pd.bdate_range(tr.entry_time.min().tz_localize(None).normalize(), SPYD.index[-1])
    S = pd.Series(daily_stock).reindex(cal, fill_value=0.0)
    O = pd.Series(daily_opt).reindex(cal, fill_value=0.0)
    out = {"name": v["name"], "step": v.get("step", ""), "trades": tr, "S": S, "O": O}
    split = SPLIT.tz_localize(None)
    for nm, sel_t, sel_d in (("x", tr.entry_time < SPLIT, S.index < split),
                             ("h", tr.entry_time >= SPLIT, S.index >= split)):
        out[nm] = metrics(tr[sel_t], S[sel_d], O[sel_d])
    return out


def curve_stats(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    yrs = max(len(r) / 252, 1e-9)
    dd = (eq / eq.cummax() - 1).min()
    sd, dn = r.std(), r[r < 0].std()
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    return dict(total=100 * (eq.iloc[-1] - 1), cagr=100 * cagr, maxdd=100 * dd,
                sharpe=(r.mean() / sd * math.sqrt(252)) if sd > 0 else 0.0,
                sortino=(r.mean() / dn * math.sqrt(252)) if dn > 0 else 0.0,
                rr=(cagr / -dd) if dd < 0 else 0.0)


def metrics(tr: pd.DataFrame, S: pd.Series, O: pd.Series) -> dict:
    r = tr.ret.to_numpy()
    win, loss = r[r > 0], r[r <= 0]
    m = dict(n=len(r), win=100 * len(win) / max(len(r), 1), avg=100 * r.mean() if len(r) else 0,
             avg_w=100 * win.mean() if len(win) else 0, avg_l=100 * loss.mean() if len(loss) else 0,
             pf=win.sum() / -loss.sum() if loss.sum() < 0 else float("inf"),
             largest=100 * r.min() if len(r) else 0, days=tr.days.mean() if len(r) else 0,
             mfe=100 * tr.mfe.mean() if len(r) else 0, mae=100 * tr.mae.mean() if len(r) else 0,
             opt_avg=100 * np.nanmean(tr.opt_ret) if len(r) else 0)
    m.update({f"s_{k}": v for k, v in curve_stats(S).items()})
    m.update({f"o_{k}": v for k, v in curve_stats(O).items()})
    return m

# ------------------------------------------------------------------ the steps
def P(**kw):
    return {"params": kw}


STEPS = [
    ("1 universe", [("vol (current)", {}), ("momentum", {"universe": "mom"}),
                    ("vol+momentum", {"universe": "volmom"}), ("rel. strength 20d", {"universe": "rs"}),
                    ("vol+mom+RS", {"universe": "combo"})], None),
    ("2a entry", [("cross (current)", {}), ("EMA>VWAP state", P(entry="state")),
                  ("cross + rising VWAP", P(entry="cross_rising")), ("cross + price>VWAP", P(entry="cross_price")),
                  ("cross by 0.25 ATR", P(entry_atr=0.25)), ("cross by 0.5 ATR", P(entry_atr=0.5)),
                  ("cross by 1.0 ATR", P(entry_atr=1.0)), ("2 closes confirm", P(confirm_bars=2))], "entry_atr"),
    ("2b EMA length", [("EMA21 (current)", {}), ("EMA9", P(ema=9)), ("EMA13", P(ema=13)), ("EMA34", P(ema=34))], "ema"),
    ("3 market regime", [("SPY EMA>VWAP (current)", {}), ("+ SPY VWAP rising", P(regime="spyvwr")),
                         ("+ QQQ EMA>VWAP", P(regime="spyvw+qqqvw")), ("no regime filter", P(regime="")),
                         ("sized bull 1 / neutral .5 / bear 0", {"params": {"regime": ""},
                          "regime_size": {"bull": 1.0, "neutral": 0.5, "bear": 0.0}})], None),
    ("4 relative strength", [("off (current)", {}), ("RS 5d > 0", P(rs=5)), ("RS 10d > 0", P(rs=10)),
                             ("RS 20d > 0", P(rs=20))], "rs"),
    ("5 min hold", [("7 bars (current)", {})] + [(f"{b} bars", P(min_bars=b)) for b in (0, 2, 4, 6, 8, 10, 12)],
     "min_bars"),
    ("6 exit", [("EMA21<VWAP (current)", {}), ("price<VWAP", P(exit="close_vwap")), ("EMA9<VWAP", P(exit="ema9")),
                ("EMA<VWAP 2 closes", P(exit="cross2")), ("EMA<VWAP + VWAP falling", P(exit="cross_falling")),
                ("ATR trail 3x", P(exit="trail", trail_k=3.0))], None),
    ("7 stop", [("6 ATR emergency (current)", {}), ("2 ATR", P(stop_atr=2.0)), ("2.5 ATR", P(stop_atr=2.5)),
                ("3 ATR", P(stop_atr=3.0)), ("3.5 ATR", P(stop_atr=3.5)), ("4 ATR", P(stop_atr=4.0)),
                ("no hard stop", P(stop_atr=0.0))], "stop_atr"),
    ("8 Monday", [("exit grace 2 (current)", {}), ("no entries first 2 Monday hours", P(entry_grace=2)),
                  ("Monday entries need confirmation", P(mon_mode="confirm"))], None),
    ("9 earnings window", [("2 days (current)", {}), ("1 day", P(earn_skip=1)), ("3 days", P(earn_skip=3)),
                           ("5 days", P(earn_skip=5)), ("none", P(earn_skip=0))], "earn_skip"),
    ("10 sizing", [("equal 10% (current)", {}), ("volatility-adjusted", {"sizing": "voladj"})], None),
]
OPTS = [(d, dl) for d in (17, 25, 38) for dl in (0.65, 0.75, 0.85)]


def merge(a: dict, b: dict) -> dict:
    out = {**a, **{k: v for k, v in b.items() if k != "params"}}
    out["params"] = {**a.get("params", {}), **b.get("params", {})}
    return out


if __name__ == "__main__":
    log, inc = [], {"name": "current"}
    pool = Pool(8)
    base = run_variant(inc)
    rows = []
    for step, cands, numkey in STEPS:
        vs = [merge(inc, c) | {"name": n, "step": step} for n, c in cands]
        res = pool.map(run_variant, vs)
        I = res[0]  # first candidate == incumbent
        ok = []
        for v, r in zip(vs, res):
            rows.append(r)
            if r is I:
                continue
            c1 = r["x"]["s_sharpe"] >= I["x"]["s_sharpe"] + 0.10
            c2 = r["h"]["s_sharpe"] >= I["h"]["s_sharpe"]
            c3 = True
            if numkey and numkey in v.get("params", {}):
                eff = lambda vv: getattr(Params(**{**CFG["params"], **inc.get("params", {}), **vv.get("params", {})}), numkey)
                grid = [(eff(vv), rr) for vv, rr in zip(vs, res) if vv is vs[0] or numkey in vv.get("params", {})]
                vals = sorted({g[0] for g in grid})
                i = vals.index(eff(v))
                nb = {vals[j] for j in (i - 1, i + 1) if 0 <= j < len(vals)}
                c3 = any(rr["x"]["s_sharpe"] >= I["x"]["s_sharpe"] + 0.10 for val, rr in grid if val in nb and rr is not I)
            r["verdict"] = "ADOPT?" if (c1 and c2 and c3) else ("fails OOS" if c1 and not c2 else
                                                               "lone spike" if c1 and c2 and not c3 else "no gain")
            if c1 and c2 and c3:
                ok.append((v, r))
        I["verdict"] = "incumbent"
        if ok:
            v, r = max(ok, key=lambda vr: vr[1]["x"]["s_sharpe"])
            r["verdict"] = "ADOPTED"
            inc = {k: val for k, val in v.items() if k not in ("name", "step")}
            log.append(f"{step}: adopted **{v['name']}** (explore Sharpe {I['x']['s_sharpe']:.2f} → {r['x']['s_sharpe']:.2f}, "
                       f"holdout {I['h']['s_sharpe']:.2f} → {r['h']['s_sharpe']:.2f})")
        else:
            log.append(f"{step}: kept current")
    final = run_variant(inc | {"name": "final"})
    # options: choose DTE/delta on explore options Sharpe, holdout as veto
    optres = pool.map(run_variant, [inc | {"name": f"{d}DTE Δ{dl}", "step": "11 options", "option": {"dte": d, "delta": dl}}
                                    for d, dl in OPTS])
    cur_opt = next(r for r in optres if r["name"] == "38DTE Δ0.65")
    best_opt = max(optres, key=lambda r: r["x"]["o_sharpe"])
    if not (best_opt["x"]["o_sharpe"] >= cur_opt["x"]["o_sharpe"] + 0.10 and best_opt["h"]["o_sharpe"] >= cur_opt["h"]["o_sharpe"]):
        best_opt = cur_opt
    pool.close()
    pickle.dump({"base": base, "rows": rows, "final": final, "inc": inc, "log": log, "optres": optres,
                 "best_opt": best_opt["name"]}, open(ROOT / "research" / "ablation.pickle", "wb"))
    for line in log:
        print(line)
    print("options:", best_opt["name"])
    print("final:", inc)
