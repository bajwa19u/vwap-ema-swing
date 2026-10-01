"""Final backtest of the live configuration: dynamic top-10-by-volatility
universe, portfolio equity (10% of equity per position), buy-and-hold
comparisons, and an options estimate (Black-Scholes, IV ~ 1.15 x realized).
Writes reports/backtest.md and reports/equity.png."""
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm

from common import ROOT, SPLIT, Params, load, run, stats, tickers
from volsel import EXCLUDE, vol_ranks

CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
S = CFG["strategies"][0]
P = Params(**S["params"])
K, LB = S["universe"]["top_k"], S["universe"]["vol_lookback_days"]
SLOT = 1.0 / K


def bs_call(s, k, t, v, r=0.04):
    if t <= 0:
        return max(s - k, 0.0)
    d1 = (math.log(s / k) + (r + v * v / 2) * t) / (v * math.sqrt(t))
    return s * norm.cdf(d1) - k * math.exp(-r * t) * norm.cdf(d1 - v * math.sqrt(t))


def strike_for_delta(s, t, v, delta, r=0.04):
    d1 = norm.ppf(delta)
    return s * math.exp(-(d1 * v * math.sqrt(t)) + (r + v * v / 2) * t)


def option_ret(row, rv, dte=30, delta=0.65, spread=0.03):
    t0 = dte / 365
    v = max(0.15, 1.15 * rv)
    k = strike_for_delta(row.entry, t0, v, delta)
    c0 = bs_call(row.entry, k, t0, v) * (1 + spread / 2)
    c1 = bs_call(row.exit, k, max(t0 - row.days / 365, 0), v) * (1 - spread / 2)
    return c1 / c0 - 1


def main():
    pool = [t for t in S["universe"]["pool"] if t not in EXCLUDE]
    ranks = vol_ranks(LB, pool)
    tr = pd.concat([run(t, P) for t in pool], ignore_index=True)
    m = tr.entry_time.map(lambda x: pd.Timestamp(x.year, x.month, 1) + pd.offsets.MonthEnd(0))
    tr["rank"] = [ranks.at[a, t] if a in ranks.index else np.nan for a, t in zip(m, tr.ticker)]
    tr = tr[tr["rank"] <= K].copy()
    rv = {}
    for t in pool:
        c = load(t)["close"]
        d = c.groupby(c.index.normalize()).last()
        rv[t] = d.pct_change().rolling(20).std() * math.sqrt(252)
    tr["rv"] = [rv[t].asof(e.normalize()) for t, e in zip(tr.ticker, tr.entry_time)]
    tr["opt_ret"] = [option_ret(r, r.rv) for r in tr.itertuples()]
    tr.to_csv(ROOT / "reports" / "trades.csv", index=False)

    # portfolio: each trade gets SLOT of equity at entry; P&L booked at exit
    tr = tr.sort_values("exit_time")
    days = pd.date_range(tr.entry_time.min().normalize().tz_localize(None), pd.Timestamp.today().normalize(), freq="B")
    curves = {}
    for col, label in (("ret", "Strategy (shares)"), ("opt_ret", "Strategy (calls, est.)")):
        eq, e, pnl = [], 1.0, tr.groupby(tr.exit_time.dt.tz_localize(None).dt.normalize())[col].sum()
        for d in days:
            if d in pnl.index:
                e *= 1 + SLOT * pnl[d] * (0.25 if col == "opt_ret" else 1)  # calls sized at 1/4 slot
            eq.append(e)
        curves[label] = pd.Series(eq, index=days)
    spy = load("SPY")["close"]
    spy = spy.groupby(spy.index.normalize()).last()
    spy.index = spy.index.tz_localize(None)
    # fair benchmark: hold the same top-K volatility names, re-picked monthly
    dc = {}
    for t in pool:
        c = load(t)["close"]
        c = c.groupby(c.index.normalize()).last()
        c.index = c.index.tz_localize(None)
        dc[t] = c
    dr = pd.DataFrame(dc).reindex(days).ffill().pct_change().fillna(0)
    member = (ranks.reindex(days, method="ffill") <= K).astype(float)
    w = member.div(member.sum(axis=1), axis=0).fillna(0)
    curves["Same names buy & hold"] = (1 + (dr * w[dr.columns]).sum(axis=1)).cumprod()
    curves["SPY buy & hold"] = (spy / spy.reindex(days, method="ffill").iloc[0]).reindex(days, method="ffill")

    def summ(s):
        dd = (s / s.cummax() - 1).min()
        yrs = (s.index[-1] - s.index[0]).days / 365.25
        return f"{100 * (s.iloc[-1] - 1):+.1f}%", f"{100 * (s.iloc[-1] ** (1 / yrs) - 1):+.1f}%", f"{100 * dd:.1f}%"

    fig, ax = plt.subplots(figsize=(10, 5))
    for k, s in curves.items():
        ax.plot(s.index, 100 * (s - 1), label=k, lw=1.6)
    ax.axvline(SPLIT.tz_localize(None), color="grey", ls="--", lw=1)
    ax.text(SPLIT.tz_localize(None), ax.get_ylim()[1] * 0.92, "  holdout →", color="grey")
    ax.set_ylabel("Return %"); ax.legend(); ax.grid(alpha=0.3)
    ax.set_title("VWAP x EMA swing: EMA21 vs weekly VWAP, 1h, top-10 volatility names")
    fig.tight_layout(); fig.savefig(ROOT / "reports" / "equity.png", dpi=110)

    lines = ["# Backtest: VWAP x EMA swing", "",
             f"Data: Yahoo 1h bars {tr.entry_time.min():%Y-%m-%d} to {tr.exit_time.max():%Y-%m-%d}. "
             f"Explore < {SPLIT:%Y-%m-%d} <= holdout. Costs 0.05% per side.", "",
             f"Rules: `{P.key()}`", f"Universe: top {K} of {len(pool)} names by {LB}-day volatility, re-ranked monthly.", "",
             "## Per trade", "", "| period | trades | win % | winners / losers | avg profit % | total profit % | avg vs SPY % | avg calls % (est.) | avg days |",
             "|---|---|---|---|---|---|---|---|---|"]
    for nm, part in (("explore", tr[~tr.holdout]), ("holdout", tr[tr.holdout]), ("all", tr)):
        s = stats(part.ret.to_numpy(), part.days.to_numpy())
        lines.append(f"| {nm} | {s['n']} | {s['win']:.1f} | {s['wins']} / {s['losses']} | {s['avg']:+.2f} | "
                     f"{s['total']:+.0f} | {100 * part.excess.mean():+.2f} | {100 * part.opt_ret.mean():+.1f} | {s['days']:.1f} |")
    lines += ["", "## Portfolio (10% of equity per share position; calls sized at 2.5%)", "",
              "| curve | total | per year | max drawdown |", "|---|---|---|---|"]
    for k, s in curves.items():
        lines.append(f"| {k} | " + " | ".join(summ(s)) + " |")
    lines += ["", "Holdout only (rules never saw this period):", "", "| curve | total | per year | max drawdown |", "|---|---|---|---|"]
    for k, s in curves.items():
        h = s[s.index >= SPLIT.tz_localize(None)]
        lines.append(f"| {k} | " + " | ".join(summ(h / h.iloc[0])) + " |")
    lines += ["", "## By ticker (all periods)", "", "| ticker | trades | win % | avg % | total % |", "|---|---|---|---|---|"]
    for t, part in tr.groupby("ticker"):
        s = stats(part.ret.to_numpy())
        lines.append(f"| {t} | {s['n']} | {s['win']:.0f} | {s['avg']:+.2f} | {s['total']:+.0f} |")
    lines += ["", "![equity](equity.png)", ""]
    (ROOT / "reports" / "backtest.md").write_text("\n".join(lines))
    print("\n".join(lines[8:30]))


if __name__ == "__main__":
    main()
