import numpy as np
import pandas as pd
import yaml

from src import alpaca
from src.scanner import ROOT, evaluate, next_slot
from src.strategy import Params, indicators, simulate
from src.universe import top_by_vol

NY = "America/New_York"


def bars(days=80, seed=0, drift=0.0):
    rng = np.random.default_rng(seed)
    idx = []
    for d in pd.bdate_range("2025-01-06", periods=days):
        idx += [pd.Timestamp(d, tz=NY) + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(hours=i) for i in range(7)]
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.006, len(idx))))
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.002, "low": np.minimum(o, c) * 0.998,
                         "close": c, "volume": rng.integers(1e5, 1e6, len(idx)).astype(float)},
                        index=pd.DatetimeIndex(idx))


LIVE = Params(**yaml.safe_load((ROOT / "config.yaml").read_text())["strategies"][0]["params"])


def test_no_lookahead():
    df, mkt = bars(seed=1), bars(seed=2)
    full = indicators(df, LIVE, mkt)
    for cut in (200, 333, 480):
        part = indicators(df.iloc[:cut], LIVE, mkt.iloc[:cut])
        pd.testing.assert_series_equal(full["sig"].iloc[:cut], part["sig"], check_names=False)
        assert np.allclose(full["ema"].iloc[:cut], part["ema"])


def test_trades_fill_next_open_and_dont_overlap():
    df, mkt = bars(seed=3), bars(seed=4)
    tr = simulate(df, LIVE, market=mkt)
    assert tr, "synthetic data should produce trades"
    d = indicators(df, LIVE, mkt)
    for a, b in zip(tr, tr[1:]):
        assert b["entry_time"] >= a["exit_time"]
    for x in tr:
        i = d.index.get_loc(x["entry_time"])
        assert d["sig"].iloc[i - 1] == 1 and x["entry"] == d["open"].iloc[i]


def test_live_settings_match_research():
    """Retune may move within NEIGHBORS; everything else stays as researched
    (shorts lost money in every variant; trailing exits failed the holdout)."""
    from src.retune import NEIGHBORS
    for k, allowed in NEIGHBORS.items():
        assert getattr(LIVE, k) in allowed, k
    assert LIVE.sides == "long" and LIVE.tf == 1 and LIVE.trail_atr == 0 and LIVE.exit == "cross"
    assert LIVE.target_atr == 0 and LIVE.stop_atr >= 4


def test_to_hourly_is_0930_anchored():
    idx = pd.date_range("2025-03-03 09:30", "2025-03-03 15:30", freq="30min", tz=NY)
    df = pd.DataFrame({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.0}, index=idx)
    h = alpaca.to_hourly(df)
    assert [t.strftime("%H:%M") for t in h.index] == ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]
    assert h["volume"].iloc[0] == 20 and h["n30"].iloc[-1] == 1


def test_next_slot_rolls_to_monday():
    fri = pd.Timestamp("2025-03-07 15:30", tz=NY)
    assert next_slot(fri) == pd.Timestamp("2025-03-10 09:30", tz=NY)
    assert next_slot(pd.Timestamp("2025-03-07 10:30", tz=NY)).hour == 11


def test_scanner_entry_then_exit_cycle():
    df, mkt = bars(seed=5, drift=0.0005), bars(seed=6, drift=0.0005)
    full = simulate(df, LIVE, market=mkt)
    x = next(t for t in full if t["reason"] == "cross")
    i_sig = df.index.get_loc(x["entry_time"]) - 1
    ex, en = evaluate(df.iloc[:i_sig + 1], mkt.iloc[:i_sig + 1], LIVE, None)
    assert ex is None and en is not None and en[1] == x["entry_time"]
    cur = {"side": 1, "price": float(df["close"].iloc[i_sig]), "entry_time": str(x["entry_time"])}
    j_exit = df.index.get_loc(x["exit_time"]) - 1  # cross-back fired on this close
    ex, _ = evaluate(df.iloc[:j_exit], mkt.iloc[:j_exit], LIVE, cur)
    assert ex is None, "still open the bar before the exit signal"
    ex, _ = evaluate(df.iloc[:j_exit + 1], mkt.iloc[:j_exit + 1], LIVE, cur)
    assert ex is not None and ex[1] == "cross"


def test_universe_ignores_current_month():
    a, b = bars(days=200, seed=7), bars(days=200, seed=8)
    b.loc[b.index >= "2025-10-01", ["open", "high", "low", "close"]] *= np.linspace(1, 5, (b.index >= "2025-10-01").sum())[:, None]
    base = top_by_vol({"A": a, "B": b}, 1, 60, asof=pd.Timestamp("2025-10-01", tz=NY))
    later = top_by_vol({"A": a, "B": b}, 1, 60, asof=pd.Timestamp("2025-10-20", tz=NY))
    assert base == later


def test_earnings_skip_and_exit():
    df, mkt = bars(seed=5, drift=0.0005), bars(seed=6, drift=0.0005)
    base = Params(**{**LIVE.__dict__, "earn_skip": 0, "earn_exit": False})
    x = next(t for t in simulate(df, base, market=mkt) if t["reason"] == "cross" and t["days"] > 2)
    entry_day = x["entry_time"].normalize()
    # a pre-market report the next weekday after entry
    report = (entry_day + pd.offsets.BDay(1)).replace(hour=7)
    skip = Params(**{**base.__dict__, "earn_skip": 2})
    assert all(t["entry_time"] != x["entry_time"] for t in simulate(df, skip, market=mkt, events=[report]))
    ex = Params(**{**base.__dict__, "earn_exit": True})
    y = next(t for t in simulate(df, ex, market=mkt, events=[report]) if t["entry_time"] == x["entry_time"])
    assert y["reason"] == "earnings"
    assert y["exit_time"].normalize() == entry_day and (y["exit_time"].hour, y["exit_time"].minute) == (15, 30)


def test_earnings_exit_fires_live_on_phantom_bar():
    """Live: the scan after the 14:30 bar must issue the exit for the 15:30 bar."""
    df, mkt = bars(seed=5, drift=0.0005), bars(seed=6, drift=0.0005)
    base = Params(**{**LIVE.__dict__, "earn_skip": 0, "earn_exit": True})
    x = next(t for t in simulate(df, Params(**{**base.__dict__, "earn_exit": False}), market=mkt)
             if t["reason"] == "cross"
             and t["exit_time"].normalize() > t["entry_time"].normalize() + pd.offsets.BDay(3))
    day = x["entry_time"].normalize()
    report = (day + pd.offsets.BDay(2)).replace(hour=16, minute=5)  # after-close report, gap 3 days on
    gap_eve = day + pd.offsets.BDay(2)                                # last session before the gap
    cut = df.index.get_loc(gap_eve + pd.Timedelta(hours=14, minutes=30)) + 1  # through the 14:30 bar
    cur = {"side": 1, "price": float(df["close"].iloc[cut - 1]), "entry_time": str(x["entry_time"])}
    ex, _ = evaluate(df.iloc[:cut], mkt.iloc[:cut], base, cur, [report])
    assert ex is not None and ex[1] == "earnings"
    ex, _ = evaluate(df.iloc[:cut - 1], mkt.iloc[:cut - 1], base, cur, [report])
    assert ex is None, "not before the final bar"


def test_live_uses_earnings_rules():
    assert LIVE.earn_skip >= 1 and LIVE.earn_exit
