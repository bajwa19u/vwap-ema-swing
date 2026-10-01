"""Minimal Alpaca market-data client (stocks bars + option chain snapshots).
Read-only: this project never places orders."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

DATA = "https://data.alpaca.markets"
NY = "America/New_York"


def _headers() -> dict:
    return {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
            "APCA-API-SECRET-KEY": os.environ["ALPACA_API_SECRET"]}


def _get(url: str, params: dict) -> dict:
    for attempt in range(4):
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


def bars_30m(symbols: list[str], days: int, feed: str = "sip") -> dict[str, pd.DataFrame]:
    """30-minute regular-session bars. The free plan serves SIP history up to
    15 minutes ago, so `end` stops 16 minutes short of now."""
    end = datetime.now(timezone.utc) - timedelta(minutes=16)
    params = {"symbols": ",".join(symbols), "timeframe": "30Min", "adjustment": "all",
              "start": (end - timedelta(days=days)).isoformat(), "end": end.isoformat(),
              "limit": 10000, "feed": feed}
    rows: dict[str, list] = {s: [] for s in symbols}
    while True:
        try:
            js = _get(f"{DATA}/v2/stocks/bars", params)
        except requests.HTTPError as e:  # no SIP entitlement: fall back to IEX
            if params["feed"] == "sip" and e.response is not None and e.response.status_code in (401, 403, 422):
                params["feed"] = "iex"
                continue
            raise
        for sym, bars in (js.get("bars") or {}).items():
            rows[sym].extend(bars)
        if not js.get("next_page_token"):
            break
        params["page_token"] = js["next_page_token"]
    out = {}
    for sym, b in rows.items():
        if not b:
            continue
        df = pd.DataFrame(b)
        df.index = pd.to_datetime(df["t"], utc=True).dt.tz_convert(NY)
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df = df[["open", "high", "low", "close", "volume"]]
        hm = df.index.hour * 60 + df.index.minute
        done = df.index + pd.Timedelta(minutes=30) <= end  # drop a still-forming bar
        out[sym] = df[(hm >= 570) & (hm < 960) & done]  # 09:30 <= t < 16:00
    return out


def to_hourly(df30: pd.DataFrame) -> pd.DataFrame:
    """09:30-anchored hourly bars (09:30, 10:30 ... 15:30), matching Yahoo's
    1h bars that the research was run on."""
    day = df30.index.normalize()
    pos = df30.groupby(day).cumcount() // 2
    g = df30.groupby([day, pos])
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last(),
                        "volume": g["volume"].sum()})
    out.index = pd.DatetimeIndex(df30.index.to_series().groupby([day, pos]).first().tolist())
    out["n30"] = g.size().values  # 30m pieces; a full hour has 2 (15:30 has 1)
    return out


def option_pick(underlying: str, side: int, spot: float, dte_min: int = 21,
                dte_max: int = 50, delta_target: float = 0.65) -> dict | None:
    """Pick a liquid call (side>0) or put (side<0) near delta_target."""
    today = datetime.now(timezone.utc).date()
    params = {"feed": "indicative", "type": "call" if side > 0 else "put", "limit": 1000,
              "expiration_date_gte": str(today + timedelta(days=dte_min)),
              "expiration_date_lte": str(today + timedelta(days=dte_max)),
              "strike_price_gte": round(spot * 0.8, 2), "strike_price_lte": round(spot * 1.2, 2)}
    try:
        js = _get(f"{DATA}/v1beta1/options/snapshots/{underlying}", params)
    except Exception:
        return None
    best, best_score = None, 9e9
    for sym, snap in (js.get("snapshots") or {}).items():
        g, q = snap.get("greeks") or {}, snap.get("latestQuote") or {}
        d, bid, ask = abs(g.get("delta") or 0), q.get("bp") or 0, q.get("ap") or 0
        if not d or bid <= 0 or ask <= 0:
            continue
        mid = (bid + ask) / 2
        spread = (ask - bid) / mid
        score = abs(d - delta_target) + 2 * spread
        if score < best_score:
            exp = datetime.strptime(sym[-15:-9], "%y%m%d").date()
            best_score = score
            best = dict(symbol=sym, expiry=str(exp), dte=(exp - today).days,
                        strike=int(sym[-8:]) / 1000, delta=round(d, 2), mid=round(mid, 2),
                        spread_pct=round(100 * spread, 1),
                        iv=round(100 * (snap.get("impliedVolatility") or 0), 1))
    return best
