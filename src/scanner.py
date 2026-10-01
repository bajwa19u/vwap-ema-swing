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

from src import alpaca, discord, earnings
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


def evaluate(h: pd.DataFrame, mkt: pd.DataFrame, p: Params, cur: dict | None, events=None):
    """Pure decision step for one ticker. Returns (exit_info | None, entry_info | None)."""
    hp, ph_time = with_phantom(h)
    mp = mkt.reindex(hp.index).ffill()
    trades = simulate(hp, p, cost=0, market=mp, events=events)
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


EVENTS = ROOT / "state" / "events.csv"


def bar_close(t: pd.Timestamp) -> pd.Timestamp:
    return min(t + pd.Timedelta(hours=1), t.normalize() + pd.Timedelta(hours=16))


def scan_once(cfg: dict, state: dict, hours: dict, mkt: pd.DataFrame, events: dict,
              live: bool = True, asof: pd.Timestamp | None = None) -> list[dict]:
    """One decision pass over data that ends at the latest completed bar.
    Mutates `state`; returns entry/exit events. Shared by live and replay."""
    out = []
    for s in cfg["strategies"]:
        p = Params(**s["params"])
        u = s["universe"]
        active = top_by_vol({t: hours[t] for t in u["pool"] if t in hours}, u["top_k"],
                            u["vol_lookback_days"], asof=asof)
        held = [k.split(":", 1)[1] for k in state if k.startswith(s["name"] + ":")]
        for t in sorted(set(active) | set(held)):
            if t not in hours:
                continue
            h = hours[t]
            if h.index[-1] != mkt.index[-1] or not strategy_bar_complete(h, p):
                continue  # stale/halted symbol, or a higher-tf bar still forming
            key = f"{s['name']}:{t}"
            cur = state.get(key)
            exit_info, entry_info = evaluate(h, mkt, p, cur, events.get(t))
            bt = h.index[-1]
            if exit_info:
                px, why = float(exit_info[0]), exit_info[1]
                ret = cur["side"] * (px / cur["price"] - 1)
                days = (bar_close(bt) - pd.Timestamp(cur["signal_time"])).total_seconds() / 86400
                out.append(dict(kind="exit", strategy=s["name"], t=t, side=cur["side"], entry=cur["price"],
                                price=px, ret=ret, days=days, why=why, bar=str(bt),
                                entry_time=cur["entry_time"]))
                state.pop(key)
            if entry_info and t in active:
                x, ph_time, ind = entry_info
                price = float(h["close"].iloc[-1])
                stop = price - x["side"] * p.stop_atr * ind.atr if p.stop_atr else None
                opt = alpaca.option_pick(t, x["side"], price, **cfg["options"]) \
                    if live and cfg.get("options") else None
                state[key] = dict(side=int(x["side"]), price=price,
                                  stop=float(stop) if stop is not None else None,
                                  entry_time=str(ph_time), signal_time=str(bar_close(bt)), option=opt)
                out.append(dict(kind="entry", strategy=s["name"], t=t, side=int(x["side"]), price=price,
                                stop=state[key]["stop"], option=opt, bar=str(bt)))
    return out


def card_for(e: dict, ts: str | None = None) -> dict:
    if e["kind"] == "entry":
        bt = pd.Timestamp(e["bar"])
        return discord.entry_card(e["t"], e["side"], e["price"], e["stop"],
                                  discord.contract_text(e["t"], e["side"], e["price"], e.get("option")),
                                  f"signal on the {bar_close(bt):%H:%M} ET bar close", ts)
    return discord.exit_card(e["t"], e["side"], e["entry"], e["price"], e["ret"], e["days"], e["why"], ts)


def run(dry: bool = False) -> None:
    cfg = load_cfg()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    mkt_sym = cfg.get("market", "SPY")
    symbols = sorted({mkt_sym, *(t for s in cfg["strategies"] for t in s["universe"]["pool"])})
    data = alpaca.bars_30m(symbols, days=cfg.get("history_days", 300))
    hours = {t: complete_hours(df) for t, df in data.items() if len(df) > 100}
    mkt = hours[mkt_sym]
    evs = scan_once(cfg, state, hours, mkt, earnings.load(sorted(set(symbols) - {mkt_sym})))
    for e in evs:
        card = card_for(e)
        print(json.dumps(card, default=str)[:300])
        if not dry:
            discord.post(cfg, card)
    if not dry:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1, default=str))
        if evs:
            log = pd.DataFrame([{k: v for k, v in e.items() if k != "option"} for e in evs])
            log.to_csv(EVENTS, mode="a", header=not EVENTS.exists(), index=False)
            ex = log[log.kind == "exit"]
            if len(ex):
                ex.rename(columns={"t": "ticker", "price": "exit", "why": "reason", "bar": "exit_time"})[
                    ["strategy", "ticker", "side", "entry_time", "entry", "exit_time", "exit", "reason", "ret"]
                ].to_csv(LEDGER, mode="a", header=not LEDGER.exists(), index=False)
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z last bar {mkt.index[-1]}, "
          f"{len(evs)} alerts, {len(state)} open")


if __name__ == "__main__":
    if "--hello" in sys.argv:
        discord.post(load_cfg(), discord.info_card("VWAP x EMA bot connected",
                     "Scanning hourly during market hours. Weekly scorecard on Saturdays."))
    else:
        run(dry="--dry" in sys.argv)
