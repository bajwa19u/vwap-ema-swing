"""Per-ticker breakdown of one config vs a drift baseline (random long entry,
same hold length). Usage: python research/pertick.py 'tf=1|ema=21|...'"""
import sys

import numpy as np
import pandas as pd

from common import SPLIT, Params, load, run, stats, tickers


def parse(key: str) -> Params:
    kw = {}
    for kv in key.split("|"):
        k, v = kv.split("=")
        f = Params.__dataclass_fields__[k].type
        kw[k] = v == "True" if f in ("bool", bool) else int(v) if f in ("int", int) \
            else float(v) if f in ("float", float) else v
    return Params(**kw)


def drift(df: pd.DataFrame, hold_bars: int, holdout: bool) -> float:
    c = df["close"].to_numpy()
    fwd = c[hold_bars:] / c[:-hold_bars] - 1
    m = (df.index[:-hold_bars] >= SPLIT) == holdout
    return 100 * fwd[m].mean()


if __name__ == "__main__":
    p = parse(sys.argv[1])
    pd.set_option("display.width", 250)
    rows, alltr = [], []
    for t in tickers():
        tr = run(t, p)
        alltr.append(tr)
        df = load(t)
        hb = max(1, int(round(tr.days.mean() * 7 * 5 / 7)))  # ~7 1h bars per trading day
        r = {"t": t}
        for nm, part, ho in (("x", tr[~tr.holdout], False), ("h", tr[tr.holdout], True)):
            s = stats(part.ret.to_numpy())
            r.update({f"{nm}_n": s["n"], f"{nm}_win": s["win"], f"{nm}_avg": s["avg"],
                      f"{nm}_tot": s["total"], f"{nm}_base": drift(df, hb, ho),
                      f"{nm}_ex": 100 * part.excess.mean() if len(part) else 0})
        rows.append(r)
    df = pd.DataFrame(rows).set_index("t")
    df["x_edge"], df["h_edge"] = df.x_avg - df.x_base, df.h_avg - df.h_base
    print(df.round(2).sort_values("x_edge", ascending=False).to_string())
    tr = pd.concat(alltr)
    for nm, part in (("explore", tr[~tr.holdout]), ("holdout", tr[tr.holdout])):
        print(nm, {k: round(v, 2) for k, v in stats(part.ret.to_numpy(), part.days.to_numpy()).items()})
    print("edge over drift, mean of tickers: explore %.2f  holdout %.2f" % (df.x_edge.mean(), df.h_edge.mean()))
    print("tickers with positive edge: explore %d/%d, holdout %d/%d, both %d" % (
        (df.x_edge > 0).sum(), len(df), (df.h_edge > 0).sum(), len(df),
        ((df.x_edge > 0) & (df.h_edge > 0)).sum()))
    print("exit reasons:", tr.reason.value_counts().to_dict())
