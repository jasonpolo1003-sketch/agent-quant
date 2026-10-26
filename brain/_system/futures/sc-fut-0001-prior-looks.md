# SC-FUT-0001 — prior looks ledger (at freeze, 2026-10-26)

Everything seen before the rule was frozen that could have influenced its choice. Hash-pinned by the frozen spec.

| # | What was seen | Overlap with this card's data | Influence |
|---|---|---|---|
| 1 | Fetna (2026) 225-cell ORB grid: 0/225 pass at $25/RT; NQ cash 15-min R2 cell net-positive but not significant, $87/trade in top volatility tercile vs $5 middle | Paper's confirmation window 2018–2024 (full-size NQ) overlaps development 2019–2023 and diagnostics 2024 | The rule was chosen from this grid's family; development data is therefore **not a fresh look** |
| 2 | Mesfin (2026) MNQ ORB: fails out of sample | MNQ, overlapping years | Reinforced a falsification framing |
| 3 | Zarattini & Aziz (2023) QQQ 5-min ORB and its public replication (gross reproduced, net ≈ 0) | ETF, 2016–2023 | Source of the 10%-ATR-stop idea (R2) via Fetna |
| 4 | Local SC-FUT-0001 outcome-blind session audit (bar presence only) | Development and diagnostics | None on returns: no prices, ranges or P&L computed |
| 5 | Local RX-0001 RSI exit replication, SC-0002 (SPY daily) | Different instrument and rule | None for this rule |

**Not seen:** any MNQ/MES price outcome of this rule; any 2025-01-01..2026-10-21 futures data (the locked period). Fetna reports no reserve-window (2025–2026) numbers.

**Treatment (Jason, 2026-10-26):** the locked 2025–2026 test is decisive because nobody, Fetna included, has looked at it. As a diagnostic only, the DSR is reported at N=1 and at N=25 (Fetna's NQ cells, 216/9 = 24 grid cells plus one comparator); it is not a pass/fail gate.
