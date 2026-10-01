"""Earnings dates for the earnings rules (Params.earn_skip / earn_exit).
Cached in state/earnings.json and refreshed at most once a day from Yahoo.
Fails open: if the fetch fails, the old cache (or nothing) is used."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "state" / "earnings.json"


def _fetch(symbols: list[str]) -> dict[str, list[str]]:
    import yfinance as yf
    out = {}
    for t in symbols:
        try:
            d = yf.Ticker(t).get_earnings_dates(limit=12)
            out[t] = sorted(str(ts.tz_convert("America/New_York")) for ts in d.index)
        except Exception as e:  # one bad symbol must not stop the rest
            print(f"earnings: {t} failed ({e.__class__.__name__})")
    return out


def load(symbols: list[str], max_age_hours: float = 20) -> dict[str, list[str]]:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {"updated": "", "dates": {}}
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(cache["updated"])
    except ValueError:
        age = timedelta(days=999)
    missing = [t for t in symbols if t not in cache["dates"]]
    if age > timedelta(hours=max_age_hours) or missing:
        try:
            fresh = _fetch(symbols)
            if fresh:
                cache["dates"].update(fresh)
                cache["updated"] = datetime.now(timezone.utc).isoformat()
                CACHE.parent.mkdir(exist_ok=True)
                CACHE.write_text(json.dumps(cache, indent=0))
        except Exception as e:
            print(f"earnings: refresh failed ({e.__class__.__name__}); using cache")
    return cache["dates"]
