"""Discord cards. House rules: no dollar signs, no share counts; report win %,
profit % and winners vs losers. Labels are plain: BUY CALL / BUY PUT,
TAKE PROFIT / STOP LOSS, and a daily recap."""
from __future__ import annotations

import math
import os
import time

import requests

GREEN, RED, GREY, BLUE, GOLD = 0x2ECC71, 0xE74C3C, 0x95A5A6, 0x5865F2, 0xF1C40F
WHY = {"cross": "trend flipped (EMA back under VWAP)", "stop": "protective stop hit", "target": "target hit",
       "time": "time stop", "reset": "signal no longer valid", "earnings": "closed ahead of earnings"}
FOOTER = "VWAP x EMA · 1h swing · not financial advice"


def _f(x) -> str:
    return "-" if x is None else f"{x:,.2f}"


def _pct(x: float) -> str:
    return f"{x:+.2f}%"


def strike_near(px: float) -> float:
    """A slightly in-the-money strike (~0.65 delta for 3-6 weeks)."""
    inc = 1 if px < 50 else 2.5 if px < 100 else 5 if px < 500 else 10
    return math.floor(px * 0.97 / inc) * inc


def contract_text(t: str, side: int, price: float, opt: dict | None) -> str:
    kind = "C" if side > 0 else "P"
    if opt:
        return (f"{t} {opt['strike']:g}{kind} · exp {opt['expiry']} · delta {opt['delta']} · "
                f"mid {_f(opt['mid'])}")
    k = strike_near(price) if side > 0 else math.ceil(price * 1.03 / (5 if price >= 100 else 1)) * (5 if price >= 100 else 1)
    return f"{t} ~{k:g}{kind} · 3-6 weeks out · ~0.65 delta"


def entry_card(t: str, side: int, price: float, stop: float | None, contract: str,
               bar_label: str, ts: str | None = None) -> dict:
    call = side > 0
    card = {"title": f"{'🟢 BUY CALL' if call else '🔴 BUY PUT'}  ·  {t}",
            "color": GREEN if call else RED,
            "description": (f"**Entry** {_f(price)}   **Stop** {_f(stop)}\n"
                            f"**Contract** {contract}\n"
                            f"**Why** 1h EMA21 crossed {'above' if call else 'below'} the weekly VWAP, market trend "
                            f"{'up' if call else 'down'}.\n"
                            f"**Plan** hold until the trend flips. Typical hold 3-5 days."),
            "footer": {"text": f"{FOOTER} · {bar_label}"}}
    if ts:
        card["timestamp"] = ts
    return card


def exit_card(t: str, side: int, entry: float, exit_: float, ret: float, days: float,
              why: str, ts: str | None = None) -> dict:
    won = ret > 0
    card = {"title": f"{'✅ TAKE PROFIT' if won else '🛑 STOP LOSS'}  ·  {t}",
            "color": GREEN if won else RED,
            "description": (f"**{_pct(100 * ret)}** on the stock  ·  {_f(entry)} → {_f(exit_)}\n"
                            f"**Held** {days:.1f} days  ·  {WHY.get(why, why)}\n"
                            f"Close the {'call' if side > 0 else 'put'}."),
            "footer": {"text": FOOTER}}
    if ts:
        card["timestamp"] = ts
    return card


def recap_card(day_label: str, opened: list[dict], closed: list[dict], open_pos: list[dict],
               spy_pct: float | None, trend_on: bool | None, wtd: list[float] | None = None,
               ts: str | None = None) -> dict:
    """opened: {t}; closed: {t, ret}; open_pos: {t, unreal}. Returns are fractions."""
    wins = [c for c in closed if c["ret"] > 0]
    realized = sum(c["ret"] for c in closed)
    parts = []
    if opened:
        parts.append(f"{len(opened)} new call{'s' if len(opened) > 1 else ''}: {', '.join(o['t'] for o in opened)}.")
    else:
        parts.append("No new entries.")
    tp = [f"{c['t']} ({_pct(100 * c['ret'])})" for c in closed if c["ret"] > 0]
    sl = [f"{c['t']} ({_pct(100 * c['ret'])})" for c in closed if c["ret"] <= 0]
    if tp:
        parts.append("Took profit on " + ", ".join(tp) + ".")
    if sl:
        parts.append("Cut " + ", ".join(sl) + ".")
    if spy_pct is not None:
        mood = "trend filter on, entries allowed" if trend_on else "trend filter off, no new entries"
        parts.append(f"SPY {_pct(spy_pct)} on the day; {mood}.")
    fields = [
        {"name": "Closed", "value": f"{len(wins)} win{'s' * (len(wins) != 1)} · {len(closed) - len(wins)} loss"
                                    f"{'es' * (len(closed) - len(wins) != 1)}" if closed else "none", "inline": True},
        {"name": "Win rate", "value": f"{100 * len(wins) / len(closed):.0f}%" if closed else "-", "inline": True},
        {"name": "Realized", "value": f"{_pct(100 * realized)} stock · {_pct(10 * realized)} account" if closed else "-",
         "inline": True},
        {"name": "Open positions", "value": "  ".join(f"{p['t']} {_pct(100 * p['unreal'])}" for p in open_pos) or "flat"},
    ]
    if wtd is not None:
        w = [r for r in wtd]
        fields.append({"name": "Week so far", "value": (f"{sum(r > 0 for r in w)}W / {sum(r <= 0 for r in w)}L · "
                                                         f"{_pct(10 * sum(w))} account") if w else "no closed trades",
                       "inline": True})
    card = {"title": f"📊 Daily Recap  ·  {day_label}", "color": GOLD, "description": " ".join(parts),
            "fields": fields, "footer": {"text": "Account % assumes 10% of the account per position · " + FOOTER}}
    if ts:
        card["timestamp"] = ts
    return card


def info_card(title: str, text: str) -> dict:
    return {"title": title, "description": text[:4000], "color": BLUE}


def post(cfg: dict, card: dict) -> None:
    url = os.environ.get(cfg.get("webhook_env", "DISCORD_WEBHOOK_VWAP"))
    if not url:
        print("no webhook configured; skipping post")
        return
    for _ in range(5):
        r = requests.post(url, json={"username": cfg.get("bot_name", "VWAP x EMA"), "embeds": [card]}, timeout=20)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)) + 0.2)
            continue
        r.raise_for_status()
        return
