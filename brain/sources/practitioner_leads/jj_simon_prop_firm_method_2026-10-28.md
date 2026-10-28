# JJ Simon (youtube.com/@itsjjsimon): prop-firm method (read 2026-10-28)

Source: 14 video transcripts (auto-captions). Grade: PRACTITIONER, self-reported, unaudited. Every video ends in a paid-mentorship pitch; his exact sizing tables are withheld on purpose.

## Claims (his numbers)
- ~$1.9M payouts after split vs ~$550K eval fees over ~19 months (Feb 2025 – Sep 2026), started with $5K. ~2,200 evals (avg ~$250, mostly 150K), ~20 firms, ~10 active.
- Rough rates: ~30% eval pass; ~40% of funded reach a ~$4K payout; ~1 payout per funded on average. Lucid Flex 25K: 37% pass, 35% payout, 4.2x ROI.
- Market edge is near zero: ~41% win at 1.5R gross, ~40% after costs (break-even). He says the money comes from the rules, not the entries.

## Method
1. **Two different objectives.** Eval: maximise P(hit target before max loss) (+ consistency). Funded: maximise expected cash withdrawn (P(payout) x size, over several payouts). Never trade them the same way.
2. **State-dependent stop/target/size.** For each account state (firm, plan, eval/funded, balance vs floor, distance to payout, after payout, live) solve V(state) = p·V(win state) + (1-p)·V(loss state) over many stop/target choices; pick the max. Re-solve when the state changes. ~1,800 states; brute-force simulation.
3. **Think of the account as an option.** Downside is the fee; risk in the account is "fee-denominated" (risking $4.5K of a $4.5K drawdown on a $250 eval = risking $250).
4. **Large risk per account, fast resolution.** Prefer more risk on one account to tiny risk copied across many; small risk takes forever to pass.
5. **Independent accounts, no copy trading.** Same EV, far lower variance; copied wins also get you moved live together (bad for EV).
6. **Firm selection by numbers.** Cost per funded = fee / pass rate; value per funded = average payouts per funded account (backtest 50 evals + 50 funded first). Choose the firm where value > cost.
7. **Bankroll.** Do not start under ~$1,000 (~20 cheap evals); keep risk of ruin < 0.5%; $3K → 50K accounts, $15K → 150K. Request payouts as soon as eligible.
8. **Entries (the "bias").** Mean reversion toward a "fair price": RTH open, pre-news price (8:30 ET), 6 PM Globex reopen, 8 PM Asia open (gap fill); VWAP as proxy. Break-of-structure and displacement-candle entries, ~10 trades/day, don't enter far beyond fair value. Discretionary about news (Forex Factory) and fair-price shifts.

## Relevance to SC-FUT-0005 / Topstep
- His trades are manual and he uses firms that ban bots (Apex, TPT, Alpha); not directly automatable.
- Testable with our simulator, $0: (a) his core claim that a zero-edge strategy with state-optimised brackets is +EV per eval (our 88-cell grid had luck negative everywhere, but with fixed P1-P4 sizes, not optimised brackets); (b) SC-FUT-0005 with a state-dependent size/stop policy instead of fixed phase sizes; (c) a mechanical "revert to open/VWAP" card. Any luck-positive result must first be treated as a possible simulator/rules error.

Videos: 0Ua-ffltO0I, 2BtwoTCxcbc, DEkzU8gqX-o, nvOaN6mRu-o, sWJa8vRfPb8, 4Zj4xKiQHQk, dJdBnSBJlgQ, GMDUiamqgig, 74CRg-mID5c, BLvsYJ4sqn8, KhooqEQK9bA, PMGhHCjYG5c, XhsbfEdJBAc, 8lbkj0PF1uM.
