# SC-FUT-0005 exam check #1 (2026-10-28): FAIL

- Question: `brain/_system/proctor/q1-sc-fut-0005.json` (frozen and committed b5da934 before the check). Approved by Jason ("Strategy first").
- Proctor: `src/quant_brain/workbench/proctor.py` (W8): one bit per check, budget 3, bars 0.05 / 0.025 / 0.0125 one-sided with small fixed noise. No exam numbers were shown or stored.
- Before the check, the full-file loader rebuilt all 1,425 practice days identically to workbench trial 266777ef, so the answer is not a loader artefact.
- **Answer: FAIL.** On 2025-01-01..2026-10-21, the frozen SC-FUT-0005 rule did not both earn a positive net per day and beat the random-direction control at the bar. Which part failed is deliberately unknown.

## How to read it
- Power (computed after the check, from practice numbers): if the true edge were exactly the practice $11.49/day with a ~$139 daily SD, ~450 exam days give an expected t of ~1.75, so even a fully real edge passes only about half the time. A FAIL does not prove the edge is gone; it means it is **not confirmed** on fresh data.
- Per the frozen question: SC-FUT-0005 is not trusted for real money; the prop and live plans built on it stop. The calm-day filter is not worth check #2 (it sits on top of this rule).
- Checks left: 2 of 3, at stricter bars (0.025, 0.0125).

## What this leaves
- Forward paper trading is now the only clean new evidence for SC-FUT-0005 (slow: months).
- New strategy research: a different, stronger edge, tested on practice data first and on the exam only as a finalist.
