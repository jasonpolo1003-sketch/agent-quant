"""SC-FUT-0013 plug-in: month-end rebalancing flow (T1) and turn of the month (T2), RTH only.

Frozen rule: brain/_system/futures/sc-fut-0013-spec.v1.json, with addendum 1
(sc-fut-0013-addendum-1.md, written before any result). Fixtures: tests/test_month_end_fixtures.py.

Positions come from the frozen NYSE calendar: L is a month's last session, L-1..L-3 the ones
before it, F1..F3 its first three. Day inputs are `bars.build_days` (volume roll) with
`context = {"position": ..., "rel": ..., "signal": ...}` attached by `attach`.

As implemented:
- T1 signal at L-3's RTH close: rel = MES month-to-date return - ZN month-to-date return, each
  from the previous month's L RTH close, on its own volume-roll front, chained across a roll at
  the roll day's closes (`chained_return`); exact fractions;
- T1 trades L-2, L-1 and L: short if rel > 0, long if rel < 0; rel == 0 or missing -> no trade;
- T2 is long on L, F1, F2 and F3;
- entry at the 08:30 CT open, exit at the 15:00 CT open (12:00 on early-close days); no stop;
  a missing entry or exit bar on a trade day -> non-evaluable;
- every other session is `no_trade` ($0), so the workbench table holds every practice session.

Matched control (spec `luck`): the same bars, each draw a random direction from
PCG64(SeedSequence([20261029, root, yyyymmdd, 13])); 0 on days without a trade.
Gates (spec, `spec_verdict`): paired test over trade days at alpha 0.0253, and net >= $1.00 per
calendar session AND >= $5.00 per trade, all at L3.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, time, timedelta
from fractions import Fraction
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from quant_brain.futures import orb
from quant_brain.futures.bars import CalendarDay, _sessions
from quant_brain.futures.controls import ROOT_CODE
from quant_brain.futures.orb import DayInput, DayResult, Trade
from quant_brain.futures.session_audit import contract_on, instrument_for, selected_contracts
from quant_brain.prop import paths

MONTH_END_SEED = 20261029
SEED_TAG = 13
TRIALS = ("T1_rebalance", "T2_turn_of_month")
TRADE_POSITIONS = {"T1_rebalance": ("L-2", "L-1", "L"), "T2_turn_of_month": ("L", "F1", "F2", "F3")}
ENTRY = time(8, 30)
EXIT = time(15, 0)
EARLY_EXIT = time(12, 0)
ZN_OPEN = time(7, 20)
ZN_CLOSE = time(14, 0)
EARLY_REGULAR_CLOSE = time(12, 15)
SPEC_ALPHA = 1 - 0.95 ** (1 / 2)  # 0.0253: Sidak split of 5% over the family's 2 trials
FLOOR_SESSION_CENTS = 100
FLOOR_TRADE_CENTS = 500

Closes = dict[tuple[str, date], int]  # (contract, session) -> RTH close in ticks


# ---------------------------------------------------------------- calendar positions


def _weekdays_between(a: date, b: date) -> bool:
    """Is there a Mon-Fri strictly between a and b (a < b)?"""
    d = a + timedelta(days=1)
    while d < b:
        if d.weekday() < 5:
            return True
        d += timedelta(days=1)
    return False


def month_positions(sessions: Sequence[date]) -> dict[date, str]:
    """{session: "L-3".."L" or "F1".."F3"} among each calendar month's sessions.

    A month at the edge of `sessions` is labelled only when no weekday lies between it and the
    month's boundary (otherwise the list may not cover the month's first or last session).
    """
    months: dict[tuple[int, int], list[date]] = {}
    for d in sorted(sessions):
        months.setdefault((d.year, d.month), []).append(d)
    keys = sorted(months)
    out: dict[date, str] = {}
    for key in keys:
        days = months[key]
        first_of_month = date(key[0], key[1], 1)
        next_month = date(key[0] + key[1] // 12, key[1] % 12 + 1, 1)
        starts = key != keys[0] or not _weekdays_between(
            first_of_month - timedelta(days=1), days[0]
        )
        ends = key != keys[-1] or not _weekdays_between(days[-1], next_month)
        labels: dict[date, str] = {}
        if starts:
            for k, d in enumerate(days[:3], start=1):
                labels[d] = f"F{k}"
        if ends:
            for k, d in enumerate(reversed(days[-4:])):
                if d in labels:
                    raise ValueError(f"{d}: month too short for disjoint positions")
                labels[d] = "L" if k == 0 else f"L-{k}"
        out.update(labels)
    return out


# ---------------------------------------------------------------- the T1 signal


def chained_return(
    window: Sequence[date], front: dict[date, str], closes: Closes
) -> Fraction | None:
    """Return from window[0]'s RTH close to window[-1]'s on the volume-roll front, chained at the
    roll day's closes (the roll day R is the first session on the new front: the old contract's
    segment ends at its close on R, the new one starts at the new contract's close on R).
    None if any close the formula needs (or a front) is missing."""
    if not window or any(d not in front for d in window):
        return None
    contract, anchor, ratio = front[window[0]], window[0], Fraction(1)
    for day in [*window[1:], None]:
        if day is not None and front[day] == contract:
            continue
        end = window[-1] if day is None else day
        a, b = closes.get((contract, anchor)), closes.get((contract, end))
        if a is None or b is None or a == 0:
            return None
        ratio *= Fraction(b, a)
        if day is not None:
            contract, anchor = front[day], day
    return ratio - 1


@dataclass(frozen=True)
class Signal:
    start: date  # previous month's L
    end: date  # this month's L-3
    mes: Fraction | None
    zn: Fraction | None

    @property
    def rel(self) -> Fraction | None:
        return None if self.mes is None or self.zn is None else self.mes - self.zn


def month_signals(
    sessions: Sequence[date],
    positions: dict[date, str],
    mes: tuple[dict[date, str], Closes],
    zn: tuple[dict[date, str], Closes],
) -> dict[tuple[int, int], Signal | None]:
    """Each month with an L-3: its signal (None when the previous month's L is unknown)."""
    order = sorted(sessions)
    index = {d: i for i, d in enumerate(order)}
    last = {(d.year, d.month): d for d, p in positions.items() if p == "L"}
    out: dict[tuple[int, int], Signal | None] = {}
    for d, p in sorted(positions.items()):
        if p != "L-3":
            continue
        prev_key = (d.year - (d.month == 1), (d.month - 2) % 12 + 1)
        start = last.get(prev_key)
        if start is None:
            out[(d.year, d.month)] = None
            continue
        window = order[index[start] : index[d] + 1]
        out[(d.year, d.month)] = Signal(
            start, d, chained_return(window, *mes), chained_return(window, *zn)
        )
    return out


def attach(
    days: Sequence[DayInput],
    positions: dict[date, str],
    signals: dict[tuple[int, int], Signal | None],
) -> list[DayInput]:
    out = []
    for day in days:
        signal = signals.get((day.trade_date.year, day.trade_date.month))
        context = {
            "position": positions.get(day.trade_date),
            "rel": None if signal is None else signal.rel,
            "signal": signal,
        }
        out.append(dataclasses.replace(day, context=context))
    return out


# ---------------------------------------------------------------- data (practice files)


def mes_leg(
    frame: pd.DataFrame,
    mappings: dict,
    roll_csv: Path,
    calendar: list[CalendarDay],
    root: str = "MES",
) -> tuple[dict[date, str], Closes]:
    """Volume-roll front per session and RTH closes (`bars._sessions`: last bar before 15:00, or
    12:15 on early-close days) of every root contract on every session."""
    by_date = {c.trade_date: c for c in calendar}
    symbols = {s: v for s, v in mappings.items() if s.startswith(root) and "-" not in s}
    iids = {iid for intervals in symbols.values() for *_, iid in intervals}
    sessions = _sessions(frame[frame["instrument_id"].isin(iids)], by_date)
    schedule = selected_contracts(roll_csv, root, "volume_roll_date")
    front = {d: contract_on(schedule, d) for d in by_date}
    closes: Closes = {}
    for symbol in symbols:
        for d in by_date:
            s = sessions.get((instrument_for(mappings, symbol, d), d))
            if s is not None and s.close is not None:
                closes[(symbol, d)] = s.close
    return front, closes


def zn_leg(frame: pd.DataFrame, calendar: list[CalendarDay]) -> tuple[dict[date, str], Closes]:
    """ZN front by `multi.volume_roll` over every calendar session, and RTH closes: last bar in
    [07:20, 14:00) CT, or [07:20, 12:15) on early-close days, on the session's own day."""
    from quant_brain.futures import multi

    days = [c.trade_date for c in calendar]
    early = {c.trade_date for c in calendar if c.early_close}
    front = multi.volume_roll(frame, days)
    local = frame["minute"].dt.time
    same_day = frame["minute"].dt.date == frame["trade_date"]
    is_early = frame["trade_date"].isin(early)
    before = (local < ZN_CLOSE) & (~is_early | (local < EARLY_REGULAR_CLOSE))
    keep = frame[same_day & (local >= ZN_OPEN) & before & frame["trade_date"].isin(set(days))]
    last = keep.groupby(["symbol", "trade_date"], sort=False)["close"].last()
    return front, {(s, d): int(c) for (s, d), c in last.items()}


def loader(dev_dir: Path, multi_dir: Path) -> Callable[[str, date, date, str], list[DayInput]]:
    """MES / MNQ practice days with month positions and the T1 signal attached. Both files are
    hash-checked against their manifests (as scripts/workbench.py's dev and multi loaders)."""
    from quant_brain.config import PROJECT_ROOT
    from quant_brain.futures import multi, runner
    from quant_brain.futures.bars import build_days, read_calendar, read_tick_bars
    from quant_brain.futures.session_audit import read_mappings

    listed = json.loads((dev_dir / "manifest.json").read_text(encoding="utf-8"))["ohlcv"]
    expected = next(r["output_sha256"] for r in listed if r["output"] == runner.DEV_BARS)
    bars_path = dev_dir / runner.DEV_BARS
    if runner.sha256(bars_path) != expected:
        raise SystemExit("dev minute-bar file does not match its manifest")
    zn_path = multi.bars_file(multi_dir, "ZN")
    zn_files = json.loads((multi_dir / "manifest.json").read_text(encoding="utf-8"))["files"]
    zn_expected = next(f["sha256"] for f in zn_files if f["file"] == zn_path.name)
    if hashlib.sha256(zn_path.read_bytes()).hexdigest() != zn_expected:
        raise SystemExit(f"{zn_path.name} does not match its manifest")
    roll_csv = PROJECT_ROOT / "brain/sources/mes_mnq/contracts/roll_volume_check.csv"
    cache: dict[str, Any] = {}

    def setup(end: date) -> None:
        if cache:
            return
        mappings = read_mappings(bars_path)
        outrights = {iid for intervals in mappings.values() for *_, iid in intervals}
        frame = read_tick_bars(bars_path, outrights)
        calendar = [c for c in read_calendar(PROJECT_ROOT / runner.CALENDAR) if c.trade_date <= end]
        zn_frame, _ = multi.read_bars(zn_path, multi.SPECS["ZN"].tick_nano)
        sessions = [c.trade_date for c in calendar]
        positions = month_positions(sessions)
        signals = month_signals(
            sessions,
            positions,
            mes_leg(frame, mappings, roll_csv, calendar),
            zn_leg(zn_frame, calendar),
        )
        cache.update(
            frame=frame, mappings=mappings, calendar=calendar, positions=positions, signals=signals
        )

    def load(market: str, start: date, end: date, roll_column: str) -> list[DayInput]:
        if roll_column != "volume_roll_date" or market not in ("MES", "MNQ"):
            raise SystemExit("month_end runs on MES / MNQ with the volume roll only")
        setup(end)
        days = build_days(
            cache["frame"],
            cache["mappings"],
            roll_csv,
            cache["calendar"],
            root=market,
            start=start,
            end=end,
            roll_column=roll_column,
        )
        return attach(list(days), cache["positions"], cache["signals"])

    load.cache = cache  # type: ignore[attr-defined]  # diagnostics read positions and signals
    return load


# ---------------------------------------------------------------- the strategy


@dataclass(frozen=True)
class MonthEnd:
    """SC-FUT-0013: T1 trades L-2, L-1, L against the month-to-date MES-minus-ZN move; T2 is long
    L, F1, F2, F3. 08:30 CT open -> 15:00 CT open (12:00 on early closes), 1 contract, no stop."""

    trial: str = "T1_rebalance"
    family: str = dataclasses.field(default="month_end", init=False)
    session: ClassVar[str] = "month_end"
    seed_tag: ClassVar[int] = SEED_TAG

    def __post_init__(self) -> None:
        if self.trial not in TRIALS:
            raise ValueError(f"trial must be one of {TRIALS}")

    def settings(self) -> dict[str, Any]:
        return {
            "card": "SC-FUT-0013",
            "trial": self.trial,
            "days": list(TRADE_POSITIONS[self.trial]),
            "signal": "short if MES-ZN month to date (prev L -> L-3) > 0, long if < 0"
            if self.trial == "T1_rebalance"
            else "long",
            "entry": "08:30 CT open",
            "exit": "15:00 CT open (12:00 on early closes)",
            "stop": None,
            "size": 1,
        }

    @property
    def first_fill(self) -> time:
        return ENTRY

    def prepare(self, day: DayInput) -> DayInput:
        return day

    def side(self, day: DayInput) -> int:
        """+1 / -1 on a trade day, 0 otherwise (not a trade position, or T1 with rel 0/missing)."""
        context = day.context or {}
        if context.get("position") not in TRADE_POSITIONS[self.trial]:
            return 0
        if self.trial == "T2_turn_of_month":
            return 1
        rel = context.get("rel")
        if rel is None or rel == 0:
            return 0
        return -1 if rel > 0 else 1

    @staticmethod
    def exit_minute(day: DayInput) -> time:
        return EARLY_EXIT if day.exit_minute < EXIT else EXIT

    def simulate(self, day: DayInput) -> DayResult:
        def result(status, trades=(), events=()):
            trades = list(trades)
            net = sum(x.net_cents for x in trades)
            return DayResult(day.trade_date, day.root, status, net, net, trades, list(events))

        side = self.side(day)
        if side == 0:
            return result("no_trade")
        exit_at = self.exit_minute(day)
        for minute in (ENTRY, exit_at):
            if minute not in day.bars:
                return result("non_evaluable", events=[("bar_missing", minute)])
        entry, exit_ = day.bars[ENTRY][0], day.bars[exit_at][0]
        gross, net = orb._net(day.root, side, entry, exit_)
        trade = Trade(
            side=side,
            signal_minute=None,
            entry_minute=ENTRY,
            entry_ticks=entry,
            stop_level_ticks=entry,  # no stop
            exit_minute=exit_at,
            exit_ticks=exit_,
            exit_reason="flatten",
            gross_cents=gross,
            net_cents=net,
            entry_bar_stop=False,
            gap_affected=False,  # no stop: a missing minute inside the hold changes nothing
            stress_exit_ticks=None,
            stress_net_cents=net,
        )
        return result("traded", [trade])

    def matched_control(
        self, day: DayInput, result: DayResult, draws: int
    ) -> tuple[list[int], list[int], list[int], list[list[tuple[int, int]]]]:
        """(gross, trades, day low, equity records) per draw: the same bars, random direction."""
        if result.status != "traded":
            return [0] * draws, [0] * draws, [0] * draws, [[]] * draws
        trade = result.trades[0]
        stamp = int(day.trade_date.strftime("%Y%m%d"))
        seq = np.random.SeedSequence([MONTH_END_SEED, ROOT_CODE[day.root], stamp, self.seed_tag])
        signs = np.random.Generator(np.random.PCG64(seq)).integers(0, 2, size=draws) * 2 - 1
        tick = orb.TICK_CENTS[day.root]
        both = {}
        for side in (1, -1):
            gross = side * trade.side * trade.gross_cents
            flipped = dataclasses.replace(trade, side=side, gross_cents=gross)
            low = paths.day_path(day.bars, [flipped], tick)[0]
            both[side] = (gross, low, paths.day_records(day.bars, [flipped], tick))
        picked = [both[int(s)] for s in signs]
        return (
            [g for g, _, _ in picked],
            [1] * draws,
            [lo for _, lo, _ in picked],
            [r for _, _, r in picked],
        )

    def spec_verdict(self, table, market: str, **kw) -> dict[str, Any]:
        return spec_verdict(table, market, **kw)


# ---------------------------------------------------------------- gates and diagnostics


def _net_arrays(table, market: str, level: str):
    from quant_brain.workbench.analysis import COSTS

    cost = COSTS[level][market]
    net = (table.orb_gross - cost * table.orb_trades).astype(float)
    ctrl = (table.ctrl_gross - cost * table.ctrl_trades).astype(float).mean(axis=1)
    return net, ctrl


def spec_verdict(
    table, market: str, *, alpha: float = SPEC_ALPHA, replicates: int | None = None
) -> dict[str, Any]:
    """Spec `gates`: p over trade days < alpha; L3 net per session (all sessions) >= $1 and per
    trade >= $5. Sharpe of daily net over all sessions is reported, not gated."""
    from quant_brain.futures import inference
    from quant_brain.workbench.analysis import COSTS, annual_sharpe

    reps = inference.BOOTSTRAP_DRAWS if replicates is None else replicates
    trade = table.evaluable & (table.orb_trades > 0)
    n_sessions = len(table.dates)
    out: dict[str, Any] = {
        "sessions": n_sessions,
        "trade_days": int(trade.sum()),
        "non_evaluable_trade_days": int((table.status == "non_evaluable").sum()),
        "alpha": alpha,
    }
    if trade.sum() < 2:
        return out | {"outcome": "FAIL", "reasons": ["fewer than 2 trade days"]}
    costs = {}
    for level in COSTS:
        net, _ = _net_arrays(table, market, level)
        costs[level] = {
            "per_trade": float(net[trade].mean() / 100),
            "per_session": float(net[trade].sum() / n_sessions / 100),
        }
    net, ctrl = _net_arrays(table, market, "L3")
    test = inference.paired_test(net[trade], ctrl[trade], replicates=reps)
    per_trade, per_session = net[trade].mean(), net[trade].sum() / n_sessions
    daily = np.where(trade, net, 0.0)
    reasons = []
    if test["p_value"] >= alpha:
        reasons.append(
            f"not better than the matched control (p {test['p_value']:.4f} vs {alpha:.4f})"
        )
    if per_session < FLOOR_SESSION_CENTS:
        reasons.append(f"below $1.00 per session (${per_session / 100:.2f})")
    if per_trade < FLOOR_TRADE_CENTS:
        reasons.append(f"below $5.00 per trade (${per_trade / 100:.2f})")
    return out | {
        "outcome": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
        "per_trade": float(per_trade / 100),
        "per_session": float(per_session / 100),
        "control_per_trade": float(ctrl[trade].mean() / 100),
        "vs_control_per_trade": test["observed_cents"] / 100,
        "p_value": test["p_value"],
        "sharpe_all_sessions": annual_sharpe(daily),
        "hit_rate": float((table.orb_gross[trade] > 0).mean()),
        "costs": costs,
    }


def per_year(table, market: str, level: str = "L3") -> dict[str, dict[str, Any]]:
    net, _ = _net_arrays(table, market, level)
    trade = table.evaluable & (table.orb_trades > 0)
    out = {}
    for year in sorted({d[:4] for d in table.dates}):
        mask = np.char.startswith(table.dates, year)
        k = trade & mask
        out[year] = {
            "sessions": int(mask.sum()),
            "trade_days": int(k.sum()),
            "net": float(net[k].sum() / 100),
            "per_trade": float(net[k].mean() / 100) if k.any() else None,
            "per_session": float(net[k].sum() / mask.sum() / 100),
            "hit_rate": float((table.orb_gross[k] > 0).mean()) if k.any() else None,
        }
    return out


def hit_rate_by_side(table) -> dict[str, dict[str, Any]]:
    """T1: side -1 means rel > 0 (short), +1 means rel < 0 (long)."""
    trade = table.evaluable & (table.orb_trades > 0)
    out = {}
    for name, side in (("rel>0 (short)", -1), ("rel<0 (long)", 1)):
        k = trade & (table.orb_side == side)
        out[name] = {
            "trade_days": int(k.sum()),
            "hit_rate": float((table.orb_gross[k] > 0).mean()) if k.any() else None,
            "gross_per_trade": float(table.orb_gross[k].mean() / 100) if k.any() else None,
        }
    return out


def always_long_other(days: Sequence[DayInput], cost_cents: int) -> dict[str, Any]:
    """Diagnostic: long 1 on every session that is not L/F1/F2/F3, same bars and exit rule."""
    nets, missing = [], 0
    for day in days:
        if (day.context or {}).get("position") in TRADE_POSITIONS["T2_turn_of_month"]:
            continue
        exit_at = MonthEnd.exit_minute(day)
        if ENTRY not in day.bars or exit_at not in day.bars:
            missing += 1
            continue
        gross = (day.bars[exit_at][0] - day.bars[ENTRY][0]) * orb.TICK_CENTS[day.root]
        nets.append(gross - cost_cents)
    arr = np.array(nets, dtype=float)
    return {
        "sessions": len(nets),
        "missing_bars": missing,
        "per_session": float(arr.mean() / 100),
        "sd": float(arr.std(ddof=1) / 100),
        "values_cents": arr,
    }


def welch_t(a: np.ndarray, b: np.ndarray) -> float:
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    return float((a.mean() - b.mean()) / np.sqrt(va + vb))
