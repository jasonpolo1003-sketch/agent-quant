# Big bets: short-dated options and news days, 2026-10-28

Script: `scripts/weekly_options_test.py`.
- Data: FRED NASDAQ100 and VXNCLS, 2005-2024. No 2025+ data was used.
- Pricing: Black-Scholes with flat VXN volatility. This ignores skew, so it is too pessimistic on OTM calls and too kind to puts.
- Costs: 10% round-trip spread.

Weekly options, staking 30% of the account per bet:

| Option | Avg return per bet, with spread | No spread | Paid 5x or more |
|---|---|---|---|
| ATM call | −12% | −3% | |
| 1% OTM call | −23% | | 1.5-1.9% of weeks |
| 2% OTM call | −37% | | 2.8-3.6% of weeks |
| 3% OTM call | −51% | | 2.9-3.3% of weeks |
| Puts (all strikes) | −28% to −42% | | |

- At a 30% stake, every variant loses 75%+ of the account within a year in 86-100% of runs.

The math, without any data:
- A bet that pays 5x and otherwise goes to zero, priced fairly, wins about 20% of the time.
- Kelly sizing only allows a 30% stake when the win rate is 44% or higher.
- Simulated, 52 bets at a 30% stake:

| Win rate | Median end | P(lose 75%+) |
|---|---|---|
| 20% (fair) | about $0 | 92% |
| 30% (big edge) | ×0.80 | 38% |

- The same 30% edge at a 5% stake: ×2.9.
- Big stakes destroy even real edges, through volatility drag.

News days:
- CPI and FOMC days, 2019-2024: average absolute NDX move 1.20%, against 1.25% implied by flat VXN. They did not move more than options already price.
- Real options also carry an event premium on top.
- 1-day calls before news days returned about +1% and puts −33%. That is the 2019-2024 uptrend, picked with hindsight, not a signal.

Conclusion:
- There is no edge in big directional option or news bets.
- At a 30% stake, the account dies even if a modest edge existed.
- What would be needed: a direction signal winning about 30%+ on a 5x payoff, staked at 5% or less.
