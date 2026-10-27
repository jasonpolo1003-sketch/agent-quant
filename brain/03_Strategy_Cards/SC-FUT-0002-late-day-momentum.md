---
card_id: SC-FUT-0002
status: frozen
frozen: true
frozen_at: 2026-10-27
frozen_spec: brain/_system/futures/sc-fut-0002-spec.v1.json
frozen_spec_sha256: 3a8cd177bd45a29f0257ba416d01cb94865f4354ab102539cdaec71c332fcd38
created: 2026-10-27
method_family: late_day_momentum
primary: MES
comparison: MNQ
source_status: peer_reviewed (Baltussen et al. 2021, JFE)
---

# SC-FUT-0002 — Late-day hedging-flow momentum

> **FROZEN 2026-10-27** by Jason before any result. Binding rules and grading: brain/_system/futures/sc-fut-0002-spec.v1.json. Grades per contract per day after L3: under $5 fail, $5-10 small edge, $10-15 good, $15+ strong; any pass also needs beating the random-direction benchmark at the honesty-adjusted bar and an annual Sharpe of at least 1.0. The random entry-time comparison is deferred.

**No results had been looked at when this card was frozen.** Research: `brain/sources/candidate_ideas_2026-10-26.md`.

## The idea in one line
If the market is up since yesterday's close by 2:30 pm Chicago, buy for the last half hour; if it is down, sell. Options dealers and leveraged ETFs are forced to trade in the day's direction near the close (Baltussen, Da, Lammers & Martens, JFE 2021).

## Rules (bare paper version, no filters)
| Item | Rule |
|---|---|
| Days | NYSE cash sessions from the frozen calendar `session-calendar.v1.csv`. **Early-close days: no trade** (they have no normal last half hour; about 2 days a year). |
| Contract | D-ROLL-01 dated contract (same as SC-FUT-0001); no stitching. |
| Signal | Return from the previous session's regular close (last bar starting before 15:00 CT, same dated contract) to the close of the 14:29 CT bar. |
| Trade | Up: long 1 contract; down: short; exactly zero: no trade ($0). |
| Entry | Open of the 14:30 CT bar. If that bar is missing: skip ($0, logged). |
| Exit | Open of the 15:00 CT bar (the cash close). If missing: non-evaluable (never a fabricated fill). |
| Stop / target | None, as in the paper. |
| Costs | L3 once per round trip: MES $6.22, MNQ $3.22; L1–L4 reported. |

## How it is judged
- **Main comparison (new):** the same 14:30→15:00 window with a **random direction**, 500 seeded draws per day. This asks whether the signal picks the right direction, not merely whether the last half hour is a good time.
- **Also reported, not deciding:** an "always long in the last half hour" benchmark (does a plain end-of-day drift explain it?). The random-entry-time comparison is deferred (see spec).
- **Statistics:** same as SC-FUT-0001 (one-sided paired stationary bootstrap, mean block 5, B = 9,999), at the workbench's honesty-adjusted bar for the new `late_momentum` family. MES is the primary; MNQ runs the identical rule as a second trial in the same family, not an independent confirmation.
- **Data:** practice 2019-05-01..2024-12-31 only. The 2025–26 exam stays locked (future proctor, 3 checks).
- **Grading (decided by Jason before any result):** see the frozen banner above.

## Carries over unchanged from SC-FUT-0001
Integer-tick prices, calendar and 12:15 CT early-close handling, no-bars-in-window → ineligible, missing-bar rules, trial ledger, and the hash-pinned freeze before running.

## Decisions
All settled on 2026-10-27; see the spec.
