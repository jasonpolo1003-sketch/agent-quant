# New-edge plan results (2026-10-28): all three FAILED

Plan: `brain/_system/plan/new_edge_plan.md`. Cards frozen bece950 (+ SC-FUT-0011 addendum 1, 8b2106f, before any result). QA: `new-edge-QA-2026-10-28.md` (shared Sidak bar 0.0170 fixed before the run; independent gap-fill recount 2,000/2,000). Practice 2019-05..2024-12, volume roll, L3.

| Card | MNQ $/day | vs luck | p (bar 0.0170) | Sharpe | MES diag $/day |
|---|---|---|---|---|---|
| SC-FUT-0009 fade inside the noise band | -8.88 | -4.49 | 0.945 | -1.22 | -11.89 |
| SC-FUT-0010 RTH gap fill | -3.68 | -2.22 | 0.740 | -0.45 | -6.12 |
| SC-FUT-0011 evening reversion to 17:00 | -2.53 | +1.10 | 0.071 | -1.18 | -7.04 |

- Not a cost problem: at L1 (fees + 1 tick) they are still negative (-6.44, -2.90, -0.91 $/day).
- 0009 loses *more* than random: fading moves inside the band is the wrong way round, consistent with SC-FUT-0005's momentum (not a new edge, the same one).
- 0011 is slightly better than its luck control but negative after costs in every year.
- Days: 1,425 (0011: 1,423; 2 non-evaluable). Traded days: 1,126 / 743 / 971.

## Diagnostic slice (not a result; never a filter chosen here)
FRED release days (CPI, jobs, GDP, PCE, PPI; 347 days): gap fill made +$11.57/day there (+$12.34 vs luck) and -$8.59 on other days. Found after the fact on one of several slices, so it is a hypothesis only. It could be tested only as a new frozen card judged on fresh data (exam check or forward), with Jason's OK.

## Housekeeping
The ledger has the SC-FUT-0011 MNQ trial twice (same fingerprint and code, 10 s apart; cause not confirmed). The honesty counter counts distinct settings, so the bar is unaffected.

## Stop rule (from the plan)
All three failed, so the plan's stop rule applies: write up and step back on the prop route before more ideas. Running count of failed same-day MNQ ideas: ORB, late momentum, shock reversal, pyramiding, multi-market, cushion sizing, day tilt, fade band, gap fill, evening reversion; SC-FUT-0005 (the one practice pass) failed exam check #1.
