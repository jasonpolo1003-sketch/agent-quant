# Plan: pass a prop evaluation within 2 months by choosing the firm and playing the account (2026-10-28)

Status: **approved by Jason 2026-10-28** ("create a plan and orchestrate it with sub-agents ... execute"). Context: plans A/B failed (`SC-FUT-0007`, `SC-FUT-0008` reviews). SC-FUT-0005 (MNQ noise-area) is a real but small edge (~$11.49/day/contract). The lever left is the account itself: which firm's rules and fees, and how size is played in each phase.

## Goal
For each firm that allows a fully automated self-written bot, answer: with SC-FUT-0005's real practice-day results, which frozen account-play policy gives the best net cash over 42 trading days, and does it beat luck playing the same policy?

## Hard limits (all agents)
- No money spent, no purchases, no accounts opened, no live or paper orders sent, no credentials used. Read-only web research only.
- Practice data 2019-05..2024-12 only. The 2025-26 exam data stays unread.
- Policies are frozen and hash-pinned before any cash result. Every cell is a ledger trial. Failures are recorded, not rewritten.
- No git push; the orchestrator commits.

## Workstreams
**R. Research agent: official rules per firm.** Topstep (50K/100K/150K, plans, TopstepX API fee), Tradeify, Lucid Trading, FundedNext Futures (+ a quick check of MyFundedFutures). For each: full-automation policy (eval + funded), Python order route (own API vs Tradovate/Rithmic), and every rule the simulator needs (drawdown type and size, lock, DLL, consistency, minimum days, fees incl. resets/activation/platform/API, payout rules). Official pages only for numbers; conflicts flagged. Output: `brain/sources/prop_firms/<firm>.md` + `brain/_system/prop/firms/<firm>_<plan>.json` drafts.

**E1. Engineering agent: multi-firm simulator.** Generalise `prop/account.py` + `prop/funded.py` to a rules schema covering the research fields (EOD vs intraday trailing, lock points, soft DLL vs hard daily loss, consistency in eval/funded, payout eligibility/caps/splits/buffers, one-time vs monthly fees, platform/API fees). Topstep must reproduce today's numbers exactly. Add phase-aware sizing (Combine size vs funded size, daily profit stop, stop-after-target). Hand-worked fixtures first. Output: code + tests, a `scripts/firm_grid.py` runner reading a pinned policy menu.

**E2. Engineering agent: paper-trading bot (dry run).** A live runner for SC-FUT-0005: the same rule as `workbench/noise.py`, driven bar by bar; a TopstepX/ProjectX API client written from the public docs but run only against a fake broker. Proof: replaying practice days through the runner reproduces the workbench trades exactly. Includes the orders-within-5-seconds check, the daily risk switch, and a kill switch. No network order calls.

**Q. Quality agent: independent review**, after E1/E2/R land: rules files vs the official sources; simulator fixtures and an independent recomputation of one firm cell; the bot's replay equivalence; adversarial read of the final grid (anything flattering, any look-ahead).

**O. Orchestrator (main session):** freeze the account-play policy menu before results; run the grid; write the review; update the vault.

## Account-play policy menu (frozen before results, written by the orchestrator)
A small menu, applied identically to luck: Combine-phase size (steady vs pass-fast), funded-phase size (safe), daily profit stop below each firm's consistency line, and stop-for-the-day after the daily loss limit. Exact numbers live in the pinned menu file.

## Gate (per firm × plan × policy cell)
Mean net cash over 42 days > $0 with its lower 90% bound > $0, AND beats luck under the same policy (lower 90% bound of the difference > $0). Report payout chance and worst 5% outcome. If luck alone is positive somewhere, flag it as a likely simulator or rules-reading error before believing it.

## Done when
Grid run and reviewed, quality findings fixed or recorded, results and the bot status reported to Jason, vault updated.
