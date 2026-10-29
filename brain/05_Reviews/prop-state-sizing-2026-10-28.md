# PROP-STATE-SIZING-v1 results (2026-10-28)

Spec frozen and committed before any result: `brain/_system/prop/state-sizing.v1.json` (0fa6ba8, sha256 b7b10ca0...). SC-FUT-0005 trial 266777ef, L3, 42 days, 2,000 paths, 40 outer. Train years 2019/2021/2023, test 2020/2022/2024. Output: `brain/04_Backtest_Reports/workbench/prop/state_sizing/266777ef7609_20261028T230551Z.json`.

## Q1: size from the cushion (SC-FUT-0005): FAILED
Best train pick per firm, judged on test years:

| Firm / path | Pick (a_eval, a_funded) | Net per 42 days | 90% range | Payout | Gate |
|---|---|---|---|---|---|
| Topstep 50K standard | (2.0, 1.5) | -$54 | [-183, +110] | 17% | fail |
| Topstep 50K consistency | (0.5, 1.5) | -$161 | [-200, -140] | 1% | fail |
| Tradeify Growth 50K | (0.5, 0.5) | -$152 | [-163, -137] | 0% | fail |

Cutting size as the cushion shrinks slows the evaluation down; the fixed sprint does better. The Topstep standard pick sat at the edge of the grid (a_eval 2.0), so larger is not ruled out.

## Q2: JJ Simon's zero-edge claim: NOT SUPPORTED
The best policy chosen for the random-direction control on its own still loses on test: Topstep -$162 [-187, -124], consistency -$183, Tradeify -$186. In this simulator and with these fees, a no-edge strategy does not make money however it is sized (within this family).

## Baseline P4 (12 / 4) on the test years
Topstep standard +$189 [-5, +509], 41% payout; consistency +$217 [-5, +507]; Tradeify Growth +$304 [+7, +578] (gate pass). **Not a pass to believe:** P4 was chosen after seeing all years, the test years are the strategy's strongest (2020/22/24), and on all years the same cell was +$134 [-36, +484] (fail). Tradeify also needs the L4 cost check and a NinjaTrader route.

## Q3: $500 live account, 1 MNQ (all practice days, broker flattens at $50 equity)
- Goal +$50 then stop (42 days): 84% reach it (median 3 days), 15% liquidated (-$451). Mean end $582: winners usually overshoot (trend days).
- Keep trading a year: 42% liquidated; median end $2,249, mean $2,299, 95th pct $6,116.
- In-sample (same years the edge was found on), latency-sensitive, and a broker's real day margin may liquidate sooner.

## Five Topstep accounts, same bot, P4 (descriptive, not a gate)
| Start | 0 paid | >= 1 paid | >= 2 paid | Mean net (5 accts) | Net < 0 |
|---|---|---|---|---|---|
| Same day (copy trading) | 60% | 40% | 40% | +$391 | 66% |
| One week apart | 32% | 68% | 54% | +$436 | 61% |
| Independent (ideal) | 8% | 92% | 66% | +$444 | 50% |

Fees include re-buying a failed Combine inside the 42 days and the API fee per account (one subscription in reality, so slightly pessimistic); the 5% worst case is about -$2,600 if every failure is re-bought.

Ledger: 9 test cells (kind state_sizing) in prop_trials.jsonl.

## Follow-up: payback of a $500 budget (descriptive, P4 12/4, Topstep 50K standard path, in-sample)
- Hard $500 budget (one account at a time, $49/mo + $49 resets + $149 activation + $29/mo API): trader payouts >= $500 within 42 trading days 31%, within 84 days 45% (then flat: money runs out). Any payout 58%. Mean payouts $1,150 by day 84 but median $316 (skewed). Spend median $403 (max ~$619 from monthly fees).
- One account already funded (4 MNQ): any payout ever 58%; median 20 trading days to the first; >= $500 within 42 days 42%.
- Four funded accounts, same bot: >= $500 within 42 days 58% (same start) / 75% (a week apart); mean ~$3,200.
