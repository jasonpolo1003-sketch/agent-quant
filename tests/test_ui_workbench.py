"""Workbench page data."""

from __future__ import annotations

import json

import pytest

from quant_brain.ui import workbench_view
from quant_brain.workbench import engine


def test_listing_joins_ledger_and_results(tmp_path):
    ledger = tmp_path / engine.LEDGER
    ledger.parent.mkdir(parents=True)
    rows = [
        {
            "at": "2026-10-26T10:00:00",
            "fingerprint": "aaa1",
            "family": "orb",
            "settings": {},
            "market": "MNQ",
            "roll": "fixed",
        },
        {
            "at": "2026-10-26T11:00:00",
            "fingerprint": "bbb2",
            "family": "orb",
            "settings": {"range_bars": 30},
            "market": "MNQ",
            "roll": "fixed",
        },
    ]
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    results = tmp_path / workbench_view.RESULTS
    results.mkdir(parents=True)
    (results / "aaa1.json").write_text(
        json.dumps({"verdict": {"outcome": "not_demonstrated", "per_day": 3.1, "alpha": 0.0253}}),
        encoding="utf-8",
    )
    d = workbench_view.listing(tmp_path)
    assert [t["id"] for t in d["trials"]] == ["bbb2", "aaa1"]
    assert d["trials"][1]["outcome"] == "not_demonstrated" and d["trials"][0]["outcome"] is None
    assert d["honesty"][0]["trials"] == 2 and d["honesty"][0]["alpha"] < 0.05
    assert workbench_view.result(tmp_path, "aaa1")["verdict"]["per_day"] == 3.1
    with pytest.raises(workbench_view.WorkbenchError):
        workbench_view.result(tmp_path, "../etc")
    with pytest.raises(workbench_view.WorkbenchError):
        workbench_view.result(tmp_path, "bbb2")


def test_saved_pass_is_rejudged_against_the_tightened_bar(tmp_path):
    ledger = tmp_path / engine.LEDGER
    ledger.parent.mkdir(parents=True)
    rows = [
        {
            "at": "2026-10-26T10:00:00",
            "fingerprint": f"r{i}",
            "family": "orb",
            "settings": {"i": i},
            "market": "MNQ",
            "roll": "fixed",
        }
        for i in range(5)
    ]
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    results = tmp_path / workbench_view.RESULTS
    results.mkdir(parents=True)
    saved = {
        "run": rows[0],
        "verdict": {
            "outcome": "pass_to_execution_calibration",
            "p_value": 0.03,
            "alpha": 0.05,
            "reasons": [],
        },
    }
    (results / "r0.json").write_text(json.dumps(saved), encoding="utf-8")
    v = workbench_view.result(tmp_path, "r0")["verdict"]
    assert v["outcome"] == "not_demonstrated" and v["alpha"] < 0.011
    assert "tightened" in v["reasons"][-1]
