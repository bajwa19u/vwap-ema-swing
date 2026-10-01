"""Hourly live scanner. Runs the exact backtest code over fresh Alpaca bars,
diffs the result against state/state.json, and posts new entries / exits to
Discord. Safe to run more than once per hour (idempotent).

Usage: python -m src.scanner [--dry]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src import alpaca, discord
from src.strategy import Params, indicators, simulate
from src.universe import top_by_vol

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "state.json"
LEDGER = ROOT / "state" / "ledger.csv"


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def complete_hours(df30: pd.DataFrame) -> pd.DataFrame:
    h = alpaca.to_hourly(df30)
    last = h.index[-1]
    full = h["n30"].iloc[-1] == 2 or (last.hour, last.minute) == (15, 30)
    return (h if full else h.iloc[:-1]).drop(columns="n30")


def next_slot(t: pd.Timestamp) -> pd.Timestamp:
    if (t.hour, t.minute) < (15, 30):
        return t + pd.Timedelta(hours=1)
    d = t.tz_localize(None).normalize() + pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d += pd.Timedelta(days=1)
    return (d + pd.Timedelta(hours=9, minutes=30)).tz_localize(t.tz)  # wall clock, DST-safe


def with_phantom(h: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Append a placeholder next bar at the last close so a signal on the last
    completed bar produces a trade (the backtest fills at the next open)."""
    t = next_slot(h.index[-1])
    c = h["close"].iloc[-1]
    ph = pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 0.0}, index=[t])
    return pd.concat([h, ph]), t


def strategy_bar_complete(h: pd.DataFrame, p: Params) -> bool:
    if p.tf == 1:
        return True
    n_today = (h.index.normalize() == h.index[-1].normalize()).sum()
    return n_today % p.tf == 0 or n_today == 7


def evaluate(h: pd.DataFrame, mkt: pd.DataFrame, p: Params, cur: dict | None):
    """Pure decision step for one ticker. Returns (exit_info | None, entry_info | None)."""
    hp, ph_time = with_phantom(h)
    mp = mkt.reindex(hp.index).ffill()
    trades = simulate(hp, p, cost=0, market=mp)
    exit_info = entry_info = None
    if cur:
        since = pd.Timestamp(cur["entry_time"])
        match = [x for x in trades if x["entry_time"] >= since and x["side"] == cur["side"]]
        x = match[0] if match else None
        if x is None or x["reason"] != "open":
            exit_info = (x["exit"] if x else float(h["close"].iloc[-1]), x["reason"] if x else "reset")
            cur = None
    if cur is None and trades and trades[-1]["entry_time"] == ph_time and trades[-1]["reason"] == "open":
        entry_info = (trades[-1], ph_time, indicators(h, p, mkt).iloc[-1])
    return exit_info, entry_info


def run(dry: bool = False) -> None:
    cfg = load_cfg()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    mkt_sym = cfg.get("market", "SPY")
    pools = {s["name"]: s["universe"]["pool"] for s in cfg["strategies"]}
    symbols = sorted({mkt_sym, *(t for pool in pools.values() for t in pool)})
    data = alpaca.bars_30m(symbols, days=cfg.get("history_days", 300))
    hours = {t: complete_hours(df) for t, df in data.items() if len(df) > 100}
    mkt = hours[mkt_sym]
    posts, closed = [], []
    for s in cfg["strategies"]:
        p = Params(**s["params"])
        u = s["universe"]
        active = top_by_vol({t: hours[t] for t in u["pool"] if t in hours}, u["top_k"], u["vol_lookback_days"])
        held = [k.split(":", 1)[1] for k in state if k.startswith(s["name"] + ":")]
        for t in sorted(set(active) | set(held)):
            if t not in hours:
                continue
            h = hours[t]
            if h.index[-1] != mkt.index[-1] or not strategy_bar_complete(h, p):
                continue  # stale/halted symbol, or a higher-tf bar still forming
            key = f"{s['name']}:{t}"
            cur = state.get(key)
            exit_info, entry_info = evaluate(h, mkt, p, cur)
            if exit_info:
                px, why = float(exit_info[0]), exit_info[1]
                ret = cur["side"] * (px / cur["price"] - 1)
                posts.append(discord.exit_card(s, t, cur, px, why, ret))
                closed.append(dict(strategy=s["name"], ticker=t, side=cur["side"],
                                   entry_time=cur["entry_time"], entry=cur["price"],
                                   exit_time=str(h.index[-1]), exit=px, reason=why, ret=ret))
                state.pop(key)
            if entry_info and t in active:
                x, ph_time, ind = entry_info
                price = float(h["close"].iloc[-1])
                stop = price - x["side"] * p.stop_atr * ind.atr if p.stop_atr else None
                tgt = price + x["side"] * p.target_atr * ind.atr if p.target_atr else None
                opt = alpaca.option_pick(t, x["side"], price, **cfg["options"]) if cfg.get("options") else None
                rec = dict(side=int(x["side"]), price=price,
                           stop=float(stop) if stop is not None else None,
                           target=float(tgt) if tgt is not None else None,
                           entry_time=str(ph_time), signal_time=str(h.index[-1]), option=opt)
                state[key] = rec
                posts.append(discord.entry_card(s, t, rec, ind))
    for card in posts:
        print(json.dumps(card, default=str)[:300])
        if not dry:
            discord.post(cfg, card)
    if not dry:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1, default=str))
        if closed:
            pd.DataFrame(closed).to_csv(LEDGER, mode="a", header=not LEDGER.exists(), index=False)
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z last bar {mkt.index[-1]}, "
          f"{len(posts)} alerts, {len(state)} open")


if __name__ == "__main__":
    if "--hello" in sys.argv:
        discord.post(load_cfg(), discord.info_card("VWAP x EMA bot connected",
                     "Scanning hourly during market hours. Weekly scorecard on Saturdays."))
    else:
        run(dry="--dry" in sys.argv)
