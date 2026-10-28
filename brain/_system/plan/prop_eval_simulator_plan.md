# Plan: prop-evaluation simulator (revised 2026-10-27 after two independent reviews)

Reviews: `brain/05_Reviews/prop-eval-simulator-plan-reviews.md`.

## Goal
Answer Jason's real question: **if this exact code traded a Topstep 50K account, would it make more money than it costs, more reliably than a no-edge version of itself?** This becomes the main gate for prop-goal strategies.

## Main output and success definition (for Jason to confirm)
- **Primary:** net cash per attempt over a fixed horizon = 90% of payouts − subscriptions − resets − activation. Also report the chance net cash > $0 and the most cash at risk.
- **Luck comparison:** the identical simulation of the strategy's random-direction version on the same resampled histories, **at the random version's own best size**.
- **Pass:** paired net-cash difference vs random has a lower 90% bound above $0, at a size frozen before results, **and** median time to first payout ≤ Jason's fee horizon. Every rate is reported with a range and the number of independent trades.

## Phases
- **Phase 1, the evaluation (Combine) only:**
  - pass/fail/censored rates;
  - days to pass;
  - fees and resets per pass.

  Payout outputs are marked `not_estimable`. 3-4 sessions.
- **Phase 2, the funded account (XFA) and payouts:**
  - caps of 50% of balance and $2,000/$3,000;
  - the $0 lock after the first payout;
  - both payout paths;
  - the scaling table.

  Built only after these are confirmed on Topstep's pages. Promotion to Live ends the bot run (no API in Live). 2-3 sessions.

## Build (Phase 1)
| # | Piece | Key requirement |
|---|---|---|
| P1 | Rules config `topstep_50k.json` | Sourced and dated. 55% Combine consistency target, no minimum days, 3:10 CT flat, $2k trailing MLL enforced intraday on open P&L and locking at start balance, fees. Unverified fields block official results. |
| P2 | Per-day path data | Computed **inside `run_trade`**: day net, **lowest equity of the day** (realized + current open loss; never the stop-bar low beyond the stop or the flatten-bar low; gap stops at the gap fill) and best open gain, per contract at gross. Stored **for the strategy and every control draw** (flip uses best gain). Non-evaluable or ineligible days are kept, with stress bounds, and count toward the fee calendar. |
| P3 | State machine | Pure functions. Target judged on end-of-day balance and the consistency rule. "Adverse first" = failure wins within a minute (fixture F4). Volatility-scaled stop slippage. Optional bot-failure scenario. |
| P4 | Replays | Historical walk-forward with censored attempts reported. Non-wrapping, regime-aware bootstrap (longer blocks) with one control draw per day on the same indices. Confidence ranges by resampling start blocks. |
| P5 | Fingerprint and ledger | Hash of day data + rules config + simulator code + seed. Every gate run counts as a trial. Size frozen per card. |
| P6 | Verification | F1–F9 plus new fixtures: stop-bar low past stop, flatten-bar low, gap stop, two trades/day, lock moment, censoring, zero-variance baseline. Corrected properties: earlier breach at larger size with target and lock off; gambler's ruin only with a fixed floor. A slow independent minute-by-minute replay must match on random days. SC-FUT-0001/0002 replayed as known no-edge cases. |
| P7 | UI | A "Prop evaluation" panel: net cash vs luck, pass/fail/censored, days to pass, cost per pass. |

## Decisions for Jason (before results)
1. Fee horizon: how many months to fund one attempt (proposal: 6).
2. Sizes to report: 1/2/3/5 micros, one frozen per strategy.
3. Confirm the success definition above.

## Known limits
Within-minute ordering (handled conservatively), gap fills and liquidation beyond the limit, rule changes over time, simulated vs live fills, bot outages.
