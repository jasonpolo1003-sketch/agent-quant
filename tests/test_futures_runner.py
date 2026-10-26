"""SC-FUT-0001 runner gates in a throwaway git repo (synthetic days only)."""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest
from futures_day_builder import random_day

from quant_brain.futures import runner


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    dev, raw = tmp_path / "dev", tmp_path / "raw"
    for d in (dev, raw):
        d.mkdir()
    (dev / "manifest.json").write_text('{"status": "development_only_partition"}', encoding="utf-8")
    (raw / runner.RAW_BARS).write_bytes(b"synthetic")
    (raw / "SHA256SUMS").write_text(
        f"{_sha(raw / runner.RAW_BARS)}  {runner.RAW_BARS}\n", encoding="utf-8"
    )
    for rel in (
        "src/quant_brain/x.py",
        "scripts/run_sc_fut_0001.py",
        "pyproject.toml",
        "uv.lock",
        runner.CALENDAR,
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x\n", encoding="utf-8")
    spec = {
        "data_partitions": {
            "source_data_manifest_sha256": _sha(dev / "manifest.json"),
            "raw_download_sha256sums_sha256": _sha(raw / "SHA256SUMS"),
        },
        "provenance": {"dependency_lock_sha256": _sha(root / "uv.lock")},
    }
    (root / runner.SPEC).parent.mkdir(parents=True, exist_ok=True)
    (root / runner.SPEC).write_text(json.dumps(spec), encoding="utf-8")
    (root / runner.LEDGER).parent.mkdir(parents=True, exist_ok=True)
    (root / runner.LEDGER).write_text(
        json.dumps({"event": "frozen", "spec_sha256": _sha(root / runner.SPEC)}) + "\n",
        encoding="utf-8",
    )
    _git(root.parent, "init", "-q", str(root))
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
    return root, dev, raw


def synthetic_loader(root_name, start, end):
    rng = random.Random(f"{root_name}{start}")
    days = []
    for i in range(25):
        day = random_day(rng)
        days.append(
            type(day)(
                start + timedelta(days=i), root_name, day.bars, day.exit_minute, day.stop_ticks
            )
        )
    return days


def events(root):
    return [e["event"] for e in runner.read_ledger(root)]


def test_development_refused_without_authorization(repo):
    root, dev, _ = repo
    with pytest.raises(runner.GateError, match="development_authorized"):
        runner.run(root, "development", dev, synthetic_loader, replicates=99)


def test_only_jason_can_authorize(repo):
    root, _, _ = repo
    with pytest.raises(runner.GateError):
        runner.authorize(root, "development_authorized", "Claude")
    with pytest.raises(runner.GateError):
        runner.authorize(root, "held_out_started", "Jason")


def test_authorized_development_run_records_completion(repo):
    root, dev, _ = repo
    runner.authorize(root, "development_authorized", "Jason")
    event = runner.run(root, "development", dev, synthetic_loader, replicates=99)
    assert event["event"] == "development_completed" and event["outcome"] in {
        "pass_to_execution_calibration",
        "not_demonstrated",
        "inconclusive",
    }
    report = json.loads((root / runner.REPORTS / "development" / "report.json").read_text())
    assert {"MNQ/development", "MNQ/diagnostics", "MES/development", "MES/diagnostics"} == set(
        report
    )
    assert "power" in report["MNQ/development"]


def test_spec_edit_and_dirty_code_are_refused(repo):
    root, dev, _ = repo
    runner.authorize(root, "development_authorized", "Jason")
    (root / "src/quant_brain/x.py").write_text("changed\n", encoding="utf-8")
    with pytest.raises(runner.GateError, match="committed and clean"):
        runner.run(root, "development", dev, synthetic_loader, replicates=99)
    (root / "uv.lock").write_text("other\n", encoding="utf-8")
    assert any("dependency lock" in p for p in runner.gate_problems(root, "development", dev))
    (root / runner.SPEC).write_text("{}", encoding="utf-8")
    problems = runner.gate_problems(root, "development", dev)
    assert any("freeze hash" in p for p in problems) and any("unreadable" in p for p in problems)


def _fake_dev_completion(root, power=0.9, review=False):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    ).stdout.strip()
    runner.append_event(
        root,
        {
            "event": "development_completed",
            "code_commit": commit,
            "power": {"joint_power": power},
            "review_required": review,
        },
    )


def test_held_out_needs_its_own_authorization_and_runs_once(repo):
    root, _, raw = repo
    runner.authorize(root, "development_authorized", "Jason")
    _fake_dev_completion(root)
    assert any("held_out_authorized" in p for p in runner.gate_problems(root, "held_out", raw))
    runner.authorize(root, "held_out_authorized", "Jason")
    runner.run(root, "held_out", raw, synthetic_loader, replicates=99)
    assert events(root)[-2:] == ["held_out_started", "held_out_completed"]
    with pytest.raises(runner.GateError, match="already read once"):
        runner.run(root, "held_out", raw, synthetic_loader, replicates=99)


def test_held_out_crash_is_recorded_and_still_counts_as_read(repo):
    root, _, raw = repo
    runner.authorize(root, "development_authorized", "Jason")
    _fake_dev_completion(root)
    runner.authorize(root, "held_out_authorized", "Jason")

    def broken(*_):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        runner.run(root, "held_out", raw, broken, replicates=99)
    assert events(root)[-2:] == ["held_out_started", "held_out_failed"]
    assert any("already read once" in p for p in runner.gate_problems(root, "held_out", raw))


def test_held_out_refused_on_low_power_review_or_code_change(repo):
    root, _, raw = repo
    runner.authorize(root, "development_authorized", "Jason")
    _fake_dev_completion(root, power=0.5, review=True)
    runner.authorize(root, "held_out_authorized", "Jason")
    problems = runner.gate_problems(root, "held_out", raw)
    assert any("power below 80%" in p for p in problems)
    assert any("ambiguity review" in p for p in problems)
    (root / "src/quant_brain/x.py").write_text("v2\n", encoding="utf-8")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "change")
    assert any("code changed" in p for p in runner.gate_problems(root, "held_out", raw))


def test_tampered_raw_file_is_refused(repo):
    root, _, raw = repo
    (raw / runner.RAW_BARS).write_bytes(b"tampered")
    runner.authorize(root, "development_authorized", "Jason")
    _fake_dev_completion(root)
    assert any(
        "does not match its checksum" in p for p in runner.gate_problems(root, "held_out", raw)
    )


def test_dates_cover_frozen_partitions():
    assert runner.PERIODS["held_out"] == (date(2025, 1, 1), date(2026, 10, 21))
    assert runner.PERIODS["development"][1] < runner.PERIODS["diagnostics"][0]
