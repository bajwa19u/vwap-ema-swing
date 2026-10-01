"""Shared research helpers: data loading, explore/holdout split, stats."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.strategy import Params, simulate  # noqa: E402

CACHE = ROOT / "research" / "cache"
SPLIT = pd.Timestamp("2025-07-01", tz="America/New_York")  # explore < SPLIT <= holdout


def load(t: str) -> pd.DataFrame:
    return pd.read_pickle(CACHE / f"{t}.pkl")


def tickers() -> list[str]:
    return sorted(p.stem for p in CACHE.glob("*.pkl"))


_SPY = None


def run(t: str, p: Params) -> pd.DataFrame:
    global _SPY
    if _SPY is None:
        _SPY = load("SPY")
    tr = pd.DataFrame(simulate(load(t), p, market=_SPY))
    if len(tr):
        tr["ticker"] = t
        tr["holdout"] = tr["entry_time"] >= SPLIT
        spy_open = _SPY["open"]
        a = spy_open.reindex(pd.DatetimeIndex(tr.entry_time)).to_numpy()
        b = spy_open.reindex(pd.DatetimeIndex(tr.exit_time)).to_numpy()
        tr["excess"] = tr.ret - tr.side * (b / a - 1)  # vs SPY over the same window
    return tr


def stats(r: np.ndarray, days: np.ndarray | None = None) -> dict:
    """Win %, profit % (sum of per-trade %), winners vs losers. No R multiples."""
    n = len(r)
    if n == 0:
        return dict(n=0, win=0.0, avg=0.0, total=0.0, pf=0.0, t=0.0, wins=0, losses=0, days=0.0)
    wins, losses = int((r > 0).sum()), int((r <= 0).sum())
    gl = -r[r <= 0].sum()
    sd = r.std(ddof=1) if n > 1 else 0.0
    return dict(n=n, win=100 * wins / n, avg=100 * r.mean(), total=100 * r.sum(),
                pf=(r[r > 0].sum() / gl) if gl > 0 else float("inf"),
                t=(r.mean() / sd * math.sqrt(n)) if sd > 0 else 0.0,
                wins=wins, losses=losses,
                days=float(np.mean(days)) if days is not None else 0.0)


def noise_floor(n_variants: int) -> float:
    """Best t-stat expected from pure noise across n_variants tries."""
    return math.sqrt(2 * math.log(max(n_variants, 2)))
