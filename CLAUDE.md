# Working on this repo

Read README.md for the strategy and results. Keep sessions short: the owner is
low on Claude usage. Don't re-read research/ unless the task is research.

## Layout
- `src/strategy.py`: the only definition of a signal; backtest and live both call `simulate`.
- `src/scanner.py`: hourly live job. `evaluate()` is the pure per-ticker step (tested).
- `src/retune.py`: weekly self-tuning within `NEIGHBORS`; `tests/` guard the rest.
- `src/universe.py`: monthly top-K by realized volatility (completed months only).
- `research/`: one-off scripts on Yahoo 1h cache (`research/cache`, gitignored).

## House rules (same as the owner's other bot)
- Report win %, profit % and winners vs losers. Never R multiples.
- No dollar signs or share counts in Discord cards.
- Choose on explore (< 2025-07-01), report holdout beside it, print the noise floor sqrt(2 ln N).
- Check the all-negative case first; compare to drift / SPY over the same window.
- Rules fire on a bar's close and fill at the next open; only stops use high/low.
- Nothing goes live untested. `python -m pytest -q` must stay green.

## Settled (don't re-litigate)
- Weekly VWAP > month/rolling/session; 1h > 2h/4h; EMA21 best; long only.
- SPY regime (SPY EMA21 > SPY weekly VWAP) is the filter that helped both splits.
- Tight stops, targets, trailing exits, trend/RS filters all failed the holdout.
- Ticker selection by past results is noise; volatility rank persists.
- Ignoring exits on the first 1-4 bars of the week helped both splits (weekly VWAP reset artifact).
- Earnings skip-2 + exit-before-gap: better t-stat and win % in both splits, lower drawdown. Live.
- Bigger pool (74 names) rejected: worse on explore; holdout gain was hindsight in the added names.
- Top 10 beats top 15/20 in both splits.
- Blocking entries on the first bars of the week (VWAP reset) hurt explore badly (+2.97 -> +1.78 per trade). Monday entries stay.
- Owner: bull-market focus; bear-year weakness (2018, 2022 in reports/longtest.md) is accepted, not to be fixed.
- Cards: BUY CALL / TAKE PROFIT / STOP LOSS + daily recap (src/recap.py, recap.yml). Replay: replay.yml.
- Ablation 2026-10-01 (reports/ablation.md, research/ablation.py): only "close > VWAP at entry" and 0.85-delta 21-30 DTE calls kept.
  Rejected: other universes, EMA 9/13/34, QQQ confirm (failed holdout), RS filters, other holds/exits/stops, Monday rules, vol sizing (close call).
- Earnings dates: src/earnings.py, Yahoo, cached in state/earnings.json, fails open.

## Running
Market data works locally (Yahoo) for research. Live and retune need Alpaca
keys and run on GitHub Actions (secrets ALPACA_API_KEY, ALPACA_API_SECRET,
DISCORD_WEBHOOK_VWAP).
