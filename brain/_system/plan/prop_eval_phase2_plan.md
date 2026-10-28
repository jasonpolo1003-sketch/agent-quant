# Plan: prop simulator Phase 2 — funded account, payouts, and account-aware risk (2026-10-28, draft)

Parent: `prop_eval_simulator_plan.md` (Phase 1 built). Status: **approved by Jason 2026-10-28** with the defaults below: 42-day primary horizon; model both plan types; assume the $1,000 DLL set at purchase (no-DLL as a variant); model both payout paths.

## Why this phase changes shape
Jason, 2026-10-28:
- six months is out of the picture, so the horizon is **1–2 months**;
- he is not sold on a fixed 2 or 3 MNQ;
- he thinks better use of the risk tools will beat picking a size.

So Phase 2 does two things:
- it answers "how much cash does this actually make in 2 months?";
- it lets the size become a **pre-registered rule that reacts to the account** (distance to the loss limit, daily loss limit, best-day cap) instead of a fixed number.

## Topstep rules re-checked 2026-10-28 (help.topstep.com)
| Rule | Value | Source (article date) |
|---|---|---|
| Combine MLL | $2,000, trails end-of-day balance, intraday incl. open P&L, **locks at the $50,000 start once reached** | MLL article (2026-09-18) |
| Combine consistency | best day ≤ 55% of profit (best day < $1,650 at the $3,000 target) | Consistency (2026-09-17) |
| Combine fees | $49/month, $49 reset (Standard); $95/$95 (No Activation Fee) | Pricing |
| Daily loss limit (optional) | $1,000 for 50K. Flattens and stops for the day; **not a violation**. Fixed if set at purchase, then carried into the XFA | DLL article (2026-06-30) |
| XFA start | balance $0, MLL −$2,000 trailing; locks at $0 once balance reaches +$2,000; **set to $0 after the first payout** | MLL article; Payout Policy |
| Payout path A, Standard | 5 winning days of ≥ $150 net; max 50% of balance, cap **$2,000** (**$4,000** if DLL set at Combine purchase); positive profit since the last payout | Payout Policy |
| Payout path B, Consistency | 3 trading days; largest day ≤ 40% of net profit; max 50% of balance, cap **$3,000** (**$6,000** with DLL at purchase) | Payout Policy; Consistency |
| Payout basics | minimum $125; 90/10 split; path chosen at activation and fixed | Payout Policy |
| XFA fees | $149 activation (Standard plan) or $0 (No Activation Fee plan); no monthly fee; Back2Funded $599 | Activation (2026-09-24); Pricing |
| XFA limits | up to 5 XFAs; inactivity > 30 days may close; automated trading allowed with conditions | XFA Parameters (2026-08-05) |
| Live (LFA) | no automation in Live; promotion closes all XFAs | LFA Parameters |
| **Unconfirmed** | XFA scaling-plan tiers (published only as a chart image; text says the 50K starts at a 2-lot = 20 micros) | Scaling Plan (2026-07-16) |

Consequences:
- **Fix:** Phase 1's no-lock variant was the conservative guess. The help centre now says the Combine locks too, so `topstep_50k.json` (lock) is the primary file again. The no-lock file stays as a stress test, and its 2026-10-27 pass rates were slightly pessimistic.
- **The DLL is a free risk tool.** It turns a disaster day into a capped −$1,000 day and doubles the payout caps if chosen at purchase. It must be decided when the Combine is bought.
- **The XFA is the hard part:**
  - after the first payout the floor is $0;
  - so the first payout can never take the whole cushion: a payout leaves the balance at ≥ 50%, and the MLL then sits at $0.

## Build
| # | Piece | Key requirement |
|---|---|---|
| Q1 | Rules files | `topstep_50k.json` re-dated (lock confirmed); new `topstep_50k_xfa.json` with every row above sourced and dated. Unconfirmed scaling tiers block sizes > 20 micros (not binding for this project). |
| Q2 | DLL on day paths | Exact with existing data: day low ≤ −DLL ⇒ day close = −DLL − stop slippage (the day low is the first point the DLL could trigger, and trading stops there). Applies to strategy and luck draws alike. |
| Q3 | XFA state machine | Pure function like `account.attempt`: winning-day counter, 40% check, payout = min(50% balance, cap) when eligible (request on the first eligible day, ≥ $125), MLL to $0 after the first payout, breach closes the account (Back2Funded off by default, a stress switch). |
| Q4 | Lifecycle | Combine → activation → XFA → payouts until breach or horizon. **Net cash = 0.9 × payouts − subscriptions − resets − activation.** Horizons 21 / **42** / 63 trading days (42 primary). Report chance net cash > $0, median days to first payout, worst cash at risk. |
| Q5 | Intraday equity path | Store each day's minute-by-minute equity (per contract, gross) for the strategy and every control draw, so in-day rules (stop for the day after +$X, cap the best day under the 55%/40% consistency lines) are exact, not guessed from close and low. Cache-format bump; the workbench re-runs once. |
| Q6 | Sizing policies (the risk answer to "2 or 3") | Size becomes a function of account state, decided before each day using only what is known that morning. A small fixed menu, frozen before any result: (a) fixed N; (b) **cushion-based**: contracts = floor(k × distance-to-MLL ÷ stress day loss per contract), capped; (c) cushion-based + DLL; (d) (c) + best-day profit stop for consistency. Each has a single pre-set k; there is no tuning sweep. |
| Q7 | Luck baseline and gate | Same pipeline, same resampled days, random-direction draws, **each policy also applied to luck** (risk tricks must beat luck using the same tricks). Gate: paired net-cash difference vs luck, lower 90% bound > $0 at the 42-day horizon, plus median first payout ≤ 42 days. |
| Q8 | Honesty | Every policy × horizon run is a ledger trial. The policy menu (≤ 4) and k values are written into the card before results. The family's trial count rises accordingly. |
| Q9 | Verification | Hand-worked fixtures for each payout path, the $0 lock, a DLL day, a breach after a payout, a consistency-blocked payout, censoring. Plus an independent day-by-day replay matching on random paths, and SC-FUT-0001/0002 replayed as known no-edge cases (should show negative net cash ≈ fees). |
| Q10 | UI | Prop panel adds net cash vs luck, a payout timeline and a policy comparison. |

Order: Q1–Q4 + Q9 first (≈ 2 sessions; answers "cash in 2 months" for the existing day data), then Q5–Q8 (≈ 2 sessions), then Q10.

## How this settles 2 vs 3
Don't pick the size by eye. Freeze the policy menu (Q6) now, run it on 2019–24 practice data through the full lifecycle, and choose the policy by a rule written down beforehand (the highest lower-bound net cash vs luck). Then spend **one** exam check (2025–26) on that single policy. A fixed 2 or 3 MNQ is just policy (a), so it is still in the race.

## Decisions for Jason (before results)
1. Horizon: 42 trading days (2 months) primary, OK?
2. Plan type to model: Standard ($49/month + $149 activation) vs No Activation Fee ($95/month, $0). Model both?
3. Assume the $1,000 DLL is set at purchase (it caps losses and doubles payout caps)?
4. Payout path: model both; choose the better one before the exam check.

## Known limits
- No automation in Live, so the bot's run ends at promotion.
- 5 XFAs on the same strategy are one bet ×5, not diversification.
- Rule changes over time.
- Scaling tiers unconfirmed.
- Payout request timing simplified to the first eligible day.
