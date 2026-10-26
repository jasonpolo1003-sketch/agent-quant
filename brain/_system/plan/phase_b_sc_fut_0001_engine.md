# Step 2 plan — SC-FUT-0001 engine (build and verify, no real P&L)

Status: proposed 2026-10-26, for Jason's approval. Implements the frozen spec `brain/_system/futures/sc-fut-0001-spec.v1.json` (SHA-256 `e19f1907…30fb`). **Step 2 uses synthetic bars only.** Running the rule on real data is Step 3 and needs Jason's separate OK.

## Goal
A program that trades the frozen rules minute by minute and a second program written independently, both producing the same trades on every test day. Plus the random-control generator, the statistics and a gated runner, all ready but not run on real data.

## Milestones

| # | Build | Key behaviour | Done when |
|---|---|---|---|
| M1 | **Bar loader** `futures/bars.py` | Reads only the dev partition (checks its manifest hash); per-contract minute bars as integer ticks; frozen `session-calendar.v1.csv` (not the live library); D-ROLL-01 contract per day. Refuses the raw `rc_2026-10-22` folder unless a held-out authorization exists (Step 4). | Unit tests on synthetic DBN; bar counts reproduce `session-audit-dev.json` exactly (counts only, no strategy maths) |
| M2 | **Rule engine** `futures/orb.py` | ATR (15 regular-hours closes, NYSE sessions, half-up tick rounding); range 08:30–08:44 (void on any gap = $0 day); signal from 08:45; next-open entry (skip if missing); 14:30 fill cutoff; stop incl. gap-through and entry-bar touch; opposite side only after the exit bar; 15:07 / 12:12 flatten; missing minute with live stop → stress bound, never a fill; missing flatten → non-evaluable; L3 cost once per round trip. Integer cents throughout. | All rule fixtures (M7) pass |
| M3 | **Random controls** `futures/controls.py` | 500 draws per day, PCG64 seeded `[20261026, root, yyyymmdd]`; k = ORB entry count; uniform legal fill minute after previous control exit; rejection on missing bar (logged); random direction; same stop/exit/cost; daily control = mean of 500. | Fixtures + determinism test (same seed → identical draws; seed change → different) |
| M4 | **Independent reference** `futures/orb_reference.py` | Written separately from M2: plain loops over a dict of minutes, `Decimal` maths, no shared helpers except the loader. | Matches M2 trade-for-trade and to the cent on every fixture and on ≥10,000 random synthetic days, including gaps, gaps through stops, early closes and roll days |
| M5 | **Statistics and verdict** `futures/inference.py` | Upgrade `prefreeze_stats.py` to the frozen test (B = 9,999, seed 20261027, null-centred, `(k+1)/(B+1)`); $15 floor; Politis–White block length (sensitivity only); DSR at N = 1 and 25 (diagnostic); 1% missing-minute and 10% same-bar alarms; power check from development variance; verdict ∈ {pass_to_execution_calibration, not_demonstrated, inconclusive}. | Synthetic tests: null → no pass; planted +$25/day → pass; planted +$10/day → not_demonstrated (below floor); alarms trigger inconclusive |
| M6 | **Gated runner** `scripts/run_sc_fut_0001.py` | `--phase development` requires: spec hash = ledger freeze hash, committed clean code, a `development_authorized` ledger event by Jason. `--phase held-out` additionally requires a separate authorization, an approved development report, code unchanged since the development run, and writes a once-only marker **before** computing. Appends every run to `SC-FUT-0001.trials.jsonl`; writes trade log, daily rows (incl. $0 days), stress-bound table and report. | Gate tests: each missing precondition refuses to run; held-out cannot run twice; a crash records `held_out_failed` |
| M7 | **Hand-worked fixtures** `brain/_system/futures/orb-fixtures.md` + tests | ~20 tiny synthetic days worked out by hand before coding M2: normal long/short; no breakout ($0); void range; long stopped then short; stop touched on entry bar; gap through stop; missing entry minute; missing minute with live stop (bound); missing flatten (non-evaluable); early close 12:12; 14:30 cutoff edge; signal on exit bar ignored; ATR ineligible; tick half-up rounding; L3 arithmetic; same-bar ambiguity counting. | Written and committed **before** M2 code; M2 and M4 both pass them |
| M8 | **Review** | Mutation check (deliberately break rules and confirm tests catch it, as in SC-0002); an independent code review against the frozen spec; fix findings. | No unresolved findings; full suite + Ruff + CI green |

Order: M7 → M1 → M2 → M4 → M3 → M5 → M6 → M8. Estimate 2–3 sessions.

## Scope kept out
- The minute-by-minute equity stream for prop-firm rules (draft `trade-equity-record-draft.json`) waits for the deferred prop-eval; M2 records trades and daily rows only.
- No UI chart wiring yet.
- No real-data strategy run, no held-out access, no purchases.

## Exit criteria for Step 2
All milestones done; engine = reference on fixtures and ≥10,000 synthetic days; gates proven by tests; review clean; PR merged. Then ask Jason for the Step 3 development authorization.
