"""Swing audit, part 2: the live rule on the live data path, and the live delay.

Runs on GitHub Actions (needs the Alpaca keys). Changes nothing.

1. The live rule on Alpaca SIP 30-minute bars made hourly by
   scanner.complete_hours, with the monthly volatility universe and earnings
   rules exactly as src/retune.py backtests it - i.e. the data the scanner
   trades from, not the Yahoo cache the research used.
2. Signal by signal, the same trades against the Yahoo backtest
   (reports/audit_trades.csv from research/audit.py).
3. The delay. The scanner sees an hourly bar 15 minutes after it closes and
   runs at :47, so a signal reaches Discord about 17 minutes after the price
   the backtest fills at. Entries and non-stop exits are re-priced on SIP
   15-minute bars at +15 and +30 minutes. Signals from the 15:30 bar are
   posted at 16:17 and filled at the next open in both the backtest and real
   life, so they are not delayed. Stops are resting orders and keep their fill.
4. The live ledger's prices against what could have been traded at +15 min.

Usage: python research/audit_live.py
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import alpaca, earnings  # noqa: E402
from src.retune import backtest, monthly_members  # noqa: E402
from src.scanner import complete_hours, load_cfg  # noqa: E402
from src.strategy import Params  # noqa: E402

NY = alpaca.NY
SPLIT = pd.Timestamp("2025-07-01", tz=NY)
FWD = pd.Timestamp("2026-10-02", tz=NY)
END = datetime(2026, 10, 16, 20, 30, tzinfo=timezone.utc)      # after the 16 Oct close
START = datetime(2023, 11, 6, 13, 0, tzinfo=timezone.utc)      # the Yahoo cache's first day
COST = 0.0005


def bars(symbols, tf: str) -> dict:
    """Regular-session SIP bars between START and END (alpaca.bars_30m with a
    fixed window and any timeframe)."""
    params = {"symbols": ",".join(symbols), "timeframe": tf, "adjustment": "all", "start": START.isoformat(),
              "end": END.isoformat(), "limit": 10000, "feed": "sip"}
    rows = {s: [] for s in symbols}
    while True:
        js = alpaca._get(f"{alpaca.DATA}/v2/stocks/bars", params)
        for s, b in (js.get("bars") or {}).items():
            rows[s].extend(b)
        if not js.get("next_page_token"):
            break
        params["page_token"] = js["next_page_token"]
    out = {}
    for s, b in rows.items():
        if not b:
            continue
        df = pd.DataFrame(b)
        df.index = pd.to_datetime(df["t"], utc=True).dt.tz_convert(NY)
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})[
            ["open", "high", "low", "close", "volume"]]
        hm = df.index.hour * 60 + df.index.minute
        out[s] = df[(hm >= 570) & (hm < 960)]
    return out


def period(t):
    return "explore" if t < SPLIT else "holdout" if t < FWD else "forward"


def st(r) -> dict:
    r = np.asarray(r, float)
    n = len(r)
    if not n:
        return dict(n=0)
    w, l = r[r > 0], r[r <= 0]
    sd = r.std(ddof=1) if n > 1 else 0.0
    return dict(n=n, win=100 * len(w) / n, wins=len(w), losses=len(l), avg=100 * r.mean(),
                pf=w.sum() / -l.sum() if l.sum() < 0 else float("inf"), total=100 * r.sum(),
                avg_w=100 * w.mean() if len(w) else 0.0, avg_l=100 * l.mean() if len(l) else 0.0,
                t=r.mean() / sd * math.sqrt(n) if sd > 0 else 0.0)


def row(name, r) -> str:
    s = st(r)
    if not s["n"]:
        return f"| {name} | 0 | | | | | |"
    return (f"| {name} | {s['n']} | {s['win']:.1f}% ({s['wins']}/{s['losses']}) | {s['avg']:+.2f}% | {s['pf']:.2f} | "
            f"{s['avg_w']:+.2f}% / {s['avg_l']:+.2f}% | {s['t']:+.2f} |")


HDR = "| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | t |\n|---|---|---|---|---|---|---|"


def px_at(q: dict, sym: str, t: pd.Timestamp, minutes: int) -> float:
    """Open of the 15-minute bar starting `minutes` after t (the price a trader
    acting then would see); nan if missing."""
    df = q.get(sym)
    if df is None:
        return float("nan")
    ts = t + pd.Timedelta(minutes=minutes)
    i = df.index.searchsorted(ts)
    if i >= len(df) or df.index[i].normalize() != ts.normalize():
        return float("nan")
    return float(df["open"].iloc[i])


def delayed(tr: pd.DataFrame, q: dict, minutes: int) -> pd.Series:
    out = []
    for r in tr.itertuples():
        e, x = r.entry, r.exit
        if not (r.entry_time.hour == 9 and r.entry_time.minute == 30):
            e2 = px_at(q, r.ticker, r.entry_time, minutes)
            e = e2 if e2 == e2 else e
        if r.reason not in ("stop", "open") and not (r.exit_time.hour == 9 and r.exit_time.minute == 30):
            x2 = px_at(q, r.ticker, r.exit_time, minutes)
            x = x2 if x2 == x2 else x
        out.append(r.side * (x / e - 1) - 2 * COST)
    return pd.Series(out, index=tr.index)


def main():
    cfg = load_cfg()
    s0 = cfg["strategies"][0]
    u = s0["universe"]
    p = Params(**s0["params"])
    msym = cfg.get("market", "SPY")
    syms = sorted({msym, *u["pool"]})
    d30 = bars(syms, "30Min")
    hours = {t: complete_hours(df) for t, df in d30.items() if len(df) > 1000}
    mkt = hours.pop(msym)
    members = monthly_members(hours, u["top_k"], u["vol_lookback_days"])
    ev = earnings.load(sorted(hours))
    tr = backtest(p, hours, mkt, members, ev)
    tr["period"] = tr.entry_time.map(period)
    tr = tr[tr.entry_time >= pd.Timestamp("2024-05-01", tz=NY)].sort_values("entry_time").reset_index(drop=True)
    q = bars(syms, "15Min")
    tr["ret15"], tr["ret30"] = delayed(tr, q, 15), delayed(tr, q, 30)

    L = ["# Swing audit: the live rule on the live data path (Alpaca SIP), and the 17-minute delay", "",
         f"Rule: `{p.key()}`. SIP 30-minute bars {START:%Y-%m-%d} to {END:%Y-%m-%d} made hourly by "
         "`scanner.complete_hours`; universe and earnings as `retune.backtest`. Trades entered from 2024-05-01 "
         "(the Yahoo backtest's first). 0.05% a side.", "", "## 1. Backtest on live data, fills as the research assumes", "", HDR]
    J = {}
    for k in ("explore", "holdout", "forward"):
        part = tr[tr.period == k]
        L.append(row(k, part.ret))
        J[k] = {c: st(part[c]) for c in ("ret", "ret15", "ret30")}
    L.append(row("all", tr.ret))
    L += ["", "## 2. The same trades filled late (SIP 15-minute bars)", "",
          "| period | at the bar (backtest) | +15 min | +30 min | change at +15 |", "|---|---|---|---|---|"]
    for k in ("explore", "holdout", "forward", "all"):
        part = tr if k == "all" else tr[tr.period == k]
        if len(part):
            a, b, c = (100 * part[x].mean() for x in ("ret", "ret15", "ret30"))
            L.append(f"| {k} | {a:+.2f}% | {b:+.2f}% | {c:+.2f}% | {b - a:+.2f}% |")
    L += ["", "Win %, holdout: " + ", ".join(f"{nm} {st(tr[tr.period == 'holdout'][c]).get('win', 0):.1f}%"
                                             for nm, c in (("bar", "ret"), ("+15", "ret15"), ("+30", "ret30"))), ""]

    # 3. against the Yahoo backtest
    y = pd.read_csv(ROOT / "reports" / "audit_trades.csv", parse_dates=["entry_time", "exit_time"])
    y["entry_time"] = pd.to_datetime(y.entry_time, utc=True).dt.tz_convert(NY)
    y["key"] = y.ticker + y.entry_time.astype(str)
    tr["key"] = tr.ticker + tr.entry_time.astype(str)
    both = set(y.key) & set(tr.key)
    yo, ao = y[~y.key.isin(both)], tr[~tr.key.isin(both)]
    L += ["## 3. Live data vs the Yahoo research data, signal by signal", "",
          "| | trades | avg net per trade |", "|---|---|---|",
          f"| same entry bar on both | {len(both)} | Yahoo {100 * y[y.key.isin(both)].ret.mean():+.2f}% / SIP {100 * tr[tr.key.isin(both)].ret.mean():+.2f}% |",
          f"| Yahoo only | {len(yo)} | {100 * yo.ret.mean():+.2f}% |",
          f"| SIP only (live data) | {len(ao)} | {100 * ao.ret.mean():+.2f}% |", "",
          "Hourly volume differs between the two sources, so the weekly VWAP and its crosses differ; the research "
          "numbers are not the numbers of the bars the scanner trades.", ""]
    J["overlap"] = dict(both=len(both), yahoo_only=len(yo), sip_only=len(ao))

    # 4. the live ledger
    lg_path = ROOT / "state" / "ledger.csv"
    if lg_path.exists():
        lg = pd.read_csv(lg_path)
        L += ["## 4. Live ledger prices vs a +15-minute fill", "",
              "| ticker | entry bar | ledger entry | +15 min | ledger exit | +15 min | ledger result | at +15 min |",
              "|---|---|---|---|---|---|---|---|"]
        for r in lg.itertuples():
            et = pd.Timestamp(r.entry_time).tz_convert(NY)       # the bar after the signal; price = signal close
            xt = pd.Timestamp(r.exit_time).tz_convert(NY)        # the bar the exit was seen on; price = its close
            e15 = px_at(q, r.ticker, et, 0 if (et.hour, et.minute) == (9, 30) else 15)
            if r.reason == "stop":
                x15 = r.exit
            elif (xt.hour, xt.minute) == (15, 30):               # seen after the close: next open
                x15 = px_at(q, r.ticker, xt + pd.Timedelta(hours=17, minutes=30), 0)
            else:
                x15 = px_at(q, r.ticker, xt + pd.Timedelta(hours=1), 15)
            r15 = (x15 / e15 - 1) * 100 if e15 == e15 and x15 == x15 else float("nan")
            L.append(f"| {r.ticker} | {et:%Y-%m-%d %H:%M} | {r.entry:.2f} | {e15:.2f} | {r.exit:.2f} | {x15:.2f} | {100 * r.ret:+.2f}% | {r15:+.2f}% |")
        L.append("")
    (ROOT / "reports" / "audit_live.md").write_text("\n".join(L) + "\n")
    (ROOT / "reports" / "audit_live.json").write_text(json.dumps(J, indent=1, default=float))
    tr.drop(columns=["key"]).to_csv(ROOT / "reports" / "audit_live_trades.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
