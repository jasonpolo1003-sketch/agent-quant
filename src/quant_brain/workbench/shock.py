"""SC-FUT-0004 plug-in: fade a rare, time-of-day-scaled 15-minute shock.

Frozen rules: brain/_system/futures/sc-fut-0004-spec.v1.json. Fixtures:
tests/test_shock_reversal_fixtures.py (written before this module).
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

FOMC_DAYS_CSV = "brain/_system/futures/fomc_statement_days_2019_2024.csv"
SHOCK_SEED = 20261026
START = time(9, 15)
LAST_ENTRY = time(14, 30)
EARLY_CLOSE_LAST_SIGNAL = time(11, 30)
FOMC_CUTOFF = time(12, 45)


def _minute(m: time) -> int:
    return m.hour * 60 + m.minute


def _clock(n: int) -> time:
    return time(n // 60, n % 60)


def fomc_days() -> set[str]:
    from quant_brain.config import PROJECT_ROOT

    path = PROJECT_ROOT / FOMC_DAYS_CSV
    lines = path.read_text(encoding="utf-8").splitlines()[1:]
    return {line.split(",")[0] for line in lines if line.strip()}


@dataclass(frozen=True)
class ShockReversal:
    threshold: float = 4.0
    lookback_sessions: int = 60
    min_observations: int = 40
    window: int = 15
    confirm_bars: int = 10
    hold_minutes: int = 60
    family: str = dataclasses.field(default="shock_reversal", init=False)

    def settings(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "lookback_sessions": self.lookback_sessions,
            "window": self.window,
            "confirm_bars": self.confirm_bars,
            "hold_minutes": self.hold_minutes,
        }

    @property
    def first_fill(self) -> time:
        return START

    def prepare(self, day: DayInput) -> DayInput:
        return day

    def _moves(self, day: DayInput) -> dict[int, int]:
        out = {}
        for n in range(_minute(START), _minute(LAST_ENTRY) + 1):
            now, before = day.bars.get(_clock(n)), day.bars.get(_clock(n - self.window))
            if now is not None and before is not None:
                out[n] = now[3] - before[3]
        return out

    def prepare_all(self, days: list[DayInput]) -> list[DayInput]:
        """Attach each day's scale (RMS of the previous sessions' moves per minute) and FOMC flag."""
        fomc = fomc_days()
        history: list[dict[int, int]] = []
        out = []
        for day in days:
            past = history[-self.lookback_sessions :]
            scale = {}
            for n in range(_minute(START), _minute(LAST_ENTRY) + 1):
                values = [h[n] for h in past if n in h]
                if len(values) >= self.min_observations:
                    rms = float(np.sqrt(np.mean(np.square(values))))
                    if rms > 0:
                        scale[n] = rms
            context = {"scale": scale, "fomc": day.trade_date.isoformat() in fomc}
            out.append(dataclasses.replace(day, context=context))
            if day.bars:
                history.append(self._moves(day))
        return out

    def _plan(self, day: DayInput) -> tuple[str, dict | None, list[tuple[str, time]]]:
        ctx = day.context or {}
        scale = ctx.get("scale") or {}
        early = day.exit_minute < time(15, 0)
        last_signal = EARLY_CLOSE_LAST_SIGNAL if early else LAST_ENTRY
        last_entry = min(LAST_ENTRY, orb.add_minutes(day.exit_minute, -1))
        if ctx.get("fomc"):
            last_signal = min(last_signal, FOMC_CUTOFF)
            last_entry = min(last_entry, FOMC_CUTOFF)
        shock = None
        for n in range(_minute(START), _minute(last_signal) + 1):
            now, before = day.bars.get(_clock(n)), day.bars.get(_clock(n - self.window))
            if now is None or before is None or n not in scale:
                continue
            move = now[3] - before[3]
            if abs(move) >= self.threshold * scale[n]:
                shock = (n, 1 if move > 0 else -1)
                break
        if shock is None:
            return "no_trade", None, []
        n0, direction = shock
        confirm = None
        for n in range(n0 + 1, n0 + self.confirm_bars + 1):
            bar = day.bars.get(_clock(n))
            if bar is not None and (bar[3] < bar[0] if direction > 0 else bar[3] > bar[0]):
                confirm = n
                break
        if confirm is None:
            return "no_trade", None, [("no_confirmation", _clock(n0))]
        entry_at = _clock(confirm + 1)
        if entry_at > last_entry or entry_at not in day.bars:
            return "no_trade", None, [("entry_unavailable", entry_at)]
        span = [
            day.bars[_clock(n)]
            for n in range(n0 - self.window, confirm + 1)
            if _clock(n) in day.bars
        ]
        side = -direction
        entry = day.bars[entry_at][0]
        stop_level = min(b[2] for b in span) - 1 if side > 0 else max(b[1] for b in span) + 1
        stop_ticks = side * (entry - stop_level)
        if stop_ticks < 1:
            return "no_trade", None, [("entry_beyond_extreme", entry_at)]
        exit_at = min(orb.add_minutes(entry_at, self.hold_minutes), day.exit_minute)
        plan = {
            "signal": _clock(n0),
            "entry_at": entry_at,
            "stop_ticks": stop_ticks,
            "exit_at": exit_at,
            "side": side,
        }
        return "planned", plan, []

    def _run(self, day: DayInput, plan: dict, side: int) -> Trade | None:
        return orb.run_trade(
            day.bars,
            root=day.root,
            side=side,
            entry_minute=plan["entry_at"],
            stop_ticks=plan["stop_ticks"],
            exit_minute=plan["exit_at"],
            signal_minute=plan["signal"],
        )

    def simulate(self, day: DayInput) -> DayResult:
        if not day.bars:
            return DayResult(day.trade_date, day.root, "ineligible", 0, 0, [], [])
        status, plan, events = self._plan(day)
        if plan is None:
            return DayResult(day.trade_date, day.root, status, 0, 0, [], events)
        trade = self._run(day, plan, plan["side"])
        if trade is None:
            return DayResult(day.trade_date, day.root, "non_evaluable", 0, 0, [], events)
        return DayResult(
            day.trade_date,
            day.root,
            "traded",
            trade.net_cents,
            trade.stress_net_cents,
            [trade],
            events,
        )

    def matched_control(
        self, day: DayInput, result: DayResult, draws: int
    ) -> tuple[list[int], list[int], list[int]]:
        """Same entry minute, same stop distance mirrored, same exit rule; random direction."""
        if result.status != "traded":
            return [0] * draws, [0] * draws, [0] * draws
        _, plan, _ = self._plan(day)
        t = result.trades[0]
        flip = self._run(day, plan, -t.side)
        tick = orb.TICK_CENTS[day.root]
        same = (t.gross_cents, paths.day_path(day.bars, [t], tick)[0])
        other = (flip.gross_cents, paths.day_path(day.bars, [flip], tick)[0]) if flip else same
        stamp = int(day.trade_date.strftime("%Y%m%d"))
        seq = np.random.SeedSequence([SHOCK_SEED, ROOT_CODE[day.root], stamp, 4])
        signs = np.random.Generator(np.random.PCG64(seq)).integers(0, 2, size=draws)
        picks = [same if s else other for s in signs]
        return [g for g, _ in picks], [1] * draws, [lo for _, lo in picks]
