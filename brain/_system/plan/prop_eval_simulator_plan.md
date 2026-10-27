# Plan: prop-evaluation simulator (draft 2026-10-27, for review)

## Goal
Answer the question Jason actually cares about: **if this exact code traded a Topstep 50K evaluation, how often would it pass, how fast, at what cost, and would it keep earning payouts afterwards?** This becomes the main gate for prop-goal strategies, ahead of Sharpe and $/day. It is useful before any winner exists: run SC-FUT-0001 and SC-FUT-0002 through it, and a random no-edge strategy, to see what "passing by luck" looks like.

## Why it matters
A $2,000 trailing drawdown that counts open trades can end an account on one bad day, even for a strategy that is profitable on average. A no-edge strategy also passes some of the time: a fair coin walk between +$3,000 and −$2,000 passes about 40% of the time before costs. So "it passed" means nothing unless it passes clearly more often than luck.

## Rules config (versioned, sourced)
`brain/_system/prop/topstep_50k.json`, with source links and the date checked:
- start $50,000; target +$3,000;
- maximum loss limit (MLL) $2,000, trailing from the highest end-of-day balance, enforced intraday on equity including open positions, locking at the starting balance;
- 50 micros maximum;
- flat by 3:10 pm CT;
- $49/month; reset $49; XFA activation $149;
- XFA payout: 5 winning days of at least $150; 90/10 split.

Fields we haven't verified (consistency rules, minimum days, XFA MLL behaviour, scaling plan) are marked `unverified` and must be confirmed from Topstep's help centre before results count. Other firms come later as other config files.

## Engineering build
| # | Piece | Notes |
|---|---|---|
| S1 | **Rules config + loader** | Schema with required fields; unverified fields block "official" results. |
| S2 | **Intraday path per day** | Extend the workbench run to store, per trade in order: net P&L and **worst open loss** (from 1-minute highs/lows while in the trade) and best open gain, plus costs. One-minute bars can't tell which came first inside a minute, so assume **adverse first** (conservative), as in the existing hand-worked simulator fixtures (`brain/_system/futures/simulator-handworked-fixtures.md`, F1–F9). |
| S3 | **Account state machine** | Pure functions: balance, trailing floor, intraday breach check, end-of-day update, target check, fees and resets, then the XFA phase (payout eligibility, payouts, floor behaviour). |
| S4 | **Two ways to replay history** | (a) Historical walk-forward: start an evaluation on every practice day and run forward on the real sequence. (b) Bootstrap: resample whole days in blocks (stationary, mean block 5), 10,000 paths. Report both. |
| S5 | **Luck baseline** | The same simulator on the strategy's matched random benchmark (same days, times, sizes; random direction) gives the pass rate a no-edge version gets. The strategy must clearly beat it. |
| S6 | **Sizing** | Fixed 1, 2, 3, 5 micros (no tuning after results), never max size; all sizes shown, with the chosen size frozen per card. |
| S7 | **Outputs** | Pass probability; fail probability (and from a single day); median days to pass; expected fees/resets per pass; XFA payout probability and expected payouts in N days; worst open loss distribution. The same luck-baseline numbers sit side by side. |
| S8 | **Verification** | F1–F9 fixtures; property tests (bigger size never lowers risk of a breach; zero-edge walk ≈ gambler's-ruin math); an independent reference; replay SC-FUT-0001/0002 as known no-edge cases. |
| S9 | **UI** | Workbench run page gets a "Prop evaluation" panel: pass chance vs luck, days to pass, cost per pass, payout odds. |

## Decisions Jason makes (before results)
1. Firm/account: Topstep 50K Combine to XFA.
2. Sizes to report (proposal 1/2/3/5 micros).
3. Horizon: how many months of fees he's willing to spend per attempt.
4. Success definition: for example, pass rate clearly above the luck baseline AND expected payouts over 6 months exceed expected fees, at a frozen size.

## Known limits
1-minute data can't order events inside a minute (handled conservatively); stop slippage in fast markets; rule changes over time; simulated fills are not live fills; XFA rules may differ from what's verified.

## Estimate
3–4 sessions including verification.
