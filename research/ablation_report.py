"""Turn research/ablation.pickle into reports/ablation.md."""
import pickle

import numpy as np
import pandas as pd

from common import ROOT, SPLIT

R = pickle.load(open(ROOT / "research" / "ablation.pickle", "rb"))
L = []
w = L.append


def row(r, k):
    m = r[k]
    return (f"{m['n']} | {m['win']:.1f} | {m['avg']:+.2f} | {m['avg_w']:+.2f} / {m['avg_l']:+.2f} | {m['pf']:.2f} | "
            f"{m['s_total']:+.1f} | {m['s_cagr']:+.1f} | {m['s_maxdd']:.1f} | {m['s_sharpe']:.2f} | {m['s_sortino']:.2f} | "
            f"{m['s_rr']:.2f} | {m['largest']:+.1f} | {m['days']:.1f} | {m['mfe']:+.1f} / {m['mae']:+.1f} | "
            f"{m['o_total']:+.1f} | {m['o_sharpe']:.2f}")


HDR = ("| version | verdict | period | trades | win % | avg trade % | avg win / loss % | PF | total % | CAGR % | max DD % | "
       "Sharpe | Sortino | CAGR/DD | largest loss % | hold d | MFE / MAE % | calls total % | calls Sharpe |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

w("# Strategy ablation study\n")
w(f"Yahoo 1h bars, 25-stock pool, May 2024 to Sep 2026. Explore = entries before {SPLIT:%Y-%m-%d}; holdout after. "
  "Account marked to market daily; 10% of the account per position unless sizing says otherwise; "
  "0.05% cost per side on shares. Calls: Black-Scholes, IV = 1.10 x 20-day realized vol re-marked daily, "
  "spread 1-2.5% each side + 0.5% slippage, sized to the same delta exposure as the share position, "
  "skipped when realized vol is over 2x its 1-year median.\n")
w("Decision rule (fixed before running): adopt only if explore Sharpe improves by 0.10+, holdout Sharpe does not "
  "get worse, and for numeric settings a neighbouring value also clears the bar.\n")
w("## What each change added or removed\n")
for line in R["log"]:
    w(f"- {line}")
w("")
steps = []
for r in R["rows"]:
    if r["step"] not in steps:
        steps.append(r["step"])
for st in steps:
    w(f"### {st}\n")
    w(HDR)
    for r in [x for x in R["rows"] if x["step"] == st]:
        for k, lab in (("x", "explore"), ("h", "holdout")):
            w(f"| {r['name']} | {r.get('verdict', '') if k == 'x' else ''} | {lab} | {row(r, k)} |")
    w("")
w("### 11 options (on the final rules)\n")
w("| contract | explore calls total % | explore Sharpe | explore max DD % | holdout calls total % | holdout Sharpe | holdout max DD % | avg call trade % (h) |")
w("|---|---|---|---|---|---|---|---|")
for r in R["optres"]:
    x, h = r["x"], r["h"]
    w(f"| {r['name']}{' ← chosen' if r['name'] == R['best_opt'] else ''} | {x['o_total']:+.1f} | {x['o_sharpe']:.2f} | "
      f"{x['o_maxdd']:.1f} | {h['o_total']:+.1f} | {h['o_sharpe']:.2f} | {h['o_maxdd']:.1f} | {h['opt_avg']:+.2f} |")
w("")

F, B = R["final"], R["base"]
best = next(r for r in R["optres"] if r["name"] == R["best_opt"])
w("## Current vs final, full detail\n")
w(HDR)
for r, nm in ((B, "current"), (F, "final")):
    for k, lab in (("x", "explore"), ("h", "holdout")):
        w(f"| {nm} | | {lab} | {row(r, k)} |")
w("")


def breakdown(tr, col, title):
    w(f"### By {title} (final rules, all periods)\n")
    w("| " + title + " | trades | win % | avg % | total % (stock) | avg call % |")
    w("|---|---|---|---|---|---|")
    for key, g in tr.groupby(col):
        r = g.ret
        w(f"| {key} | {len(g)} | {100 * (r > 0).mean():.0f} | {100 * r.mean():+.2f} | {100 * r.sum():+.0f} | "
          f"{100 * np.nanmean(g.opt_ret):+.1f} |")
    w("")


tr = best["trades"].copy()
tr["year"] = [e.year for e in tr.entry_time]
tr["season"] = ["earnings season" if (e.month in (1, 4, 7, 10) and e.day >= 10) or (e.month in (2, 5, 8, 11) and e.day <= 15)
                else "off season" for e in tr.entry_time]
tr["period"] = np.where(tr.entry_time >= SPLIT, "holdout", "explore")
for col, title in (("ticker", "ticker"), ("regime", "market regime at entry"), ("year", "year"),
                   ("season", "earnings season"), ("period", "period")):
    breakdown(tr, col, title)

w("## Quarter by quarter (final rules, shares, account %)\n")
q = best["S"].groupby(best["S"].index.to_period("Q")).apply(lambda r: 100 * ((1 + r).prod() - 1))
qo = best["O"].groupby(best["O"].index.to_period("Q")).apply(lambda r: 100 * ((1 + r).prod() - 1))
w("| quarter | shares % | calls % |")
w("|---|---|---|")
for k in q.index:
    w(f"| {k} | {q[k]:+.1f} | {qo[k]:+.1f} |")
w("")
(ROOT / "reports" / "ablation.md").write_text("\n".join(L) + "\n")
print("\n".join(L[:12]))
