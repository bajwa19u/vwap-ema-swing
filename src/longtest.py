"""Long-history check of the live rules on Alpaca bars since 2016, year by year.
Not used to choose anything; it shows how the rules behave in bad years.
Caveat: the pool is today's names (survivorship), so read it as a stress test.

Usage: python -m src.longtest [days]
"""
from __future__ import annotations

import sys

import pandas as pd

from src import alpaca, earnings
from src.retune import backtest, monthly_members, stats
from src.scanner import ROOT, complete_hours, load_cfg
from src.strategy import Params


def main(days: int = 3800) -> None:
    cfg = load_cfg()
    s0 = cfg["strategies"][0]
    u = s0["universe"]
    msym = cfg.get("market", "SPY")
    data = alpaca.bars_30m(sorted({msym, *u["pool"]}), days=days)
    hours = {t: complete_hours(df) for t, df in data.items() if len(df) > 1000}
    mkt = hours.pop(msym)
    members = monthly_members(hours, u["top_k"], u["vol_lookback_days"])
    ev = earnings.load(sorted(hours))
    base = s0["params"]
    variants = {"live": base["regime"]}
    for extra in ("spy200", "spy100", "spy50"):
        variants[f"+{extra}"] = f"{base['regime']}+{extra}"
    res = {}
    for name, reg in variants.items():
        tr = backtest(Params(**{**base, "regime": reg}), hours, mkt, members, ev)
        tr["year"] = [t.year for t in tr.entry_time]
        res[name] = tr
    spy = mkt["close"].groupby(mkt.index.year).agg(["first", "last"])
    names = list(variants)
    lines = ["# Long-history check", "",
             f"Alpaca bars {mkt.index[0]:%Y-%m-%d} to {mkt.index[-1]:%Y-%m-%d}. Account % = 10% of the account per "
             "position, summed per year. Today's pool, so survivorship applies. Choose on 2016-2022, check 2023+.", "",
             "| year | SPY % | " + " | ".join(f"{n} acct % (n, win %)" for n in names) + " |",
             "|---|---|" + "---|" * len(names)]
    for y in sorted(set(res["live"].year)):
        sp = 100 * (spy.at[y, "last"] / spy.at[y, "first"] - 1)
        cells = []
        for n in names:
            part = res[n][res[n].year == y]
            s = stats(part.ret)
            cells.append(f"{10 * part.ret.sum():+.1f} ({s['n']}, {s['win']:.0f})")
        lines.append(f"| {y} | {sp:+.1f} | " + " | ".join(cells) + " |")
    for label, cond in (("2016-2022 (choose)", lambda t: t.year <= 2022), ("2023+ (check)", lambda t: t.year >= 2023)):
        cells = []
        for n in names:
            part = res[n][[cond(t) for t in res[n].entry_time]]
            s = stats(part.ret)
            yrs = part.year.nunique() or 1
            cells.append(f"{10 * part.ret.sum() / yrs:+.1f}/yr ({s['n']}, {s['win']:.0f}, t {s['t']:.1f})")
        lines.append(f"| **{label}** | | " + " | ".join(cells) + " |")
    out = "\n".join(lines)
    print(out)
    (ROOT / "reports" / "longtest.md").write_text(out + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3800)
