---
card_id: SC-FUT-0001
status: draft_for_review
frozen: false
created: 2026-10-25
method_family: opening_range_breakout
primary: MNQ
comparison: MES
plan_change: PROP-011
source_status: unreviewed_research_lead
---

# SC-FUT-0001 — Draft MNQ cash-open 15-minute ORB, R2 exit

**FREEZE-REVIEW DRAFT — NOT FROZEN OR TESTABLE.** Jason supplied an economic floor and defaults for the open rows; they are engineering assumptions, not sourced findings. The proposed canonical spec is `brain/_system/futures/sc-fut-0001-spec.v0.json` (draft, fail-closed); the freeze-review checklist is `brain/05_Reviews/SC-FUT-0001-freeze-review.md`. No implementation or strategy P&L run is authorized by these documents. Fetna's headline result is negative after costs; the expected outcome is `not_demonstrated`, not a prop-eval timeline.

## Question and hierarchy

Does one predeclared cash-open ORB on one MNQ contract produce economically meaningful **net daily P&L after L3 costs** beyond paired same-session random-time controls on a locked internal held-out period? Include all eligible session days, even days without a trade. MES is reported separately under the same rule as a comparison; it cannot rescue an MNQ miss. A pass permits only a proposed execution-calibration study, not paid purchases or trading.

## Source and selection history

The rule is adapted from Fetna (2026), *Opening-Range Breakout Does Not Survive Trading Costs*, an unreviewed preprint with a 225-cell predeclared grid across nine full-size futures. Local saved text: `brain/sources/mes_mnq/source_files/orb/fetna_2026_orb_225cell.txt` in the separate `testing` worktree; research summary: `brain/sources/mes_mnq/orb_evidence/fetna_2026_addendum.md`. The saved PDF's source hash is reported there as `40b68d2f60561cec7f384559c48f7d3e5a528ca1591a0ea1dcabac6ae67e249f`; verify before freezing. The note labels its evidence **unreviewed/not promoted** and may not be silently promoted with this card.

The researcher had looked at Fetna's 225-cell grid and at Mesfin's MNQ ORB before this card. The 15-minute cash-open R2 choice was mentioned as a candidate in `validation/validation_methods.md` §4; it is not a fresh, independent discovery. It is **one new local rule**, with inherited selection exposure to be described conservatively; do not automatically count every paper cell as Jason's own trial or use an optimistic effective-trial count. A single frozen local rule has **PBO not applicable**, per accepted PROP-011; a future selectable family is a different experiment requiring CSCV/PBO and all trial daily series.

## Sourced rule spine (not implementation-complete)

Fetna's saved text, §4.1 (lines 119–136), states:

> “the range is the high–low of the N one-minute bars from the anchor; a range with any missing bar is void.”
>
> “the first one-minute close beyond the range high (long) or below the range low (short) after the range completes, filled at the next one-minute open; one trade per session per side; no re-entry after a stop; no trade if both sides break on the same bar.”
>
> “R2 (‘ATR-stop’, Zarattini et al. 2024): stop at 10% of the 14-day ATR, no target, flat at close.”
>
> “when a bar gaps through a stop or target level, the fill is taken at that bar’s open, not at the level.”

**Proposed adaptation:** use the 08:30 CT equity-index cash open, take the first 15 complete one-minute bars, consider breakout signals only from a bar **after** range completion, next-minute-open entry, one MNQ micro, R2's 10%-of-prior-14-day ATR stop, no target, and voluntary flat by 15:07 CT rather than at the CME session close. “08:30 CT” and the 15:07 exit are project engineering choices; Fetna's paper does not state the exact index cash-anchor clock. The R2 rule in the original paper was on full-size NQ among other markets, not MNQ.

**Known preserved decisions:** use raw dated contracts (no back-adjustment for fills), `America/Chicago` session/calendar; fixed roll from D-ROLL-01 primary and prior-day-volume sensitivity; do not forward-fill absent minutes into fills; adverse same-bar stop-first where relevant; no event-day exclusions in the primary; L3 round-turn MNQ $3.22 and MES $6.22, with L1–L5 reported as nonselectable stress scenarios. The fixed early roll trades a thinner contract around the window, so roll-window outcomes must be visible. Annual, regime and top-day concentration are diagnostics, not independent automatic pass gates.

## Jason's supplied defaults — all **engineering assumptions**, not paper findings

| Topic | Freeze-review draft |
|---|---|
| Economic relevance | **At least $15 net per MNQ per eligible session day** at L3, with no-trade days $0. This is an economic floor, **not an observed effect**; absolute daily mean below this cannot qualify as useful even if statistically distinguishable from controls. |
| Entry eligibility | One trade per side per session; a short may follow a stopped long; no new **entry fill** after 14:30 CT. One close cannot be both strictly above the range high and strictly below its low: simultaneous double-break is impossible for this close-based signal; assert the invariant. |
| ATR | Simple mean of true ranges from prior 14 completed sessions of the *dated contract being traded*, no stitching. Missing prior close or fewer than 14 valid prior dated-contract sessions makes the candidate session **ineligible from data alone**, not from trade outcomes. Stop distance = 10% of ATR, nearest 0.25-point tick, minimum one tick; exact midpoint rounds **up to the next tick** (half-up). Session boundary/close definition remains for approval. |
| Entry | First one-minute close beyond the 15-minute range, next minute's open; if that minute is missing, skip and log. L3 already includes modeled slippage; **do not add it a second time**. |
| Stop | Stop level, or adverse bar open if gapped through; stop on the entry bar if touched. No target. If a minute is missing **while a stop is live**, the worse of stop level and next visible bar's adverse extreme is a **stress bound only**, not an observed fill; flag/count it and retain outcome as uncertain. Proposed pre-result alarm: >1% of eligible sessions **or** >1% of executed trades with such a gap makes affected result inconclusive, subject to Jason's approval. Even below this alarm, any conclusion that flips under the bound is inconclusive. Never replace unknown primary execution with the bound as fact. |
| Exit | Market exit at 15:07 CT minute open. On verified early-close days, flatten at the minute open three minutes before the close. If unavailable, do not manufacture a fill; mark non-evaluable/failure by an approved fail-closed policy. |
| Primary inference | One-sided paired daily ORB-minus-random-anchor mean, α = 0.05, stationary block bootstrap mean block length five eligible days; absolute net MNQ mean at least $15/day is an additional **economic** requirement. Bootstrap implementation/p-value, power target and selection adjustment need signoff. |
| Controls | 500 seeded draws **per eligible session**, random minute after range completion through 14:30 CT and random direction, same ATR stop, exit, cost and contract. Preserve every draw and paired day; random-entry controls are **not** an ORB breakout-rule clone. Freeze seed and exact sampling/aggregation. |
| Ambiguity | More than 10% of executed trades with entry and stop touched in the same one-minute bar causes review **before** held-out. Define denominator, zero-trade policy and what the review can approve without result-driven tuning. |
| Sample | Development 2019-05-01..2023-12-31; diagnostics 2024-01-01..2024-12-31; locked internal held-out 2025-01-01..2026-10-21, inclusive dates in Chicago session/trade-date convention. Calendar/contract coverage still requires audit. No claim of independent discovery. |

**Cost accounting caution:** paper-style gap-through execution price and D-COST-01 L3 four ticks round turn apply to different layers. A gap fill is the observed OHLC reference, then L3 is the *single* assumed aggregate spread/slippage/fee adjustment; do not add an extra stop penalty or subtract the spread again. L5 is a paused/no-fill scenario rather than a dollar charge.

**Remaining freeze decisions** (do not silently default): precise dated-contract true range session close; proposed missing-stop stress-bound frequency threshold; still-unavailable halt/early-close calendar and date eligibility; final control matching/seed/aggregation and same-direction timing diagnostic; joint power target and one-sided paired bootstrap specification; selection/DSR and prior-look ledger; trial/manifest hashes. See `brain/05_Reviews/SC-FUT-0001-prefreeze-defaults.md` for one reviewable list. The machine-readable draft remains non-executable pending approval.

No dev or held-out P&L or empirical standard deviation has been measured here; $100–150/day in the pasted commentary is illustrative only.

## Proposed decision structure (requires approved statistical addendum)

- **Pre-run feasibility:** estimate power/MDE for the $15 net/MNQ/eligible-day economic floor using only allowed development or defensible external variance information; the paired-control test and absolute mean threshold both need adequate power. Set the power target and algorithm before opening held-out data. If MDE exceeds $15, stop and redesign *before* held-out results.
- **Decisive evidence (freeze-review proposal):** one-sided paired daily ORB-minus-random-anchor mean at α = 0.05 with mean-five-day stationary blocks **and** absolute MNQ L3 net daily *observed* mean at least $15 including no-trade $0, subject to a predeclared selection/DSR treatment. The **lower one-sided confidence bound on the absolute mean clearing $15 is an unselected alternative** for freeze review, not an added pass gate. Exact p-value construction, target true effect for power and trial adjustment remain unapproved. Avoid nine independent vetoes or forced “remove best 5%” tests.
- **Development-only prop-eval diagnostic:** after freezing and authorized dev replay, block-bootstrap the daily L3 rule and paired controls at 1/2/3/5 MNQ against a **versioned, supplied** evaluation rulebook. Report pass, blow-up, timeout probabilities and conditional median days to pass. Intraday trailing drawdown and daily loss limits require intraday equity/excursion paths; daily totals alone cannot establish exact venue probabilities. See the freeze-review packet. This is not an outcome gate, evaluation purchase, or live-trading approval.
- **Diagnostics:** year/regime, fixed versus volume roll, L1–L5, ambiguity, top-day concentration relative to the random control, leave-one-month/quarter-out. Materially fill-sensitive or calendar-unsupported results are `inconclusive`.
- **Outcomes:** `pass_to_execution_calibration`, `not_demonstrated`, `inconclusive`. No tuning, MES rescue, reuse of held-out as unseen, evaluation purchase or broker automation.

## Review checklist and freeze requirements

- [ ] Resolve the freeze-review blockers, pin the exact eval venue/rulebook separately, and verify source/status labels and paper hash.
- [ ] Produce the final canonical spec, full data/calendar/source hash inventory, and local trial-exposure ledger; draft `brain/_system/futures/sc-fut-0001-spec.v0.json` is deliberately non-executable and contains null blockers.
- [ ] Produce a reproducible development-only power/MDE worksheet using **$15 net per eligible day** and a prespecified power target, including no-trade days and dependence; **no locked P&L**.
- [ ] Quant-method and software reviews find no material ambiguity; review is a checklist, not independent empirical validation.
- [ ] Jason approves the exact card, decision statistic and thresholds; hash and commit the approved version before strategy implementation or development-period ORB P&L. A prop-eval simulator diagnostic follows authorized dev replay and cannot substitute for the held-out gate.

**Current state:** freeze-review draft, not frozen. No strategy P&L, simulator probability, empirical MDE or authorization to open held-out; missing parameters are not silently inferred.