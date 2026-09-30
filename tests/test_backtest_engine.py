"""The engine executes SC-0002's pinned rules; expected trades are worked by hand.

The position core takes boolean signal arrays, so each case below states its
signals directly and checks fills, holding times, returns and equity.
"""

import numpy as np
import pandas as pd
import pytest

from quant_brain.backtest import engine as en
from quant_brain.config import PROJECT_ROOT
from quant_brain.strategy import card as sc

OPENS = np.array([100.0, 101.0, 102.0, 104.0, 103.0, 105.0, 106.0, 108.0])
CLOSES = np.array([100.5, 101.5, 103.0, 104.5, 103.5, 105.5, 107.0, 108.5])
N = len(OPENS)


def flags(*on):
    arr = np.zeros(N, dtype=bool)
    arr[list(on)] = True
    return arr


def run(entry=(), exit=(), add=(), *, fraction=1.0, units=1, cost=0.0, p0=0, p1=N - 1):
    return en.simulate_positions(
        OPENS, CLOSES, flags(*entry), flags(*exit), flags(*add),
        unit_fraction=fraction, max_units=units, cost=cost, p0=p0, p1=p1,
    )


def test_a_close_signal_fills_at_the_next_open_and_exits_at_the_next_open():
    result = run(entry=[1], exit=[3])

    [trade] = result.trades
    assert (trade.signal_index, trade.entry_index, trade.exit_index) == (1, 2, 4)
    assert trade.holding_days == 2 and not trade.forced
    assert trade.trade_return == pytest.approx(OPENS[4] / OPENS[2] - 1)


def test_entries_while_in_a_position_are_ignored_and_re_entry_waits_for_the_exit_day_close():
    result = run(entry=[1, 2, 3, 4], exit=[3])

    assert [(t.entry_index, t.exit_index) for t in result.trades] == [(2, 4), (5, 7)]
    # entry at close 4 (the exit-fill day) is the first allowed re-entry; never same-bar


def test_an_exit_can_be_signalled_on_the_fill_day_close():
    [trade] = run(entry=[1], exit=[2]).trades

    assert (trade.entry_index, trade.exit_index, trade.holding_days) == (2, 3, 1)


def test_costs_are_multiplicative_on_every_fill():
    [trade] = run(entry=[1], exit=[3], cost=0.0005).trades

    assert trade.trade_return == pytest.approx(0.9995 * OPENS[4] / OPENS[2] * 0.9995 - 1)


def test_a_last_bar_signal_is_dropped_and_an_open_trade_is_force_closed_at_the_last_close():
    result = run(entry=[2, 5], p1=6)

    [trade] = result.trades
    assert trade.forced and (trade.entry_index, trade.exit_index) == (3, 6)
    assert trade.holding_days == 3
    assert trade.trade_return == pytest.approx(CLOSES[6] / OPENS[3] - 1)
    assert len(result.equity) == 7


def test_a_last_bar_entry_signal_while_flat_is_dropped():
    result = run(entry=[6], p1=6)

    assert result.trades == []
    assert result.equity.iloc[-1] == 1.0


def test_signals_outside_the_period_are_ignored():
    result = run(entry=[1, 4], exit=[5], p0=3)

    [trade] = result.trades
    assert trade.signal_index == 4 and trade.entry_index == 5


def test_b_adds_its_second_unit_only_after_the_first_close_after_unit_one():
    # entry signal 1 -> unit 1 at open 2; add on signal day 1 does not count;
    # add on close 2 -> unit 2 at open 3; exit signal 4 -> exit at open 5
    result = run(entry=[1], add=[1, 2, 3], exit=[4], fraction=0.5, units=2)

    [trade] = result.trades
    assert trade.unit_indices == [2, 3]
    proceeds = (0.5 / OPENS[2] + 0.5 / OPENS[3]) * OPENS[5]
    assert trade.trade_return == pytest.approx(proceeds - 1)


def test_one_unit_b_trade_returns_half_the_price_move():
    [trade] = run(entry=[1], exit=[3], fraction=0.5, units=2).trades

    assert trade.trade_return == pytest.approx(0.5 * (OPENS[4] / OPENS[2] - 1))


def test_equity_compounds_and_flat_days_return_zero():
    result = run(entry=[1, 4], exit=[3, 6])

    first = OPENS[4] / OPENS[2]
    second = OPENS[7] / OPENS[5]
    assert result.equity.iloc[-1] == pytest.approx(first * second)
    returns = result.daily_returns
    assert returns.iloc[0] == 0.0 and returns.iloc[1] == 0.0  # flat
    assert returns.iloc[2] == pytest.approx(CLOSES[2] / OPENS[2] - 1)  # fill day: open -> close
    assert returns.iloc[4] == pytest.approx(OPENS[4] / CLOSES[3] - 1)  # exit day: prior close -> open


def test_buy_and_hold_pays_one_entry_and_one_exit_cost():
    result = en.buy_and_hold(OPENS, CLOSES, cost=0.0005, p0=1, p1=6)

    assert result.equity.iloc[-1] == pytest.approx(0.9995 * CLOSES[6] / OPENS[1] * 0.9995)
    assert result.daily_returns.iloc[0] == pytest.approx(0.9995 * CLOSES[1] / OPENS[1] - 1)


# --- signals from the card ---------------------------------------------------------


def card_rules():
    spec = sc.read_card(PROJECT_ROOT / "brain/03_Strategy_Cards/SC-0002-rsi2-connors-spy.md")
    return {rule.rule_id: rule for rule in sc.StrategyCard.model_validate(spec).rules}


def test_card_rules_map_to_exact_engine_parameters():
    rules = {rid: en.RuleSpec.from_card_rule(rule) for rid, rule in card_rules().items()}

    a, b, d = rules["A"], rules["B"], rules["D"]
    assert (a.rsi_period, a.rsi_method, a.filter_sma, a.entry_below) == (2, "wilder", 200, 10)
    assert (a.exit_kind, a.exit_value, a.max_units, a.unit_fraction) == ("close_above_sma", 5, 1, 1.0)
    assert (b.rsi_period, b.filter_sma, b.entry_below, b.add_below) == (4, 200, 25, 20)
    assert (b.exit_kind, b.exit_value, b.max_units, b.unit_fraction) == ("rsi_above", 55, 2, 0.5)
    assert (d.rsi_method, d.filter_sma, d.entry_below) == ("cutler", None, 10)
    assert (d.exit_kind, d.exit_value) == ("rsi_above", 40)


def test_signals_use_strict_comparisons_and_need_full_indicator_warmup():
    closes = pd.Series([10.0, 9.0, 8.0, 9.5, 11.0, 10.0, 9.0, 8.0])
    spec = en.RuleSpec(rule_id="T", rsi_period=2, rsi_method="cutler", filter_sma=3,
                       entry_below=40, exit_kind="close_above_sma", exit_value=3,
                       add_below=None, max_units=1, unit_fraction=1.0)

    entry, exit_, add = en.build_signals(closes, spec)

    # Cutler RSI(2): idx2 0, idx3 (g .0,1.5 l 1,0) -> RS 1.5/1=... ; filter needs SMA3 from idx2
    sma3 = closes.rolling(3).mean()
    for i in range(len(closes)):
        rsi = en.indicator(closes, spec).iloc[i]
        expected = (not np.isnan(rsi)) and not np.isnan(sma3.iloc[i]) and closes.iloc[i] > sma3.iloc[i] \
            and rsi < 40
        assert entry[i] == expected, i
        assert exit_[i] == (not np.isnan(sma3.iloc[i]) and closes.iloc[i] > sma3.iloc[i]), i
    assert not add.any()
    assert not entry[:2].any()  # no signal before a full lookback


def test_an_exit_takes_priority_over_an_add_on_the_same_close():
    [trade] = run(entry=[1], add=[2], exit=[2], fraction=0.5, units=2).trades

    assert trade.unit_indices == [2] and trade.exit_index == 3
