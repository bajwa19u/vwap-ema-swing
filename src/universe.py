"""Which names to trade this month: the top K of the pool by realized
volatility of daily closes, measured as of the previous month-end (the same
rule the backtest used, research/volsel.py)."""
from __future__ import annotations

import math

import pandas as pd


def top_by_vol(hours: dict[str, pd.DataFrame], k: int, lookback: int,
               asof: pd.Timestamp | None = None) -> list[str]:
    vols = {}
    for t, h in hours.items():
        daily = h["close"].groupby(h.index.normalize()).last()
        month_start = (asof or daily.index[-1]).normalize().replace(day=1)
        daily = daily[daily.index < month_start]  # completed months only
        if len(daily) < lookback * 0.8:
            continue
        r = daily.pct_change().dropna().tail(lookback)
        if len(r) >= lookback * 0.8:
            vols[t] = r.std() * math.sqrt(252)
    return sorted(vols, key=vols.get, reverse=True)[:k]
