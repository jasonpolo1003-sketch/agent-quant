"""SC-FUT-0005 plug-in: noise-area intraday momentum with a band/VWAP trailing stop.

Frozen rules: brain/_system/futures/sc-fut-0005-spec.v1.json (from Zarattini, Aziz &
Barbon, "Beat the Market"). Fixtures: tests/test_noise_area_fixtures.py (written first).
Decisions happen only at HH:00/HH:30 checks, using the close of the bar ending at the
check, and fill at the open of the check-minute bar.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import time
from typing import Any

import numpy as np

from quant_brain.futures import orb
from quant_brain.futures.controls import ROOT_CODE
from quant_brain.futures.orb import DayInput, DayResult, Trade
from quant_brain.prop import paths

OPEN = time(8, 30)
FIRST_CHECK = time(9, 0)
LAST_CHECK = time(14, 30)
EARLY_LAST_CHECK = time(11, 30)
CLOSE = time(15, 0)
EARLY_CLOSE = time(12, 0)
NOISE_SEED = 20261026


def _n(m: time) -> int:
    return m.hour * 60 + m.minute


def _t(n: int) -> time:
    return time(n // 60, n % 60)


def _checks(early: bool) -> list[int]:
    last = EARLY_LAST_CHECK if early else LAST_CHECK
    return list(range(_n(FIRST_CHECK), _n(last) + 1, 30))


@dataclass(frozen=True)
class NoiseArea:
    lookback_sessions: int = 14
    min_observations: int = 10
    family: str = dataclasses.field(default="noise_area", init=False)

    def settings(self) -> dict[str, Any]:
        return {"lookback_sessions": self.lookback_sessions, "stop": "band_or_vwap", "size": 1}

    @property
    def first_fill(self) -> time:
        return FIRST_CHECK

    def prepare(self, day: DayInput) -> DayInput:
        return day

    @staticmethod
    def _moves(day: DayInput) -> dict[int, float]:
        first = day.bars.get(OPEN)
        if first is None or first[0] <= 0:
            return {}
        out = {}
        for n in _checks(early=False):
            bar = day.bars.get(_t(n - 1))
            if bar is not None:
                out[n] = abs(bar[3] / first[0] - 1)
        return out

    def prepare_all(self, days: list[DayInput]) -> list[DayInput]:
        """Attach sigma per check: the mean move over the previous 14 sessions only."""
        history: list[dict[int, float]] = []
        out = []
        for day in days:
            past = history[-self.lookback_sessions :]
            sigma = {}
            for n in _checks(early=False):
                values = [h[n] for h in past if n in h]
                if len(values) >= self.min_observations:
                    sigma[n] = float(np.mean(values))
            out.append(dataclasses.replace(day, context={"sigma": sigma}))
            if day.bars:
                history.append(self._moves(day))
        return out

    def _legs(self, day: DayInput) -> tuple[str, list[dict]]:
        """Planned legs [{side, entry_at, entry, exit_at, exit, reason}] or a non-evaluable status."""
        sigma = (day.context or {}).get("sigma") or {}
        first = day.bars.get(OPEN)
        if first is None or day.prev_close is None:
            return "no_trade", []
        open_ = first[0]
        hi_anchor, lo_anchor = max(open_, day.prev_close), min(open_, day.prev_close)
        early = day.exit_minute < CLOSE
        flat_at = EARLY_CLOSE if early else CLOSE
        pv = vol = 0.0
        legs: list[dict] = []
        position = None  # (side, entry_at, entry)
        cum_until = _n(OPEN)
        for n in _checks(early):
            # VWAP over cash-hours bars ending by this check
            while cum_until < n:
                bar = day.bars.get(_t(cum_until))
                if bar is not None:
                    v = (day.volumes or {}).get(_t(cum_until), 1) or 0
                    pv += v * (bar[1] + bar[2] + bar[3]) / 3
                    vol += v
                cum_until += 1
            price_bar = day.bars.get(_t(n - 1))
            fill_bar = day.bars.get(_t(n))
            if n not in sigma or price_bar is None or fill_bar is None:
                continue
            price, fill = price_bar[3], fill_bar[0]
            upper = hi_anchor * (1 + sigma[n])
            lower = lo_anchor * (1 - sigma[n])
            vwap = pv / vol if vol else price
            exited = 0
            if position is not None:
                side, entry_at, entry = position
                stop = max(upper, vwap) if side > 0 else min(lower, vwap)
                if (side > 0 and price < stop) or (side < 0 and price > stop):
                    legs.append(
                        {
                            "side": side,
                            "entry_at": entry_at,
                            "entry": entry,
                            "exit_at": _t(n),
                            "exit": fill,
                            "reason": "signal_exit",
                        }
                    )
                    position, exited = None, side
            if position is None:
                # After an exit, only a reversal may happen at the same check (frozen spec).
                if price > upper and exited != 1:
                    position = (1, _t(n), fill)
                elif price < lower and exited != -1:
                    position = (-1, _t(n), fill)
        if position is not None:
            close_bar = day.bars.get(flat_at)
            if close_bar is None:
                return "non_evaluable", legs
            side, entry_at, entry = position
            legs.append(
                {
                    "side": side,
                    "entry_at": entry_at,
                    "entry": entry,
                    "exit_at": flat_at,
                    "exit": close_bar[0],
                    "reason": "close",
                }
            )
        return ("traded" if legs else "no_trade"), legs

    @staticmethod
    def _trade(day: DayInput, leg: dict, side: int) -> Trade:
        gross = side * (leg["exit"] - leg["entry"]) * orb.TICK_CENTS[day.root]
        net = gross - orb.L3_ROUND_TRIP_CENTS[day.root]
        return Trade(
            side=side,
            signal_minute=leg["entry_at"],
            entry_minute=leg["entry_at"],
            entry_ticks=leg["entry"],
            stop_level_ticks=leg["entry"],  # trailing stop is checked only at checks
            exit_minute=leg["exit_at"],
            exit_ticks=leg["exit"],
            exit_reason=leg["reason"],
            gross_cents=gross,
            net_cents=net,
            entry_bar_stop=False,
            gap_affected=False,
            stress_exit_ticks=None,
            stress_net_cents=net,
        )

    def simulate(self, day: DayInput) -> DayResult:
        if not day.bars:
            return DayResult(day.trade_date, day.root, "ineligible", 0, 0, [], [])
        status, legs = self._legs(day)
        trades = [self._trade(day, leg, leg["side"]) for leg in legs]
        if status == "non_evaluable":
            return DayResult(day.trade_date, day.root, status, 0, 0, trades, [])
        net = sum(x.net_cents for x in trades)
        return DayResult(day.trade_date, day.root, status, net, net, trades, [])

    def matched_control(
        self, day: DayInput, result: DayResult, draws: int
    ) -> tuple[list[int], list[int], list[int]]:
        """The same legs (times, prices), each with an independent random direction."""
        if result.status != "traded":
            return [0] * draws, [0] * draws, [0] * draws
        _, legs = self._legs(day)
        stamp = int(day.trade_date.strftime("%Y%m%d"))
        seq = np.random.SeedSequence([NOISE_SEED, ROOT_CODE[day.root], stamp, 5])
        flips = np.random.Generator(np.random.PCG64(seq)).integers(0, 2, size=(draws, len(legs)))
        tick = orb.TICK_CENTS[day.root]
        cache: dict[tuple[int, ...], tuple[int, int]] = {}
        gross, lows = [], []
        for row in flips:
            key = tuple(int(x) for x in row)
            if key not in cache:
                trades = [
                    self._trade(day, leg, 1 if f else -1) for leg, f in zip(legs, key, strict=True)
                ]
                cache[key] = (
                    sum(t.gross_cents for t in trades),
                    paths.day_path(day.bars, trades, tick)[0],
                )
            g, lo = cache[key]
            gross.append(g)
            lows.append(lo)
        return gross, [len(legs)] * draws, lows
