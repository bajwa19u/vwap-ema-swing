"""VWAP / EMA cross strategy. Shared by the backtest and the live scanner so the
two can never disagree about what a signal is.

Bars: regular-session bars indexed in America/New_York, columns
open/high/low/close/volume, at 1h granularity (09:30-anchored). Higher
timeframes are built with `resample`. `market` is the same for SPY and feeds
the regime / relative-strength filters.

Rules (all decisions on a bar's CLOSE, filled at the NEXT bar's open):
  long  entry : EMA crosses above VWAP (+ optional filters)
  short entry : EMA crosses below VWAP (+ optional filters)
  exits       : stop / target are resting orders (may use high/low);
                cross-back and time stop fire on close, fill next open.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd

BARS_PER_DAY = {1: 7, 2: 4, 4: 2}


@dataclass
class Params:
    tf: int = 1              # bars of 1h per strategy bar: 1, 2 or 4 (4 = half-day)
    ema: int = 21
    vwap: str = "week"       # session | week | month | roll<N>  (rolling N strategy bars)
    trend: int = 0           # 0 = off, else close must be beyond EMA(trend)
    sides: str = "long"      # long | short | both
    stop_atr: float = 0.0    # 0 = off
    target_atr: float = 0.0  # 0 = off
    exit_cross: bool = True  # exit when the exit line is crossed back (see `exit`)
    min_bars: int = 0        # ignore cross-back exits before this many bars held
    max_bars: int = 0        # 0 = off; time stop
    confirm: bool = False    # close must also be on the trade side of both lines
    entry: str = "cross"     # cross | state | cross_rising | cross_price | cross_or_pb
    entry_atr: float = 0.0   # >0: the cross is of EMA over VWAP + this many ATR
    confirm_bars: int = 1    # 2: the signal must still hold on the next hourly close
    exit: str = "cross"      # cross | close_vwap | ema9 | cross2 | cross_falling | trail
    trail_k: float = 3.0     # exit="trail": close below best close - k ATR
    mon_mode: str = ""       # "" | confirm: Monday reset-window crosses wait for bar 3 and price > VWAP
    regime: str = ""         # "+"-joined: spyvw (SPY EMA above SPY VWAP), spyN (SPY above its N-day SMA)
    rs: int = 0              # 0 = off, else N-day return must beat SPY's
    dtrend: int = 0          # 0 = off, else close above own N-day SMA (daily closes)
    week_grace: int = 0      # ignore cross-back exits in the first N bars of the week (VWAP just reset)
    entry_grace: int = 0     # no entries in the first N bars of the week (VWAP just reset)
    earn_skip: int = 0       # 0 = off; no entries when earnings gap within N trading days
    earn_exit: bool = False  # exit at the open of the last bar before an earnings gap
    trail_atr: float = 0.0   # 0 = off; once a close is this many ATR in profit, exit on a close back through the EMA

    def key(self) -> str:
        return "|".join(f"{k}={v}" for k, v in asdict(self).items())


def resample(df: pd.DataFrame, k: int) -> pd.DataFrame:
    if k == 1:
        return df
    day = df.index.normalize()
    pos = df.groupby(day).cumcount() // k
    g = df.groupby([day, pos])
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
        "close": g["close"].last(), "volume": g["volume"].sum(),
    })
    out.index = pd.DatetimeIndex(df.index.to_series().groupby([day, pos]).first().tolist())
    return out


def _vwap(df: pd.DataFrame, kind: str) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    pv = tp * df["volume"]
    if kind.startswith("roll"):
        n = int(kind[4:])
        return pv.rolling(n).sum() / df["volume"].rolling(n).sum()
    if kind == "session":
        key = df.index.normalize()
    elif kind == "week":
        key = df.index.tz_localize(None).to_period("W-FRI")
    elif kind == "month":
        key = df.index.tz_localize(None).to_period("M")
    else:
        raise ValueError(kind)
    return pv.groupby(key).cumsum() / df["volume"].groupby(key).cumsum()


def _sma_daily_prev(d: pd.DataFrame, n: int) -> pd.Series:
    """N-day SMA of completed daily closes (excludes today), mapped onto bars."""
    day = d.index.normalize()
    closes = d["close"].groupby(day).last()
    sma = closes.rolling(n).mean().shift(1)
    return pd.Series(sma.reindex(day).to_numpy(), index=d.index)


def indicators(df: pd.DataFrame, p: Params, market: pd.DataFrame | None = None,
               market2: pd.DataFrame | None = None) -> pd.DataFrame:
    d = resample(df, p.tf).copy()
    d["ema"] = d["close"].ewm(span=p.ema, adjust=False).mean()
    d["vwap"] = _vwap(d, p.vwap)
    prev_c = d["close"].shift()
    tr = pd.concat([d["high"] - d["low"], (d["high"] - prev_c).abs(),
                    (d["low"] - prev_c).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    d["trend"] = d["close"].ewm(span=p.trend, adjust=False).mean() if p.trend else np.nan
    diff = d["ema"] - d["vwap"]
    d["above"] = diff > 0
    vw_up = d["vwap"].diff() > 0
    dx = diff - p.entry_atr * d["atr"] if p.entry_atr else diff
    up = (dx > 0) & (dx.shift() <= 0)
    dn = (diff < 0) & (diff.shift() >= 0)
    if p.entry == "state":
        up = dx > 0
    elif p.entry == "cross_rising":
        up &= vw_up
    elif p.entry == "cross_price":
        up &= d["close"] > d["vwap"]
    if p.confirm_bars == 2:
        up = up.shift(1, fill_value=False) & (dx > 0)
    wk = d.index.tz_localize(None).to_period("W-FRI")
    bow = pd.Series(1, index=d.index).groupby(wk).cumsum()
    if p.mon_mode == "confirm":
        fresh = bow <= 2
        delayed = (bow == 3) & d["above"] & (d["close"] > d["vwap"]) & \
            (up.shift(1, fill_value=False) | up.shift(2, fill_value=False))
        up = (up & ~fresh) | delayed
    if p.entry == "cross_or_pb":  # first touch of VWAP from above, closing back above
        up |= d["above"] & (d["low"] <= d["vwap"]) & (d["close"] > d["vwap"]) & \
              (d["low"].shift() > d["vwap"].shift())
        dn |= ~d["above"] & (d["high"] >= d["vwap"]) & (d["close"] < d["vwap"]) & \
              (d["high"].shift() < d["vwap"].shift())
    # line that decides the exit, as "still on the long side?"
    below = ~d["above"]
    d["hold_long"] = {
        "cross": d["above"],
        "close_vwap": d["close"] > d["vwap"],
        "ema9": d["close"].ewm(span=9, adjust=False).mean() > d["vwap"],
        "cross2": ~(below & below.shift(1, fill_value=False)),
        "cross_falling": ~(below & ~vw_up),
        "trail": pd.Series(True, index=d.index),
    }[p.exit]

    ok_l = pd.Series(True, index=d.index)
    ok_s = pd.Series(True, index=d.index)
    if p.trend:
        ok_l &= d["close"] > d["trend"]
        ok_s &= d["close"] < d["trend"]
    if p.confirm:
        ok_l &= d["close"] > d[["ema", "vwap"]].max(axis=1)
        ok_s &= d["close"] < d[["ema", "vwap"]].min(axis=1)
    if p.dtrend:
        sma = _sma_daily_prev(d, p.dtrend)
        ok_l &= d["close"] > sma
        ok_s &= d["close"] < sma
    if (p.regime or p.rs) and market is not None:
        m = resample(market, p.tf).reindex(d.index).ffill()
        bull = None
        for part in filter(None, p.regime.split("+")):  # e.g. "spyvw+spy200": all must hold
            if part in ("spyvw", "spyvwr"):
                mv = _vwap(m, p.vwap)
                b = m["close"].ewm(span=p.ema, adjust=False).mean() > mv
                if part == "spyvwr":
                    b &= mv.diff() > 0
            elif part == "qqqvw" and market2 is not None:
                q = resample(market2, p.tf).reindex(d.index).ffill()
                b = q["close"].ewm(span=p.ema, adjust=False).mean() > _vwap(q, p.vwap)
            elif part.startswith("spy") and part[3:].isdigit():  # SPY above its N-day SMA
                b = m["close"] > _sma_daily_prev(m, int(part[3:]))
            else:
                raise ValueError(part)
            bull = b if bull is None else bull & b
        if bull is not None:
            ok_l &= bull
            ok_s &= ~bull
        if p.rs:
            n = p.rs * BARS_PER_DAY[p.tf]
            rel = d["close"].pct_change(n) - m["close"].pct_change(n)
            ok_l &= rel > 0
            ok_s &= rel < 0
    if p.entry_grace:
        wk = d.index.tz_localize(None).to_period("W-FRI")
        fresh = pd.Series(1, index=d.index).groupby(wk).cumsum() <= p.entry_grace
        ok_l &= ~fresh
        ok_s &= ~fresh
    sig = np.zeros(len(d), dtype=int)
    if p.sides in ("long", "both"):
        sig[(up & ok_l).to_numpy()] = 1
    if p.sides in ("short", "both"):
        sig[(dn & ok_s).to_numpy()] = -1
    d["sig"] = sig
    return d


def gap_days(events) -> np.ndarray:
    """Earnings timestamps -> the session whose open carries the reaction:
    the same day for a pre-market report, the next weekday otherwise."""
    out = []
    for ts in events or ():
        ts = pd.Timestamp(ts)
        d = np.datetime64(ts.date(), "D")
        out.append(d if ts.hour < 12 else np.busday_offset(d, 1, roll="forward"))
    return np.unique(np.array(out, dtype="datetime64[D]"))


def simulate(df: pd.DataFrame, p: Params, cost: float = 0.0005, warmup: int = 0,
             market: pd.DataFrame | None = None, events=None, market2: pd.DataFrame | None = None):
    """Return list of trades (dicts). cost is per side, as a fraction.
    events: earnings timestamps for this ticker (used by earn_skip / earn_exit)."""
    d = indicators(df, p, market, market2)
    o, h, l, c = (d[x].to_numpy() for x in ("open", "high", "low", "close"))
    atr, hold_long, ema = d["atr"].to_numpy(), d["hold_long"].to_numpy(), d["ema"].to_numpy()
    wk = d.index.tz_localize(None).to_period("W-FRI")
    bar_of_week = pd.Series(1, index=d.index).groupby(wk).cumsum().to_numpy()
    idx = d.index
    sig = d["sig"].to_numpy()
    gaps = gap_days(events) if (p.earn_skip or p.earn_exit) else np.array([], dtype="datetime64[D]")
    days = idx.tz_localize(None).values.astype("datetime64[D]")

    last_start = 570 + 60 * p.tf * (6 // p.tf)  # minutes; start of a session's final bar
    mins = idx.hour * 60 + idx.minute

    def last_before(k, g):
        """Bar k is the final bar of the last session before gap day g."""
        if days[k] >= g:
            return False
        if k + 1 < n and days[k + 1] != days[k]:
            return days[k + 1] >= g
        return mins[k] >= last_start and np.busday_offset(days[k], 1, roll="forward") >= g

    def next_gap(day):
        k = np.searchsorted(gaps, day, side="right")
        return gaps[k] if k < len(gaps) else None
    start = max(warmup, p.ema, 20, p.trend if p.trend else 0)
    trades, i, n = [], start, len(d)
    while i < n - 1:
        side = sig[i]
        if side == 0:
            i += 1
            continue
        j = i + 1
        if p.earn_skip and len(gaps):
            g = next_gap(days[j])
            if g is not None and g <= np.busday_offset(days[j], p.earn_skip, roll="forward"):
                i += 1
                continue
        g_hold = next_gap(days[j]) if p.earn_exit and len(gaps) else None
        entry = o[j]
        a = atr[i]
        stop = entry - side * p.stop_atr * a if p.stop_atr else None
        tgt = entry + side * p.target_atr * a if p.target_atr else None
        exit_px, reason, k = None, None, j
        best = entry
        hi_max, lo_min = h[j], l[j]
        while k < n:
            hi_max, lo_min = max(hi_max, h[k]), min(lo_min, l[k])
            if stop is not None and (l[k] <= stop if side > 0 else h[k] >= stop):
                exit_px = (min(o[k], stop) if side > 0 else max(o[k], stop)); reason = "stop"; break
            if tgt is not None and (h[k] >= tgt if side > 0 else l[k] <= tgt):
                exit_px = (max(o[k], tgt) if side > 0 else min(o[k], tgt)); reason = "target"; break
            held = k - j + 1
            if g_hold is not None and k > j and last_before(k, g_hold):
                exit_px, reason = o[k], "earnings"; break
            if k + 1 < n:
                if p.exit_cross and held >= p.min_bars and (hold_long[k] != (side > 0)) \
                        and bar_of_week[k] > p.week_grace:
                    exit_px, reason, k = o[k + 1], "cross", k + 1; break
                best = max(best, c[k]) if side > 0 else min(best, c[k])
                if p.exit == "trail" and held >= p.min_bars and side * (c[k] - (best - side * p.trail_k * atr[k])) < 0:
                    exit_px, reason, k = o[k + 1], "trail", k + 1; break
                if p.trail_atr and side * (best - entry) >= p.trail_atr * a and side * (c[k] - ema[k]) < 0:
                    exit_px, reason, k = o[k + 1], "trail", k + 1; break
                if p.max_bars and held >= p.max_bars:
                    exit_px, reason, k = o[k + 1], "time", k + 1; break
            k += 1
        if exit_px is None:  # still open at end of data: mark at last close
            k, exit_px, reason = n - 1, c[n - 1], "open"
        ret = side * (exit_px / entry - 1) - 2 * cost
        trades.append(dict(entry_time=idx[j], exit_time=idx[k], side=side,
                           entry=entry, exit=exit_px, ret=ret, reason=reason, atr=a,
                           mfe=side * ((hi_max if side > 0 else lo_min) / entry - 1),
                           mae=side * ((lo_min if side > 0 else hi_max) / entry - 1),
                           days=(idx[k] - idx[j]).total_seconds() / 86400))
        # a cross/time exit fired on bar k-1's close; that bar may carry the
        # reversal signal, so resume there. Stops/targets resume on bar k.
        i = max(k - 1 if reason in ("cross", "time", "trail") else k, j)
    return trades
