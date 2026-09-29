---
id: phase_08_backtest_runner
type: phase_plan
status: proposed
created: 2026-09-29
parent: PROP-007 steps 5 and 6
card: SC-0002 (frozen, spec sha256 4b838196…)
---

# Backtest runner: plan (PROP-007 step 5)

## Goal
Run **exactly** what frozen card SC-0002 defines, and nothing else. Every run is recorded, and the verdict comes from the card's pre-declared test. The runner makes **no** strategy choices of its own: every definition it needs is already pinned on the card. If something turns out not to be pinned, the runner stops and reports it; it does not decide.

## Guardrails (built first, tested first)
1. **Card gate.** The runner refuses to start unless `verify_frozen_card("SC-0002") == []`, which rejects a card that isn't frozen, has been superseded, or has changed. Every run records the card's spec and file sha256.
2. **Data gate.** Every dataset is loaded through `load_dataset`, which accepts verified datasets only, and its content hash must equal the one pinned on the card.
3. **Code gate.** The runner refuses a dirty git tree under `src/quant_brain/backtest/` and records the exact commit. A result is always tied to the code that produced it.
4. **One read of the held-out period**, in two separate phases:
   - **Phase 1: in-sample only (2000–2015).** Every rule, cost level and symbol, the in-sample report, and a stop.
   - **Jason reviews the in-sample report.** Nothing on the card can change as a result: it is frozen, and any change would be a new card with its own ledger history.
   - **Phase 2: held-out (2016–2026), run once.** It needs an explicit `--held-out` flag **and** a recorded in-sample approval. The ledger refuses a second held-out run for the same card, even after a crash: a started run is recorded before any held-out number is computed.
5. **Trial ledger.** It is append-only (`brain/04_Backtest_Reports/SC-0002.trials.jsonl`, committed, byte-exact) and also written to the existing `backtests` and `metrics` tables. Each trial records the card, dataset and code hashes, the rule, symbol, cost, period, the seed range, and its metrics. Nothing is ever deleted or rewritten. A failed run is recorded as failed.
6. **Second implementation before the held-out read.** A small, independent, vectorised reference implementation of rule A (written separately and sharing no engine code) must reproduce the engine's **in-sample trade list** exactly: the same entry and exit dates, and returns to 1e-12. This follows Jason's rule that "the selected strategy must be rerun through a second implementation before acceptance". A mismatch blocks phase 2.

## Engine (`src/quant_brain/backtest/`, pandas, readable over fast)
- **`indicators.py`:** SMA, Wilder RSI and Cutler RSI, exactly per `implementation.sma`, `rsi_wilder` and `rsi_cutler`.
- **`engine.py`:** one bar-by-bar event loop, shared by A, B and D, driven only by the card's parameters. It implements:
  - close signals filled at the next open (`adj_open`);
  - level-tested entries while flat, with the trend filter checked on the signal day only;
  - exits while in a position;
  - B's add, from the first close after unit 1's fill;
  - no same-bar entry and exit;
  - last-bar signals dropped, and a forced close on the period's last bar;
  - multiplicative costs on every fill;
  - compounding equity, and 0% on cash;
  - daily returns with flat days = 0.
- **`benchmarks.py`:** buy-and-hold with the same costs and daily-return rules; the seeded random-entry runs, exactly per `benchmarks.random_entry` (`default_rng(seed_start + i)`, shuffled holding times, fit and no-overlap, 10,000-draw retry, discarded runs counted, strict-below percentile).
- **`stats.py`:** per-period and annualised Sharpe (rf = 0, √252), maximum drawdown, trade statistics, and the DSR exactly per `multiple_testing.formula` (biased skew and raw kurtosis, ddof = 1 variance, Euler gamma, N = 3).
- **`run.py` and `scripts/run_backtest.py`:** the gates, both phases, the ledger, and the reports.

## What gets run
- **Phase 1:** 3 rules × 3 cost levels × 3 symbols = 27 in-sample trials, plus in-sample buy-and-hold per symbol.
- **Phase 2:** the same 27 held-out, plus buy-and-hold, plus 1,000 random-entry runs for rule A on SPY at 5 bps, plus the DSR. Only rule A on SPY at 5 bps receives the verdict.

## Reports (`brain/04_Backtest_Reports/`)
- `SC-0002-in-sample.md` and, later, `SC-0002-held-out.md`. Each is readable Markdown plus a JSON block the UI agent can render.
- Contents:
  - a trades table (dates, holding days, return);
  - equity and drawdown figures as data series;
  - per-trial metrics (CAGR, Sharpe, maximum drawdown, exposure, trade count, win rate, average trade, holding-time distribution);
  - the cost sensitivity;
  - QQQ and IWM as robustness checks.
- The held-out report adds the four criteria, each with its value, threshold and pass/fail, and the verdict. It always states "a backtest is not proof of future profit".

## Tests (hermetic, focused on correctness)
- **Indicators:** hand-computed values on a tiny series: the Wilder seed and smoothing, Cutler's simple means, and RSI = 100 when there are no losses.
- **Engine:** constructed price paths whose correct trade list is known by hand:
  - next-open fills;
  - no same-bar entry and exit;
  - the filter checked only on the signal day;
  - B's add timing (a signal-day RSI below 20 does not add);
  - a dropped last-bar signal and a forced close;
  - multiplicative costs;
  - compounding.
- **Benchmarks and stats:**
  - seeded random entry is reproducible, with no overlap and no fill on the period's first day;
  - the percentile's tie handling;
  - Sharpe and drawdown on known series;
  - the DSR against an independent line-by-line computation of the card's formula, including the V = 0 case.
- **Gates:** a superseded card (SC-0001), an edited card, a dirty backtest tree, a second held-out run, and a held-out run without approval are all refused. The ledger is append-only.
- **Cross-check:** the reference implementation matches the engine on a synthetic series in CI. The real-data match is a phase-1 step.

## Sequence and stops
1. Build the guardrails, then the engine, benchmarks and stats, then the reference implementation, all test-first, followed by an independent code review.
2. **Phase 1**, the in-sample run, then the report. **Stop for Jason.**
3. After Jason's approval: **phase 2**, the held-out run, once. The verdict report goes to the adversarial review (PROP-007 step 6). **Stop.**

## Out of scope
Parameter sweeps or optimisation, new rules or symbols, intraday data, the prop-firm check (step 7), paper or live trading, vectorbt or backtesting.py, and any change to SC-0002, the market data or the research harness.

## Decisions for Jason (recommended defaults in bold)
1. **Two phases, with your in-sample review between them.** The alternative is running both periods in one go: faster, but with no checkpoint before the one-shot held-out read.
2. **The second implementation must match before the held-out read.** The alternative is skipping it: quicker, but it breaks your "second implementation" rule.
3. **Markdown and JSON reports** in `brain/04_Backtest_Reports/`, readable by the UI agent.
