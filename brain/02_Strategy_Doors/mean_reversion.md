# Mean Reversion Door

## What this method is

Mean reversion strategies look for prices that moved unusually far from a normal level and bet that they will partially return.

## Common variations

- RSI oversold/overbought
- Bollinger Band reversion
- Z-score reversion
- Gap fade
- Short-term reversal

## Required data

- Historical OHLCV prices
- Adjusted close if using split/dividend adjusted research
- Transaction cost assumptions

## Known failure modes

- Strong trends can keep moving against the trade.
- Works before costs but fails after spread/slippage.
- Overfitted thresholds.
- Signal uses closing price but assumes same-close execution.

## Strategy cards

None yet.

## Key sources

None yet.

## Open questions

- Which RSI window is robust across ETFs?
- Does it survive next-day execution?
- Does it beat buy-and-hold after costs?
