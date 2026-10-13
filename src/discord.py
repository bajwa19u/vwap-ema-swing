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
DISCLAIMER = "Signals only, not financial advice"


def _f(x) -> str:
    return "-" if x is None else f"{x:,.2f}"


def _pct(x: float) -> str:
    return f"{x:+.2f}%"


def strike_near(px: float) -> float:
    """An in-the-money strike, ~0.85 delta for 3-4 weeks out."""
    inc = 1 if px < 50 else 2.5 if px < 100 else 5 if px < 500 else 10
    return math.floor(px * 0.88 / inc) * inc


def contract_text(t: str, side: int, price: float, opt: dict | None) -> str:
    kind = "C" if side > 0 else "P"
    if opt:
        return (f"{t} {opt['strike']:g}{kind} · exp {opt['expiry']} · delta {opt['delta']} · "
                f"mid {_f(opt['mid'])}")
    k = strike_near(price) if side > 0 else math.ceil(price * 1.03 / (5 if price >= 100 else 1)) * (5 if price >= 100 else 1)
    return f"{t} ~{k:g}{kind} · 3-4 weeks out · ~0.85 delta"


def _sign(x: float) -> str:
    return f"{x:+.2f}%".replace("-", "−")


# House style, shared with the day-trade channels (tradingbot/src/cards.py):
#   🔔 BUY CALLS / BUY PUTS in one neutral colour; 🟢 SOLD for a profit, 🔴 SOLD for a loss;
#   a daily report with today, the last 5 days, last week and month to date.
def entry_card(t: str, side: int, price: float, stop: float | None, contract: str,
               bar_label: str, ts: str | None = None) -> dict:
    kind = "CALLS" if side > 0 else "PUTS"
    card = {"title": f"🔔 BUY {kind} · {t}", "color": BLUE,
            "description": (f"Hourly 21-EMA crossed {'above' if side > 0 else 'below'} the weekly VWAP with the market "
                            f"trend {'up' if side > 0 else 'down'}."),
            "fields": [{"name": "Entry", "value": _f(price), "inline": True},
                       {"name": "Stop", "value": _f(stop), "inline": True},
                       {"name": "Exit plan", "value": "When the trend turns · typically 3–5 days", "inline": True},
                       {"name": "Suggested contract", "value": contract, "inline": False}],
            "footer": {"text": f"Swing · {bar_label} · Levels are the stock price · {DISCLAIMER}"}}
    if ts:
        card["timestamp"] = ts
    return card


def exit_card(t: str, side: int, entry: float, exit_: float, ret: float, days: float,
              why: str, ts: str | None = None) -> dict:
    won = ret > 0
    kind = "CALLS" if side > 0 else "PUTS"
    card = {"title": f"{'🟢' if won else '🔴'} SOLD · {t} {kind} · {_sign(100 * ret)}",
            "color": GREEN if won else RED,
            "fields": [{"name": "Bought", "value": _f(entry), "inline": True},
                       {"name": "Sold", "value": _f(exit_), "inline": True},
                       {"name": "Held", "value": f"{days:.1f} days", "inline": True},
                       {"name": "Result", "value": f"**{_sign(100 * ret)}** on the stock · {_sign(10 * ret)} of account",
                        "inline": True},
                       {"name": "Closed by", "value": WHY.get(why, why).capitalize(), "inline": True}],
            "footer": {"text": f"Swing · Close the {kind.lower()[:-1]} position · {DISCLAIMER}"}}
    if ts:
        card["timestamp"] = ts
    return card


def windows(ledger, day) -> list[tuple[str, dict]]:
    """Today, the last 5 sessions, last calendar week (Mon-Fri), month to date.
    ledger: closed trades with exit_time and ret (fraction); account = 10% a position."""
    import datetime as dt
    import pandas as pd
    if ledger is None or not len(ledger):
        ledger = pd.DataFrame(columns=["exit_time", "ret"])
    d = pd.to_datetime(ledger["exit_time"].astype(str).str[:10]).dt.date
    acct = ledger["ret"].astype(float) * 10                     # % of account at 10% per position

    def st(m):
        r = acct[m]
        w = int((r > 0).sum())
        return {"n": len(r), "won": w, "lost": len(r) - w, "total": float(r.sum()), "win": 100 * w / len(r) if len(r) else None}
    sessions = sorted({x for x in d if x <= day} | {day})
    monday = day - dt.timedelta(days=day.weekday())
    lw0, lw1 = monday - dt.timedelta(days=7), monday - dt.timedelta(days=3)
    return [("Today", st(d == day)), ("Last 5 days", st(d.isin(set(sessions[-5:])))),
            (f"Last week ({lw0:%-d}–{lw1:%-d %b})", st((d >= lw0) & (d <= lw1))),
            (f"{day:%B} to date", st((d >= day.replace(day=1)) & (d <= day)))]


def _window_value(s: dict) -> str:
    if not s["n"]:
        return "No closed trades"
    return f"**{_sign(s['total'])}**\nWin rate {s['win']:.0f}%\n{s['won']} won · {s['lost']} lost"


def recap_card(day_label: str, opened: list[dict], closed: list[dict], open_pos: list[dict],
               spy_pct: float | None, trend_on: bool | None, wtd: list[float] | None = None,
               ts: str | None = None, ledger=None, day=None) -> dict:
    """opened: {t}; closed: {t, ret}; open_pos: {t, unreal}. Returns are fractions."""
    realized = sum(c["ret"] for c in closed)
    lines = [f"{'🟢' if c['ret'] > 0 else '🔴'} **{c['t']}** Calls sold  ·  **{_sign(100 * c['ret'])}** on the stock"
             for c in closed]
    lines += [f"🔔 **{o['t']}** Calls bought" for o in opened]
    lines += [f"⏳ **{q['t']}** open  ·  {_sign(100 * q['unreal'])}" for q in open_pos]
    market = ""
    if spy_pct is not None:
        market = (f"\n\nSPY {_sign(spy_pct)} on the day · trend filter "
                  f"{'on: new entries allowed' if trend_on else 'off: no new entries'}")
    fields = ([{"name": nm, "value": _window_value(s), "inline": True} for nm, s in windows(ledger, day)]
              if day is not None else
              [{"name": "Today", "value": (f"**{_sign(10 * realized)}** of account\n{sum(c['ret'] > 0 for c in closed)} won · "
                                          f"{sum(c['ret'] <= 0 for c in closed)} lost") if closed else "No closed trades",
                "inline": True}])
    card = {"title": "📊 Swing · Daily Report", "color": GREEN if realized > 0 else RED if realized < 0 else GREY,
            "description": f"**{day_label}**\n\n" + ("\n".join(lines) if lines else "No trades today.") + market,
            "fields": fields,
            "footer": {"text": f"Account % assumes 10% of the account per position · {DISCLAIMER}"}}
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
