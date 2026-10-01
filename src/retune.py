"""Weekly self-improvement. Re-tests the live rules against nearby variants on
fresh Alpaca history (dynamic top-K volatility universe, as live). A
challenger replaces the incumbent only if it wins on BOTH the full history
and the last 12 months by a clear margin. Posts a scorecard to Discord and
writes reports/retune/<date>.md. No Claude usage: runs on GitHub Actions.

Usage: python -m src.retune [--dry]
"""
from __future__ import annotations

import itertools
import math
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src import alpaca, discord
from src.scanner import LEDGER, ROOT, complete_hours, load_cfg
from src.strategy import Params, simulate
from src.universe import top_by_vol

NEIGHBORS = dict(ema=[13, 21, 34], min_bars=[0, 7, 14], vwap=["week", "roll35"], regime=["spyvw", ""],
                 week_grace=[0, 2, 4])
MARGIN = 0.15        # avg profit % per trade a challenger must add, in both windows
MIN_RECENT_N = 100   # trades in the last 12 months
MIN_RECENT_T = 2.0   # t-stat of the challenger's last-12-month trades


def stats(r) -> dict:
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n < 2:
        return dict(n=n, win=0.0, avg=0.0, t=0.0, wins=0, losses=n)
    return dict(n=n, win=100 * (r > 0).mean(), avg=100 * r.mean(),
                t=r.mean() / r.std(ddof=1) * math.sqrt(n), wins=int((r > 0).sum()), losses=int((r <= 0).sum()))


def monthly_members(hours: dict, k: int, lookback: int) -> dict:
    months = sorted({(t.year, t.month) for t in next(iter(hours.values())).index})
    return {m: set(top_by_vol(hours, k, lookback, asof=pd.Timestamp(m[0], m[1], 1, tz=alpaca.NY)))
            for m in months}


def backtest(p: Params, hours: dict, mkt: pd.DataFrame, members: dict) -> pd.DataFrame:
    out = []
    for t, h in hours.items():
        tr = pd.DataFrame(simulate(h, p, market=mkt.reindex(h.index).ffill()))
        if len(tr):
            tr["ticker"] = t
            keep = [t in members.get((e.year, e.month), ()) for e in tr.entry_time]
            out.append(tr[keep])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["ret", "entry_time", "days"])


def set_params(text: str, new: dict) -> str:
    for k, v in new.items():
        text = re.sub(rf"^(\s+){k}: .*$", lambda m: f"{m.group(1)}{k}: {v if v != '' else chr(34) * 2}",
                      text, count=1, flags=re.M)
    return text


def scorecard() -> str:
    if not LEDGER.exists():
        return "Live: no closed signals yet."
    lg = pd.read_csv(LEDGER, parse_dates=["exit_time"])
    s = stats(lg.ret)
    wk = lg[lg.exit_time >= lg.exit_time.max() - pd.Timedelta(days=7)]
    w = stats(wk.ret)
    return (f"Live since start: {s['n']} closed, win {s['win']:.0f}%, {s['wins']} winners / {s['losses']} losers, "
            f"total {100 * lg.ret.sum():+.1f}%.\nLast 7 days: {w['n']} closed, total {100 * wk.ret.sum():+.1f}%.")


def main(dry: bool = False) -> None:
    cfg = load_cfg()
    s0 = cfg["strategies"][0]
    u = s0["universe"]
    data = alpaca.bars_30m(sorted({cfg.get("market", "SPY"), *u["pool"]}), days=1100)
    hours = {t: complete_hours(df) for t, df in data.items() if len(df) > 1000}
    mkt = hours.pop(cfg.get("market", "SPY"))
    members = monthly_members(hours, u["top_k"], u["vol_lookback_days"])
    cutoff = mkt.index[-1] - pd.Timedelta(days=365)

    inc = Params(**s0["params"])
    rows = []
    for combo in itertools.product(*NEIGHBORS.values()):
        p = Params(**{**s0["params"], **dict(zip(NEIGHBORS, combo))})
        tr = backtest(p, hours, mkt, members)
        full, rec = stats(tr.ret), stats(tr[tr.entry_time >= cutoff].ret)
        rows.append(dict(p=p, **{f"f_{k}": v for k, v in full.items()}, **{f"r_{k}": v for k, v in rec.items()},
                         days=tr.days.mean(), is_inc=p == inc))
    df = pd.DataFrame(rows)
    I = df[df.is_inc].iloc[0]
    ok = df[(df.f_avg >= I.f_avg + MARGIN) & (df.r_avg >= I.r_avg + MARGIN) &
            (df.r_n >= MIN_RECENT_N) & (df.r_t >= MIN_RECENT_T)]
    winner = ok.sort_values("r_t", ascending=False).iloc[0] if len(ok) else None

    text = (ROOT / "config.yaml").read_text()
    changed = ""
    if winner is not None:
        new = {k: getattr(winner.p, k) for k in NEIGHBORS if getattr(winner.p, k) != getattr(inc, k)}
        text = set_params(text, new)
        changed = ", ".join(f"{k}: {getattr(inc, k)!r} → {v!r}" for k, v in new.items())
        I = winner
    live_stats = (f"Last 12 months: {int(I.r_n)} trades, win {I.r_win:.0f}%, avg {I.r_avg:+.2f}% per trade "
                  f"(shares), avg hold {I.days:.1f} days")
    text = re.sub(r'^(\s+)stats: .*$', lambda m: f'{m.group(1)}stats: "{live_stats}"', text, count=1, flags=re.M)
    active = top_by_vol(hours, u["top_k"], u["vol_lookback_days"])

    top = df.sort_values("r_t", ascending=False).head(8)
    lines = [f"# Retune {date.today()}", "", f"Data through {mkt.index[-1]}. Variants tried: {len(df)}. "
             f"Noise floor t≈{math.sqrt(2 * math.log(len(df))):.2f}.", "",
             f"Decision: {'CHANGED ' + changed if changed else 'kept the current rules'}", "",
             f"This month's names: {', '.join(active)}", "",
             "| ema | min_bars | vwap | regime | full n | full win % | full avg % | 12m n | 12m win % | 12m avg % | 12m t |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in top.itertuples():
        lines.append(f"| {r.p.ema} | {r.p.min_bars} | {r.p.vwap} | {r.p.regime or 'none'} | {r.f_n} | {r.f_win:.1f} | "
                     f"{r.f_avg:+.2f} | {r.r_n} | {r.r_win:.1f} | {r.r_avg:+.2f} | {r.r_t:.2f} |"
                     + (" ← live" if r.is_inc else ""))
    report = "\n".join(lines)
    print(report)
    if dry:
        return
    (ROOT / "config.yaml").write_text(text)
    out = ROOT / "reports" / "retune"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{date.today()}.md").write_text(report + "\n")
    msg = (f"{scorecard()}\n\nBacktest, {live_stats.lower()}.\n"
           f"Rules: {'**updated** (' + changed + ')' if changed else 'unchanged'}.\n"
           f"Names this month: {', '.join(active)}")
    discord.post(cfg, discord.info_card("Weekly scorecard", msg))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
