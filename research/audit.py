"""Profitability audit of the live swing rule on the research cache (Yahoo 1h).

BEFORE baseline, reproduction of reports/backtest.md, costs and late fills,
benchmarks, selection checks, and the options model next to the live scanner.
Writes reports/audit_backtest.md and reports/audit_trades.csv. Changes nothing.

Periods (entry time): explore < 2025-07-01 <= holdout < 2026-10-02 <= forward.
The ablation of 1 Oct 2026 used the holdout as a veto, so the holdout is no
longer untouched; only the forward weeks (bars fetched 17 Oct 2026) are.

Usage: python research/audit.py   (needs research/cache from research/fetch.py)
"""
import json
import math
import sys

import numpy as np
import pandas as pd

from common import ROOT, SPLIT, Params, load, noise_floor, stats
from common import _EARN
from final import CFG, K, LB, P, option_ret, option_ret_v1
from volsel import EXCLUDE, vol_ranks
from src.strategy import simulate

NY = "America/New_York"
FWD = pd.Timestamp("2026-10-02", tz=NY)
REPRO_END = pd.Timestamp("2026-10-01 16:00", tz=NY)   # reports/backtest.md was run on 1 Oct
POOL = [t for t in CFG["strategies"][0]["universe"]["pool"] if t not in EXCLUDE]
OPT = CFG["options"]
COSTS = {"0.05% a side (realistic)": 0.0005, "0.10% a side (stressed)": 0.0010, "0.20% a side (harsh)": 0.0020}
PUBLISHED = {"explore": (179, 61.5, 2.38), "holdout": (215, 56.7, 1.48)}   # reports/backtest.md


def period(t):
    return "explore" if t < SPLIT else "holdout" if t < FWD else "forward"


def spy():
    return load("SPY")


def trades(p: Params, cost: float, end=None, pool=POOL, k=K) -> pd.DataFrame:
    """The live rule on the volatility universe, exactly as research/final.py builds it."""
    S = spy() if end is None else spy()[spy().index <= end]
    ranks = vol_ranks(LB, pool)
    out = []
    for t in pool:
        df = load(t) if end is None else load(t)[load(t).index <= end]
        tr = pd.DataFrame(simulate(df, p, cost=cost, market=S, events=_EARN.get(t)))
        if not len(tr):
            continue
        tr["ticker"] = t
        a = S["open"].reindex(pd.DatetimeIndex(tr.entry_time)).to_numpy()
        b = S["open"].reindex(pd.DatetimeIndex(tr.exit_time)).to_numpy()
        tr["spy_ret"] = b / a - 1
        out.append(tr)
    tr = pd.concat(out, ignore_index=True)
    m = tr.entry_time.map(lambda x: pd.Timestamp(x.year, x.month, 1) + pd.offsets.MonthEnd(0))
    tr["rank"] = [ranks.at[a, t] if a in ranks.index else np.nan for a, t in zip(m, tr.ticker)]
    tr = tr[tr["rank"] <= k].copy()
    tr["period"] = tr.entry_time.map(period)
    tr["excess"] = tr.ret - tr.spy_ret
    return tr.sort_values("entry_time").reset_index(drop=True)


def late(tr: pd.DataFrame, bars: int = 1) -> pd.DataFrame:
    """Same trades, entry and cross/earnings exits filled `bars` hourly bars later
    (stops are resting orders and keep their fill). A stress bound for a signal
    acted on late; the 17-minute live delay is measured on 15-minute bars by
    research/audit_live.py."""
    out = tr.copy()
    for i, r in tr.iterrows():
        d = load(r.ticker)
        ix = d.index
        j = ix.get_indexer([r.entry_time])[0]
        e = d["open"].iloc[min(j + bars, len(d) - 1)]
        x = r.exit
        if r.reason not in ("stop", "open"):
            k = ix.get_indexer([r.exit_time])[0]
            x = d["open"].iloc[min(k + bars, len(d) - 1)]
        cost = (r.side * (r.exit / r.entry - 1) - r.ret) / 2
        out.at[i, "ret"] = r.side * (x / e - 1) - 2 * cost
    return out


def portfolio(tr: pd.DataFrame, col="ret", slot=1.0 / K, start=None, end=None) -> dict:
    """10% of equity per position, P&L booked at exit (research/final.py's curve)."""
    if not len(tr):
        return dict(total=0.0, dd=0.0)
    days = pd.date_range((start or tr.entry_time.min()).tz_localize(None).normalize(),
                         (end or tr.exit_time.max()).tz_localize(None).normalize(), freq="B")
    pnl = tr.groupby(tr.exit_time.dt.tz_localize(None).dt.normalize())[col].sum()
    e, eq = 1.0, []
    for d in days:
        e *= 1 + slot * pnl.get(d, 0.0)
        eq.append(e)
    s = pd.Series(eq, index=days)
    return dict(total=100 * (s.iloc[-1] - 1), dd=100 * float((s / s.cummax() - 1).min()))


def bench(start, end) -> dict:
    """SPY and the same top-10 names held, re-picked monthly, over [start, end]."""
    days = pd.date_range(start.tz_localize(None).normalize(), end.tz_localize(None).normalize(), freq="B")
    dc = {}
    for t in POOL + ["SPY"]:
        c = load(t)["close"]
        c = c.groupby(c.index.normalize()).last()
        c.index = c.index.tz_localize(None)
        dc[t] = c
    px = pd.DataFrame(dc).reindex(days).ffill()
    dr = px.pct_change().fillna(0)
    ranks = vol_ranks(LB, POOL)
    member = (ranks.reindex(days, method="ffill") <= K).astype(float)
    w = member.div(member.sum(axis=1), axis=0).fillna(0)
    out = {}
    for nm, r in (("SPY buy & hold", dr["SPY"]), ("same names buy & hold", (dr[POOL] * w[POOL]).sum(axis=1))):
        s = (1 + r).cumprod()
        out[nm] = dict(total=100 * (s.iloc[-1] - 1), dd=100 * float((s / s.cummax() - 1).min()))
    return out


def m(tr) -> dict:
    s = stats(tr.ret.to_numpy(), tr.days.to_numpy())
    w, l = tr.ret[tr.ret > 0], tr.ret[tr.ret <= 0]
    s.update(avg_w=100 * w.mean() if len(w) else 0.0, avg_l=100 * l.mean() if len(l) else 0.0,
             excess=100 * tr.excess.mean() if len(tr) else 0.0)
    return s


def line(name, tr, pf=None) -> str:
    if not len(tr):
        return f"| {name} | 0 | | | | | | | | | |"
    s = m(tr)
    pf = pf or portfolio(tr)
    return (f"| {name} | {s['n']} | {s['win']:.1f}% ({s['wins']}/{s['losses']}) | {s['avg']:+.2f}% | {s['pf']:.2f} | "
            f"{s['avg_w']:+.2f}% / {s['avg_l']:+.2f}% | {pf['total']:+.1f}% | {pf['dd']:.1f}% | {s['excess']:+.2f}% | "
            f"{s['t']:+.2f} | {s['days']:.1f} |")


HDR = ("| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | "
       "max DD | avg vs SPY same window | t | avg days |\n|---|---|---|---|---|---|---|---|---|---|---|")


def by_period(tr) -> list:
    L = [HDR]
    for k in ("explore", "holdout", "forward"):
        part = tr[tr.period == k]
        L.append(line(k, part))
    L.append(line("all", tr))
    return L


def main():
    L = ["# Swing audit: the live rule on Yahoo 1h bars (BEFORE)", "",
         f"Rule (config.yaml): `{P.key()}`", f"Universe: top {K} of {len(POOL)} by {LB}-day realized volatility, re-ranked monthly.",
         f"Periods by entry: explore < {SPLIT:%Y-%m-%d} <= holdout < {FWD:%Y-%m-%d} <= forward (to 2026-10-16). "
         "The holdout was used as a veto in the 1 Oct ablation, so only the forward weeks are untouched.", ""]
    J = {}

    # 1. reproduction
    rep = trades(P, 0.0005, end=REPRO_END)
    L += ["## 1. Reproduction of reports/backtest.md (data cut at 2026-10-01)", "",
          "| period | published trades / win % / avg | reproduced trades / win % / avg |", "|---|---|---|"]
    J["reproduction"] = {}
    for k in ("explore", "holdout"):
        s = m(rep[rep.period == k])
        J["reproduction"][k] = s
        a = PUBLISHED[k]
        L.append(f"| {k} | {a[0]} / {a[1]:.1f}% / {a[2]:+.2f}% | {s['n']} / {s['win']:.1f}% / {s['avg']:+.2f}% |")
    L.append("")

    # 2. baseline and costs
    base = trades(P, 0.0005)
    J["baseline"] = {k: m(base[base.period == k]) for k in ("explore", "holdout", "forward")}
    L += ["## 2. Baseline, all costs (backtest)", ""]
    for nm, c in COSTS.items():
        t = base if c == 0.0005 else trades(P, c)
        L += [f"### {nm}", ""] + by_period(t) + [""]
        J[f"cost_{c}"] = {k: m(t[t.period == k]) for k in ("explore", "holdout", "forward")}
    lt = late(base, 1)
    L += ["### 0.05% a side, every entry and non-stop exit one full hourly bar late (stress bound)", ""] + by_period(lt) + [""]
    J["late_1bar"] = {k: m(lt[lt.period == k]) for k in ("explore", "holdout", "forward")}

    # 3. benchmarks on the same windows
    L += ["## 3. Against SPY and holding the same names (same windows)", "",
          "| window | strategy (10%/position) | strategy max DD | SPY buy & hold | SPY max DD | same names held | their max DD |",
          "|---|---|---|---|---|---|---|"]
    for k in ("explore", "holdout", "forward"):
        part = base[base.period == k]
        if not len(part):
            continue
        a, b = part.entry_time.min(), part.exit_time.max()
        p_, bb = portfolio(part), bench(a, b)
        L.append(f"| {k} {a:%Y-%m-%d} to {b:%Y-%m-%d} | {p_['total']:+.1f}% | {p_['dd']:.1f}% | {bb['SPY buy & hold']['total']:+.1f}% | "
                 f"{bb['SPY buy & hold']['dd']:.1f}% | {bb['same names buy & hold']['total']:+.1f}% | {bb['same names buy & hold']['dd']:.1f}% |")
        J[f"bench_{k}"] = dict(strategy=p_, **bb)
    L.append("")
    exposure = (base.days.sum() / K) / max(1, (base.exit_time.max() - base.entry_time.min()).days * 5 / 7)
    L += [f"Average share of capital in the market: {100 * exposure:.0f}% (10% slots).", ""]

    # 4. splits
    def split(col, title, df=base):
        R = [f"#### {title}", "", "| bucket | explore n | explore avg | holdout n | holdout avg | forward n | forward avg | all n | all avg | all PF | share of all profit |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
        tot = df.ret.sum()
        for b, g in df.groupby(col):
            cells = []
            for k in ("explore", "holdout", "forward"):
                q = g[g.period == k]
                cells.append(f"{len(q)} | {100 * q.ret.mean():+.2f}%" if len(q) else "0 | -")
            s = m(g)
            R.append(f"| {b} | " + " | ".join(cells) + f" | {s['n']} | {s['avg']:+.2f}% | {s['pf']:.2f} | {100 * g.ret.sum() / tot:.0f}% |")
        return R + [""]
    base["hour"] = base.entry_time.dt.strftime("%H:%M")
    spyc = spy()["close"]
    spyd = spyc.groupby(spyc.index.normalize()).last()
    sma200 = spyd.rolling(200).mean().shift(1)
    prev = spyd.shift(1)
    base["spy_regime"] = ["SPY above 200-day" if prev.asof(t.normalize()) > sma200.asof(t.normalize()) else "SPY below 200-day"
                          if sma200.asof(t.normalize()) == sma200.asof(t.normalize()) else "n/a" for t in base.entry_time]
    base["half"] = base.entry_time.dt.year.astype(str) + "H" + ((base.entry_time.dt.month > 6) + 1).astype(str)
    L += ["## 4. Splits (0.05% a side)", ""] + split("ticker", "By ticker") + split("hour", "By entry bar (fill time)") + \
        split("spy_regime", "By SPY vs its 200-day average (prior close)") + split("half", "By half-year") + split("reason", "By exit")

    # 5. concentration and selection
    tot = base.ret.sum()
    top5 = base.ret.nlargest(5).sum()
    tick = base.groupby("ticker").ret.sum().sort_values(ascending=False)
    drop3 = base[~base.ticker.isin(tick.index[:3])]
    allpool = trades(P, 0.0005, k=99)
    low = trades(P, 0.0005, k=99)
    low = low[low["rank"] > K]
    L += ["## 5. Concentration and selection", "",
          f"- Best 5 of {len(base)} trades = {100 * top5 / tot:.0f}% of the summed profit; without them the average is "
          f"{100 * base.ret.drop(base.ret.nlargest(5).index).mean():+.2f}% (from {100 * base.ret.mean():+.2f}%).",
          f"- Best 3 tickers ({', '.join(tick.index[:3])}) = {100 * tick.iloc[:3].sum() / tot:.0f}% of the profit. Without them:", ""]
    L += by_period(drop3) + ["", "- The rule on every pool name, no volatility ranking (same dates):", ""] + by_period(allpool)
    L += ["", f"- The rule on the names ranked below the top {K} (what the ranking leaves out):", ""] + by_period(low)
    L += ["", "The 25-name pool was written in 2026 and holds the period's big winners (PLTR, HOOD, MSTR, COIN, SMCI, ARM). "
          "The monthly ranking itself uses only completed months, but the pool is chosen with hindsight: the results "
          "carry survivorship and selection bias that no split inside this data can remove.", ""]

    # 6. options: research vs live
    rv = {}
    for t in POOL:
        c = load(t)["close"]
        d = c.groupby(c.index.normalize()).last()
        rv[t] = d.pct_change().rolling(20).std() * math.sqrt(252)
    base["rv"] = [rv[t].asof(e.normalize() - pd.Timedelta(days=1)) for t, e in zip(base.ticker, base.entry_time)]
    base["rv_exit"] = [rv[t].asof(e.normalize() - pd.Timedelta(days=1)) for t, e in zip(base.ticker, base.exit_time)]
    base["opt_published"] = [option_ret_v1(r, r.rv) for r in base.itertuples()]
    base["opt_live"] = [option_ret(r, r.rv, r.rv_exit) for r in base.itertuples()]
    L += ["## 6. Options: what the reports modelled vs what the live scanner suggests", "",
          "| | reports/backtest.md + README (research/final.py) | research/ablation.py (chose the live spec) | live scanner (config.yaml + src/alpaca.py) |",
          "|---|---|---|---|",
          "| delta | 0.65 | 0.85 chosen | nearest 0.85 (score = delta gap + 2 x spread) |",
          f"| expiry | 30 DTE fixed | 21-30 DTE chosen | {OPT['dte_min']}-{OPT['dte_max']} DTE listed expiries |",
          "| IV | 1.15 x 20-day realized, fixed for the trade | 1.10 x realized, re-marked daily | market quote (indicative feed, 15 min late) |",
          "| spread / slippage | 3% round trip | 1-2% half-spread + 0.5% slippage | real quote; skips spreads > 8% of mid |",
          "| sizing | 1/4 of the share slot | same delta exposure as the share slot | not stated on the card |",
          "| skip rule | none | shares only when RV20 > 2x its 1-year median | none (always suggests a contract) |",
          "| exit | with the stock signal | with the stock signal | with the stock signal |", ""]
    L += ["Option returns per trade, estimated (Black-Scholes, no option prices observed):", "",
          "| period | trades | published model avg | published model win % | live spec avg | live spec win % |", "|---|---|---|---|---|---|"]
    for k in ("explore", "holdout", "forward"):
        part = base[base.period == k]
        if len(part):
            L.append(f"| {k} | {len(part)} | {100 * part.opt_published.mean():+.1f}% | {100 * (part.opt_published > 0).mean():.0f}% | "
                     f"{100 * part.opt_live.mean():+.1f}% | {100 * (part.opt_live > 0).mean():.0f}% |")
    L.append("")

    # 7. retune arithmetic
    hold = base[base.period != "explore"]
    se = 100 * hold.ret.std(ddof=1) / math.sqrt(max(1, len(hold)))
    L += ["## 7. Weekly retune: margin against noise", "",
          f"src/retune.py adopts a challenger from 108 variants if it beats the live rule by 0.15% a trade on the full "
          f"history and on the last 12 months, with t >= 2.0 on the last 12 months. The standard error of a 12-month "
          f"average here is about {se:.2f}% a trade, so 0.15% is {0.15 / se:.2f} standard errors; the noise floor for "
          f"108 variants is {noise_floor(108):.2f}. The bar can be cleared by luck.", ""]

    (ROOT / "reports" / "audit_backtest.md").write_text("\n".join(L) + "\n")
    (ROOT / "reports" / "audit_backtest.json").write_text(json.dumps(J, indent=1, default=float))
    base.drop(columns=["rv", "rv_exit"]).to_csv(ROOT / "reports" / "audit_trades.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
