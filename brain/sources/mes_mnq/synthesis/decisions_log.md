---
title: MES/MNQ decisions log
status: unreviewed
promoted: false
created: 2026-10-22
---
# Decisions log (QAB ENGINEERING POLICY)

| ID | Date | Decision | Label | Decided by | Reversible | Rationale | Revisit trigger | Sources |
|---|---|---|---|---|---|---|---|---|
| D-COST-01 | 2026-10-22 | Carry L1–L5 as stress columns in all MES/MNQ backtests. **Gate level = L3**: MES $6.22, MNQ $3.22 round turn | QAB ENGINEERING POLICY | Jason, by delegation ("whatever u think is best") | Yes | ORB stop entries during breakouts likely slip more than the one-tick ES spread proxy, so the gate fails closed | CME Liquidity Tool or tick-sample spread data contradicts it | execution_costs/execution_costs_mes_mnq.md (cost ladder L0–L5); synthesis/synthesis.md §4 |

The L3 dollar figures come from the Package 4 ladder: $1.22 fees plus 4 ticks (MES 4 × $1.25; MNQ 4 × $0.50). L0 (fees only) remains a reject candidate and is not carried as a column. L5 (no fill / pause) is a scenario column, not a dollar level.

| ID | Date | Decision | Label | Decided by | Reversible | Rationale | Revisit trigger | Sources |
|---|---|---|---|---|---|---|---|---|
| D-ROLL-01 | 2026-10-23 | **Fixed calendar roll**: trade the next quarterly contract from the start of the CME trade date = actual expiration (from definitions) minus 8 calendar days, moved to the prior business day if a CME holiday/no session. Normally the Thursday 8 days before the third-Friday expiry; Jun 2026/2027 (Thursday expiry, Juneteenth) roll on Wednesday. Sensitivity: volume roll using prior-day volume only | QAB ENGINEERING POLICY | Jason, by delegation ("Ok go for it") | Yes | ORB is flat intraday so the roll barely matters; fixed calendar has zero look-ahead; matches CME's equity-index roll week | Sensitivity run shows materially different ORB results or fills on roll days; see liquidity note below | contracts/roll_calendar_2019_2026.csv, contracts/roll_volume_check.csv, contracts/build_roll_calendar.py; contracts/contracts_sessions_rollover.md; source_files/cme_equity_rolldates.* |

D-ROLL-01 liquidity note (2026-10-23 check, local R-C data): on all 60 historical roll dates (30 MES, 30 MNQ) the to-contract had LESS prior-day volume than the from-contract (0/60 agreement). The prior-day-volume roll comes 2–4 trading days later (mean 2.6 MES, 3.0 MNQ), usually the Monday–Wednesday of expiry week. So the fixed roll trades the thinner deferred micro for about 3 days per quarter. That is a cost/fill sensitivity item for Jason to review; the decision itself is unchanged.
