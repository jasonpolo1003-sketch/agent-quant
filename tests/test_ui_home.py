"""Home page: plain answers derived from the ledger and the curated needs-you list."""

from __future__ import annotations

import json

import pytest

from quant_brain.futures import runner
from quant_brain.ui import home


def _ledger(root, *events):
    path = root / runner.LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps({"event": e, "at": "2026-10-26T12:00:00"}) + "\n" for e in events),
        encoding="utf-8",
    )


@pytest.fixture
def root(tmp_path):
    out = tmp_path / runner.REPORTS / "development"
    out.mkdir(parents=True)
    verdict = {
        "outcome": "not_demonstrated",
        "absolute_mean_cents": 311.0,
        "observed_paired_cents": 528.0,
        "p_value": 0.1142,
    }
    (out / "report.json").write_text(
        json.dumps({"MNQ/development": {"verdict": verdict}}), encoding="utf-8"
    )
    return tmp_path


def test_final_exam_decision_appears_after_practice_and_clears_when_closed(root):
    _ledger(root, "frozen", "development_authorized", "development_completed")
    assert [n["id"] for n in home.needs_you(root)] == ["sc-fut-0001-final-exam"]
    assert "close the card" in home.where_we_are(root)["next"]
    _ledger(root, "frozen", "development_authorized", "development_completed", "card_closed")
    assert home.needs_you(root) == []
    assert home.where_we_are(root)["now"].startswith("Closed")


def test_curated_needs_are_listed_and_done_items_hidden(root):
    _ledger(root, "frozen")
    (root / home.NEEDS_YOU).parent.mkdir(parents=True, exist_ok=True)
    (root / home.NEEDS_YOU).write_text(
        json.dumps([{"id": "a", "title": "A"}, {"id": "b", "title": "B", "done": True}]),
        encoding="utf-8",
    )
    assert [n["id"] for n in home.needs_you(root)] == ["a"]
    (root / home.NEEDS_YOU).write_text("{broken", encoding="utf-8")
    assert "unreadable" in home.needs_you(root)[0]["title"]


def test_learned_states_the_result_in_plain_words(root):
    first = home.learned(root)[0]
    assert first["id"] == "SC-FUT-0001" and first["outcome"] == "not_demonstrated"
    assert "$3.11 a day" in first["plain"] and "below the $15 goal" in first["plain"]
    assert "could not be told apart from luck" in first["plain"]


def test_home_bundles_all_three_answers(root):
    _ledger(root, "frozen")
    assert set(home.home(root)) == {"where", "needs", "learned"}
