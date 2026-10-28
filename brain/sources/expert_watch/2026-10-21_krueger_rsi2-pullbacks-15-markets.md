---
title: "RSI(2) and Other Pullback Rules on 15 Markets: Search Period Passed, 0 of 23 in the Holdout"
link: https://kruegeralgorithms.com/en/research/rsi2-pullbacks-15-markets-search-passed-holdout-0-of-23
author: Krueger Algorithms (via Quantocracy)
date: 2026-10-21
captured_at: 2026-10-26
evidence_grade: NOT_EVIDENCE
found_by: weekly expert watch 2026-10-26
status: unreviewed
promoted: false
---
## Summary
Pre-registered test of RSI(2)<10 / <5, IBS<0.2, 7-day low, three lower closes, long and short, with/without 200-day filter, max hold 20 days, on 12 non-US markets (IWM included) with SPY/QQQ/DIA as comparison. Primary rule (RSI(2)<10 above 200dma, exit first close above 5-day average) earned +22.35 bps net per trade 2000-2018 but +6.49 bps (t 0.34) in a one-shot 2019-Oct 2026 holdout; 0 of 23 candidates held. Entering at next open instead of the close cut the search-period edge to +8.7 bps. The page says the same rule passed an earlier holdout on SPY, QQQ and DIA (+48 bps per trade after costs).
## Why it matters
Directly on our Connors RSI(2) exit replication: close-vs-next-open fill sensitivity, a 5-day SMA exit spec, an IWM data point (three lower closes, t 1.78), and an example of pre-registration plus a single holdout for overfitting control.
