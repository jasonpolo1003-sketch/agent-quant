# Plan: find a stronger, different same-day edge (2026-10-28, proposed)

Why: SC-FUT-0005 (noise-area momentum) failed exam check #1 on 2025-26 (`brain/05_Reviews/SC-FUT-0005-exam-check-1-2026-10-28.md`). Tried and failed so far: opening-range breakout, late-day momentum, shock reversal, noise-area variants (pyramiding, multi-market, sizing, day tilt). Not tried: **reversion to a fair price**, the evening session, gap fills.

## Constraints (unchanged)
- Same-day MNQ/MES, flat by 15:10 CT (Topstep), automatable in Python, orders within seconds of the signal.
- Practice data 2019-05..2024-12 only; the exam (2 checks left, bars 0.025 then 0.0125) only for one finalist, with Jason's OK.
- No money spent. FRED (free, key already in `.env`) for release dates; notice in README.

## Candidates (each a frozen card before any result; parameters from the source, not tuned)
| Card | Rule (plain English) | Source | Trades/day |
|---|---|---|---|
| **C1 Fade inside the noise band** | Between 9:00 and 14:30 CT, when price is inside the noise-area band but more than half-way from the open to the band edge, trade back toward the open; stop just beyond the band edge (where momentum takes over); flat at 15:00. | Zarattini et al. (inside the band = noise) + JJ Simon's "open is fair price" | 0-3 |
| **C2 RTH gap fill** | If the 8:30 CT open gaps more than a set fraction of normal daily range from the previous 15:00 close, trade toward the previous close; stop at a multiple of the gap; flat at noon or the fill. | Classic gap-fill studies; JJ's gap-fill trades | 0-1 |
| **C3 Evening reversion to the 17:00 reopen** | 17:00-20:30 CT: after a move away from the reopen price beyond its normal size for that time, trade back to the reopen price; stop beyond the move's extreme; flat by 20:30. | JJ Simon's 6 PM / Asia-open setup | 0-2 |

Each is judged like SC-FUT-0005: L3 costs, matched random-direction control, paired test with the family's honesty bar, by-year and calm/volatile slices. FRED release dates (CPI, jobs, GDP, PCE, PPI) are added as a **diagnostic slice only**, never a filter chosen on results.

## Order
1. **Data checks:** confirm the minute bars cover the evening session for C3 (the RTH loader may need an evening session builder) and pull FRED release dates for 2019-2024.
2. Freeze C1-C3 cards (one commit, before any run). Build each as a workbench plug-in with hand-worked fixtures first.
3. Run all three on practice data. A candidate goes further only if it beats luck at its bar AND has a practice Sharpe that gives the exam a fair chance (target >= 1.5 annual; SC-FUT-0005's 1.31 gave ~50% exam power).
4. Prop simulator on any survivor (P1-P4 menu), then Jason decides on exam check #2.
5. Stop rule: if all three fail, write it up and step back on the prop route before more ideas.

## Roles
Engineering (plug-ins + evening loader), quality (fixtures, look-ahead audit of each rule, independent recount of one card), research (sources for each rule's fixed numbers, FRED pull), orchestrator (freezes, runs, review, vault).

## Effort
About 1-2 sessions, $0.
