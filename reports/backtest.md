# Backtest: VWAP x EMA swing

Data: Yahoo 1h bars 2024-05-03 to 2026-10-01. Explore < 2025-07-01 <= holdout. Costs 0.05% per side.

Rules: `tf=1|ema=21|vwap=week|trend=0|sides=long|stop_atr=6.0|target_atr=0.0|exit_cross=True|min_bars=7|max_bars=0|confirm=False|entry=cross_price|entry_atr=0.0|confirm_bars=1|exit=cross|trail_k=3.0|mon_mode=|regime=spyvw|rs=0|dtrend=0|week_grace=2|entry_grace=0|earn_skip=2|earn_exit=True|trail_atr=0.0`
Universe: top 10 of 25 names by 120-day volatility, re-ranked monthly.

## Per trade

| period | trades | win % | winners / losers | avg profit % | total profit % | avg vs SPY % | avg calls % (est.) | avg days |
|---|---|---|---|---|---|---|---|---|
| explore | 179 | 61.5 | 110 / 69 | +2.38 | +426 | +1.64 | +6.8 | 4.5 |
| holdout | 215 | 56.7 | 122 / 93 | +1.48 | +317 | +1.40 | +6.4 | 3.8 |
| all | 394 | 58.9 | 232 / 162 | +1.89 | +743 | +1.51 | +6.6 | 4.1 |

## Portfolio (10% of equity per share position; calls sized at 2.5%)

| curve | total | per year | max drawdown |
|---|---|---|---|
| Strategy (shares) | +104.6% | +34.6% | -6.4% |
| Strategy (calls, est.) | +81.8% | +28.1% | -11.2% |
| Same names buy & hold | +227.2% | +63.5% | -37.3% |
| SPY buy & hold | +48.8% | +17.9% | -19.0% |

Holdout only (rules never saw this period):

| curve | total | per year | max drawdown |
|---|---|---|---|
| Strategy (shares) | +35.5% | +27.4% | -6.4% |
| Strategy (calls, est.) | +36.4% | +28.2% | -11.2% |
| Same names buy & hold | +62.5% | +47.4% | -37.3% |
| SPY buy & hold | +23.2% | +18.2% | -9.1% |

## By ticker (all periods)

| ticker | trades | win % | avg % | total % |
|---|---|---|---|---|
| AMD | 22 | 45 | +1.67 | +37 |
| ARM | 40 | 62 | +2.62 | +105 |
| AVGO | 11 | 36 | -0.49 | -5 |
| COIN | 39 | 44 | +0.32 | +12 |
| HOOD | 46 | 54 | +2.53 | +116 |
| MSTR | 34 | 53 | +2.65 | +90 |
| MU | 37 | 73 | +2.97 | +110 |
| NVDA | 14 | 79 | +2.88 | +40 |
| ORCL | 11 | 73 | +2.01 | +22 |
| PLTR | 30 | 57 | +0.75 | +23 |
| SHOP | 36 | 58 | +0.58 | +21 |
| SMCI | 41 | 56 | +1.32 | +54 |
| TSLA | 33 | 79 | +3.56 | +117 |

![equity](equity.png)
