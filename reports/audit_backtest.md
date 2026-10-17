# Swing audit: the live rule on Yahoo 1h bars (BEFORE)

Rule (config.yaml): `tf=1|ema=21|vwap=week|trend=0|sides=long|stop_atr=6.0|target_atr=0.0|exit_cross=True|min_bars=7|max_bars=0|confirm=False|entry=cross_price|entry_atr=0.0|confirm_bars=1|exit=cross|trail_k=3.0|mon_mode=|regime=spyvw|rs=0|dtrend=0|week_grace=2|entry_grace=0|earn_skip=2|earn_exit=True|trail_atr=0.0`
Universe: top 10 of 25 by 120-day realized volatility, re-ranked monthly.
Periods by entry: explore < 2025-07-01 <= holdout < 2026-10-02 <= forward (to 2026-10-16). The holdout was used as a veto in the 1 Oct ablation, so only the forward weeks are untouched.

## 1. Reproduction of reports/backtest.md (data cut at 2026-10-01)

| period | published trades / win % / avg | reproduced trades / win % / avg |
|---|---|---|
| explore | 179 / 61.5% / +2.38% | 179 / 61.5% / +2.38% |
| holdout | 215 / 56.7% / +1.48% | 215 / 56.7% / +1.48% |

## 2. Baseline, all costs (backtest)

### 0.05% a side (realistic)

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 179 | 61.5% (110/69) | +2.38% | 2.36 | +6.71% / -4.53% | +51.1% | -5.4% | +1.64% | +3.96 | 4.5 |
| holdout | 215 | 56.7% (122/93) | +1.50% | 1.79 | +6.01% / -4.41% | +36.2% | -6.4% | +1.42% | +3.08 | 3.8 |
| forward | 1 | 100.0% (1/0) | +0.84% | inf | +0.84% / +0.00% | +0.1% | 0.0% | +0.07% | +0.00 | 3.0 |
| all | 395 | 59.0% (233/162) | +1.90% | 2.04 | +6.32% / -4.46% | +106.0% | -6.4% | +1.51% | +4.99 | 4.1 |

### 0.10% a side (stressed)

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 179 | 60.3% (108/71) | +2.28% | 2.28 | +6.73% / -4.50% | +48.4% | -5.5% | +1.54% | +3.80 | 4.5 |
| holdout | 215 | 56.7% (122/93) | +1.40% | 1.72 | +5.91% / -4.51% | +33.4% | -6.7% | +1.32% | +2.88 | 3.8 |
| forward | 1 | 100.0% (1/0) | +0.74% | inf | +0.74% / +0.00% | +0.1% | 0.0% | -0.03% | +0.00 | 3.0 |
| all | 395 | 58.5% (231/164) | +1.80% | 1.96 | +6.27% / -4.50% | +98.1% | -6.7% | +1.41% | +4.73 | 4.1 |

### 0.20% a side (harsh)

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 179 | 58.7% (105/74) | +2.08% | 2.11 | +6.72% / -4.51% | +43.3% | -5.6% | +1.34% | +3.46 | 4.5 |
| holdout | 215 | 55.8% (120/95) | +1.20% | 1.59 | +5.80% / -4.61% | +27.8% | -7.6% | +1.12% | +2.47 | 3.8 |
| forward | 1 | 100.0% (1/0) | +0.54% | inf | +0.54% / +0.00% | +0.1% | 0.0% | -0.23% | +0.00 | 3.0 |
| all | 395 | 57.2% (226/169) | +1.60% | 1.82 | +6.21% / -4.57% | +83.2% | -7.6% | +1.21% | +4.20 | 4.1 |

### 0.05% a side, every entry and non-stop exit one full hourly bar late (stress bound)

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 179 | 60.9% (109/70) | +2.37% | 2.43 | +6.60% / -4.23% | +50.8% | -5.9% | +1.64% | +4.04 | 4.5 |
| holdout | 215 | 56.7% (122/93) | +1.36% | 1.72 | +5.72% / -4.35% | +32.4% | -8.3% | +1.42% | +2.89 | 3.8 |
| forward | 1 | 0.0% (0/1) | -0.21% | 0.00 | +0.00% / -0.21% | -0.0% | -0.0% | +0.07% | +0.00 | 3.0 |
| all | 395 | 58.5% (231/164) | +1.81% | 2.02 | +6.13% / -4.27% | +99.6% | -8.3% | +1.51% | +4.91 | 4.1 |

## 3. Against SPY and holding the same names (same windows)

| window | strategy (10%/position) | strategy max DD | SPY buy & hold | SPY max DD | same names held | their max DD |
|---|---|---|---|---|---|---|
| explore 2024-05-03 to 2025-06-30 | +51.1% | -5.4% | +20.9% | -19.0% | +109.3% | -37.2% |
| holdout 2025-07-03 to 2026-10-05 | +36.2% | -6.4% | +23.8% | -9.1% | +62.5% | -37.3% |
| forward 2026-10-02 to 2026-10-05 | +0.1% | 0.0% | +0.7% | 0.0% | +0.9% | 0.0% |

Average share of capital in the market: 26% (10% slots).

## 4. Splits (0.05% a side)

#### By ticker

| bucket | explore n | explore avg | holdout n | holdout avg | forward n | forward avg | all n | all avg | all PF | share of all profit |
|---|---|---|---|---|---|---|---|---|---|---|
| AMD | 5 | -0.99% | 17 | +2.46% | 0 | - | 22 | +1.67% | 1.71 | 5% |
| ARM | 19 | +2.25% | 21 | +2.96% | 0 | - | 40 | +2.62% | 2.43 | 14% |
| AVGO | 10 | -0.76% | 1 | +2.17% | 0 | - | 11 | -0.49% | 0.68 | -1% |
| COIN | 14 | +0.22% | 25 | +0.37% | 0 | - | 39 | +0.32% | 1.12 | 2% |
| HOOD | 23 | +4.69% | 23 | +0.37% | 0 | - | 46 | +2.53% | 2.41 | 16% |
| MSTR | 14 | +5.46% | 20 | +0.68% | 0 | - | 34 | +2.65% | 2.15 | 12% |
| MU | 13 | +1.86% | 24 | +3.58% | 0 | - | 37 | +2.97% | 3.08 | 15% |
| NVDA | 12 | +3.32% | 2 | +0.24% | 0 | - | 14 | +2.88% | 9.40 | 5% |
| ORCL | 0 | - | 11 | +2.01% | 0 | - | 11 | +2.01% | 2.59 | 3% |
| PLTR | 12 | +0.92% | 18 | +0.65% | 0 | - | 30 | +0.75% | 1.49 | 3% |
| SHOP | 16 | +1.34% | 20 | +0.27% | 0 | - | 36 | +0.74% | 1.53 | 4% |
| SMCI | 21 | +1.96% | 20 | +0.65% | 1 | +0.84% | 42 | +1.31% | 1.41 | 7% |
| TSLA | 20 | +3.52% | 13 | +3.62% | 0 | - | 33 | +3.56% | 7.98 | 16% |

#### By entry bar (fill time)

| bucket | explore n | explore avg | holdout n | holdout avg | forward n | forward avg | all n | all avg | all PF | share of all profit |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:30 | 21 | +4.91% | 15 | +5.19% | 0 | - | 36 | +5.02% | 8.07 | 24% |
| 10:30 | 41 | +3.73% | 55 | +1.73% | 0 | - | 96 | +2.58% | 2.14 | 33% |
| 11:30 | 11 | +0.58% | 24 | +0.26% | 0 | - | 35 | +0.36% | 1.17 | 2% |
| 12:30 | 32 | +2.45% | 28 | +1.59% | 0 | - | 60 | +2.05% | 2.27 | 16% |
| 13:30 | 26 | +1.44% | 36 | +1.08% | 1 | +0.84% | 63 | +1.22% | 1.88 | 10% |
| 14:30 | 24 | +0.25% | 29 | +0.26% | 0 | - | 53 | +0.26% | 1.11 | 2% |
| 15:30 | 24 | +1.72% | 28 | +1.89% | 0 | - | 52 | +1.81% | 2.03 | 13% |

#### By SPY vs its 200-day average (prior close)

| bucket | explore n | explore avg | holdout n | holdout avg | forward n | forward avg | all n | all avg | all PF | share of all profit |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY above 200-day | 108 | +2.17% | 215 | +1.50% | 1 | +0.84% | 324 | +1.72% | 1.88 | 74% |
| SPY below 200-day | 22 | +2.75% | 0 | - | 0 | - | 22 | +2.75% | 2.56 | 8% |
| n/a | 49 | +2.67% | 0 | - | 0 | - | 49 | +2.67% | 3.82 | 17% |

#### By half-year

| bucket | explore n | explore avg | holdout n | holdout avg | forward n | forward avg | all n | all avg | all PF | share of all profit |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024H1 | 26 | +1.86% | 0 | - | 0 | - | 26 | +1.86% | 2.57 | 6% |
| 2024H2 | 85 | +2.68% | 0 | - | 0 | - | 85 | +2.68% | 2.61 | 30% |
| 2025H1 | 68 | +2.19% | 0 | - | 0 | - | 68 | +2.19% | 2.07 | 20% |
| 2025H2 | 0 | - | 99 | +1.16% | 0 | - | 99 | +1.16% | 1.73 | 15% |
| 2026H1 | 0 | - | 69 | +1.48% | 0 | - | 69 | +1.48% | 1.70 | 14% |
| 2026H2 | 0 | - | 47 | +2.26% | 1 | +0.84% | 48 | +2.23% | 2.01 | 14% |

#### By exit

| bucket | explore n | explore avg | holdout n | holdout avg | forward n | forward avg | all n | all avg | all PF | share of all profit |
|---|---|---|---|---|---|---|---|---|---|---|
| cross | 167 | +2.90% | 204 | +2.05% | 1 | +0.84% | 372 | +2.43% | 2.63 | 120% |
| earnings | 5 | +1.73% | 1 | +0.32% | 0 | - | 6 | +1.50% | 2.12 | 1% |
| stop | 7 | -9.63% | 10 | -9.47% | 0 | - | 17 | -9.54% | 0.00 | -22% |

## 5. Concentration and selection

- Best 5 of 395 trades = 19% of the summed profit; without them the average is +1.57% (from +1.90%).
- Best 3 tickers (TSLA, HOOD, MU) = 46% of the profit. Without them:

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 123 | 57.7% (71/52) | +1.81% | 1.89 | +6.67% / -4.82% | +24.1% | -4.8% | +1.15% | +2.39 | 4.6 |
| holdout | 155 | 53.5% (83/72) | +1.17% | 1.57 | +6.04% / -4.44% | +18.9% | -6.6% | +1.11% | +2.01 | 3.9 |
| forward | 1 | 100.0% (1/0) | +0.84% | inf | +0.84% / +0.00% | +0.1% | 0.0% | +0.07% | +0.00 | 3.0 |
| all | 279 | 55.6% (155/124) | +1.45% | 1.71 | +6.30% / -4.60% | +47.7% | -6.6% | +1.13% | +3.13 | 4.2 |

- The rule on every pool name, no volatility ranking (same dates):

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 443 | 64.8% (287/156) | +1.57% | 2.33 | +4.26% / -3.37% | +95.0% | -9.9% | +0.91% | +5.72 | 4.5 |
| holdout | 532 | 55.1% (293/239) | +0.77% | 1.55 | +3.92% / -3.10% | +46.9% | -10.2% | +0.67% | +3.41 | 4.0 |
| forward | 5 | 60.0% (3/2) | -0.03% | 0.95 | +0.93% / -1.47% | -0.0% | -0.3% | -0.20% | -0.04 | 2.6 |
| all | 980 | 59.5% (583/397) | +1.13% | 1.87 | +4.07% / -3.20% | +186.4% | -10.2% | +0.77% | +6.45 | 4.2 |

- The rule on the names ranked below the top 10 (what the ranking leaves out):

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | portfolio return (10%/position) | max DD | avg vs SPY same window | t | avg days |
|---|---|---|---|---|---|---|---|---|---|---|
| explore | 264 | 67.0% (177/87) | +1.03% | 2.27 | +2.74% / -2.45% | +30.4% | -5.1% | +0.41% | +4.82 | 4.6 |
| holdout | 317 | 53.9% (171/146) | +0.27% | 1.26 | +2.43% / -2.26% | +8.5% | -5.7% | +0.17% | +1.51 | 4.2 |
| forward | 4 | 50.0% (2/2) | -0.24% | 0.67 | +0.98% / -1.47% | -0.1% | -0.3% | -0.27% | -0.27 | 2.5 |
| all | 585 | 59.8% (350/235) | +0.61% | 1.65 | +2.58% / -2.33% | +41.4% | -5.7% | +0.28% | +4.43 | 4.3 |

The 25-name pool was written in 2026 and holds the period's big winners (PLTR, HOOD, MSTR, COIN, SMCI, ARM). The monthly ranking itself uses only completed months, but the pool is chosen with hindsight: the results carry survivorship and selection bias that no split inside this data can remove.

## 6. Options: what the reports modelled vs what the live scanner suggests

| | reports/backtest.md + README (research/final.py) | research/ablation.py (chose the live spec) | live scanner (config.yaml + src/alpaca.py) |
|---|---|---|---|
| delta | 0.65 | 0.85 chosen | nearest 0.85 (score = delta gap + 2 x spread) |
| expiry | 30 DTE fixed | 21-30 DTE chosen | 21-30 DTE listed expiries |
| IV | 1.15 x 20-day realized, fixed for the trade | 1.10 x realized, re-marked daily | market quote (indicative feed, 15 min late) |
| spread / slippage | 3% round trip | 1-2% half-spread + 0.5% slippage | real quote; skips spreads > 8% of mid |
| sizing | 1/4 of the share slot | same delta exposure as the share slot | not stated on the card |
| skip rule | none | shares only when RV20 > 2x its 1-year median | none (always suggests a contract) |
| exit | with the stock signal | with the stock signal | with the stock signal |

Option returns per trade, estimated (Black-Scholes, no option prices observed):

| period | trades | published model avg | published model win % | live spec avg | live spec win % |
|---|---|---|---|---|---|
| explore | 179 | +6.6% | 50% | +6.0% | 54% |
| holdout | 215 | +7.2% | 50% | +5.6% | 53% |
| forward | 1 | -1.6% | 0% | -0.0% | 0% |

## 7. Weekly retune: margin against noise

src/retune.py adopts a challenger from 108 variants if it beats the live rule by 0.15% a trade on the full history and on the last 12 months, with t >= 2.0 on the last 12 months. The standard error of a 12-month average here is about 0.48% a trade, so 0.15% is 0.31 standard errors; the noise floor for 108 variants is 3.06. The bar can be cleared by luck.

