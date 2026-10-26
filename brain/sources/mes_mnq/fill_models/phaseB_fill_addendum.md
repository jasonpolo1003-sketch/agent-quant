---
title: Phase B fill addendum (gap-fill to Package 7)
status: unreviewed
promoted: false
date: 2026-10-22
retrieved: 2026-10-22
---
# Phase B fill addendum — latency, fast-market spreads, limits of 1-minute OHLCV

Does not modify Package 7 files (another executor is working in fill_models/). Quotes: `fill_models/phaseB_quote_verification.tsv` (4/4 MATCH).

## 1. What 1-minute OHLCV is
- Databento: OHLCV bars "provide open, high, low, and close prices and total volume aggregated from trades at 1-second, 1-minute, 1-hour, or 1-day intervals." (Databento docs, Aggregate bars (OHLCV), databento.com/docs/schemas-and-data-formats/ohlcv, saved `source_files/phaseB/db_ohlcv.txt` L698) [vendor] **VENDOR METHOD**.
- Inference: bars are trade-built, so they contain **no bid/ask**; a minute with no trades produces no bar (Package 3 notes; treat as convention to verify on sample).

## 2. Can / cannot infer from ohlcv-1m
| Question | 1m OHLCV | Needs |
|---|---|---|
| Opening range high/low | Yes (trade prices) | — |
| Whether stop price traded (CME stop trigger = trade at/through) | Yes, at minute resolution | — |
| Order of stop vs target within the same minute | **No** | trades (C9 $26.73 / C17 $25.80 for ~60 sessions MES) |
| Fill price vs bid/ask, spread at breakout | **No** | tbbo (C10 $44.55) or mbp-1 (C11 $79.10) |
| Queue position for limit fills | **No** | mbp-1/mbo; out of scope |
| Halts/pauses (Velocity Logic) | Only as gaps | `status` schema |
| Volume around event | Yes | — |
- Databento `status` "provides updates about the trading session, such as halts, pauses, short-selling restrictions, auction start, and other matching engine statuses." (db_status.txt L698) and defines "Trading in the instrument has been paused." / "halted." [vendor] **VENDOR METHOD** — unpriced as standalone in this run (schema exists in GLBX.MDP3 range 2010→now).

## 3. Latency assumptions
- No official latency figure was found for Topstep/ProjectX order routing (Package 2 holds ProjectX rate limits only). **Unknown.** Options (none chosen): (a) zero latency, next-trade fill; (b) fixed delay of N seconds — only testable with trades data; (c) next-bar-open fill (already a Package 7 option). **QAB ENGINEERING POLICY (options)**.

## 4. Fast-market spread/slippage evidence
- No free official MES/MNQ spread-during-breakout statistics retrieved. CME Liquidity Tool remains manual-only (cmegroup.com blocks scripts — see contracts addendum). Measurable via tbbo sample (C10/C18) if Jason approves. Cost levels L1–L5 (D-COST-01) remain the stress mechanism.

## 5. Are quotes/trades needed?
- For a frozen ORB falsification on 1m bars: **no** for the base test; **yes** to bound same-bar ambiguity (trades) and slippage (tbbo). Options and prices in `providers/databento_request_design.md`.

## Verified facts
- Databento OHLCV is aggregated from trades; status schema reports halts/pauses.
## Indirect but credible evidence
- Inference that empty minutes produce no bar (to verify on sample).
## Conflicting evidence
- None new.
## Unknowns
- Topstep/ProjectX latency; real MES/MNQ breakout spreads; frequency of same-minute stop+target.
## Engineering assumptions still required
- Latency option; whether to fill missing minutes; status-gap handling.
## What was genuinely new
- Exact prices for the trades/tbbo/mbp-1 samples (trades ≈ $26, tbbo ≈ $43–45, mbp-1 ≈ $71–79 for ~60 MES sessions).
## What it confirmed
- Package 7: bars cannot order intrabar events.
## Roadmap changes
- Add a `status`-based halt mask option to the engine.
## What should not change
- Package 7 options table; no policy chosen; no strategy code.
## Next bounded action
- If Jason approves, MES trades ~60 sessions (C9/C17) to measure 1m ambiguity rate.
