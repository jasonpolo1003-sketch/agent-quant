---
card_id: SC-FUT-0004
status: draft_for_review
frozen: false
created: 2026-10-27
method_family: liquidity_shock_reversal
primary: MES
second_trial: MNQ
gate: prop evaluation simulator (Topstep 50K) first, workbench statistics second
---

# SC-FUT-0004 — Rare liquidity-shock reversal (draft, not frozen)

**Draft for Jason. No results have been looked at.** Research: `brain/sources/prop_firm_same_day_ideas_2026-10-27.md` (Christensen, Oomen & Renò, "drift bursts", J. Econometrics).

## The idea in one line
On the rare minutes when the market lurches far faster than normal (not on a scheduled news release), wait for the lurch to stall, then bet on part of it snapping back, with a stop just beyond the extreme and out within an hour.

## Proposed rules (every number is a decision for Jason, fixed before any result)
| Item | Proposal | Why |
|---|---|---|
| Market | MES first; the identical rule on MNQ as a second, related trial | Research is S&P-based; MES/MNQ are not independent evidence |
| Trading window | Signals and entries 09:15–14:30 CT; flat by 15:07 CT | Skips the open (that was SC-FUT-0001's territory) and the 7:30 and 9:00 CT data releases; leaves time to exit before Topstep's 3:10 cutoff |
| Shock | The 15-minute move (close now vs close 15 minutes ago) is at least **4×** the typical 15-minute move for that time of day, measured over the previous 60 sessions only | A "4-sigma" move: rare, and scaled to normal volatility so calm and wild years are treated alike |
| News exclusion | No trades on FOMC statement days after 12:45 CT | The one major scheduled release inside the window. Fading real news is "standing in front of a train" |
| Confirmation | Within 10 minutes of the shock, the first 1-minute bar that closes against the shock (an up bar after a down-shock, and vice versa); no confirmation means no trade | Don't catch a falling knife: wait for the selling (or buying) to pause |
| Entry | Next bar's open, opposite the shock; at most one trade per day | |
| Stop | 1 tick beyond the most extreme price since the shock began | If it makes a new extreme, the snap-back idea is wrong |
| Exit | 60 minutes after entry, or the stop, or 15:07 CT, whichever comes first; no profit target | The research found reversals over roughly an hour |
| Size for the prop test | **2 micros**, frozen | 1 micro can't reach $3,000 in time (simulator lesson); 2 keeps a typical stop well inside the $2,000 limit |
| Costs | L3 primary; the prop simulation is also reported at L4 | Shock minutes have wider spreads and slippage |

## How it is judged
1. **First, before any P&L:** report how many trades the rule produces in 2019–2024. If it is fewer than about 40, the test is too thin to judge and stops there (it isn't tuned up to get more).
2. **Prop simulator gate (main):** chance of passing a Topstep 50K account before blowing it up, at 2 micros, vs the luck version at its best size, over a 6-month fee budget. It needs a 90% range above zero.
3. **Workbench statistics (supporting):** vs a **matched random direction** (same days, same entry minute, same stop distance mirrored, same exit), at the honesty-adjusted bar. Also reported: by year, calm/volatile, and cost ladder.
4. Phase 2 (payouts and net cash) applies once built. The 2025–26 exam stays locked.

## Engineering needed
- A plug-in for this rule.
- A time-of-day volatility table built only from past sessions.
- A historical FOMC date list from the official Fed page; the repo already has a fetcher.
- A matched control that mirrors the stop.
- Hand-worked fixtures written first, as with SC-FUT-0001.
