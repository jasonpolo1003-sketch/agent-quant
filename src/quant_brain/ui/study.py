"""Study page data for SC-FUT-0001: verdict, luck band, histogram, replay, honesty trail.

Reads only the runner's outputs (`brain/04_Backtest_Reports/SC-FUT-0001/<phase>/`)
and the trial ledger. Replay candles come from the development partition; dates
inside the locked held-out period are refused until the held-out read is done.
"""

from __future__ import annotations

import calendar
import csv
import json
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from quant_brain.futures import runner
from quant_brain.futures.bars import build_days, read_calendar, read_tick_bars
from quant_brain.futures.controls import daily_control
from quant_brain.futures.orb import RANGE_BARS, RANGE_START, add_minutes, simulate_day
from quant_brain.futures.session_audit import read_mappings

DEV_DIR = Path(__file__).resolve().parents[4] / "data" / "databento" / "dev_2019-05-01_2024-12-31"
POINTS_PER_TICK = 0.25
STAGES = [
    ("frozen", "Rules frozen", "Every rule, seed and input fingerprinted before any result."),
    ("development_authorized", "Practice run approved", "Jason's OK to run on 2019-2024 data."),
    (
        "development_completed",
        "Practice run done",
        "Strategy and 500 random entries per day, 2019-2023 (+2024 check).",
    ),
    (
        "held_out_authorized",
        "Final exam approved",
        "A separate OK to open the locked 2025-2026 data.",
    ),
    ("held_out_completed", "Final exam done", "The locked data, read exactly once."),
]


class StudyError(RuntimeError):
    pass


def _phase_dir(root: Path, phase: str) -> Path:
    return root / runner.REPORTS / phase


def _daily(root: Path, phase: str, key: str) -> list[dict[str, str]]:
    path = _phase_dir(root, phase) / f"{key}.daily.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def trail(root: Path) -> list[dict[str, Any]]:
    events = runner.read_ledger(root)
    out = []
    for name, label, about in STAGES:
        names = {"frozen", "freeze_provenance_corrected"} if name == "frozen" else {name}
        hits = [e for e in events if e["event"] in names]
        last = hits[-1] if hits else None
        out.append(
            {
                "stage": name,
                "label": label,
                "about": about,
                "done": last is not None,
                "at": last["at"] if last else None,
                "detail": (last or {}).get("spec_sha256") or (last or {}).get("code_commit"),
            }
        )
    failed = [e for e in events if e["event"] == "held_out_failed"]
    if failed:
        out[-1] |= {
            "done": True,
            "label": "Final exam failed (still counts as read)",
            "at": failed[-1]["at"],
        }
    return out


def overview(root: Path) -> dict[str, Any]:
    phases = {}
    for phase in ("development", "held_out"):
        report = _phase_dir(root, phase) / "report.json"
        if report.exists():
            phases[phase] = json.loads(report.read_text(encoding="utf-8"))
    return {"card_id": runner.CARD_ID, "trail": trail(root), "phases": phases}


def series(root: Path, phase: str, key: str) -> dict[str, Any]:
    """Cumulative ORB vs control mean, the 5-95% band of control draws, and the luck histogram."""
    rows = _daily(root, phase, key)
    if not rows:
        raise StudyError(f"no daily results for {phase}/{key}")
    keep = [i for i, r in enumerate(rows) if r["status"] != "non_evaluable"]
    dates = [rows[i]["trade_date"] for i in keep]
    orb = np.array([float(rows[i]["orb_cents"]) for i in keep]) / 100
    control = np.array([float(rows[i]["control_cents"]) for i in keep]) / 100
    out: dict[str, Any] = {
        "dates": dates,
        "orb": np.cumsum(orb).round(2).tolist(),
        "control_mean": np.cumsum(control).round(2).tolist(),
        "days": len(keep),
        "skipped_non_evaluable": len(rows) - len(keep),
    }
    draws_path = _phase_dir(root, phase) / f"{key}.draws.npy"
    if draws_path.exists():
        draws = np.load(draws_path)[keep] / 100  # days x 500
        paths = np.cumsum(draws, axis=0)
        out["band_low"] = np.percentile(paths, 5, axis=1).round(2).tolist()
        out["band_high"] = np.percentile(paths, 95, axis=1).round(2).tolist()
        totals = paths[-1]
        counts, edges = np.histogram(totals, bins=30)
        out["histogram"] = {
            "counts": counts.tolist(),
            "edges": edges.round(2).tolist(),
            "orb_total": round(float(orb.sum()), 2),
            "share_of_draws_beaten": float((totals < orb.sum()).mean()),
        }
    return out


def day_list(root: Path, phase: str, key: str) -> list[dict[str, Any]]:
    return [
        {
            "date": r["trade_date"],
            "status": r["status"],
            "orb": round(float(r["orb_cents"]) / 100, 2),
            "vs_luck": round((float(r["orb_cents"]) - float(r["control_cents"])) / 100, 2),
            "trades": int(r["orb_trades"]),
        }
        for r in _daily(root, phase, key)
    ]


@lru_cache(maxsize=2)
def _dev_frame(bars_path: str):
    mappings = read_mappings(Path(bars_path))
    outrights = {iid for intervals in mappings.values() for *_, iid in intervals}
    return read_tick_bars(Path(bars_path), outrights), mappings


def _held_out_read(root: Path) -> bool:
    return any(
        e["event"] in {"held_out_completed", "held_out_failed"} for e in runner.read_ledger(root)
    )


def _chart_time(day: date, minute: time) -> int:
    """Chicago wall-clock minute as a UTC timestamp, so the chart axis reads in CT."""
    return calendar.timegm(datetime.combine(day, minute).timetuple())


def replay(root: Path, root_name: str, day_iso: str, dev_dir: Path = DEV_DIR) -> dict[str, Any]:
    try:
        day = date.fromisoformat(day_iso)
    except ValueError as exc:
        raise StudyError("date must be YYYY-MM-DD") from exc
    locked_from = runner.PERIODS["held_out"][0]
    if day >= locked_from and not _held_out_read(root):
        raise StudyError("that date is in the locked final-exam period")
    if day >= locked_from:
        raise StudyError("held-out replay needs the raw download; not wired yet")
    if root_name not in runner.ROOTS:
        raise StudyError("unknown market")
    frame, mappings = _dev_frame(str(dev_dir / runner.DEV_BARS))
    calendar = read_calendar(root / runner.CALENDAR)
    days = list(
        build_days(
            frame, mappings, root / runner.ROLL_CSV, calendar, root=root_name, start=day, end=day
        )
    )
    if not days:
        raise StudyError("not a trading session")
    d = days[0]
    result = simulate_day(d)
    k = len(result.trades) if result.status == "traded" else 0
    control = (
        daily_control(d, k)
        if d.stop_ticks is not None and result.status in {"traded", "no_trade", "void_range"}
        else None
    )
    pts = lambda ticks: round(ticks * POINTS_PER_TICK, 2)  # noqa: E731
    candles = [
        {
            "time": _chart_time(day, m),
            "open": pts(o),
            "high": pts(h),
            "low": pts(lo),
            "close": pts(c),
        }
        for m, (o, h, lo, c) in sorted(d.bars.items())
    ]
    range_minutes = [add_minutes(RANGE_START, i) for i in range(RANGE_BARS)]
    in_range = [d.bars[m] for m in range_minutes if m in d.bars]
    present = set(d.bars)
    gaps = []
    m = RANGE_START
    while m <= d.exit_minute:
        if m not in present:
            gaps.append(_chart_time(day, m))
        m = add_minutes(m, 1)
    return {
        "date": day_iso,
        "root": root_name,
        "status": result.status,
        "net": result.net_cents / 100,
        "stress_net": result.stress_net_cents / 100,
        "stop_points": pts(d.stop_ticks) if d.stop_ticks else None,
        "range": {
            "high": pts(max(b[1] for b in in_range)) if in_range else None,
            "low": pts(min(b[2] for b in in_range)) if in_range else None,
            "start": _chart_time(day, RANGE_START),
            "end": _chart_time(day, range_minutes[-1]),
        },
        "candles": candles,
        "gaps": gaps,
        "trades": [
            {
                "side": "long" if t.side > 0 else "short",
                "signal": _chart_time(day, t.signal_minute) if t.signal_minute else None,
                "entry_time": _chart_time(day, t.entry_minute),
                "entry": pts(t.entry_ticks),
                "stop": pts(t.stop_level_ticks),
                "exit_time": _chart_time(day, t.exit_minute),
                "exit": pts(t.exit_ticks),
                "reason": t.exit_reason,
                "net": t.net_cents / 100,
                "gap_affected": t.gap_affected,
            }
            for t in result.trades
        ],
        "events": [{"kind": k_, "time": _chart_time(day, m_)} for k_, m_ in result.events],
        "control": None
        if control is None or not control.draws
        else {
            "mean": control.mean_cents / 100,
            "entries": [
                {
                    "time": _chart_time(day, t.entry_minute),
                    "price": pts(t.entry_ticks),
                    "side": t.side,
                }
                for dr in control.draws[:100]
                for t in dr.trades[:1]
            ],
        },
    }
