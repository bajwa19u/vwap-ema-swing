"""Daily recap card. Shared by the live job (python -m src.recap, after the
close) and the replay. Posts once per day."""
from __future__ import annotations

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src import alpaca, discord
from src.scanner import EVENTS, ROOT, complete_hours, load_cfg, read_events
from src.strategy import Params, indicators

NY = ZoneInfo("America/New_York")
LAST = ROOT / "state" / "recap_last.txt"


def build(day: pd.Timestamp, day_events: list[dict], state: dict, hours: dict, mkt: pd.DataFrame,
          p: Params, week_rets: list[float], ts: str | None = None) -> dict:
    opened = [{"t": e["t"]} for e in day_events if e["kind"] == "entry"]
    closed = [{"t": e["t"], "ret": float(e["ret"])} for e in day_events if e["kind"] == "exit"]
    open_pos = []
    for key, rec in state.items():
        t = key.split(":", 1)[1]
        if t in hours:
            last = float(hours[t]["close"].iloc[-1])
            open_pos.append({"t": t, "unreal": rec["side"] * (last / rec["price"] - 1)})
    daily = mkt["close"].groupby(mkt.index.normalize()).last()
    spy_pct = 100 * (daily.iloc[-1] / daily.iloc[-2] - 1) if len(daily) > 1 else None
    trend_on = bool(indicators(mkt, Params(ema=p.ema, vwap=p.vwap))["above"].iloc[-1])
    return discord.recap_card(f"{day:%a, %b %-d}", opened, closed, open_pos, spy_pct, trend_on, week_rets, ts)


def main(force: bool = False) -> None:
    import json
    cfg = load_cfg()
    now = datetime.now(NY)
    today = now.date().isoformat()
    if not force and (now.hour * 60 + now.minute < 16 * 60 + 15 or
                      (LAST.exists() and LAST.read_text().strip() == today)):
        print("not after the close, or already posted today")
        return
    state = json.loads((ROOT / "state" / "state.json").read_text()) if (ROOT / "state" / "state.json").exists() else {}
    ev = read_events()
    ev["day"] = ev["bar"].astype(str).str[:10]
    monday = (pd.Timestamp(today) - pd.Timedelta(days=pd.Timestamp(today).weekday())).date().isoformat()
    week = ev[(ev.kind == "exit") & (ev.day >= monday)]["ret"].astype(float).tolist()
    msym = cfg.get("market", "SPY")
    held = sorted({k.split(":", 1)[1] for k in state})
    data = alpaca.bars_30m(sorted({msym, *held}), days=60)
    hours = {t: complete_hours(df) for t, df in data.items() if len(df)}
    if hours[msym].index[-1].date().isoformat() != today:
        print("market closed today; no recap")
        return
    p = Params(**cfg["strategies"][0]["params"])
    card = build(pd.Timestamp(today), ev[ev.day == today].to_dict("records"), state, hours, hours[msym], p, week)
    discord.post(cfg, card)
    LAST.write_text(today)
    print("recap posted")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
