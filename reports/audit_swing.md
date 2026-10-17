# Swing bot (EMA21 x weekly VWAP): profitability audit, 17 Oct 2026

Branch `profitability-audit`. Evidence: [audit_backtest.md](audit_backtest.md) (Yahoo research data, local),
[audit_live.md](audit_live.md) (Alpaca SIP data the scanner trades from, GitHub Action "audit").

## Verdict

**The stock rule holds up in backtest; no strategy change was promoted.** Holdout (Jul 2025 - Sep 2026):
215 trades, 56.7% won, +1.50% net a trade, PF 1.79, portfolio +36.2% with a -6.4% max drawdown, against
SPY +23.8% (-9.1%). It survives 0.20% a side (+1.20%) and fills a full hour late (+1.36%). But:
it trails simply holding the same names (+62.5%, with a -37.3% drawdown); three tickers (TSLA, HOOD, MU)
make 46% of the profit; the 25-name pool was written in 2026 with hindsight; and the swing repo's own
2016-2026 check (`longtest.md`, never used for choosing) shows losing years in 2018 and 2022 and trailing
SPY in 2016-2020. Option returns are Black-Scholes estimates only. Recommendation: keep it running as
signals; treat the holdout as optimistic; validate on the live-data record before sizing up. On the
scanner's own data (Alpaca SIP) the holdout is +1.65% a trade (225 trades, PF 1.90), and the
17-minute signal delay costs about 0.04% a trade.

## Before / After

Strategy version: `config.yaml` params (EMA21 x weekly VWAP, close above VWAP, SPY regime, earnings
skip/exit, 6 ATR stop, top 10 of 25 by 120-day volatility). Kind: backtest, Yahoo 1h, 0.05% a side,
period = holdout 2025-07-01 to 2026-10-01 (215 trades). Before = After: no strategy change passed.

| metric | Before | After | Change |
|---|---|---|---|
| completed trades | 215 | 215 | 0 |
| win rate | 56.7% (122 / 93) | 56.7% | 0 |
| avg net P&L per trade (= expectancy) | +1.50% | +1.50% | 0 |
| profit factor | 1.79 | 1.79 | 0 |
| cumulative net return (10% per position) | +36.2% | +36.2% | 0 |
| max drawdown | -6.4% | -6.4% | 0 |
| net after stressed costs (0.10% / 0.20% a side) | +1.40% / +1.20% a trade | same | 0 |
| untouched-test expectancy (forward 2-16 Oct, backtest) | 1 trade, +0.84% | same | too few |
| options, live contract (estimate, not observed) | +5.6% a trade (published model said +7.2%) | estimate now matches live | report corrected |
| live ledger (posted, 28 Sep - 14 Oct) | 4 trades: +0.56%, +13.43%, +0.94%, -7.90% | - | too few |

Explore (Nov 2023 - Jun 2025, rules chosen here): 179 trades, 61.5%, +2.38%. Reproduction of
`reports/backtest.md`: exact (179 / 61.5% / +2.38%, 215 / 56.7% / +1.48% on data cut at 1 Oct).

## On the scanner's own data (Alpaca SIP), and the 17-minute delay

| period | trades | win % | avg net per trade | PF | filled +15 min late | +30 min late |
|---|---|---|---|---|---|---|
| explore | 178 | 62.9% | +2.42% | 2.48 | +2.42% | +2.38% |
| holdout | 225 | 57.3% | +1.65% | 1.90 | +1.61% | +1.62% |
| forward (2-16 Oct) | 3 | 66.7% | -2.22% | 0.17 | -2.37% | -2.41% |

- **The delay costs about 0.04% a trade.** Signals reach Discord ~17 min after the price the backtest
  fills at; re-pricing every entry and non-stop exit on SIP 15-minute bars barely moves the result.
- **The two data sources disagree on about 1 signal in 5:** 312 trades on both, 83 Yahoo-only, 94
  SIP-only (both groups profitable). Hourly volume differs, so the weekly VWAP crosses differ. That is
  why the live bot took MSTR on 2 Oct and ORCL on 9 Oct, which the research data does not have. The
  live-data result is no worse than the research one.
- **Ledger prices vs a +15-minute fill:** MSTR +0.56% vs +0.48%, SHOP +13.43% vs +14.30%, SMCI +0.94%
  vs +0.67%, ORCL -7.90% vs -7.97% (stop). The ledger is close to what was tradeable.


## What was wrong (with evidence) and what changed

| problem | evidence | change | file |
|---|---|---|---|
| Weekly retune never finished | failed 3 and 10 Oct: `git pull --rebase` hit the unstaged `state/earnings.json` | `--autostash` | `.github/workflows/retune.yml` |
| Retune could swap the live rule on noise | adopts a challenger at +0.15%/trade (~0.3 standard errors) after trying 108 variants (noise floor t 3.06) | `retune.ADOPT = False`: challengers are reported, never written to config; test pins it | `src/retune.py`, `tests/test_core.py` |
| Queued runs rebuilt state from a stale commit | scan/recap/replay/retune share the `state` queue and checked out the commit they were queued on (the fault fixed in the day-trade repo on 8 Oct) | checkout `github.ref_name`, `pull --autostash` | 5 workflows |
| Options: three different contracts | reports/README: 0.65 delta, 30 DTE, fixed IV; ablation chose 0.85 delta 21-30 DTE; live suggests 0.85, 21-30 | the research estimate now prices the live contract (`final.option_ret`; old model kept as `option_ret_v1`); README corrected | `research/final.py`, `README.md` |
| README results out of date | README showed the pre-ablation run (283 / 316 trades); config's stats line and `backtest.md` show 179 / 215 | README matches the reproducible backtest | `README.md` |
| Rules documented but not live | ablation's "exact final rules" list a $300M dollar-volume screen and an options skip when RV20 > 2x its median; neither is in the scanner or the backtest. The screen would only have removed 10 explore trades (HOOD/MSTR, 2024) | documented, not implemented (live unchanged) | - |
| Ledger prices are not fills | entries and exits are recorded at the signal bar's close; the card reaches Discord ~17 min later | measured in `audit_live.md`; not changed | - |

No strategy logic changed. Shorts stay off; the settled list in CLAUDE.md was not re-tested.

## Remaining risks

- Survivorship and hindsight in the 25-name pool; the edge leans on 3 names.
- Research and live use different data sources (Yahoo vs Alpaca SIP); about 20% of signals differ, with similar results.
- Bear years: 2018 and 2022 lost money in the long-history check (owner accepted this).
- Options are modelled, not observed; the live scanner uses the indicative (delayed) option feed.
- The forward sample is 1-4 trades.

## Reproduce

```
python research/audit.py          # needs research/cache (research/fetch.py, then append recent bars)
gh workflow run audit.yml --ref profitability-audit   # live-data half, needs the Alpaca secrets
python -m pytest -q
```
