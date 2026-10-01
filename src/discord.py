"""Discord webhook cards. House rules: no dollar signs, no share counts;
report win %, profit % and winners vs losers."""
from __future__ import annotations

import os
import time

import requests

GREEN, RED, GREY, BLUE = 0x2ECC71, 0xE74C3C, 0x95A5A6, 0x3498DB


def _f(x) -> str:
    return "-" if x is None else f"{x:,.2f}"


def _vwap_name(v: str) -> str:
    return {"session": "daily VWAP", "week": "weekly VWAP", "month": "monthly VWAP"}.get(
        v, f"{v[4:]}-bar rolling VWAP" if v.startswith("roll") else v)


def entry_card(s: dict, t: str, rec: dict, ind) -> dict:
    p = s["params"]
    long_ = rec["side"] > 0
    tf = {1: "1h", 2: "2h", 4: "4h"}[p["tf"]]
    fields = [
        {"name": "Entry (approx)", "value": _f(rec["price"]), "inline": True},
        {"name": "Stop", "value": _f(rec["stop"]), "inline": True},
        {"name": "Target", "value": _f(rec["target"]) if rec["target"] else "trail: exit on cross back", "inline": True},
        {"name": "Setup", "value": f"{tf} EMA{p['ema']} crossed {'above' if long_ else 'below'} the "
                                   f"{_vwap_name(p['vwap'])} (EMA {_f(ind.ema)} / VWAP {_f(ind.vwap)})"},
        {"name": "Exit plan", "value": "Stop is a resting order. Otherwise hold until the EMA closes back "
                                       f"{'below' if long_ else 'above'} the VWAP. Typical hold: "
                                       f"{s.get('typical_days', 'a few')} days."},
    ]
    o = rec.get("option")
    if o:
        kind = "call" if long_ else "put"
        fields.append({"name": "Options idea", "value":
                       f"`{o['symbol']}`: {t} {o['expiry']} {o['strike']:g} {kind}, delta {o['delta']}, "
                       f"mid {_f(o['mid'])}, IV {o['iv']}%, spread {o['spread_pct']}%"})
    if s.get("stats"):
        fields.append({"name": "Backtest for this setup", "value": s["stats"]})
    return {"title": f"{'🟢 LONG' if long_ else '🔴 SHORT'} {t}  ·  {s['name']}",
            "color": GREEN if long_ else RED, "fields": fields,
            "footer": {"text": "Signal on bar close. Not financial advice."}}


def exit_card(s: dict, t: str, cur: dict, px: float, why: str, ret: float) -> dict:
    words = {"cross": "EMA crossed back through VWAP", "stop": "stop hit", "target": "target hit",
             "time": "time stop", "reset": "position no longer valid"}
    won = ret > 0
    return {"title": f"{'✅' if won else '❌'} EXIT {t}  ·  {s['name']}",
            "color": GREEN if won else RED if ret < 0 else GREY,
            "fields": [{"name": "Reason", "value": words.get(why, why), "inline": True},
                       {"name": "Entry → Exit", "value": f"{_f(cur['price'])} → {_f(px)}", "inline": True},
                       {"name": "Result (stock)", "value": f"{100 * ret:+.2f}%", "inline": True}]}


def info_card(title: str, text: str) -> dict:
    return {"title": title, "description": text[:4000], "color": BLUE}


def post(cfg: dict, card: dict) -> None:
    url = os.environ.get(cfg.get("webhook_env", "DISCORD_WEBHOOK_VWAP"))
    if not url:
        print("no webhook configured; skipping post")
        return
    for _ in range(3):
        r = requests.post(url, json={"username": cfg.get("bot_name", "VWAP x EMA"),
                                     "embeds": [card]}, timeout=20)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)))
            continue
        r.raise_for_status()
        return
