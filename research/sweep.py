"""Stage 1: pooled grid search across the whole universe.
Chooses on EXPLORE only; HOLDOUT printed beside it, never used to rank.
Usage: python research/sweep.py [out.csv]"""
from __future__ import annotations

import itertools
import sys
from multiprocessing import Pool

import pandas as pd

from common import Params, ROOT, noise_floor, run, stats, tickers

GRIDS = {
    1: dict(tf=[1, 2, 4], ema=[9, 21, 50], vwap=["session", "week", "month", "roll20", "roll50"],
            trend=[0, 200], sides=["long", "short"], stop_atr=[0, 2.0, 3.0],
            target_atr=[0, 4.0], min_bars=[0, 7], confirm=[False, True]),
    2: dict(ema=[13, 21, 34], vwap=["week", "roll35", "roll50"], entry=["cross", "cross_or_pb"],
            exit=["cross", "close_vwap"], regime=["", "spy50", "spyvw"], rs=[0, 20],
            dtrend=[0, 50], min_bars=[0, 7], stop_atr=[0, 4.0]),
}
ROUND = int(sys.argv[1]) if len(sys.argv) > 1 else 2
GRID = GRIDS[ROUND]
TICKERS = tickers()


def one(combo):
    p = Params(**dict(zip(GRID, combo)))
    if p.min_bars and p.tf > 1:  # min_bars is given in 1h bars (7 = one session); convert
        p.min_bars = max(1, round(p.min_bars / p.tf))
    tr = pd.concat([run(t, p) for t in TICKERS], ignore_index=True)
    out = {"key": p.key()}
    for name, part in (("x", tr[~tr.holdout]), ("h", tr[tr.holdout])):
        s = stats(part.ret.to_numpy(), part.days.to_numpy()) if len(part) else stats([])
        out.update({f"{name}_{k}": v for k, v in s.items()})
        ex = part.excess.dropna().to_numpy() if len(part) else []
        out[f"{name}_ex"] = 100 * ex.mean() if len(ex) else 0.0
        out[f"{name}_ext"] = stats(ex)["t"] if len(ex) > 1 else 0.0
    return out


if __name__ == "__main__":
    combos = list(itertools.product(*GRID.values()))
    with Pool(8) as pool:
        rows = pool.map(one, combos, chunksize=8)
    df = pd.DataFrame(rows).sort_values("x_ext", ascending=False)
    out = ROOT / "research" / f"sweep{ROUND}.csv"
    df.to_csv(out, index=False)
    nf = noise_floor(len(combos))
    print(f"{len(combos)} variants, noise floor t≈{nf:.2f}")
    print(f"all-negative check: explore avg>0 in {(df.x_avg > 0).mean():.0%} of variants, "
          f"holdout avg>0 in {(df.h_avg > 0).mean():.0%}")
    cols = ["key", "x_n", "x_win", "x_avg", "x_t", "x_days", "x_ex", "x_ext", "h_n", "h_win", "h_avg", "h_t", "h_ex", "h_ext"]
    pd.set_option("display.width", 250, "display.max_colwidth", 140)
    df["key"] = df.key.str.replace(r"(tf=1\|)|(trend=0\|)|(sides=long\|)|(target_atr=0.0\|)|(exit_cross=True\|)|(max_bars=0\|)|(confirm=False\|)", "", regex=True)
    print(df[cols].head(25).round(2).to_string(index=False))
