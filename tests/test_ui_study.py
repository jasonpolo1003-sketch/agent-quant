"""Study page backend: trail, luck band/histogram, day list, locked-date refusal."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from quant_brain.futures import runner
from quant_brain.ui import study


@pytest.fixture
def root(tmp_path):
    out = tmp_path / runner.REPORTS / "development"
    out.mkdir(parents=True)
    rows = [
        ("2020-01-02", "traded", 1000, 0.0),
        ("2020-01-03", "non_evaluable", 99999, 0.0),
        ("2020-01-06", "no_trade", 0, 0.0),
        ("2020-01-07", "traded", -500, -250.0),
    ]
    lines = ["trade_date,root,status,orb_cents,orb_stress_cents,orb_trades,control_cents"]
    lines += [f"{d},MNQ,{s},{o},{o},{1 if s == 'traded' else 0},{c}" for d, s, o, c in rows]
    (out / "MNQ.development.daily.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    draws = np.zeros((4, 500), dtype=np.int64)
    draws[0] = np.arange(500) - 250  # day 1: random entries spread -$2.50..+$2.49
    draws[3] = -250
    np.save(out / "MNQ.development.draws.npy", draws)
    (out / "report.json").write_text(
        json.dumps({"MNQ/development": {"verdict": {}}}), encoding="utf-8"
    )
    (tmp_path / runner.LEDGER).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / runner.LEDGER).write_text(
        "\n".join(
            json.dumps(e)
            for e in [
                {"event": "frozen", "at": "2026-10-26T10:00:00", "spec_sha256": "abc"},
                {"event": "development_authorized", "at": "2026-10-26T11:00:00"},
                {
                    "event": "development_completed",
                    "at": "2026-10-26T12:00:00",
                    "code_commit": "c0ffee",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_trail_marks_done_and_locked_stages(root):
    stages = {s["stage"]: s["done"] for s in study.trail(root)}
    assert stages == {
        "frozen": True,
        "development_authorized": True,
        "development_completed": True,
        "held_out_authorized": False,
        "held_out_completed": False,
    }


def test_series_excludes_non_evaluable_and_builds_band(root):
    s = study.series(root, "development", "MNQ.development")
    assert s["dates"] == ["2020-01-02", "2020-01-06", "2020-01-07"]
    assert s["orb"] == [10.0, 10.0, 5.0] and s["control_mean"] == [0.0, 0.0, -2.5]
    assert s["skipped_non_evaluable"] == 1
    assert s["band_low"][0] < 0 < s["band_high"][0]
    h = s["histogram"]
    assert sum(h["counts"]) == 500 and h["orb_total"] == 5.0 and h["share_of_draws_beaten"] == 1.0


def test_day_list_reports_vs_luck(root):
    days = study.day_list(root, "development", "MNQ.development")
    assert days[3] == {
        "date": "2020-01-07",
        "status": "traded",
        "orb": -5.0,
        "vs_luck": -2.5,
        "trades": 1,
    }


def test_replay_refuses_locked_period_and_bad_dates(root):
    with pytest.raises(study.StudyError, match="locked"):
        study.replay(root, "MNQ", "2025-03-03")
    with pytest.raises(study.StudyError, match="YYYY-MM-DD"):
        study.replay(root, "MNQ", "yesterday")


REPO = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not study.DEV_DIR.exists(), reason="dev partition not on this machine")
def test_replay_of_a_real_dev_day_matches_the_engine():
    r = study.replay(REPO, "MNQ", "2022-06-15")
    assert r["candles"] and r["range"]["high"] >= r["range"]["low"]
    assert r["candles"][0]["time"] % 60 == 0
    assert all(t["entry_time"] >= r["range"]["end"] for t in r["trades"])
