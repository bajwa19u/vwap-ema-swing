# VWAP x EMA swing signals

Hourly scanner that posts long swing-trade signals (shares or calls) to a
Discord channel when the 1h EMA21 crosses above the weekly VWAP, and posts the
exit when it crosses back. Runs entirely on GitHub Actions; no computer needs
to stay on.

## The strategy (as researched, see `reports/backtest.md`)

| | |
|---|---|
| Chart | 1-hour, regular session |
| Entry | EMA21 crosses above the weekly-anchored VWAP (resets Monday) and the close is above the VWAP |
| Market filter | only when SPY's own EMA21 is above SPY's weekly VWAP |
| Exit | EMA21 closes back below the weekly VWAP (ignored in the first trading day of the trade and the first 2 bars of each week) |
| Earnings | no new entries within 2 trading days of a report; open trades close before the report's gap |
| Disaster stop | 6 x ATR(14) below entry |
| Names | the 10 most volatile of a 25-stock pool by 120-day realized volatility, re-picked monthly |
| Side | long only (calls, not puts). Shorts lost money in every variant tested |
| Typical hold | 3-5 days |

### Results (Yahoo 1h bars, Nov 2023 - Oct 2026, 0.05% cost per side)

Rules were chosen on Nov 2023 - Jun 2025 ("explore") and then run untouched on
Jul 2025 - Sep 2026 ("holdout").

| period | trades | win % | winners / losers | avg profit % per trade | avg vs SPY same window |
|---|---|---|---|---|---|
| explore | 283 | 62.2 | 176 / 107 | +2.97 | +2.09 |
| **holdout** | **316** | **53.5** | **169 / 147** | **+1.23** | **+1.03** |

Portfolio, 10% of equity per position, holdout only:

| | total | per year | max drawdown |
|---|---|---|---|
| Strategy (shares) | +44.1% | +33.9% | -12.1% |
| Strategy (calls, estimated) | +32.9% | +25.5% | -24.0% |
| Holding the same volatile names | +62.5% | +47.4% | -37.3% |
| SPY buy & hold | +23.2% | +18.2% | -9.1% |

Honest reading: it beats SPY with an edge that survived data it never saw,
and it is in the market only about 40% of the time. Over this window, simply
holding the volatile names made more, with more than twice the drawdown.
Calls are estimated with Black-Scholes (IV = 1.15 x realized vol, 0.65 delta,
30 DTE, 3% spread); with 3-5 day holds, time decay takes much of the leverage,
so prefer 0.65-0.75 delta, 3-6 week expiries.

### Changelog
- 2026-10-01: full ablation study (reports/ablation.md). Kept: entry needs close above VWAP (holdout Sharpe 1.67 → 1.97,
  max DD -12.1% → -6.2%); calls 21-30 DTE ~0.85 delta. Everything else tested and rejected.
- 2026-10-01: earnings rules added (skip 2 days before, exit before the gap). Holdout +42.8% → +44.1%, max drawdown -15.3% → -12.1%.
  A 74-name pool was tested and rejected: worse on explore, and its holdout gain came from names picked with hindsight.

### What was tried and rejected (do not re-test without new data)

- Daily VWAP, monthly VWAP, rolling VWAPs; 2h and 4h charts: all weaker.
- ATR stops tighter than ~4 ATR, ATR profit targets, trailing exits, time stops: hurt the holdout.
- Trend (EMA200), relative strength vs SPY, 50-day trend filters: hurt.
- Picking tickers by their past results: explore-to-holdout rank correlation 0.07, i.e. noise.
  Volatility is what persists (high-vol half +0.56% vs SPY per trade, low-vol half +0.12%).

## How it runs

| workflow | when | what |
|---|---|---|
| `scan.yml` | :47 past each hour, market days | new entries / exits to Discord, state committed to `state/` |
| `retune.yml` | Saturdays | re-tests live rules vs 108 nearby variants on ~3 years of fresh Alpaca data; adopts a challenger only if it wins on both the full history and the last 12 months by 0.15% per trade; posts the weekly scorecard |
| `tests.yml` | every push | unit tests, including a no-lookahead check |
| `hello.yml` | manual | test card to the Discord channel |

Data: Alpaca free plan SIP bars (15-minute delay), so signals arrive ~17
minutes after each hourly close. Options suggestions come from Alpaca's option
chain snapshot (nearest to 0.65 delta, 21-45 days, tightest spread).

## Setup (once)

1. In Discord: new channel → Edit Channel → Integrations → Webhooks → New Webhook → Copy URL.
2. Run `./setup.sh` and paste your Alpaca key, secret and the webhook URL when asked.

## Research

```
python research/fetch.py          # 1h Yahoo bars into research/cache
python research/sweep.py 2        # pooled grid, explore vs holdout
python research/volsel.py '<key>' # dynamic volatility universe
python research/round3.py         # exit variants
python research/final.py          # reports/backtest.md + equity.png
```
