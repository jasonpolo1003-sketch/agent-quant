# Bold play (zero-edge, max-risk brackets) on Topstep 50K: 2026-10-28

Question (Jason): skip the edge, use the firm's convexity. Make one huge trade, then small trades to meet the payout rules.

Model (`scripts/bold_play_model.py`; cross-checked against `firm_sim`, which matched):
- Each trade is a coin-flip bracket on a driftless price, P(win) = stop / (target + stop).
- Costs: $10 per trade, plus $10 slippage on a stop-out.
- Eval: risk the whole cushion. Step 1 makes +$1,650 (the 55% consistency limit), then the rest.
- Funded (standard path): one bold trade to +G, then $150 grind days until 5 winning days.

Results:
- Eval pass rate is 32.3% per attempt. A 60% one-shot pass is impossible with no edge; the hard limit is cushion / (cushion + target).
- Average funded cash per account:

| G | P(payout) | Avg funded cash |
|---|---|---|
| $1,000 | 64% | $550 |
| $2,000 | 50% | $831 |
| $4,000 | 33% | $1,022 |

- 3 months with a fee budget:

| Budget | G | Mean net | Median net | P(net > 0) |
|---|---|---|---|---|
| $500 | $2,000 | +$491 | −$97 | 49% |
| $1,000 | $4,000 | +$1,652 | +$805 | 65% |

- This contradicts the earlier "luck policy" result (−$160 to −$186). That test used small sizing, which has almost no option value.

Caveats, any of which can kill it:
- **Rules.** Topstep's Prohibited Trading Strategies page (10305426, read 2026-10-28) bans "Account Stacking". The wording: "Repeatedly trading aggressively, hitting the Maximum Loss Limit (MLL) in one account, then switching to another". Also banned: "excessive purchases of Trading Combines or Resets", and a catch-all against conduct that "games the market ... is not a viable strategy". Penalties include denial of payouts and permanent closure. The repeated-blowup version of bold play is exactly what this describes.
- **Market model.** The model uses coin-flip fills only. Real NQ has gaps, stop slippage and unresolved brackets. It is not yet replayed on real bars.
- **XFA scaling plan.** The account starts at 2 NQ, so a $2,000 stop is about 50 points. That is feasible.

Status: an idea, not a strategy. Next step if pursued: replay random-direction bold brackets on real 2019-2024 NQ minutes, and pick a firm whose written rules allow it.

## Real-bar replay (scripts/bold_play_real.py), same day

Setup:
- Random-direction brackets on 1,425 practice MNQ days (2019-05..2024-12), priced as NQ.
- Real fills: stop first in a shared bar; gaps fill at the bar open; +1 tick slippage.
- Limited to at most 3 evaluation purchases per month.
- `deny` is the chance a payout is refused and the account closed.

Findings:
- **The coin-flip model holds.** Step-1 win rate is 54.2% real vs 54.7% modelled. The eval passes 31-32% of the time.
- **The paper edge exists only at near-full-cushion risk.** Three months, 3 buys a month:

| Risk per day | Budget | Mean net (deny 0 / 0.25) | P(ahead) |
|---|---|---|---|
| Whole cushion, G $4,000 | $1,000 | +$1,028 / +$403 | 57% / 46% |
| Whole cushion, G $2,000 | $500 | +$297 / +$23 | 45% / 34% |
| $1,000 a day | $1,000 | +$152..231 / −$111..−119 | — |
| $700 a day | any | negative | — |
| $500 a day | any | about −$270 | 14% |

Conclusion:
- The payoff comes from the all-in pattern itself. That is the pattern Topstep calls account stacking and FundedNext calls gambling.
- An aggressive but ordinary risk level gets none of it, and a modest denial risk erases even the all-in version.
- Not pursued as a strategy.
