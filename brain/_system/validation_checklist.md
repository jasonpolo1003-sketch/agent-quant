# Validation Checklist

Use this before accepting any strategy result.

## Data

- [ ] Data source is recorded.
- [ ] Date range is recorded.
- [ ] Symbols/universe are recorded before the test.
- [ ] Adjusted vs raw prices are explained.
- [ ] Missing data was checked.

## Bias Checks

- [ ] No lookahead bias.
- [ ] Close-based signals enter no earlier than next bar.
- [ ] No survivorship bias, or limitation is clearly stated.
- [ ] No repeated tuning on the final test period.
- [ ] Parameter choices are explained.

## Costs / Reality

- [ ] Commission assumption included.
- [ ] Spread/slippage assumption included.
- [ ] Turnover is reported.
- [ ] Liquidity/capacity is considered.

## Metrics

- [ ] Total return.
- [ ] CAGR.
- [ ] Sharpe.
- [ ] Sortino.
- [ ] Max drawdown.
- [ ] Win rate.
- [ ] Number of trades.
- [ ] Benchmark comparison.

## Reject If

- [ ] Works only before costs.
- [ ] Works only on one symbol with no reason.
- [ ] Collapses under small parameter changes.
- [ ] Has too few trades to mean anything.
- [ ] Has unacceptable drawdown.
- [ ] Requires data unavailable at trade time.
