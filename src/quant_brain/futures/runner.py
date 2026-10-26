"""Gated SC-FUT-0001 runner: authorizations, once-only held-out read, ledger, reports.

Gates (frozen spec `execution_gates`):
- development: spec bytes match the ledger's freeze hash, code is committed and
  clean, the dev partition matches its pinned manifest, and a
  `development_authorized` event by Jason follows the latest freeze event.
- held-out: all of the above, a completed development run with joint power
  >= 80% and any ambiguity review cleared, code unchanged since that run, the
  raw download matching its pinned checksums, a separate `held_out_authorized`
  event, and no earlier `held_out_started`. The marker is written before any
  data is read; a crash records `held_out_failed`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from quant_brain.futures import inference
from quant_brain.futures.controls import daily_control
from quant_brain.futures.orb import L3_ROUND_TRIP_CENTS, DayInput, simulate_day

CARD_ID = "SC-FUT-0001"
SPEC = "brain/_system/futures/sc-fut-0001-spec.v1.json"
LEDGER = "brain/04_Backtest_Reports/SC-FUT-0001.trials.jsonl"
REPORTS = "brain/04_Backtest_Reports/SC-FUT-0001"
CALENDAR = "brain/_system/futures/session-calendar.v1.csv"
ROLL_CSV = "brain/sources/mes_mnq/contracts/roll_calendar_2019_2026.csv"
CODE_PATHS = (
    "src/quant_brain",
    "scripts/run_sc_fut_0001.py",
    "pyproject.toml",
    "uv.lock",
    SPEC,
    CALENDAR,
)
DEV_BARS = "glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-dev.dbn.zst"
RAW_BARS = "glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-20261022.dbn.zst"
FREEZE_EVENTS = {"frozen", "freeze_provenance_corrected"}
PERIODS = {
    "development": (date(2019, 5, 1), date(2023, 12, 31)),
    "diagnostics": (date(2024, 1, 1), date(2024, 12, 31)),
    "held_out": (date(2025, 1, 1), date(2026, 10, 21)),
}
COST_LADDER_CENTS = {
    "L1": {"MNQ": 172, "MES": 247},
    "L2": {"MNQ": 222, "MES": 372},
    "L3": {"MNQ": 322, "MES": 622},
    "L4": {"MNQ": 522, "MES": 1122},
}
ROOTS = ("MNQ", "MES")

Loader = Callable[[str, date, date], list[DayInput]]


class GateError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_ledger(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def append_event(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    record = {"at": _now(), "card_id": CARD_ID, **record}
    with (root / LEDGER).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _last_index(events: list[dict], names: set[str]) -> int:
    hits = [i for i, e in enumerate(events) if e["event"] in names]
    return hits[-1] if hits else -1


def frozen_spec_hash(events: list[dict]) -> str | None:
    i = _last_index(events, FREEZE_EVENTS)
    return events[i]["spec_sha256"] if i >= 0 else None


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


def code_commit(root: Path) -> str | None:
    """HEAD if the gated code paths are committed and clean, else None."""
    if _git(root, "status", "--porcelain", "--", *CODE_PATHS).strip():
        return None
    return _git(root, "rev-parse", "HEAD").strip()


def code_unchanged_since(root: Path, commit: str) -> bool:
    return not _git(root, "diff", "--name-only", commit, "HEAD", "--", *CODE_PATHS).strip()


def _spec(root: Path) -> dict[str, Any]:
    return json.loads((root / SPEC).read_text(encoding="utf-8"))


def gate_problems(root: Path, phase: str, data_dir: Path) -> list[str]:
    events = read_ledger(root)
    problems: list[str] = []
    frozen = frozen_spec_hash(events)
    if frozen is None or sha256(root / SPEC) != frozen:
        problems.append("spec bytes do not match the ledger freeze hash")
    if code_commit(root) is None:
        problems.append("gated code paths are not committed and clean")
    freeze_at = _last_index(events, FREEZE_EVENTS)
    if _last_index(events, {"development_authorized"}) < freeze_at or freeze_at < 0:
        problems.append("no development_authorized event after the latest freeze")
    try:
        spec = _spec(root)
        spec["data_partitions"]["source_data_manifest_sha256"]
        spec["data_partitions"]["raw_download_sha256sums_sha256"]
        locked = spec["provenance"]["dependency_lock_sha256"]
    except (OSError, ValueError, KeyError, TypeError):
        return [*problems, "spec unreadable or missing pinned hashes"]
    if sha256(root / "uv.lock") != locked:
        problems.append("uv.lock differs from the frozen dependency lock")
    if phase == "development":
        manifest = data_dir / "manifest.json"
        if (
            not manifest.exists()
            or sha256(manifest) != spec["data_partitions"]["source_data_manifest_sha256"]
        ):
            problems.append("dev partition manifest does not match the frozen spec")
            return problems
        listed = json.loads(manifest.read_text(encoding="utf-8")).get("ohlcv", [])
        expected = next((r["output_sha256"] for r in listed if r.get("output") == DEV_BARS), None)
        bars = data_dir / DEV_BARS
        if expected is None or not bars.exists() or sha256(bars) != expected:
            problems.append("dev minute-bar file does not match the partition manifest")
        return problems

    dev_done = _last_index(events, {"development_completed"})
    if dev_done < 0:
        return [*problems, "no completed development run"]
    dev = events[dev_done]
    if not code_unchanged_since(root, dev["code_commit"]):
        problems.append("code changed since the development run")
    if dev.get("power", {}).get("joint_power", 0.0) < inference.POWER_TARGET:
        problems.append("development power below 80%: extend prospectively or record inconclusive")
    if dev.get("review_required") and _last_index(events, {"ambiguity_review_cleared"}) < dev_done:
        problems.append("same-bar ambiguity review not cleared")
    if _last_index(events, {"held_out_authorized"}) < dev_done:
        problems.append("no held_out_authorized event after the development run")
    if _last_index(events, {"held_out_started"}) >= 0:
        problems.append("held-out already read once")
    sums = data_dir / "SHA256SUMS"
    if (
        not sums.exists()
        or sha256(sums) != spec["data_partitions"]["raw_download_sha256sums_sha256"]
    ):
        problems.append("raw download checksums file does not match the frozen spec")
    else:
        recorded = {}
        for line in sums.read_text(encoding="utf-8").splitlines():
            if line.strip():
                digest, name = line.split(maxsplit=1)
                recorded[name.strip().lstrip("*")] = digest
        if sha256(data_dir / RAW_BARS) != recorded.get(RAW_BARS):
            problems.append("raw minute-bar file does not match its checksum")
    return problems


def authorize(root: Path, event: str, by: str) -> dict[str, Any]:
    allowed = {"development_authorized", "held_out_authorized", "ambiguity_review_cleared"}
    if event not in allowed:
        raise GateError(f"unknown authorization {event}")
    if by != "Jason":
        raise GateError("only Jason can authorize")
    return append_event(root, {"event": event, "by": by, "spec_sha256": sha256(root / SPEC)})


def _records(days: list[DayInput]) -> tuple[list[inference.DayRecord], list[dict], list[dict]]:
    records, daily, trades = [], [], []
    for day in days:
        result = simulate_day(day)
        if result.status == "ineligible":
            continue
        control = daily_control(day, len(result.trades) if result.status == "traded" else 0)
        record = inference.day_record(result, control)
        records.append(record)
        avg_control_trades = (
            float(np.mean([len(d.trades) for d in control.draws if d.evaluable]))
            if control.evaluable_draws
            else 0.0
        )
        daily.append(
            {
                "trade_date": day.trade_date.isoformat(),
                "root": day.root,
                "status": record.status,
                "orb_cents": result.net_cents,
                "orb_stress_cents": result.stress_net_cents,
                "orb_trades": len(result.trades),
                "control_cents": control.mean_cents,
                "control_stress_cents": control.stress_mean_cents,
                "control_avg_trades": avg_control_trades,
                "control_rejections": control.rejections,
                "control_not_taken": control.not_taken,
                "control_non_evaluable": control.non_evaluable_draws,
                "stop_ticks": day.stop_ticks,
            }
        )
        trades += [
            {"trade_date": day.trade_date.isoformat(), "root": day.root, **asdict(t)}
            for t in result.trades
        ]
    return records, daily, trades


def _diagnostics(records, daily, root_name: str) -> dict[str, Any]:
    good = [(r, d) for r, d in zip(records, daily, strict=True) if r.status in inference.EVALUABLE]
    if len(good) < 2:
        return {}
    orb = np.array([r.orb_cents for r, _ in good], dtype=float)
    ctl = np.array([r.control_cents for r, _ in good], dtype=float)
    orb_trades = np.array([d["orb_trades"] for _, d in good], dtype=float)
    ctl_trades = np.array([d["control_avg_trades"] for _, d in good], dtype=float)
    l3 = L3_ROUND_TRIP_CENTS[root_name]
    ladder = {}
    for level, costs in COST_LADDER_CENTS.items():
        shift = l3 - costs[root_name]
        a = orb + shift * orb_trades
        ladder[level] = {
            "absolute_mean_cents": float(a.mean()),
            "paired_mean_cents": float((a - ctl - shift * ctl_trades).mean()),
        }
    years: dict[str, dict] = {}
    for (r, d), o, c in zip(good, orb, ctl, strict=True):
        y = years.setdefault(d["trade_date"][:4], {"days": 0, "orb": 0.0, "paired": 0.0})
        y["days"] += 1
        y["orb"] += o
        y["paired"] += o - c
    by_year = {
        k: {
            "days": v["days"],
            "absolute_mean_cents": v["orb"] / v["days"],
            "paired_mean_cents": v["paired"] / v["days"],
        }
        for k, v in sorted(years.items())
    }
    top = np.sort(orb - ctl)[::-1]
    return {
        "cost_ladder": ladder,
        "by_year": by_year,
        "top_5pct_days_share_of_paired_total": float(
            top[: max(1, len(top) // 20)].sum() / top.sum()
        )
        if top.sum()
        else None,
        "politis_white_block_length": inference.politis_white_block_length(orb - ctl),
        "dsr": inference.dsr_diagnostic([r for r, _ in good]),
    }


def _write_outputs(out: Path, name: str, daily: list[dict], trades: list[dict]) -> dict[str, str]:
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for label, rows in (("daily", daily), ("trades", trades)):
        path = out / f"{name}.{label}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        hashes[path.name] = sha256(path)
    return hashes


def run(
    root: Path,
    phase: str,
    data_dir: Path,
    load: Loader,
    *,
    replicates: int = inference.BOOTSTRAP_DRAWS,
) -> dict[str, Any]:
    if phase not in ("development", "held_out"):
        raise GateError(f"unknown phase {phase}")
    problems = gate_problems(root, phase, data_dir)
    if problems:
        raise GateError("; ".join(problems))
    commit = code_commit(root)
    spec_hash = sha256(root / SPEC)
    base = {"code_commit": commit, "spec_sha256": spec_hash, "data_dir": str(data_dir)}
    if phase == "held_out":
        append_event(root, {"event": "held_out_started", **base})
    try:
        summary = _execute(root, phase, load, replicates)
    except BaseException as exc:
        if phase == "held_out":
            append_event(root, {"event": "held_out_failed", "error": repr(exc), **base})
        raise
    return append_event(root, {"event": f"{phase}_completed", **base, **summary})


def _execute(root: Path, phase: str, load: Loader, replicates: int) -> dict[str, Any]:
    out = root / REPORTS / phase
    windows = ["development", "diagnostics"] if phase == "development" else ["held_out"]
    results: dict[str, Any] = {}
    outputs: dict[str, str] = {}
    for root_name in ROOTS:
        for window in windows:
            start, end = PERIODS[window]
            records, daily, trades = _records(load(root_name, start, end))
            v = inference.verdict(records, replicates=replicates)
            entry = {"verdict": asdict(v), "diagnostics": _diagnostics(records, daily, root_name)}
            if window == "development" and root_name == "MNQ":
                good = [r for r in records if r.status in inference.EVALUABLE]
                entry["power"] = inference.power_check(
                    [r.orb_cents for r in good],
                    [r.control_cents for r in good],
                    replicates=replicates,
                )
            results[f"{root_name}/{window}"] = entry
            outputs |= _write_outputs(out, f"{root_name}.{window}", daily, trades)
    primary_key = "MNQ/development" if phase == "development" else "MNQ/held_out"
    primary = results[primary_key]
    (out / "report.json").write_text(
        json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8"
    )
    outputs["report.json"] = sha256(out / "report.json")
    return {
        "primary": primary_key,
        "outcome": primary["verdict"]["outcome"],
        "power": primary.get("power", {}),
        "review_required": primary["verdict"]["review_required"],
        "outputs_sha256": outputs,
    }
