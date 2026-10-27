"""Workbench runs (W7): one strategy x market x roll over the whole practice period.

A run starts from committed code plus a settings dict. Its fingerprint hashes
both, so the same run always gives the same answer and is read back from the
cache instead of being recomputed or counted twice. Every distinct run is one
trial in the append-only workbench ledger. Practice data only: the loader is
never asked for dates in the locked exam period.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures.controls import DRAWS, daily_control
from quant_brain.futures.orb import L3_ROUND_TRIP_CENTS, TICK_CENTS, DayInput
from quant_brain.prop import paths
from quant_brain.workbench.strategies import Strategy

WORKBENCH = "brain/04_Backtest_Reports/workbench"
LEDGER = f"{WORKBENCH}/trials.jsonl"
CACHE = f"{WORKBENCH}/cache"
PRACTICE = (date(2019, 5, 1), date(2024, 12, 31))
ROLLS = {"fixed": "roll_trade_date", "volume": "volume_roll_date"}
MARKETS = ("MNQ", "MES")
CODE_FILES = (
    "src/quant_brain/futures/orb.py",
    "src/quant_brain/futures/controls.py",
    "src/quant_brain/futures/bars.py",
    "src/quant_brain/futures/session_audit.py",
    "src/quant_brain/workbench/strategies.py",
    "src/quant_brain/workbench/engine.py",
    "src/quant_brain/prop/paths.py",
    "src/quant_brain/workbench/shock.py",
)
EVALUABLE = ("traded", "no_trade", "void_range")

Loader = Callable[[str, date, date, str], list[DayInput]]


def code_hash() -> str:
    """Hash of the engine source actually imported (line endings normalised)."""
    digest = hashlib.sha256()
    for rel in CODE_FILES:
        digest.update(rel.encode())
        digest.update((PROJECT_ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def fingerprint(root: Path, strategy: Strategy, market: str, roll: str) -> str:
    spec = {
        "family": strategy.family,
        "settings": strategy.settings(),
        "market": market,
        "roll": roll,
        "period": [d.isoformat() for d in PRACTICE],
        "code": code_hash(),
        "draws": DRAWS,
    }
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


@dataclass
class DayTable:
    """Per-day arrays for every eligible practice day (ineligible days are dropped)."""

    dates: np.ndarray  # ISO strings
    status: np.ndarray
    atr: np.ndarray  # 14-TR sum (ticks), for volatility regimes
    orb_side: np.ndarray  # first trade's direction (+1/-1), 0 if none
    orb_gross: np.ndarray
    orb_low: np.ndarray  # lowest intraday equity, cents per contract, gross (prop simulator)
    orb_stress_gross: np.ndarray
    orb_trades: np.ndarray
    entry_bar_stops: np.ndarray
    gap_trades: np.ndarray
    ctrl_gross: np.ndarray  # days x draws
    ctrl_stress_gross: np.ndarray
    ctrl_trades: np.ndarray
    ctrl_ok: np.ndarray  # every draw evaluable
    ctrl_low: np.ndarray  # days x draws lowest intraday equity, gross

    @property
    def evaluable(self) -> np.ndarray:
        return np.isin(self.status, EVALUABLE) & self.ctrl_ok

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **self.__dict__)

    @classmethod
    def load(cls, path: Path) -> DayTable:
        with np.load(path, allow_pickle=False) as data:
            return cls(**{k: data[k] for k in data.files})


def simulate(strategy: Strategy, days: list[DayInput], *, draws: int = DRAWS) -> DayTable:
    rows: dict[str, list] = {k: [] for k in DayTable.__dataclass_fields__}
    if hasattr(strategy, "prepare_all"):  # cross-day, point-in-time inputs (past sessions only)
        days = strategy.prepare_all(days)
    for raw in days:
        day = strategy.prepare(raw)
        result = strategy.simulate(day)
        if result.status == "ineligible":
            continue
        k = len(result.trades) if result.status == "traded" else 0
        cost = L3_ROUND_TRIP_CENTS[day.root]
        tick = TICK_CENTS[day.root]
        if hasattr(strategy, "matched_control"):
            # Strategy-specific benchmark (e.g. same window, random direction); no stops,
            # so stress equals primary and every draw is evaluable.
            gross, taken, lows = strategy.matched_control(day, result, draws)
            ctrl_gross, ctrl_stress, ctrl_trades, ctrl_ok = gross, gross, taken, True
            ctrl_low = lows
        else:
            control = daily_control(day, k, draws=draws, first_fill=strategy.first_fill)
            draw_rows = control.draws or []
            ctrl_gross = [sum(t.gross_cents for t in d.trades) for d in draw_rows] or [0] * draws
            ctrl_stress = [d.stress_net_cents + cost * len(d.trades) for d in draw_rows] or [
                0
            ] * draws
            ctrl_trades = [len(d.trades) for d in draw_rows] or [0] * draws
            ctrl_ok = control.non_evaluable_draws == 0
            ctrl_low = (
                [
                    # never kinder than the missing-minute stress bound
                    min(paths.day_path(day.bars, d.trades, tick)[0], s)
                    for d, s in zip(draw_rows, ctrl_stress, strict=True)
                ]
                if draw_rows
                else [0] * draws
            )
        rows["dates"].append(day.trade_date.isoformat())
        rows["status"].append(result.status)
        rows["atr"].append(day.atr_tr_sum or 0)
        rows["orb_side"].append(result.trades[0].side if result.trades else 0)
        rows["orb_gross"].append(sum(t.gross_cents for t in result.trades))
        rows["orb_low"].append(
            min(
                paths.day_path(day.bars, result.trades, tick)[0],
                result.stress_net_cents + cost * len(result.trades),
            )
        )
        rows["orb_stress_gross"].append(result.stress_net_cents + cost * len(result.trades))
        rows["orb_trades"].append(len(result.trades))
        rows["entry_bar_stops"].append(sum(t.entry_bar_stop for t in result.trades))
        rows["gap_trades"].append(sum(t.gap_affected for t in result.trades))
        rows["ctrl_gross"].append(ctrl_gross)
        rows["ctrl_stress_gross"].append(ctrl_stress)
        rows["ctrl_trades"].append(ctrl_trades)
        rows["ctrl_ok"].append(ctrl_ok)
        rows["ctrl_low"].append(ctrl_low)
    as_int = lambda key: np.array(rows[key], dtype=np.int64)  # noqa: E731
    return DayTable(
        dates=np.array(rows["dates"], dtype="<U10"),
        status=np.array(rows["status"], dtype="<U16"),
        atr=as_int("atr"),
        orb_side=as_int("orb_side"),
        orb_gross=as_int("orb_gross"),
        orb_low=as_int("orb_low"),
        orb_stress_gross=as_int("orb_stress_gross"),
        orb_trades=as_int("orb_trades"),
        entry_bar_stops=as_int("entry_bar_stops"),
        gap_trades=as_int("gap_trades"),
        ctrl_gross=as_int("ctrl_gross").reshape(-1, draws),
        ctrl_stress_gross=as_int("ctrl_stress_gross").reshape(-1, draws),
        ctrl_trades=as_int("ctrl_trades").reshape(-1, draws),
        ctrl_ok=np.array(rows["ctrl_ok"], dtype=bool),
        ctrl_low=as_int("ctrl_low").reshape(-1, draws),
    )


def read_ledger(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def run(
    root: Path, strategy: Strategy, market: str, roll: str, loader: Loader
) -> tuple[DayTable, dict[str, Any], bool]:
    """(table, ledger record, was_cached). A new fingerprint appends one trial."""
    if market not in MARKETS or roll not in ROLLS:
        raise ValueError("unknown market or roll")
    fp = fingerprint(root, strategy, market, roll)
    cache = root / CACHE / f"{fp}.npz"
    known = next((e for e in read_ledger(root) if e["fingerprint"] == fp), None)
    if known and cache.exists():
        return DayTable.load(cache), known, True
    start, end = PRACTICE
    days = loader(market, start, end, ROLLS[roll])
    if any(d.trade_date > PRACTICE[1] for d in days):
        raise RuntimeError("loader returned exam-period days; refusing")
    table = simulate(strategy, days)
    table.save(cache)
    if known:
        return table, known, False
    record = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "fingerprint": fp,
        "family": strategy.family,
        "settings": strategy.settings(),
        "market": market,
        "roll": roll,
        "code": code_hash(),
        "days": len(table.dates),
    }
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return table, record, False
