# Backtest: VWAP x EMA swing

Data: Yahoo 1h bars 2024-05-03 to 2026-10-01. Explore < 2025-07-01 <= holdout. Costs 0.05% per side.

Rules: `tf=1|ema=21|vwap=week|trend=0|sides=long|stop_atr=6.0|target_atr=0.0|exit_cross=True|min_bars=7|max_bars=0|confirm=False|entry=cross|exit=cross|regime=spyvw|rs=0|dtrend=0|week_grace=2|trail_atr=0.0`
Universe: top 10 of 25 names by 120-day volatility, re-ranked monthly.

## Per trade

| period | trades | win % | winners / losers | avg profit % | total profit % | avg vs SPY % | avg calls % (est.) | avg days |
|---|---|---|---|---|---|---|---|---|
| explore | 293 | 61.4 | 180 / 113 | +2.98 | +872 | +2.06 | +11.1 | 4.8 |
| holdout | 324 | 53.1 | 172 / 152 | +1.18 | +382 | +0.99 | +4.1 | 3.8 |
| all | 617 | 57.1 | 352 / 265 | +2.03 | +1254 | +1.50 | +7.4 | 4.2 |

## Portfolio (10% of equity per share position; calls sized at 2.5%)

| curve | total | per year | max drawdown |
|---|---|---|---|
| Strategy (shares) | +226.0% | +63.2% | -15.3% |
| Strategy (calls, est.) | +177.8% | +52.7% | -27.3% |
| Same names buy & hold | +227.2% | +63.5% | -37.3% |
| SPY buy & hold | +48.8% | +17.9% | -19.0% |

Holdout only (rules never saw this period):

| curve | total | per year | max drawdown |
|---|---|---|---|
| Strategy (shares) | +42.8% | +32.9% | -15.3% |
| Strategy (calls, est.) | +32.1% | +24.9% | -27.3% |
| Same names buy & hold | +62.5% | +47.4% | -37.3% |
| SPY buy & hold | +23.2% | +18.2% | -9.1% |

## By ticker (all periods)

| ticker | trades | win % | avg % | total % |
|---|---|---|---|---|
| AMD | 33 | 48 | +1.96 | +65 |
| ARM | 65 | 60 | +2.52 | +164 |
| AVGO | 21 | 48 | +1.31 | +28 |
| COIN | 59 | 46 | +0.88 | +52 |
| HOOD | 68 | 54 | +2.59 | +176 |
| MSTR | 54 | 43 | +1.16 | +63 |
| MU | 56 | 73 | +3.47 | +195 |
| NVDA | 20 | 70 | +1.65 | +33 |
| ORCL | 21 | 62 | +1.07 | +22 |
| PLTR | 51 | 61 | +2.38 | +121 |
| SHOP | 54 | 59 | +1.54 | +83 |
| SMCI | 67 | 51 | +1.64 | +110 |
| TSLA | 48 | 73 | +2.99 | +144 |

![equity](equity.png)
