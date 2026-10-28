# Prop-firm grid: quality review (workstream Q, 2026-10-28)

Reviewer: quality agent (Claude). Scope: plan `brain/_system/plan/prop_firm_grid_plan.md` workstream Q. Code at `c0c8f68` + `7e66b5c` (branch `testing`), plus the fixes listed below (uncommitted). The grid was **not** run on real workbench data.

## Verdict
The simulator core is right. An independent re-implementation (`scripts/q_independent_firm_check.py`), written from the rule text, matches the project path for path on 600 synthetic 42-day paths, with **0 differences** in net, fees, payouts, passes, closures and first-payout day for Topstep 50K Standard (with and without the DLL) and Tradeify Growth 50K. That holds once the same conventions are used and after the Growth fix below.

Before this review, four firm files had payout rules that the loader misread or ignored (three flattering, one pessimistic), and the grid's daily-loss path treated market lows *after* a DLL flatten as account breaches. All of these are now fixed with tests. What remains open is mostly about **interpreting** the grid, not about its arithmetic: the commission differences between firms, the lack of an order route outside Topstep, the number of cells (multiple testing), and two ambiguous rules.

**Blocking before the grid runs:** none left in the code. Two must-do items for the orchestrator before believing any non-Topstep cell (see H2, H3), and one before choosing a winner (H4).

## Findings (most severe first)

### H1. Lows after a DLL exit counted as floor breaches (fixed)
- **What:** `policy.Days.outcome` returns the whole day's low even when the soft DLL has flattened the trader. `firm_sim._breached` checks the floor against that low, so a market drop *after* the exit could fail the account. E1 kept this so that Topstep matches the old results ("pessimistic").
- **Judgement:** wrong, not just pessimistic. Every firm says the DLL flattens the account (Topstep P5 "forced break", Tradeify T11, FundedNext F7), and after that it cannot lose more. The error is biased against exactly the cells the menu prefers ("where the plan offers an optional DLL, it is ON"): every Topstep cell, plus Tradeify Growth, FundedNext Rapid Daily and Direct, whose DLLs are mandatory. That distorts the firm ranking, not only the level.
- **Size:** in the independent check, on synthetic paths, the old convention costs Topstep 50K with DLL **-$180 per path** (-102 vs +77 mean net) and Tradeify Growth **-$110 per path**. The size on real MNQ days is unknown but cannot be assumed small.
- **Fix:** `play.day_fn` now gives the floor check the low *until the exit* (`Days.extremes` stop_low) whenever the DLL fires. The old behaviour stays available as `run_play(..., post_exit_lows=True)`, which the legacy-reproduction test now uses. New test: `test_lows_after_a_dll_exit_do_not_breach_the_floor`. `firm_sim.array_days` (used only by tests and the legacy path) still keeps the old convention.
- **Consequence:** Topstep cells in the grid will **not** reproduce the earlier SC-FUT-0005 sizing-policy cash numbers wherever the DLL fired. That is intended. Say so in the grid review.

### H2. One cost level for every firm; Tradeify commissions are higher (open, flattering non-Topstep firms)
- **What:** `Days` charges the workbench L3 cost, $3.22 per MNQ round trip (Topstep fees $1.22 + 4 ticks), for every firm. Tradeify's official MNQ commission is **$1.82** per round trip (T1, re-read today), so the true L3-equivalent cost is $3.82. FundedNext commissions are not in the research at all.
- **Impact:** Tradeify cells are flattered by $0.60 per round trip per micro: about $7 a day at 12 micros (P3/P4). That is material next to an edge of about $11.49 per day per contract. FundedNext cost is unknown.
- **Not fixed:** this needs a per-firm cost in `Days`/`play`, and the review scope excluded `workbench`. **Before believing a Tradeify or FundedNext cell:** rerun those cells at L4, or add a firm-specific commission delta. Also find FundedNext's MNQ commission.

### H3. Firms with no confirmed bot route are simulated with no route cost (open)
- **What:** Tradeify and FundedNext have no firm API (`python_order_route_verified: false`). The likely routes are NinjaTrader on Jason's PC or a paid webhook bridge, and the simulator charges $0 for them, while Topstep pays $29 a month for its API.
- **Rules that also matter:** Tradeify forbids running the same bot "across multiple firms" (T3) and asks for a live video of enabling it. FundedNext monitors bots.
- **Impact:** non-Topstep cash is flattered by any route cost, and the cells may not be tradeable at all. Report non-Topstep winners as "if a route exists".

### H4. Multiple testing and winner selection (open, interpretation)
- **What:** 18 loadable firm variants × 4 plays = **72 cells** (88 with `--topstep`). Each is gated at a one-sided 5% lower bound, and the "selected" cell is the highest lower bound among those that pass. With no edge anywhere, about 3 or 4 cells would pass by chance (correlated, since all cells share the seed and the days). The selected cell's bound is biased upward (winner's curse).
- **Recommendation:** treat a lone passing cell as a hypothesis, not a result. Pre-state a family-wise rule before running, for example Bonferroni at the 1 - 0.05/72 one-sided bound, or require a pass at both L3 and L4. The exam data must stay locked, so there is no out-of-sample confirmation inside this plan.

### M1. Tradeify Growth payout read as a buffer (fixed, was pessimistic)
- **What:** the JSON had `payout_buffer_rel_start_usd: 3000` with share 1.0, so only the excess over $53,000 could be paid. That made the first $500 payout need $53,500, and the payouts were tiny.
- **Official rule** (Growth payout policy, read today): $53,000 is the minimum balance to **request**; requests are hard-capped at $1,500 / $2,000 / $2,500 / $3,000 by payout number; "$53,000 balance, $1,500 request leaves $51,500".
- **Fix:** new schema field `payout_min_balance_rel_start_usd` (`FundedRules.min_balance`). In the JSON: buffer 0, share 1.0, min balance 3,000. A capped request is clipped to stay $1 above the post-payout floor (previously such a payout was silently skipped).
- **Size:** synthetic mean net -$427 → -$403. Tests: `test_min_balance_gates_the_request_but_is_not_a_buffer`, `test_qa_corrected_research_values`.

### M2. FundedNext Flex paid 50% of total profit instead of 50% of the cycle's profit (fixed, was flattering)
- **What:** `payout_share_of_profit` and `payout_share_of_balance` both map to one share, which is applied to balance - start. The official rule (F14) is "Up to 50% of your profit per cycle". After the first payout, the old code paid again on the unpaid half.
- **Fix:** new field `payout_base: "cycle"`, set in the JSON.
- **Size:** synthetic mean net -$156 → -$179. Test: `test_cycle_payout_base_pays_a_share_of_profit_since_the_last_payout`.

### M3. Tradeify Select Daily "up to 2x the profit since the last request" ignored (fixed, was flattering)
- **What:** the rule was only in a text field (`payout_rule`), so the loader ignored it. After a capped payout, the old code could pay the full $1,250 again on a tiny next-day profit.
- **Fix:** new field `payout_max_cycle_profit_multiple: 2`.
- **Size:** synthetic -$310 → -$322. Test: `test_max_cycle_multiple_limits_the_request`.

### M4. FundedNext Direct "perpetual" consistency dropped (fixed, was flattering)
- **What:** the official rule (F15) is that the best day *ever* must be ≤ 20% of the current cycle's profit. The text was in `funded_consistency_effect` only, so the loader defaulted to the cycle's own best day.
- **Fix:** `funded_consistency_scope: "best_ever"`. Small effect on synthetic paths (-$2).

### M5. Topstep billing over-charged (open, pessimistic for Topstep against the one-time-fee firms)
- **What:** the official rule (What is a Reset, 2026-09-25) is that a reset "pushes your Rebill date out 30 days from the date of purchase", and each monthly rebill adds a free Reset Credit. The simulator rebills every 21 trading days from the subscription start, regardless of resets, and never grants credits.
- **Size:** independent check, Topstep fees -$20 per path without the DLL and -$24 with it; the simulator overstates Topstep fees by these amounts.
- **Not fixed:** it changes the documented Topstep reproduction. Topstep cells are slightly understated relative to Tradeify and FundedNext.

### M6. `--skip-invalid` and skipped firms leave no ledger trace (open)
- **What:** 5 of 17 drafts refuse to load (3 Lucid with a null price; FundedNext Rapid Pro and Tradeify Lightning with no payout share). The grid can only run with `--skip-invalid`. Those files, and the automation-skipped ones, are then listed only in the result JSON (`invalid`, `skipped`), not in `prop_trials.jsonl`.
- **Not silently lost:** they are printed and kept in the result file. But the plan's rule ("every cell is a ledger trial, failures recorded") argues for writing one ledger line per refused firm file.
- **Suggestion:** a ledger entry with `gate: "not_run"` and the error text.

### M7. Ambiguous rules where the JSON takes the generous reading (open)
- **FundedNext Direct "$2,100 buffer in your current cycle":** if this means cycle profit ≥ $2,100 every cycle, later payouts need about $2,900 of new profit, against $800 under the balance reading the JSON uses. Treat a Direct result as an upper bound until support confirms.
- **Tradeify Select eval consistency:** T12 FAQ hints it may govern payouts rather than passing. The simulator raises the target, which is stricter. Fine.

### L1. Smaller items (open, small)
- **Payouts and activation are instant.** Payouts are paid at the close of the first eligible day, and the funded account starts the day after the pass. Real requests take days, and Tradeify denies a payout if the account fails before processing. Slightly flattering.
- **FundedNext Flex price:** $84.99 from the 3rd purchase; the simulator uses $74.99 every time. A few dollars flattering.
- **Tradeify Growth funded DLL** rises to $2,000 at $53,000; the simulator keeps $1,250. Conservative, ±$0 in the check.
- **Topstep doubled caps with the DLL** are a "limited-time offer" (no end date). The 100K/150K XFA lock level is assumed. Both are flagged in the JSON `unverified` fields.
- **`funded_consistency_safe`** uses the first payout's share and profit requirement only, so it ignores schedules. FundedNext Direct gets no funded stop (no target and no goal); this is consistent with the menu's text.
- **`firm_grid.py`** does not re-check that the cached table's dates end by 2024-12-31. The workbench loader refuses exam days when the table is built, so this is defence in depth only. Suggested: refuse if `table.dates.max() > engine.PRACTICE[1]`.

## Checks that passed
- **Rules against sources (12 loadable files):** every simulator number was checked against the source notes. These were also checked live today against the official pages:
  - Topstep pricing, resets and activation (P1), and the payout policy: paths, 50%-of-balance, caps, DLL-doubled caps, $125 minimum, 90% split, MLL to $0 after payout, counts restart (P8).
  - Tradeify Growth eval (T4), drawdown and locks (T10), pricing (T1), Growth payout (T5), consistency (T12), Select payout (T7).
  - FundedNext prices (F5), Flex challenge and funded rules (F13, F14), Rapid Daily funded (F12), Direct (F15).
  - All match except M1–M4 (now fixed) and the open notes above.
- **Loader:**
  - Required fields raise when missing.
  - Topstep `min_days: 2` against the legacy 0 is harmless (55% consistency already needs at least 2 days).
  - FundedNext Flex `min_days: 3` is not stated officially, but the 40%-of-target day cap implies it.
  - Unmapped numeric keys were reviewed. The decision-relevant ones were M3 and H2 (commission); the others (Tradeify DLL rise, list prices, Back2Funded, discounted API) are unused on purpose or conservative.
- **Simulator semantics** (`firm_sim.py`, `play.py`):
  - EOD floors move at the close and are breached on the intraday low.
  - The intraday-trailing breach test is exact or conservative (proof in the docstring checked). No loaded firm uses it.
  - Locks cap the floor. Soft DLL flattens; hard DLL fails on the low until the exit.
  - Eval consistency raises the target; funded consistency blocks payouts.
  - Cap schedules, minimum payout and split are applied; the floor moves after a payout; max payouts end the account without closing it.
  - Monthly billing every 21 trading days with one-time fees, resets, activation per pass, and the platform/API fee for every month touched.
  - Stop-at-target lands at target + $0.01. Size is cut to the max micros.
- **Luck:** gets the identical `Resolved` play (same firm with the optional DLL applied) on the same resampled day indices. It uses its own `rng.integers` draws, has its own account state (its own `to_target` and cushion), and its memo keys include the draw.
- **Menu pin:** the SHA-256 of `account-play-menu.v1.json` equals the `.sha256` pin (`3dc4c2d7…`), and the runner refuses on a mismatch.
- **Exam data:** the runner reads only a workbench trial table, which the engine builds from 2019-05..2024-12 and refuses exam days.
- **Paper bot (skim):** `ProjectXBroker.__init__` raises `LiveTradingDisabled` unless `live=True` and all three env credentials are set. Nothing in `live/runner.py` or the scripts constructs it with `live=True`.

## Independent recomputation
`scripts/q_independent_firm_check.py` (imports nothing from `quant_brain.prop` for its own model) on 600 synthetic paths (sizes 1/2/4/8, drift -20..+40 per lot, seed 7):

| Cell | Mode | Paths differing | Mean net project / independent |
|---|---|---|---|
| Topstep 50K Std, no DLL | match | 0 | 89.40 / 89.40 |
| Topstep 50K Std, DLL | match | 0 | -102.50 / -102.50 |
| Tradeify Growth 50K | match | 0 | -402.76 / -402.76 |
| Topstep no DLL | official billing (M5) | 247 | 89.40 / 109.57 |
| Topstep DLL | low until exit (H1) | 231 | -102.50 / 77.42 |
| Topstep DLL | official billing (M5) | 287 | -102.50 / -79.07 |
| Tradeify Growth | low until exit (H1) | 199 | -402.76 / -293.11 |
| Tradeify Growth | DLL rises to $2,000 | 38 | -402.76 / -402.79 |

Every difference is explained by one named convention. The project's `array_days` path still uses the old low (H1), which is why the "low until exit" rows differ; the grid path (`play.day_fn`) now uses the low until exit.

## Changes made (uncommitted)
- `src/quant_brain/prop/firms.py`: `FundedRules.payout_base`, `min_balance`, `max_cycle_multiple` and their aliases.
- `src/quant_brain/prop/firm_sim.py`: payout uses them; a capped request with `min_balance` is clipped `FLOOR_MARGIN` above the floor; docstrings.
- `src/quant_brain/prop/play.py`: floor checked on the low until the DLL exit; `post_exit_lows` switch for the legacy reproduction.
- `brain/sources/prop_firms/gen_firms.py`, then regenerated (only 4 JSONs changed): `tradeify_growth_50k`, `tradeify_select_daily_50k`, `fundednext_flex_50k`, `fundednext_direct_50k`. Recorded under "QA corrections 2026-10-28" in `tradeify.md` and `fundednext.md`.
- Tests: 4 new tests in `tests/test_prop_firms.py`, 1 new test plus 2 updated expectations in `tests/test_prop_play.py`.
- New: `scripts/q_independent_firm_check.py`.

## Tests
Prop files (`test_prop_firms`, `test_prop_play`, `test_firm_grid`, `test_prop_funded`, `test_prop_policy`, `test_prop_simulator`, `test_prop_portfolio`): 102 passed before, **107 passed** after. Full suite: **1211 passed, 4 skipped** (185 s).
