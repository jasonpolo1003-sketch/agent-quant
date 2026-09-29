"""An independent second implementation of rule A, for cross-checking the engine.

Written separately from ``engine``/``indicators`` (its own RSI and SMA, and a
jump-search over signal days instead of a bar-by-bar state machine), so a bug
in one is unlikely to be repeated in the other. It must reproduce the engine's
trades exactly before a held-out period may be read.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence


def _wilder(closes: Sequence[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= n:
        return out
    ups = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    downs = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    up, down = sum(ups[:n]) / n, sum(downs[:n]) / n
    for i in range(n, len(closes)):
        if i > n:
            up = (up * (n - 1) + ups[i - 1]) / n
            down = (down * (n - 1) + downs[i - 1]) / n
        out[i] = 100.0 if down == 0 else 100.0 - 100.0 / (1.0 + up / down)
    return out


def _sma(closes: Sequence[float], n: int) -> list[float | None]:
    running, out = 0.0, []
    for i, value in enumerate(closes):
        running += value
        if i >= n:
            running -= closes[i - n]
        out.append(running / n if i >= n - 1 else None)
    return out


def rule_a_trades(
    opens: Sequence[float], closes: Sequence[float], *, rsi_period: int, entry_below: float,
    filter_sma: int, exit_sma: int, cost: float, p0: int, p1: int,
) -> list[tuple[int, int, int, float]]:
    """(signal, entry fill, exit fill, return) for each rule A trade in [p0, p1]."""
    rsi, trend, fast = _wilder(closes, rsi_period), _sma(closes, filter_sma), _sma(closes, exit_sma)
    entries = [t for t in range(p0, p1) if rsi[t] is not None and trend[t] is not None
               and closes[t] > trend[t] and rsi[t] < entry_below]
    exits = [t for t in range(p0, p1) if fast[t] is not None and closes[t] > fast[t]]
    keep = 1 - cost
    trades, position = [], p0
    while True:
        i = bisect_left(entries, position)
        if i == len(entries):
            return trades
        signal = entries[i]
        fill = signal + 1
        j = bisect_left(exits, fill)
        if j == len(exits):
            trades.append((signal, fill, p1, keep * closes[p1] / opens[fill] * keep - 1))
            return trades
        out = exits[j] + 1
        trades.append((signal, fill, out, keep * opens[out] / opens[fill] * keep - 1))
        position = out
