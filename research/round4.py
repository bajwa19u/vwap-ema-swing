"""Round 4: bigger pool x top-K x earnings rules, live params otherwise.
Choose on explore, report holdout beside it. Usage: python research/round4.py"""
import itertools
import pickle
from multiprocessing import Pool

import numpy as np
import pandas as pd
import yaml

from common import CACHE, ROOT, SPLIT, Params, load, noise_floor, stats, tickers
from src.strategy import simulate

CFG = yaml.safe_load((ROOT / "config.yaml").read_text())["strategies"][0]
POOL25 = CFG["universe"]["pool"]
POOL_ALL = [t for t in tickers() if t not in ("SPY", "QQQ", "IWM")]
EARN = pickle.load(open(CACHE / "earnings.pickle", "rb"))
EVARS = {"off": {}, "skip2": dict(earn_skip=2), "exit": dict(earn_exit=True),
         "skip2+exit": dict(earn_skip=2, earn_exit=True), "skip5+exit": dict(earn_skip=5, earn_exit=True)}
SPY = load("SPY")


def ranks(pool, lookback=120):
    v = {}
    for t in pool:
        c = load(t)["close"]
        d = c.groupby(c.index.normalize()).last()
        d.index = d.index.tz_localize(None)
        v[t] = d.pct_change().rolling(lookback).std()
    return pd.DataFrame(v).resample("ME").last().rank(axis=1, ascending=False).shift(1)


def trades_for(ev):
    p = Params(**{**CFG["params"], **EVARS[ev]})
    out = []
    for t in POOL_ALL:
        tr = pd.DataFrame(simulate(load(t), p, market=SPY, events=EARN.get(t)))
        if len(tr):
            tr["ticker"] = t
            out.append(tr)
    tr = pd.concat(out, ignore_index=True)
    tr["holdout"] = tr.entry_time >= SPLIT
    tr["month"] = [pd.Timestamp(x.year, x.month, 1) + pd.offsets.MonthEnd(0) for x in tr.entry_time]
    return ev, tr


if __name__ == "__main__":
    with Pool(5) as pool:
        TR = dict(pool.map(trades_for, list(EVARS)))
    R = {"p25": ranks(POOL25), "p74": ranks(POOL_ALL)}
    rows = []
    for pname, k, ev in itertools.product(R, (10, 15, 20), EVARS):
        tr, rk = TR[ev], R[pname]
        r = [rk.at[m, t] if (m in rk.index and t in rk.columns) else np.nan for m, t in zip(tr.month, tr.ticker)]
        sel = tr[np.array(r) <= k]
        row = dict(pool=pname, k=k, earn=ev)
        for nm, part in (("x", sel[~sel.holdout]), ("h", sel[sel.holdout])):
            s = stats(part.ret.to_numpy(), part.days.to_numpy())
            # account %: each position = 1/k of the account, summed per period
            row.update({f"{nm}_n": s["n"], f"{nm}_win": s["win"], f"{nm}_avg": s["avg"], f"{nm}_t": s["t"],
                        f"{nm}_acct": 100 * part.ret.sum() / k})
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("x_t", ascending=False)
    df.to_csv(ROOT / "research" / "sweep4.csv", index=False)
    print(f"{len(df)} variants, noise floor t≈{noise_floor(len(df)):.2f}; holdout avg>0 in {(df.h_avg > 0).mean():.0%}")
    pd.set_option("display.width", 220)
    print(df.round(2).to_string(index=False))
    for c in ("pool", "k", "earn"):
        print(df.groupby(c)[["x_avg", "h_avg", "x_acct", "h_acct", "h_win"]].mean().round(2).to_string())
