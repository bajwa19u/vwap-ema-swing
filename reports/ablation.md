# Final rules after the ablation study (2026-10-01)

## 1. Current strategy (before)
Top 10 of 25 by 120-day volatility · enter when 1h EMA21 crosses above weekly VWAP while SPY EMA21 > SPY weekly VWAP and no earnings within 2 trading days · exit when EMA21 closes below weekly VWAP (ignored for 7 bars after entry and the first 2 bars of the week), at the last bar before earnings, or at a 6 ATR emergency stop · 10% per position · calls ~0.65 delta, 3-6 weeks.

## 2. Robust modifications kept
| change | explore Sharpe | holdout Sharpe | explore max DD | holdout max DD | why kept |
|---|---|---|---|---|---|
| Entry cross only counts if the close is also above the VWAP | 2.43 → 2.55 | 1.67 → 1.97 | -12.8% → -4.8% | -12.1% → -6.2% | better on both periods, drawdown halved |
| Calls: 21-30 DTE, ~0.85 delta (was 30-45 DTE, ~0.65) | 0.70 → 1.45 | 0.39 → 0.90 | -6.2% → -6.0% | -13.2% → -10.3% | best of 9 contract types on both periods; less theta per unit of exposure |

Everything else was tested and **not** kept (full tables below): other universes (momentum, vol+momentum, relative strength, combined), state/rising-VWAP/ATR-distance/2-close entries, EMA 9/13/34, SPY+rising VWAP, SPY+QQQ (better explore, failed holdout), regime-based sizing, relative-strength filters, 0-12 bar minimum holds, price/EMA9/2-close/falling-VWAP/ATR-trail exits, 2-4 ATR stops, Monday entry blocks/confirmation, 1/3/5-day earnings windows, volatility-adjusted sizing (same explore Sharpe; better holdout and lower drawdown, but it did not clear the pre-set +0.10 bar, so it stays optional).

## 3. Exact final rules
Checked at every 1-hour bar close (09:30-anchored regular-session bars); orders at the next bar's open.

**4. Entry (all must hold)**
1. The stock's 21 EMA crosses above its weekly VWAP (VWAP resets at Monday's open) on this bar's close.
2. The close is above the weekly VWAP.
3. SPY's 21 EMA is above SPY's weekly VWAP.
4. No earnings reaction session within the next 2 trading days.
5. The stock is in this month's universe and has no open position.

**5. Exit (first to happen)**
1. The 21 EMA closes below the weekly VWAP, but not within the first 7 hourly bars of the trade and not on the first 2 bars of the week.
2. The open of the last hourly bar before an earnings reaction session.

**6. Stop**
Emergency stop 6 x ATR(14, hourly) below entry, resting order. Tighter 2-4 ATR stops all lowered risk-adjusted returns; the trend exit is the real stop.

**7. Universe**
On the first trading day of each month, from the 25-stock pool, keep names with 20-day average dollar volume ≥ 300M, rank by 120-day realized volatility of daily closes (completed months only), trade the top 10.

**8. Options**
Call, 21-30 days to expiry, delta closest to 0.85, bid/ask spread ≤ 8% of mid, implied vol ≤ 200%. Skip the option (shares only) when 20-day realized vol is over 2x its one-year median. Close it when the stock signal exits.

**9. Position sizing**
Shares: 10% of the account per position, up to 10 positions.
Calls: contracts = (0.10 × account) ÷ (delta × 100 × stock price), i.e. the same delta exposure as the share position (about 1.5-2% of the account in premium per trade).

## 10. What each change added or removed
See "What each change added or removed" and the per-step tables below.

## 11. Out-of-sample (holdout Jul 2025 - Sep 2026, rules never fitted on it)
| | trades | win % | avg trade | PF | total | CAGR | max DD | Sharpe | Sortino | calls total | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|
| current | 316 | 53.5 | +1.23% | 1.57 | +43.0% | +31.6% | -12.1% | 1.67 | 2.19 | -0.7% (0.65Δ 38d) | 0.06 |
| final | 215 | 56.7 | +1.48% | 1.77 | +34.7% | +25.7% | -6.2% | 1.97 | 2.84 | +13.5% (0.85Δ 25d) | 0.90 |

Every full quarter from 2024Q2 to 2026Q3 was positive for the final rules on shares.

## 12. Why the final version is more robust
It makes fewer, better trades: requiring price above the VWAP removes crosses where the EMA lags a falling price, which cut the worst drawdown in half in both periods while raising win rate, profit factor and Sharpe. It did not depend on a tuned number: the change is a yes/no condition, and the numbers next to it (EMA 21, 7-bar hold, 2-day earnings window, 6 ATR stop) were each re-tested against neighbours and left alone because nothing beat them by a meaningful margin. On options, the old 0.65-delta choice lost its edge to theta and spread out of sample; deep in-the-money, shorter-dated calls keep most of the stock edge.

**Trade-off, stated plainly:** at the same 10% position size, the final rules make less total return (holdout +34.7% vs +43.0%) because they trade a third less often, with half the drawdown. Return per unit of drawdown is 4.1 vs 2.6.

**Limits of this test:** 2.9 years of hourly data (one market regime, bullish); today's 25 names applied to the past (survivorship); options priced with a model (Black-Scholes, IV from realized vol, assumed spreads), not historical option quotes; the holdout was used as a veto, so it is not perfectly untouched; no full rolling re-optimization (the weekly retune is the live walk-forward).

---

# Strategy ablation study

Yahoo 1h bars, 25-stock pool, May 2024 to Sep 2026. Explore = entries before 2025-07-01; holdout after. Account marked to market daily; 10% of the account per position unless sizing says otherwise; 0.05% cost per side on shares. Calls: Black-Scholes, IV = 1.10 x 20-day realized vol re-marked daily, spread 1-2.5% each side + 0.5% slippage, sized to the same delta exposure as the share position, skipped when realized vol is over 2x its 1-year median.

Decision rule (fixed before running): adopt only if explore Sharpe improves by 0.10+, holdout Sharpe does not get worse, and for numeric settings a neighbouring value also clears the bar.

## What each change added or removed

- 1 universe: kept current
- 2a entry: adopted **cross + price>VWAP** (explore Sharpe 2.43 → 2.55, holdout 1.67 → 1.97)
- 2b EMA length: kept current
- 3 market regime: kept current
- 4 relative strength: kept current
- 5 min hold: kept current
- 6 exit: kept current
- 7 stop: kept current
- 8 Monday: kept current
- 9 earnings window: kept current
- 10 sizing: kept current

### 1 universe

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vol (current) | incumbent | explore | 278 | 62.9 | +2.95 | +7.62 / -4.99 | 2.60 | +116.3 | +100.8 | -12.8 | 2.43 | 3.17 | 7.87 | -34.7 | 4.8 | +7.7 / -3.7 | +45.5 | 1.25 |
| vol (current) |  | holdout | 316 | 53.5 | +1.23 | +6.36 / -4.66 | 1.57 | +43.0 | +31.6 | -12.1 | 1.67 | 2.19 | 2.60 | -17.1 | 3.8 | +5.6 / -3.8 | -0.7 | 0.06 |
| momentum | no gain | explore | 276 | 65.2 | +2.23 | +5.54 / -3.97 | 2.62 | +80.7 | +70.6 | -13.3 | 2.11 | 2.54 | 5.30 | -18.1 | 4.9 | +6.1 / -3.1 | +31.5 | 1.06 |
| momentum |  | holdout | 299 | 54.2 | +0.85 | +4.74 / -3.75 | 1.50 | +26.6 | +19.9 | -12.5 | 1.43 | 1.63 | 1.59 | -17.1 | 4.1 | +4.3 / -3.1 | +1.5 | 0.15 |
| vol+momentum | no gain | explore | 273 | 64.1 | +2.81 | +6.92 / -4.53 | 2.73 | +107.1 | +93.0 | -13.0 | 2.42 | 3.02 | 7.18 | -18.1 | 4.8 | +7.1 / -3.4 | +52.7 | 1.46 |
| vol+momentum |  | holdout | 318 | 54.7 | +1.18 | +5.77 / -4.37 | 1.60 | +41.1 | +30.3 | -12.0 | 1.68 | 2.08 | 2.53 | -17.1 | 4.0 | +5.2 / -3.5 | +4.2 | 0.27 |
| rel. strength 20d | no gain | explore | 277 | 62.8 | +2.26 | +5.63 / -3.44 | 2.76 | +82.2 | +71.9 | -10.6 | 2.37 | 3.29 | 6.81 | -15.2 | 4.6 | +5.7 / -2.7 | +37.4 | 1.27 |
| rel. strength 20d |  | holdout | 307 | 54.1 | +0.81 | +4.57 / -3.62 | 1.49 | +26.1 | +19.5 | -11.1 | 1.49 | 1.81 | 1.76 | -17.1 | 4.0 | +4.1 / -2.9 | -0.1 | 0.05 |
| vol+mom+RS | no gain | explore | 277 | 63.2 | +2.46 | +6.33 / -4.18 | 2.60 | +91.5 | +79.8 | -13.9 | 2.24 | 2.78 | 5.74 | -18.1 | 4.8 | +6.6 / -3.3 | +33.2 | 1.07 |
| vol+mom+RS |  | holdout | 302 | 53.6 | +1.06 | +5.60 / -4.20 | 1.54 | +33.8 | +25.0 | -12.7 | 1.60 | 1.84 | 1.97 | -17.1 | 3.9 | +4.9 / -3.4 | +2.4 | 0.20 |

### 2a entry

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cross (current) | incumbent | explore | 278 | 62.9 | +2.95 | +7.62 / -4.99 | 2.60 | +116.3 | +100.8 | -12.8 | 2.43 | 3.17 | 7.87 | -34.7 | 4.8 | +7.7 / -3.7 | +45.5 | 1.25 |
| cross (current) |  | holdout | 316 | 53.5 | +1.23 | +6.36 / -4.66 | 1.57 | +43.0 | +31.6 | -12.1 | 1.67 | 2.19 | 2.60 | -17.1 | 3.8 | +5.6 / -3.8 | -0.7 | 0.06 |
| EMA>VWAP state | no gain | explore | 390 | 56.2 | +1.88 | +7.15 / -4.88 | 1.88 | +95.1 | +82.9 | -15.1 | 1.93 | 2.47 | 5.51 | -34.7 | 4.5 | +6.7 / -4.0 | +18.5 | 0.60 |
| EMA>VWAP state |  | holdout | 460 | 55.9 | +1.12 | +5.67 / -4.64 | 1.55 | +60.8 | +44.0 | -17.9 | 1.81 | 2.58 | 2.46 | -17.4 | 3.9 | +5.3 / -3.7 | -6.1 | -0.13 |
| cross + rising VWAP | no gain | explore | 133 | 63.2 | +2.04 | +5.62 / -4.10 | 2.35 | +30.1 | +26.8 | -4.3 | 2.14 | 2.53 | 6.24 | -18.1 | 4.4 | +6.0 / -3.4 | +2.5 | 0.26 |
| cross + rising VWAP |  | holdout | 163 | 58.9 | +1.35 | +5.27 / -4.26 | 1.77 | +23.5 | +17.6 | -5.0 | 1.82 | 2.46 | 3.53 | -14.9 | 3.8 | +5.1 / -3.1 | -1.8 | -0.11 |
| cross + price>VWAP | ADOPTED | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| cross + price>VWAP |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| cross by 0.25 ATR | no gain | explore | 278 | 65.1 | +2.89 | +7.46 / -5.63 | 2.47 | +112.0 | +97.1 | -14.3 | 2.36 | 2.91 | 6.80 | -34.7 | 4.9 | +7.6 / -3.9 | +42.4 | 1.16 |
| cross by 0.25 ATR |  | holdout | 305 | 55.7 | +1.18 | +5.83 / -4.67 | 1.57 | +39.4 | +29.0 | -12.8 | 1.65 | 2.00 | 2.27 | -17.4 | 3.9 | +5.4 / -3.8 | -3.5 | -0.08 |
| cross by 0.5 ATR | no gain | explore | 258 | 61.6 | +2.87 | +7.85 / -5.12 | 2.46 | +99.8 | +86.8 | -13.1 | 2.27 | 2.83 | 6.62 | -34.7 | 4.9 | +7.5 / -3.8 | +37.3 | 1.08 |
| cross by 0.5 ATR |  | holdout | 282 | 58.5 | +1.49 | +5.81 / -4.61 | 1.78 | +48.3 | +35.4 | -10.7 | 1.89 | 2.29 | 3.32 | -17.1 | 4.0 | +5.5 / -3.7 | +1.1 | 0.13 |
| cross by 1.0 ATR | no gain | explore | 202 | 60.4 | +3.17 | +8.61 / -5.13 | 2.56 | +82.2 | +72.3 | -13.6 | 2.15 | 2.41 | 5.31 | -34.7 | 5.0 | +7.9 / -3.9 | +44.0 | 1.32 |
| cross by 1.0 ATR |  | holdout | 197 | 51.8 | +1.23 | +6.11 / -4.01 | 1.63 | +25.4 | +19.0 | -10.0 | 1.36 | 1.36 | 1.90 | -17.1 | 4.0 | +5.3 / -3.7 | -3.7 | -0.16 |
| 2 closes confirm | no gain | explore | 286 | 62.9 | +2.69 | +7.34 / -5.20 | 2.40 | +105.6 | +91.7 | -12.8 | 2.30 | 2.98 | 7.14 | -35.2 | 4.7 | +7.4 / -3.8 | +39.2 | 1.12 |
| 2 closes confirm |  | holdout | 328 | 53.7 | +1.01 | +5.98 / -4.74 | 1.46 | +34.9 | +25.9 | -14.5 | 1.38 | 1.75 | 1.78 | -17.8 | 3.8 | +5.3 / -3.9 | -6.9 | -0.22 |

### 2b EMA length

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EMA21 (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| EMA21 (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| EMA9 | no gain | explore | 288 | 45.1 | +0.97 | +7.03 / -4.00 | 1.44 | +29.3 | +26.0 | -10.3 | 1.39 | 1.71 | 2.52 | -24.9 | 3.9 | +6.1 / -3.7 | -2.7 | -0.04 |
| EMA9 |  | holdout | 343 | 44.9 | +0.91 | +6.61 / -3.74 | 1.44 | +32.8 | +24.3 | -8.8 | 1.53 | 2.36 | 2.77 | -12.3 | 3.8 | +5.1 / -3.4 | +2.8 | 0.21 |
| EMA13 | no gain | explore | 261 | 49.4 | +1.47 | +7.47 / -4.40 | 1.66 | +42.6 | +37.8 | -8.3 | 1.78 | 2.20 | 4.55 | -29.3 | 4.2 | +6.4 / -4.1 | +11.9 | 0.61 |
| EMA13 |  | holdout | 276 | 47.8 | +1.09 | +6.61 / -3.97 | 1.53 | +31.8 | +23.6 | -6.0 | 1.62 | 2.41 | 3.93 | -12.2 | 3.9 | +5.2 / -3.6 | +1.5 | 0.15 |
| EMA34 | no gain | explore | 107 | 66.4 | +2.44 | +5.87 / -4.33 | 2.67 | +29.8 | +26.7 | -8.5 | 2.25 | 2.03 | 3.16 | -17.3 | 4.2 | +5.9 / -3.4 | +13.5 | 1.14 |
| EMA34 |  | holdout | 111 | 63.1 | +1.70 | +5.29 / -4.44 | 2.04 | +19.3 | +14.5 | -7.8 | 1.48 | 1.96 | 1.87 | -15.9 | 3.9 | +4.8 / -3.8 | +5.2 | 0.47 |

### 3 market regime

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY EMA>VWAP (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| SPY EMA>VWAP (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| + SPY VWAP rising | no gain | explore | 132 | 62.1 | +1.91 | +5.59 / -4.13 | 2.22 | +27.3 | +24.4 | -3.7 | 2.09 | 2.76 | 6.52 | -18.1 | 4.4 | +5.9 / -3.3 | -0.2 | 0.03 |
| + SPY VWAP rising |  | holdout | 163 | 58.3 | +1.32 | +5.26 / -4.19 | 1.75 | +22.8 | +17.1 | -5.0 | 1.74 | 2.37 | 3.43 | -14.9 | 3.8 | +5.1 / -3.2 | -2.4 | -0.17 |
| + QQQ EMA>VWAP | fails OOS | explore | 157 | 64.3 | +2.60 | +6.52 / -4.48 | 2.63 | +48.0 | +42.5 | -4.8 | 2.67 | 3.16 | 8.82 | -34.7 | 4.6 | +6.9 / -3.5 | +12.4 | 0.86 |
| + QQQ EMA>VWAP |  | holdout | 194 | 55.2 | +1.30 | +5.98 / -4.47 | 1.65 | +26.3 | +19.7 | -6.7 | 1.64 | 2.28 | 2.93 | -14.9 | 3.8 | +5.3 / -3.6 | +0.3 | 0.07 |
| no regime filter | no gain | explore | 274 | 58.4 | +1.60 | +5.90 / -4.43 | 1.87 | +52.1 | +46.0 | -5.6 | 2.31 | 3.02 | 8.17 | -34.7 | 4.4 | +5.7 / -3.7 | -1.3 | 0.01 |
| no regime filter |  | holdout | 369 | 55.3 | +1.17 | +5.87 / -4.65 | 1.56 | +48.8 | +35.7 | -9.7 | 1.95 | 3.01 | 3.69 | -18.8 | 3.8 | +5.2 / -3.6 | +6.7 | 0.38 |
| sized bull 1 / neutral .5 / bear 0 | no gain | explore | 261 | 57.9 | +1.50 | +5.84 / -4.45 | 1.80 | +35.2 | +31.3 | -3.9 | 2.36 | 3.43 | 8.13 | -34.7 | 4.4 | +5.7 / -3.7 | -0.6 | 0.01 |
| sized bull 1 / neutral .5 / bear 0 |  | holdout | 348 | 54.9 | +1.21 | +5.97 / -4.58 | 1.58 | +38.2 | +28.2 | -5.5 | 2.00 | 3.10 | 5.12 | -18.8 | 3.7 | +5.3 / -3.5 | +6.7 | 0.44 |

### 4 relative strength

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| off (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| off (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| RS 5d > 0 | no gain | explore | 123 | 65.9 | +2.42 | +6.03 / -4.55 | 2.56 | +33.2 | +29.5 | -4.3 | 2.35 | 2.68 | 6.88 | -18.1 | 4.3 | +6.4 / -3.4 | +7.2 | 0.65 |
| RS 5d > 0 |  | holdout | 153 | 60.8 | +1.74 | +5.70 / -4.39 | 2.01 | +29.0 | +21.6 | -5.0 | 2.11 | 3.01 | 4.31 | -14.9 | 3.8 | +5.4 / -3.2 | +4.4 | 0.40 |
| RS 10d > 0 | no gain | explore | 114 | 64.0 | +2.10 | +5.35 / -3.69 | 2.58 | +26.2 | +23.4 | -3.1 | 2.30 | 2.86 | 7.57 | -11.9 | 4.3 | +6.1 / -3.1 | +0.9 | 0.14 |
| RS 10d > 0 |  | holdout | 144 | 58.3 | +1.67 | +6.17 / -4.63 | 1.87 | +25.4 | +19.0 | -9.3 | 1.78 | 2.50 | 2.05 | -14.9 | 3.7 | +5.6 / -3.4 | +4.9 | 0.41 |
| RS 20d > 0 | no gain | explore | 110 | 65.5 | +2.24 | +5.33 / -3.60 | 2.80 | +27.4 | +24.4 | -2.9 | 2.48 | 3.36 | 8.56 | -11.9 | 4.2 | +6.0 / -3.1 | +4.4 | 0.48 |
| RS 20d > 0 |  | holdout | 132 | 59.1 | +1.54 | +5.88 / -4.73 | 1.80 | +21.2 | +15.9 | -6.0 | 1.73 | 2.09 | 2.65 | -12.8 | 3.5 | +5.4 / -3.2 | +4.2 | 0.42 |

### 5 min hold

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 7 bars (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| 7 bars (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| 0 bars | no gain | explore | 183 | 62.8 | +2.21 | +6.07 / -4.32 | 2.38 | +47.4 | +42.0 | -4.9 | 2.56 | 3.06 | 8.63 | -34.7 | 4.1 | +6.3 / -3.3 | +9.7 | 0.68 |
| 0 bars |  | holdout | 227 | 56.4 | +1.28 | +5.46 / -4.12 | 1.71 | +31.6 | +23.5 | -6.5 | 1.85 | 2.72 | 3.62 | -14.9 | 3.5 | +4.9 / -3.3 | +2.0 | 0.19 |
| 2 bars | no gain | explore | 180 | 62.8 | +2.27 | +6.17 / -4.29 | 2.42 | +48.1 | +42.6 | -4.9 | 2.59 | 3.13 | 8.62 | -34.7 | 4.2 | +6.4 / -3.3 | +10.0 | 0.70 |
| 2 bars |  | holdout | 223 | 57.4 | +1.34 | +5.50 / -4.27 | 1.74 | +32.6 | +24.2 | -6.3 | 1.89 | 2.79 | 3.87 | -14.9 | 3.6 | +5.0 / -3.3 | +3.1 | 0.25 |
| 4 bars | no gain | explore | 177 | 63.3 | +2.34 | +6.24 / -4.39 | 2.45 | +48.8 | +43.2 | -4.8 | 2.62 | 3.15 | 8.96 | -34.7 | 4.3 | +6.5 / -3.4 | +10.8 | 0.74 |
| 4 bars |  | holdout | 217 | 56.2 | +1.40 | +5.86 / -4.32 | 1.74 | +33.0 | +24.5 | -6.3 | 1.89 | 2.80 | 3.89 | -14.9 | 3.7 | +5.2 / -3.4 | +4.0 | 0.31 |
| 6 bars | no gain | explore | 175 | 63.4 | +2.38 | +6.37 / -4.53 | 2.44 | +49.2 | +43.6 | -4.8 | 2.63 | 3.18 | 9.04 | -34.7 | 4.4 | +6.6 / -3.4 | +11.5 | 0.78 |
| 6 bars |  | holdout | 216 | 56.5 | +1.42 | +5.87 / -4.35 | 1.75 | +33.4 | +24.8 | -6.7 | 1.92 | 2.81 | 3.68 | -14.9 | 3.7 | +5.3 / -3.4 | +4.3 | 0.32 |
| 8 bars | no gain | explore | 173 | 63.0 | +2.40 | +6.45 / -4.49 | 2.44 | +49.0 | +43.4 | -4.8 | 2.61 | 3.25 | 9.00 | -34.7 | 4.5 | +6.7 / -3.5 | +11.6 | 0.79 |
| 8 bars |  | holdout | 214 | 56.1 | +1.53 | +6.08 / -4.28 | 1.81 | +36.0 | +26.7 | -5.8 | 2.02 | 2.91 | 4.62 | -14.9 | 3.9 | +5.4 / -3.5 | +6.3 | 0.44 |
| 10 bars | no gain | explore | 172 | 61.0 | +2.27 | +6.60 / -4.53 | 2.29 | +45.3 | +40.1 | -4.8 | 2.43 | 3.05 | 8.32 | -34.7 | 4.6 | +6.8 / -3.6 | +9.2 | 0.64 |
| 10 bars |  | holdout | 211 | 55.9 | +1.45 | +6.09 / -4.45 | 1.74 | +33.1 | +24.5 | -6.3 | 1.88 | 2.72 | 3.87 | -14.9 | 4.1 | +5.6 / -3.6 | +2.8 | 0.23 |
| 12 bars | no gain | explore | 171 | 61.4 | +2.27 | +6.70 / -4.78 | 2.23 | +45.0 | +39.9 | -4.8 | 2.39 | 3.04 | 8.27 | -34.7 | 4.7 | +6.9 / -3.8 | +10.1 | 0.69 |
| 12 bars |  | holdout | 210 | 57.6 | +1.37 | +5.92 / -4.80 | 1.68 | +30.8 | +22.9 | -7.3 | 1.70 | 2.42 | 3.11 | -14.9 | 4.5 | +5.7 / -3.8 | +0.3 | 0.08 |

### 6 exit

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EMA21<VWAP (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| EMA21<VWAP (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| price<VWAP | no gain | explore | 161 | 53.4 | +2.21 | +6.78 / -3.03 | 2.56 | +39.9 | +35.4 | -5.2 | 2.46 | 3.81 | 6.84 | -13.9 | 4.0 | +7.6 / -2.7 | +15.1 | 0.94 |
| price<VWAP |  | holdout | 208 | 45.7 | +1.16 | +6.10 / -3.00 | 1.71 | +24.7 | +18.5 | -6.5 | 1.88 | 2.65 | 2.83 | -11.8 | 3.3 | +5.3 / -2.7 | +1.7 | 0.18 |
| EMA9<VWAP | no gain | explore | 169 | 55.6 | +1.92 | +6.38 / -3.66 | 2.18 | +36.2 | +32.2 | -5.0 | 2.18 | 2.57 | 6.50 | -18.1 | 4.1 | +6.5 / -3.2 | +2.2 | 0.21 |
| EMA9<VWAP |  | holdout | 211 | 50.2 | +1.39 | +6.44 / -3.70 | 1.76 | +31.5 | +23.4 | -6.3 | 1.92 | 2.93 | 3.74 | -12.4 | 3.5 | +5.3 / -3.0 | +5.3 | 0.39 |
| EMA<VWAP 2 closes | no gain | explore | 171 | 62.6 | +2.38 | +6.64 / -4.74 | 2.34 | +47.5 | +42.1 | -5.6 | 2.48 | 3.15 | 7.46 | -34.7 | 4.6 | +6.8 / -3.6 | +10.9 | 0.73 |
| EMA<VWAP 2 closes |  | holdout | 214 | 56.1 | +1.45 | +6.07 / -4.45 | 1.74 | +33.7 | +25.0 | -6.2 | 1.89 | 2.66 | 4.06 | -14.9 | 3.9 | +5.4 / -3.6 | +4.7 | 0.34 |
| EMA<VWAP + VWAP falling | no gain | explore | 156 | 56.4 | +2.88 | +8.38 / -4.25 | 2.55 | +52.6 | +46.5 | -5.4 | 2.51 | 3.47 | 8.65 | -34.7 | 5.6 | +8.8 / -3.6 | +24.8 | 1.21 |
| EMA<VWAP + VWAP falling |  | holdout | 204 | 51.5 | +1.43 | +6.95 / -4.43 | 1.67 | +30.7 | +22.8 | -10.8 | 1.70 | 2.63 | 2.12 | -14.9 | 4.6 | +6.5 / -3.6 | +4.6 | 0.32 |
| ATR trail 3x | no gain | explore | 143 | 46.2 | +2.82 | +11.00 / -4.19 | 2.25 | +46.4 | +41.1 | -6.9 | 2.20 | 3.23 | 5.97 | -22.6 | 6.9 | +10.7 / -3.6 | +17.6 | 0.84 |
| ATR trail 3x |  | holdout | 177 | 40.7 | +1.27 | +9.01 / -4.03 | 1.53 | +21.8 | +16.3 | -9.0 | 1.13 | 1.72 | 1.81 | -11.8 | 6.2 | +8.4 / -3.6 | -2.2 | -0.01 |

### 7 stop

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 ATR emergency (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| 6 ATR emergency (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| 2 ATR | no gain | explore | 176 | 51.1 | +1.84 | +7.04 / -3.59 | 2.05 | +36.2 | +32.2 | -4.2 | 2.27 | 2.73 | 7.63 | -23.9 | 3.4 | +6.2 / -2.9 | +5.4 | 0.44 |
| 2 ATR |  | holdout | 215 | 48.8 | +1.20 | +5.95 / -3.34 | 1.70 | +27.3 | +20.4 | -4.2 | 1.93 | 2.39 | 4.80 | -7.4 | 2.9 | +4.7 / -2.7 | +0.8 | 0.11 |
| 2.5 ATR | no gain | explore | 174 | 56.3 | +1.94 | +6.67 / -4.16 | 2.07 | +38.1 | +33.8 | -5.2 | 2.29 | 2.73 | 6.54 | -23.9 | 3.8 | +6.4 / -3.1 | +6.4 | 0.49 |
| 2.5 ATR |  | holdout | 215 | 52.1 | +1.27 | +5.85 / -3.72 | 1.71 | +29.0 | +21.6 | -5.8 | 1.95 | 2.46 | 3.75 | -8.9 | 3.2 | +4.9 / -3.0 | +1.6 | 0.17 |
| 3 ATR | no gain | explore | 174 | 56.9 | +1.87 | +6.67 / -4.46 | 1.97 | +36.2 | +32.2 | -5.6 | 2.19 | 2.75 | 5.78 | -23.9 | 3.9 | +6.4 / -3.2 | +4.6 | 0.37 |
| 3 ATR |  | holdout | 215 | 53.5 | +1.29 | +5.85 / -3.96 | 1.70 | +29.5 | +22.0 | -5.3 | 1.88 | 2.34 | 4.16 | -10.7 | 3.3 | +5.0 / -3.1 | +2.0 | 0.19 |
| 3.5 ATR | no gain | explore | 174 | 59.2 | +2.09 | +6.63 / -4.50 | 2.14 | +41.7 | +37.0 | -5.6 | 2.42 | 3.04 | 6.64 | -23.9 | 4.1 | +6.6 / -3.3 | +6.5 | 0.49 |
| 3.5 ATR |  | holdout | 215 | 55.3 | +1.49 | +5.99 / -4.09 | 1.82 | +35.3 | +26.2 | -6.0 | 2.04 | 2.68 | 4.32 | -12.4 | 3.5 | +5.2 / -3.2 | +6.4 | 0.46 |
| 4 ATR | no gain | explore | 174 | 59.2 | +2.13 | +6.63 / -4.42 | 2.18 | +42.7 | +37.9 | -6.1 | 2.46 | 3.09 | 6.25 | -23.9 | 4.2 | +6.6 / -3.4 | +6.3 | 0.48 |
| 4 ATR |  | holdout | 215 | 55.8 | +1.46 | +5.94 / -4.21 | 1.78 | +34.3 | +25.4 | -6.1 | 1.99 | 2.70 | 4.17 | -14.2 | 3.6 | +5.3 / -3.3 | +5.8 | 0.42 |
| no hard stop | no gain | explore | 174 | 63.2 | +2.43 | +6.53 / -4.62 | 2.43 | +50.1 | +44.4 | -4.9 | 2.64 | 3.25 | 8.99 | -34.7 | 4.6 | +6.8 / -3.6 | +12.7 | 0.85 |
| no hard stop |  | holdout | 215 | 57.2 | +1.52 | +5.93 / -4.36 | 1.82 | +36.4 | +26.9 | -6.2 | 1.98 | 2.91 | 4.34 | -19.3 | 4.0 | +5.4 / -3.6 | +5.1 | 0.37 |

### 8 Monday

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exit grace 2 (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| exit grace 2 (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| no entries first 2 Monday hours | no gain | explore | 137 | 61.3 | +1.85 | +5.62 / -4.13 | 2.16 | +27.8 | +24.8 | -4.3 | 2.00 | 2.42 | 5.77 | -18.1 | 4.4 | +5.9 / -3.5 | -0.1 | 0.05 |
| no entries first 2 Monday hours |  | holdout | 165 | 59.4 | +1.39 | +5.26 / -4.26 | 1.80 | +24.6 | +18.4 | -4.7 | 1.86 | 2.50 | 3.94 | -14.9 | 3.8 | +5.1 / -3.2 | -1.7 | -0.10 |
| Monday entries need confirmation | no gain | explore | 162 | 61.1 | +1.81 | +6.04 / -4.83 | 1.97 | +32.3 | +28.8 | -5.9 | 1.92 | 2.34 | 4.85 | -33.6 | 4.6 | +6.3 / -3.8 | +0.1 | 0.07 |
| Monday entries need confirmation |  | holdout | 195 | 57.4 | +1.45 | +5.64 / -4.21 | 1.81 | +30.8 | +22.9 | -5.8 | 1.98 | 2.75 | 3.93 | -14.9 | 3.8 | +5.2 / -3.3 | +0.9 | 0.12 |

### 9 earnings window

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 days (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| 2 days (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| 1 day | no gain | explore | 176 | 62.5 | +2.37 | +6.51 / -4.53 | 2.39 | +49.2 | +43.5 | -4.8 | 2.61 | 3.28 | 9.02 | -34.7 | 4.5 | +6.7 / -3.5 | +11.3 | 0.77 |
| 1 day |  | holdout | 217 | 57.1 | +1.48 | +5.89 / -4.41 | 1.78 | +35.1 | +26.0 | -6.2 | 1.98 | 2.86 | 4.18 | -14.9 | 3.8 | +5.3 / -3.5 | +5.5 | 0.40 |
| 3 days | no gain | explore | 171 | 62.6 | +2.38 | +6.54 / -4.59 | 2.38 | +47.6 | +42.2 | -4.8 | 2.57 | 3.17 | 8.75 | -34.7 | 4.5 | +6.7 / -3.5 | +10.8 | 0.75 |
| 3 days |  | holdout | 211 | 56.4 | +1.48 | +6.07 / -4.45 | 1.76 | +34.0 | +25.2 | -6.4 | 1.95 | 2.79 | 3.96 | -14.9 | 3.8 | +5.4 / -3.5 | +5.6 | 0.40 |
| 5 days | no gain | explore | 166 | 62.0 | +2.36 | +6.62 / -4.60 | 2.35 | +45.6 | +40.4 | -4.8 | 2.58 | 3.08 | 8.39 | -34.7 | 4.6 | +6.7 / -3.5 | +10.3 | 0.74 |
| 5 days |  | holdout | 206 | 55.8 | +1.45 | +6.15 / -4.48 | 1.73 | +32.2 | +23.9 | -6.4 | 1.87 | 2.65 | 3.76 | -14.9 | 3.8 | +5.4 / -3.5 | +4.6 | 0.34 |
| none | no gain | explore | 181 | 62.4 | +2.27 | +6.39 / -4.58 | 2.32 | +48.2 | +42.7 | -4.8 | 2.57 | 3.21 | 8.86 | -34.7 | 4.4 | +6.5 / -3.4 | +10.3 | 0.70 |
| none |  | holdout | 218 | 57.3 | +1.47 | +5.84 / -4.41 | 1.78 | +35.1 | +26.0 | -6.2 | 1.98 | 2.87 | 4.18 | -14.9 | 3.8 | +5.3 / -3.4 | +5.4 | 0.39 |

### 10 sizing

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| equal 10% (current) | incumbent | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| equal 10% (current) |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |
| volatility-adjusted | no gain | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +36.1 | +32.1 | -4.0 | 2.55 | 3.21 | 8.01 | -34.7 | 4.5 | +6.7 / -3.5 | +8.1 | 0.70 |
| volatility-adjusted |  | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +39.8 | +29.4 | -4.9 | 2.16 | 3.37 | 6.01 | -14.9 | 3.8 | +5.3 / -3.5 | +14.9 | 0.88 |

### 11 options (on the final rules)

| contract | explore calls total % | explore Sharpe | explore max DD % | holdout calls total % | holdout Sharpe | holdout max DD % | avg call trade % (h) |
|---|---|---|---|---|---|---|---|
| 17DTE Δ0.65 | +12.9 | 0.85 | -6.5 | +7.7 | 0.52 | -12.3 | +6.79 |
| 17DTE Δ0.75 | +17.3 | 1.11 | -6.4 | +9.3 | 0.63 | -11.7 | +6.14 |
| 17DTE Δ0.85 | +21.3 | 1.35 | -6.1 | +11.3 | 0.77 | -10.9 | +5.47 |
| 25DTE Δ0.65 | +13.3 | 0.88 | -6.3 | +8.5 | 0.57 | -12.0 | +5.84 |
| 25DTE Δ0.75 | +18.1 | 1.17 | -6.1 | +10.7 | 0.71 | -11.3 | +5.45 |
| 25DTE Δ0.85 ← chosen | +23.1 | 1.45 | -6.0 | +13.5 | 0.90 | -10.3 | +5.05 |
| 38DTE Δ0.65 | +10.1 | 0.70 | -6.2 | +5.4 | 0.39 | -13.2 | +4.00 |
| 38DTE Δ0.75 | +15.1 | 1.00 | -6.1 | +7.9 | 0.55 | -11.8 | +3.87 |
| 38DTE Δ0.85 | +20.5 | 1.32 | -5.9 | +11.1 | 0.76 | -10.8 | +3.73 |

## Current vs final, full detail

| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| current | | explore | 278 | 62.9 | +2.95 | +7.62 / -4.99 | 2.60 | +116.3 | +100.8 | -12.8 | 2.43 | 3.17 | 7.87 | -34.7 | 4.8 | +7.7 / -3.7 | +45.5 | 1.25 |
| current | | holdout | 316 | 53.5 | +1.23 | +6.36 / -4.66 | 1.57 | +43.0 | +31.6 | -12.1 | 1.67 | 2.19 | 2.60 | -17.1 | 3.8 | +5.6 / -3.8 | -0.7 | 0.06 |
| final | | explore | 174 | 62.1 | +2.32 | +6.51 / -4.53 | 2.35 | +47.3 | +41.9 | -4.8 | 2.55 | 3.17 | 8.68 | -34.7 | 4.5 | +6.7 / -3.5 | +10.1 | 0.70 |
| final | | holdout | 215 | 56.7 | +1.48 | +5.96 / -4.41 | 1.77 | +34.7 | +25.7 | -6.2 | 1.97 | 2.84 | 4.14 | -14.9 | 3.8 | +5.3 / -3.5 | +5.4 | 0.39 |

### By ticker (final rules, all periods)

| ticker | trades | win % | avg % | total % (stock) | avg call % |
|---|---|---|---|---|---|
| AMD | 25 | 48 | +1.75 | +44 | +11.7 |
| ARM | 39 | 62 | +2.56 | +100 | +6.7 |
| AVGO | 13 | 46 | +0.48 | +6 | -2.2 |
| COIN | 38 | 42 | +0.26 | +10 | -3.4 |
| HOOD | 39 | 54 | +2.13 | +83 | +5.8 |
| MSTR | 31 | 52 | +2.65 | +82 | +5.7 |
| MU | 40 | 72 | +2.69 | +108 | +13.4 |
| NVDA | 13 | 77 | +2.84 | +37 | +11.4 |
| ORCL | 11 | 73 | +2.01 | +22 | +8.0 |
| PLTR | 33 | 61 | +1.13 | +37 | -1.6 |
| SHOP | 35 | 57 | +0.50 | +18 | -1.6 |
| SMCI | 40 | 57 | +1.44 | +57 | +1.9 |
| TSLA | 32 | 78 | +3.67 | +117 | +15.1 |

### By market regime at entry (final rules, all periods)

| market regime at entry | trades | win % | avg % | total % (stock) | avg call % |
|---|---|---|---|---|---|
| bull | 333 | 57 | +1.57 | +523 | +4.5 |
| neutral | 56 | 70 | +3.54 | +198 | +9.7 |

### By year (final rules, all periods)

| year | trades | win % | avg % | total % (stock) | avg call % |
|---|---|---|---|---|---|
| 2024 | 106 | 64 | +2.40 | +255 | +6.3 |
| 2025 | 167 | 57 | +1.58 | +264 | +4.9 |
| 2026 | 116 | 57 | +1.75 | +203 | +4.7 |

### By earnings season (final rules, all periods)

| earnings season | trades | win % | avg % | total % (stock) | avg call % |
|---|---|---|---|---|---|
| earnings season | 171 | 65 | +2.77 | +473 | +8.0 |
| off season | 218 | 54 | +1.14 | +248 | +3.1 |

### By period (final rules, all periods)

| period | trades | win % | avg % | total % (stock) | avg call % |
|---|---|---|---|---|---|
| explore | 174 | 62 | +2.32 | +404 | +5.5 |
| holdout | 215 | 57 | +1.48 | +317 | +5.1 |

## Quarter by quarter (final rules, shares, account %)

| quarter | shares % | calls % |
|---|---|---|
| 2024Q2 | +2.0 | +0.7 |
| 2024Q3 | +9.3 | +5.9 |
| 2024Q4 | +14.6 | +7.2 |
| 2025Q1 | +5.4 | +3.6 |
| 2025Q2 | +9.5 | +4.0 |
| 2025Q3 | +6.9 | +3.5 |
| 2025Q4 | +4.5 | +2.2 |
| 2026Q1 | +0.3 | -1.9 |
| 2026Q2 | +9.8 | +3.4 |
| 2026Q3 | +9.4 | +5.7 |
| 2026Q4 | +0.0 | -0.0 |

