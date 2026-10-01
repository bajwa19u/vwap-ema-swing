"""Replay recent sessions bar by bar through the live decision code and post
the cards to Discord in order, with a recap after each day, as if live.
Positions are warmed up on the sessions before the window (not posted).

Usage: python -m src.replay [sessions=5] [--dry]
"""
from __future__ import annotations

import sys
import time

import pandas as pd

from src import alpaca, discord, earnings, recap
from src.scanner import bar_close, card_for, complete_hours, load_cfg, scan_once
from src.strategy import Params


def main(sessions: int = 5, dry: bool = False, warmup: int = 10, delay: float = 2.2, seed: bool = False) -> None:
    """seed=True: afterwards hand the replayed open positions to the live bot
    (state/state.json) and mark the last replayed day's recap as posted."""
    cfg = load_cfg()
    s0 = cfg["strategies"][0]
    p = Params(**s0["params"])
    msym = cfg.get("market", "SPY")
    syms = sorted({msym, *s0["universe"]["pool"]})
    data = alpaca.bars_30m(syms, days=cfg.get("history_days", 300) + 40)
    full = {t: complete_hours(df) for t, df in data.items() if len(df) > 100}
    mkt_all = full[msym]
    ev = earnings.load(sorted(set(full) - {msym}))
    days = sorted({d for d in mkt_all.index.normalize()
                   if (mkt_all.index == d + pd.Timedelta(hours=15, minutes=30)).any()})
    window, warm = days[-sessions:], days[-sessions - warmup:-sessions]
    state: dict = {}
    cards = []

    def step(t_bar):
        hrs = {t: h[h.index <= t_bar] for t, h in full.items()}
        return scan_once(cfg, state, hrs, hrs[msym], ev, live=False, asof=t_bar), hrs

    for d in warm:  # silent: just build the positions we'd be carrying
        for t_bar in mkt_all.index[mkt_all.index.normalize() == d]:
            step(t_bar)
    carried = sorted(k.split(":", 1)[1] for k in state)
    span = f"{window[0]:%a %b %-d}" if len(window) == 1 else f"{window[0]:%b %-d} – {window[-1]:%b %-d}"
    intro = (f"Replaying {span} bar by bar, exactly as the bot would have posted. "
             f"Each card is timestamped with its original time.\n"
             f"Positions already open going in: {', '.join(carried) or 'none'}.")
    cards.append(discord.info_card("⏪ Replay", intro))
    week: list[float] = []
    for d in window:
        if d.weekday() == 0:
            week = []
        today = []
        for t_bar in mkt_all.index[mkt_all.index.normalize() == d]:
            evs, hrs = step(t_bar)
            ts = (bar_close(t_bar) + pd.Timedelta(minutes=17)).isoformat()
            for e in evs:
                c = card_for(e, ts)
                c["title"] = f"⏪ REPLAY {d:%a %b %-d} · " + c["title"]
                cards.append(c)
                today.append(e)
                if e["kind"] == "exit":
                    week.append(e["ret"])
        close_ts = (d + pd.Timedelta(hours=16, minutes=20)).isoformat()
        rc = recap.build(d, today, state, hrs, hrs[msym], p, list(week), close_ts)
        rc["title"] = "⏪ REPLAY · " + rc["title"]
        cards.append(rc)
    cards.append(discord.info_card("⏹ End of replay",
                 "Everything above was a replay. Live signals and the daily recap continue from here"
                 + (f", holding: {', '.join(sorted(k.split(':', 1)[1] for k in state)) or 'nothing'}." if seed else ".")))
    for c in cards:
        print(c["title"], "|", (c.get("description") or "")[:110].replace("\n", " "))
        if not dry:
            discord.post(cfg, c)
            time.sleep(delay)
    print(f"{len(cards)} cards")
    if seed and not dry:
        import json
        from src.recap import LAST
        from src.scanner import STATE
        STATE.write_text(json.dumps(state, indent=1, default=str))
        LAST.write_text(f"{window[-1]:%Y-%m-%d}")
        print("seeded live state:", sorted(state))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(int(args[0]) if args else 5, dry="--dry" in sys.argv, seed="--seed" in sys.argv)
