"""Round 3: exits, on the dynamic top-10-by-volatility universe."""
import itertools
from multiprocessing import Pool

import numpy as np
import pandas as pd

from common import Params, noise_floor, run, stats, tickers
from volsel import EXCLUDE, vol_ranks

import yaml
from common import ROOT
POOL = yaml.safe_load((ROOT / "config.yaml").read_text())["strategies"][0]["universe"]["pool"]
RANKS = vol_ranks(120, POOL)
import sys
GRID = dict(min_bars=[0, 7, 14], stop_atr=[0, 4.0, 6.0], trail_atr=[0, 2.0, 3.0, 5.0],
            max_bars=[0, 21, 35], exit=["cross", "close_vwap"])
BASE = dict(ema=21, vwap="week", regime="spyvw")
if "grace" in sys.argv:
    GRID = dict(week_grace=[0, 1, 2, 4, 7], min_bars=[0, 7])
    BASE = dict(ema=21, vwap="week", regime="spyvw", stop_atr=6.0)
if "egrace" in sys.argv:
    GRID = dict(entry_grace=[0, 1, 2, 4, 7, 14])
    BASE = dict(ema=21, vwap="week", regime="spyvw", stop_atr=6.0, min_bars=7, week_grace=2,
                earn_skip=2, earn_exit=True)


def selected(tr):
    m = tr.entry_time.map(lambda x: pd.Timestamp(x.year, x.month, 1) + pd.offsets.MonthEnd(0))
    r = [RANKS.at[a, t] if a in RANKS.index else np.nan for a, t in zip(m, tr.ticker)]
    return tr[np.array(r) <= 10]


def one(combo):
    p = Params(**BASE, **dict(zip(GRID, combo)))
    tr = selected(pd.concat([run(t, p) for t in POOL], ignore_index=True))
    out = {k: v for k, v in zip(GRID, combo)}
    for nm, part in (("x", tr[~tr.holdout]), ("h", tr[tr.holdout])):
        s = stats(part.ret.to_numpy(), part.days.to_numpy())
        out.update({f"{nm}_n": s["n"], f"{nm}_win": s["win"], f"{nm}_avg": s["avg"],
                    f"{nm}_t": s["t"], f"{nm}_days": s["days"], f"{nm}_ex": 100 * part.excess.mean()})
    return out


if __name__ == "__main__":
    combos = list(itertools.product(*GRID.values()))
    with Pool(8) as pool:
        df = pd.DataFrame(pool.map(one, combos, chunksize=4)).sort_values("x_t", ascending=False)
    df.to_csv("sweep3%s.csv" % ("e" if "egrace" in sys.argv else "g" if "grace" in sys.argv else ""), index=False)
    print(f"{len(combos)} variants, noise floor t≈{noise_floor(len(combos)):.2f}; "
          f"holdout avg>0 in {(df.h_avg > 0).mean():.0%}")
    pd.set_option("display.width", 250)
    print(df.head(15).round(2).to_string(index=False))
    if "grace" in sys.argv or "egrace" in sys.argv:
        raise SystemExit
    print("baseline:"); print(df[(df.min_bars == 7) & (df.stop_atr == 0) & (df.trail_atr == 0) & (df.max_bars == 0) & (df.exit == "cross")].round(2).to_string(index=False))
    for c in GRID:
        print(df.groupby(c)[["x_avg", "h_avg", "x_win", "h_win", "h_days"]].median().round(2).to_string())
