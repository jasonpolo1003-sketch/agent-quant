"""Plan B2: per-market sessions for the noise-area rule, and the extra markets' volume roll."""

from __future__ import annotations

import dataclasses
from datetime import date, time

import pandas as pd

from quant_brain.futures import multi
from quant_brain.futures.orb import DayInput
from quant_brain.workbench.noise import NoiseArea, _session


def _t(s):
    return time.fromisoformat(s)


def test_sessions_are_the_frozen_hours():
    assert _session("MNQ")[1][0] == 9 * 60 and _session("MNQ")[1][-1] == 14 * 60 + 30
    open_, checks, flat = _session("ZN")
    assert (open_, checks[0], checks[-1], flat) == (_t("07:20"), 470, 13 * 60 + 20, _t("14:00"))
    _, checks, flat = _session("MGC")
    assert (checks[-1], flat) == (11 * 60 + 50, _t("12:30"))  # 12:20 is after close - 30
    _, checks, flat = _session("ZC")
    assert (checks[0], checks[-1], flat) == (9 * 60, 12 * 60 + 30, _t("13:15"))


def _zn_day(listed):
    """07:20..14:00, flat at the previous bar's close unless listed (open 105, prev close 105)."""
    bars, prev = {}, (105, 110, 100, 105)
    for n in range(7 * 60 + 20, 14 * 60 + 1):
        m = time(n // 60, n % 60)
        bar = listed.get(m.strftime("%H:%M"), (prev[3],) * 4 if n > 440 else prev)
        bars[m] = bar
        prev = bar
    sigma = {c: 0.02 for c in _session("ZN")[1]}
    return DayInput(
        date(2020, 1, 2), "ZN", bars, _t("14:00"), None, None, 105,
        {"sigma": sigma, "skip": False}, {m: 1 for m in bars},
    )


def test_zn_enters_at_its_first_check_and_flattens_at_its_close():
    r = NoiseArea().simulate(_zn_day({"07:49": (105, 108, 105, 108)}))
    t = r.trades[0]
    assert (t.side, t.entry_minute, t.entry_ticks, t.exit_minute) == (1, _t("07:50"), 108, _t("14:00"))
    assert r.net_cents == -6580  # flat after entry: L3 only


def test_volume_roll_switches_the_session_after_the_next_contract_out_trades():
    d1, d2, d3 = date(2020, 3, 2), date(2020, 3, 3), date(2020, 3, 4)
    frame = pd.DataFrame(
        {
            "iid": [1, 2, 1, 2, 1, 2],
            "trade_date": [d1, d1, d2, d2, d3, d3],
            "volume": [100, 10, 40, 60, 5, 90],
        }
    )
    roll = multi.volume_roll(frame, {1: "ZNH0", 2: "ZNM0"}, [d1, d2, d3])
    assert roll == {d1: 1, d2: 1, d3: 2}  # ZNM0 out-traded on d2, so it is used from d3


def test_expiry_order_handles_the_decade_digit():
    syms = ["GCZ9", "GCG0", "GCJ4", "GCM9"]
    assert sorted(syms, key=multi._expiry_key) == ["GCM9", "GCZ9", "GCG0", "GCJ4"]
    assert dataclasses.is_dataclass(multi.SPECS["ZN"])
