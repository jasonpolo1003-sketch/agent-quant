---
title: Addendum: Fetna 2026 (SSRN 7428398) full-text record
status: unreviewed
promoted: false
created: 2026-10-22 (UTC-5)
package: 5
source: source_files/orb/fetna_2026_orb_225cell.pdf (sha256 40b68d2f60561cec7f384559c48f7d3e5a528ca1591a0ea1dcabac6ae67e249f; Jason manual SSRN download)
---
# Fetna 2026: "Opening-Range Breakout Does Not Survive Trading Costs" (F1)

**Identity confirmed:** the title, author (Mulham Fetna, BeInMedia/Nmo AI), the 225-cell pre-registration and the 2010–2026 sample all match. It is a 9-page preprint, not peer-reviewed. The code and evidence ledger are at github.com/mulhamfetna/trading-strategy-finder (Zenodo 10.5281/zenodo.21473312). I did not inspect the repo; that is a LEAD. Quote IDs F1–F20 (F19 dropped because the table text extraction is non-linear) are in `quote_verification.tsv`.

## Study record
| Field | Value |
|---|---|
| Instruments | NQ, ES, RTY, YM, GC, SI, HG, CL, NG (F2). Full-size contracts only: **no MES/MNQ** |
| Contract series | continuous contract; roll method not stated; roll days are left inside the trade books (F3, F17) |
| Dates | 2010-06 to 2026-08-07. Exploration 2010–2017 (sign check only); **confirmation 2018–2024 (all verdicts)** (F5); reserve 2025–2026-08 (descriptive) |
| Bars / TZ | 1-minute bars, labelled by opening minute, ET (F3) |
| Session anchors | Arm A at the cash open (for index futures, presumably 09:30 ET; the paper does not state index times, only that 7 of 9 anchors were volume-confirmed and that SI was moved to 07:00 and HG to 09:00). Arm B at the 18:00 ET Globex open |
| OR lengths | 5/15/30/60 minutes (F6) |
| Entry | first 1-minute close beyond the range, filled at the next 1-minute open. One trade per side per session, no re-entry, skip if both sides break on the same bar (F7) |
| Exits / stops | R1: opposite edge stop (1R), 10R target, flat at close. R2: stop at 10% of 14-day ATR, no target, flat at close. R3: opposite edge stop, target at 50% of range. C1: Holmberg volatility threshold comparator |
| Fill conventions | stop fills first when stop and target share a bar (F8); gap-through fills at the bar open |
| Size | 1 contract throughout, with point values held at current specs (F4) |
| Costs | gross, $10 and $25 per round turn, with $25 as the headline (F9). Costs are applied per full-size contract |
| Verdict rule | POSITIVE requires t ≥ 2.5 (Bonferroni within 12 cells), exploration sign agreement, ≥60% of years positive with no year >50% of profit, leave-one-year-out still positive, controls null, and a bootstrap CI excluding 0. NEGATIVE requires minimum detectable effect ≤ $25. Otherwise the cell is UNDERPOWERED or NULL |
| Controls | random anchor (20 draws, must beat the 95th percentile); direction shuffle; volatility-tercile subsumption |
| Trade counts | about 1,800 per one-trade-per-session cell over 7 years (text). Median minimum detectable effect $51/trade (F16) |

## Results
- **Grid:** 0 POSITIVE, 28 powered NEGATIVE, 58 negative-but-underpowered, 138 UNDERPOWERED, 1 NULL (F10). The grid makes +$1.57M gross and loses −$6.49M at $25 per round turn. Median gross edge is −0.01 ticks (F11).
- **Window:** 5-minute is the worst. Losses shrink monotonically as the range widens (F18). R3's 50% target is the worst exit (F20). Cash-open (−$3.70M) vs Globex-open (−$2.78M): "neither anchor is better" (table, read from the PDF but not string-matched).
- **NQ:** the only instrument whose grid is net positive at $25 (+$548k across 25 cells; gross edges up to 16–20 ticks in 60-minute cells) (F12). **No NQ cell clears the bar**: best t = 1.56, and the sign disagrees in 2010–2017 (F13).
  - The best-dollar cell is NQ Globex 60-minute R1 at $72.7/trade net. It **fails the random-anchor control**, since random-hour 60-minute ranges earn up to $113 at the 95th percentile (F14).
  - NQ cash 15-minute R2 earns $87/trade in the top volatility tercile vs $5 in the middle (F15). This is volatility exposure, not an opening effect.
- **ES:** **no ES-specific numbers are reported** in the paper. ES is included only in the grid totals. The per-cell books are said to be in the repo (LEAD, not inspected).
- **Long vs short:** not reported separately.
- **False-breakout / trend-day statistics:** not reported. The regime finding is the volatility tercile result only.
- **Post-publication decay:** the reserve window is said to be reported descriptively, but no reserve numbers appear in the paper.

## Cost sensitivity vs Package 4 levels
- The paper reports only gross, $10 and $25 per round turn, and per-cell results at $10 are **not shown** in the PDF.
- Package 4's cost levels are per **micro** contract (MES $1.22–$11.22; MNQ $1.22–$5.22). A micro is 1/10 the notional of the full-size contract, so the same dollar-per-point P&L requires 10 micros. That makes the full-size-equivalent friction about 10× (ESTIMATE, arithmetic):
  - MNQ L0–L5 ≈ $12.2–$52.2 per NQ-equivalent round turn.
  - MES L0–L5 ≈ $12.2–$112.2 per ES-equivalent round turn.
- **So Fetna's $25 headline is not "stressed" relative to micros.** It falls inside or below our micro cost range. Even our cheapest level (L0, fees only, ≈ $12.2 NQ-equivalent) is above Fetna's $10 scenario.
- Conclusion: **no ES/NQ setup in Fetna survives at any cost level reported, even gross of the verdict bar**. NQ's net-positive dollars come from cells that are not statistically significant and are explained by volatility or random-anchor controls. MES/MNQ costs, scaled to notional, would be no better.

## Corrections to the earlier snippet-based record
- Confirmed: 225 cells; 9 futures; two anchors; OR 5/15/30/60; 3 exits; 0/225 at $25; median −0.01 ticks; 5-minute worst; best cell fails the random-anchor control.
- Corrected or added:
  - The "best cell" is NQ Globex 60-minute R1.
  - The grid is 216 cells plus 9 comparator cells.
  - Verdicts come from the 2018–2024 window only.
  - A $10 scenario exists.
  - NQ is net positive in aggregate at $25 (the snippet implied uniform failure).
  - 138 cells are underpowered, meaning "not proven", not "proven absent".
  - The paper cites Mesfin as "A." with a different title from the arXiv record we hold ("M. Mesfin", "Structural Limits…"). Same arXiv ID, so this is a citation error in Fetna.

## Verified facts
F1–F18 and F20 as above.
## Indirect but credible evidence
The repo claims ledger is the source for per-cell ES/NQ books and the $10 results (LEAD).
## Conflicting evidence
- NQ is net positive in aggregate vs no NQ cell passing. Both are true; the result is underpowered, not a contradiction.
- Fetna's 5-minute-worst finding vs Zarattini's 5-minute-optimal finding is still unresolved (equities vs futures).
## Unknowns
- ES per-cell results; long/short split; $10 per-cell results; reserve-window results; exact roll method; index cash-open times.
## Engineering assumptions still required
Scaling micro costs to full-size equivalents (×10, ESTIMATE); whether roll days are excluded.
## What was genuinely new
- The power analysis: about 13,000 trades are needed to detect $25, against about 1,800 available.
- NQ-only residual dollars, explained as volatility continuation.
- Micro cost scaling makes Fetna's $25 a *favourable* case for MES/MNQ.
## What confirmed an existing decision
ORB stays a falsification target. Package 6 needs power or minimum-detectable-effect reporting and random-anchor controls.
## What should change in the roadmap
- Add minimum-detectable-effect / power reporting per cell as a Package 6 CONVENTION (QAB-OPTION, not chosen).
- Any MES/MNQ ORB test should report costs in NQ/ES-equivalent terms.
## What should not change
No parameter selection from NQ 60-minute cells; no combining with other studies.
## Next bounded action
Optional: read-only inspection of the Fetna GitHub repo evidence files for ES/NQ per-cell books, the $10 results and the long/short split. Public, no data purchase.
