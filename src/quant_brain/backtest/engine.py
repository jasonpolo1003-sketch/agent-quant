"""Bar-by-bar execution of a frozen card's rules, exactly as SC-0002 pins them.

Close-based signals fill at the next day's open (adj_open). While flat only
the entry is evaluated; while in a position only the exit (and B's add, from
the close of unit 1's fill day). Signals on the period's last bar are dropped;
a position still open there is closed at that bar's close. Costs multiply on
every fill, equity compounds, cash earns 0%, and flat days return 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from quant_brain.backtest import indicators as ind


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    rsi_period: int
    rsi_method: str
    filter_sma: int | None
    entry_below: float
    exit_kind: str  # "close_above_sma" | "rsi_above"
    exit_value: float
    add_below: float | None
    max_units: int
    unit_fraction: float

    @classmethod
    def from_card_rule(cls, rule: Any) -> RuleSpec:
        exit_params = rule.exit.params
        if "sma_days" in exit_params:
            exit_kind, exit_value = "close_above_sma", exit_params["sma_days"]
        elif "rsi_above" in exit_params:
            exit_kind, exit_value = "rsi_above", exit_params["rsi_above"]
        elif "hold_while_rsi_at_or_below" in exit_params:
            exit_kind, exit_value = "rsi_above", exit_params["hold_while_rsi_at_or_below"]
        else:
            raise ValueError(f"rule {rule.rule_id}: exit params not understood: {exit_params}")
        max_units = int(rule.add.params["max_units"]) if rule.add is not None else 1
        return cls(
            rule_id=rule.rule_id,
            rsi_period=rule.rsi.period,
            rsi_method=rule.rsi.method,
            filter_sma=rule.filter.params["sma_days"] if rule.filter is not None else None,
            entry_below=rule.entry.params["rsi_below"],
            exit_kind=exit_kind,
            exit_value=exit_value,
            add_below=rule.add.params["rsi_below"] if rule.add is not None else None,
            max_units=max_units,
            unit_fraction=1.0 / max_units,
        )


@dataclass
class Trade:
    signal_index: int
    entry_index: int
    exit_index: int = -1
    holding_days: int = 0
    trade_return: float = 0.0
    forced: bool = False
    unit_indices: list[int] = field(default_factory=list)


@dataclass
class Result:
    trades: list[Trade]
    equity: pd.Series
    daily_returns: pd.Series


def indicator(closes: pd.Series, spec: RuleSpec) -> pd.Series:
    fn = ind.rsi_wilder if spec.rsi_method == "wilder" else ind.rsi_cutler
    return fn(closes, spec.rsi_period)


def build_signals(closes: pd.Series, spec: RuleSpec) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Entry, exit and add conditions at each close (strict comparisons, no NaN)."""
    rsi = indicator(closes, spec)
    entry = rsi.notna() & (rsi < spec.entry_below)
    if spec.filter_sma is not None:
        trend = ind.sma(closes, spec.filter_sma)
        entry &= trend.notna() & (closes > trend)
    if spec.exit_kind == "close_above_sma":
        exit_sma = ind.sma(closes, int(spec.exit_value))
        exit_ = exit_sma.notna() & (closes > exit_sma)
    else:
        exit_ = rsi.notna() & (rsi > spec.exit_value)
    add = rsi.notna() & (rsi < spec.add_below) if spec.add_below is not None else rsi.isna() & False
    return entry.to_numpy(bool), exit_.to_numpy(bool), add.to_numpy(bool)


def simulate_positions(
    opens: np.ndarray, closes: np.ndarray, entry: np.ndarray, exit_: np.ndarray, add: np.ndarray,
    *, unit_fraction: float, max_units: int, cost: float, p0: int, p1: int,
) -> Result:
    cash = 1.0
    shares: list[float] = []
    notional_total = 0.0
    base = 0.0
    trade: Trade | None = None
    pending: tuple[str, int] | None = None
    trades: list[Trade] = []
    equity: list[float] = []

    for t in range(p0, p1 + 1):
        if pending is not None:  # fill at this open
            kind, signal = pending
            pending = None
            price = opens[t]
            if kind in ("entry", "add"):
                if kind == "entry":
                    base = cash
                    trade = Trade(signal_index=signal, entry_index=t)
                notional = unit_fraction * base
                shares.append(notional * (1 - cost) / price)
                cash -= notional
                notional_total += notional
                trade.unit_indices.append(t)
            else:
                proceeds = sum(shares) * price * (1 - cost)
                cash += proceeds
                trade.exit_index, trade.holding_days = t, t - trade.entry_index
                trade.trade_return = (proceeds - notional_total) / base
                trades.append(trade)
                trade, shares, notional_total = None, [], 0.0
        if t == p1:
            if trade is not None:  # forced close at the period's last close
                proceeds = sum(shares) * closes[t] * (1 - cost)
                cash += proceeds
                trade.exit_index, trade.holding_days = t, t - trade.entry_index
                trade.trade_return = (proceeds - notional_total) / base
                trade.forced = True
                trades.append(trade)
                trade, shares = None, []
            equity.append(cash)
            break
        equity.append(cash + sum(shares) * closes[t])
        if trade is None:
            if entry[t]:
                pending = ("entry", t)
        elif exit_[t]:
            pending = ("exit", t)
        elif len(shares) < max_units and t >= trade.entry_index and add[t]:
            pending = ("add", t)

    series = pd.Series(equity, index=range(p0, p1 + 1), dtype="float64")
    returns = series / pd.concat([pd.Series([1.0]), series.iloc[:-1]]).to_numpy() - 1
    return Result(trades, series, returns)


def buy_and_hold(opens: np.ndarray, closes: np.ndarray, *, cost: float, p0: int, p1: int) -> Result:
    shares = (1 - cost) / opens[p0]
    equity = [shares * closes[t] for t in range(p0, p1)] + [shares * closes[p1] * (1 - cost)]
    series = pd.Series(equity, index=range(p0, p1 + 1), dtype="float64")
    returns = series / pd.concat([pd.Series([1.0]), series.iloc[:-1]]).to_numpy() - 1
    trade = Trade(signal_index=p0 - 1, entry_index=p0, exit_index=p1, holding_days=p1 - p0,
                  trade_return=float(equity[-1] - 1), forced=True, unit_indices=[p0])
    return Result([trade], series, returns)


def period_bounds(dates: pd.Series, start: str, end: str) -> tuple[int, int]:
    inside = np.flatnonzero((dates >= start).to_numpy() & (dates <= end).to_numpy())
    if len(inside) == 0:
        raise ValueError(f"no bars between {start} and {end}")
    return int(inside[0]), int(inside[-1])


def simulate(frame: pd.DataFrame, spec: RuleSpec, *, cost_bps: float, start: str, end: str) -> Result:
    closes = frame["adj_close"].reset_index(drop=True)
    entry, exit_, add = build_signals(closes, spec)
    p0, p1 = period_bounds(frame["date"].reset_index(drop=True), start, end)
    return simulate_positions(
        frame["adj_open"].to_numpy(float), closes.to_numpy(float), entry, exit_, add,
        unit_fraction=spec.unit_fraction, max_units=spec.max_units, cost=cost_bps / 10_000,
        p0=p0, p1=p1,
    )
