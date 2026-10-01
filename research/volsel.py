"""Dynamic universe: at each trade's entry, keep it only if the ticker ranked in
the top K by trailing realized volatility as of the previous month-end
(no lookahead). Usage: python research/volsel.py '<params>' [lookback_days]"""
import sys

import numpy as np
import pandas as pd

from common import load, run, stats, tickers
from pertick import parse

EXCLUDE = {"SPY", "QQQ", "IWM"}  # the regime filter is SPY itself; edge vs SPY ~0 by construction


def vol_ranks(lookback: int) -> pd.DataFrame:
    vols = {}
    for t in tickers():
        if t in EXCLUDE:
            continue
        c = load(t)["close"]
        daily = c.groupby(c.index.normalize()).last()
        daily.index = daily.index.tz_localize(None)
        vols[t] = daily.pct_change().rolling(lookback).std() * np.sqrt(252)
    v = pd.DataFrame(vols).resample("ME").last()
    return v.rank(axis=1, ascending=False).shift(1)  # rank known at start of month


if __name__ == "__main__":
    p = parse(sys.argv[1])
    lb = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    ranks = vol_ranks(lb)
    tr = pd.concat([run(t, p) for t in tickers() if t not in EXCLUDE], ignore_index=True)
    month = tr.entry_time.map(lambda x: pd.Timestamp(x.year, x.month, 1) + pd.offsets.MonthEnd(0))
    tr["rank"] = [ranks.at[m, t] if m in ranks.index else np.nan for m, t in zip(month, tr.ticker)]
    tr = tr.dropna(subset=["rank"])
    for k in (6, 8, 10, 12, 25):
        sel = tr[tr["rank"] <= k]
        row = []
        for nm, part in (("explore", sel[~sel.holdout]), ("holdout", sel[sel.holdout])):
            s = stats(part.ret.to_numpy(), part.days.to_numpy())
            row.append(f"{nm}: n={s['n']} win={s['win']:.1f}% avg={s['avg']:+.2f}% "
                       f"vsSPY={100 * part.excess.mean():+.2f}% t={s['t']:.1f}")
        print(f"top{k:<2} | " + " | ".join(row))
    last = ranks.iloc[-1].sort_values()
    print("current top 12 by vol:", list(last.index[:12]))
