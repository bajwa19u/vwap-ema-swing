# Swing audit: the live rule on the live data path (Alpaca SIP), and the 17-minute delay

Rule: `tf=1|ema=21|vwap=week|trend=0|sides=long|stop_atr=6.0|target_atr=0.0|exit_cross=True|min_bars=7|max_bars=0|confirm=False|entry=cross_price|entry_atr=0.0|confirm_bars=1|exit=cross|trail_k=3.0|mon_mode=|regime=spyvw|rs=0|dtrend=0|week_grace=2|entry_grace=0|earn_skip=2|earn_exit=True|trail_atr=0.0`. SIP 30-minute bars 2023-11-06 to 2026-10-16 made hourly by `scanner.complete_hours`; universe and earnings as `retune.backtest`. Trades entered from 2024-05-01 (the Yahoo backtest's first). 0.05% a side.

## 1. Backtest on live data, fills as the research assumes

| | trades | win % (won/lost) | avg net per trade | PF | avg win / loss | t |
|---|---|---|---|---|---|---|
| explore | 178 | 62.9% (112/66) | +2.42% | 2.48 | +6.45% / -4.40% | +4.14 |
| holdout | 225 | 57.3% (129/96) | +1.65% | 1.90 | +6.05% / -4.28% | +3.50 |
| forward | 3 | 66.7% (2/1) | -2.22% | 0.17 | +0.67% / -8.01% | -0.77 |
| all | 406 | 59.9% (243/163) | +1.96% | 2.12 | +6.19% / -4.35% | +5.35 |

## 2. The same trades filled late (SIP 15-minute bars)

| period | at the bar (backtest) | +15 min | +30 min | change at +15 |
|---|---|---|---|---|
| explore | +2.42% | +2.42% | +2.38% | -0.00% |
| holdout | +1.65% | +1.61% | +1.62% | -0.04% |
| forward | -2.22% | -2.37% | -2.41% | -0.15% |
| all | +1.96% | +1.94% | +1.92% | -0.02% |

Win %, holdout: bar 57.3%, +15 56.9%, +30 56.9%

## 3. Live data vs the Yahoo research data, signal by signal

| | trades | avg net per trade |
|---|---|---|
| same entry bar on both | 312 | Yahoo +2.09% / SIP +2.11% |
| Yahoo only | 83 | +1.17% |
| SIP only (live data) | 94 | +1.46% |

Hourly volume differs between the two sources, so the weekly VWAP and its crosses differ; the research numbers are not the numbers of the bars the scanner trades.

## 4. Live ledger prices vs a +15-minute fill

| ticker | entry bar | ledger entry | +15 min | ledger exit | +15 min | ledger result | at +15 min |
|---|---|---|---|---|---|---|---|
| MSTR | 2026-10-02 12:30 | 159.54 | 159.48 | 160.44 | 160.25 | +0.56% | +0.48% |
| SHOP | 2026-09-28 10:30 | 138.56 | 137.75 | 157.17 | 157.46 | +13.43% | +14.30% |
| SMCI | 2026-10-02 13:30 | 43.04 | 43.27 | 43.45 | 43.56 | +0.94% | +0.67% |
| ORCL | 2026-10-09 15:30 | 142.02 | 142.12 | 130.79 | 130.79 | -7.90% | -7.97% |

