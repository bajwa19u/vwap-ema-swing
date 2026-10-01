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
    tr = backtest(Params(**s0["params"]), hours, mkt, members, earnings.load(sorted(hours)))
    tr["year"] = [t.year for t in tr.entry_time]
    spy = mkt["close"].groupby(mkt.index.year).agg(["first", "last"])
    lines = ["# Long-history check (live rules)", "",
             f"Alpaca bars {mkt.index[0]:%Y-%m-%d} to {mkt.index[-1]:%Y-%m-%d}. "
             "Account % = 10% of the account per position, summed. Today's pool, so survivorship applies.", "",
             "| year | trades | win % | winners / losers | avg per trade % | account % | SPY % |",
             "|---|---|---|---|---|---|---|"]
    for y, part in tr.groupby("year"):
        s = stats(part.ret)
        sp = 100 * (spy.at[y, "last"] / spy.at[y, "first"] - 1) if y in spy.index else float("nan")
        lines.append(f"| {y} | {s['n']} | {s['win']:.1f} | {s['wins']} / {s['losses']} | {s['avg']:+.2f} | "
                     f"{10 * part.ret.sum():+.1f} | {sp:+.1f} |")
    s = stats(tr.ret)
    lines.append(f"| all | {s['n']} | {s['win']:.1f} | {s['wins']} / {s['losses']} | {s['avg']:+.2f} | "
                 f"{10 * tr.ret.sum():+.1f} | |")
    out = "\n".join(lines)
    print(out)
    (ROOT / "reports" / "longtest.md").write_text(out + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3800)
