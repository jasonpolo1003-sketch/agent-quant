# SC-FUT-0001 — outcome-blind session audit (2026-10-26)

**Audit only.** Run on the development-only partition (`dev-partition-manifest.json`). It checks which one-minute bars exist for the D-ROLL-01 contract; no range, breakout, price or P&L was computed. Output: `brain/_system/futures/session-audit-dev.{csv,json}`; code: `src/quant_brain/futures/session_audit.py`, `scripts/audit_dev_sessions.py`.

## Calendar source
- CME's site (cmegroup.com) timed out on every fetch, so the official archive was **not** retrieved.
- Used `pandas_market_calendars` 5.5.0 (versioned, secondary): NYSE for cash-open days (1,428 in 2019-05-01..2024-12-31), CME_Equity for Globex closes. The 40 CME-only holiday sessions (e.g. Thanksgiving, MLK Day) have no cash open and are not candidate days.
- **Correction:** the library gives a 12:00 CT CME close on the 12 early-close days. Every one has MNQ/MES bars through 12:14 CT, and CME's 2011 holiday notice states 12:15 CT for Globex equity indexes. The audit uses **12:15 CT, so the exit is 12:12 CT**; each override is flagged per row. Needs Jason's confirmation.

## Results (MNQ primary; MES comparison)

| | MNQ dev 2019–23 | MNQ diag 2024 | MES dev | MES diag |
|---|---|---|---|---|
| Cash sessions | 1,176 | 252 | 1,176 | 252 |
| ATR warm-up ineligible | 17 | 0 | 17 | 0 |
| Opening range incomplete | 8 | 0 | 6 | 0 |
| **Candidate days** | **1,154** | **252** | 1,156 | 252 |
| Candidates with a missing minute while a stop could be live | 5 (0.43%) | 1 (0.40%) | 9 (0.78%) | 0 |
| Candidates missing the exit bar | 1 | 0 | 1 | 0 |

- **Below the approved 1% alarm** on the session denominator for every cell. The trade denominator can only be measured after the authorized replay.
- **Warm-up:** micros launched in May 2019 (first bar 2019-05-05), so the first 17 sessions lack 14 prior sessions.
- **Incomplete ranges:** the 2019-06-13 and 2019-09-12 roll days (thin new MNQ contracts) and the March 2020 limit-down openings (03-09, 03-12, 03-16).
- **Live-window gaps** fall almost entirely on fixed-roll days (thinner deferred contract, as the D-ROLL-01 liquidity note predicted) and on 2020-03-18. MNQ 2019-12-12 (roll day) is missing 122 live minutes and the exit bar.

## Decisions needed (recommendations in brackets)
1. Early-close time 12:15 CT, exit 12:12 CT [confirm; matches data and the CME notice].
2. A day with an incomplete opening range is a **no-trade, $0** day for both ORB and the random control, rather than dropped [recommend; follows Fetna's "void range" rule and approved item 8].
3. Whether CME-only holiday sessions count toward the 14-session ATR window [recommend no; the audit uses NYSE sessions only, and this affects only windows that span those holidays].

Development n ≈ 1,154 is close to the power worksheet's upper bound of 1,213, so the conditional power rows are not materially changed. Empirical variance still requires the authorized replay.
