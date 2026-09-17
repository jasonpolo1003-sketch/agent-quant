Wilder RSI uses a 14-period default with traditional oversold level 30.
A close-based signal may enter no earlier than the next bar.
This recorded Jina Reader fixture is for hermetic tests only.

The relative strength index was introduced by J. Welles Wilder Jr. and compares
the average magnitude of recent gains to the average magnitude of recent losses
over a fixed lookback window. The resulting value is bounded between zero and
one hundred. Wilder's original formulation applies a smoothing method that is
not identical to a simple moving average of gains and losses, so two
implementations using the same nominal lookback can produce different values on
the same price series. Anyone relying on a specific threshold should confirm
which smoothing method their library uses before treating a reading as
comparable to a published figure.

Conventional descriptions treat readings below thirty as oversold and readings
above seventy as overbought. These are conventions inherited from the original
presentation rather than tested decision rules. The documentation does not
establish an exit condition, a maximum holding period, or a cost assumption,
and it does not claim that either threshold produces a positive expectation on
any particular instrument or horizon.

Timing matters as much as the threshold. A signal derived from a closing price
is not observable until that close has occurred, so any execution based on it
must happen no earlier than the following bar. Treating a close-derived signal
as executable at the same close introduces lookahead bias and will overstate
measured performance. This is a data-availability constraint rather than a
modelling preference, and it applies regardless of which smoothing method or
threshold is chosen.
