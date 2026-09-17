"""The Gate C acceptance demonstration must stay honest and offline."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "acquisition_report.py"
FIXTURES = Path(__file__).parent / "fixtures"
QUESTION = "source supported exit rules for RSI mean reversion on ETFs"


def _module():
    spec = importlib.util.spec_from_file_location("acquisition_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_demonstration_finds_at_least_one_credible_candidate():
    report = _module().build_report(FIXTURES, QUESTION, 5)
    checks = report["gate_c_checks"]

    assert checks["at_least_one_credible_candidate"]
    assert set(checks["promotable_tiers_found"]) & {"primary", "practitioner"}


def test_every_gate_c_check_passes_on_the_recorded_bundle():
    report = _module().build_report(FIXTURES, QUESTION, 5)
    failed = [
        name
        for name, value in report["gate_c_checks"].items()
        if isinstance(value, bool) and not value
    ]
    assert failed == []


def test_acquisition_report_emits_a_traceable_record_for_every_accepted_source():
    report = _module().build_report(FIXTURES, QUESTION, 5)

    assert report["accepted"]
    for record in report["accepted"]:
        assert record["url"]
        assert record["tier"] in {"primary", "practitioner", "discovery-only"}
        assert record["reason"]
        assert record["snapshot"].startswith("brain/00_Inbox/Source_Snapshots/")
        assert record["snapshot_exists"]
        assert len(record["content_hash"]) == 64
        assert record["captured_at"]


def test_every_rejected_candidate_names_the_stage_that_rejected_it():
    report = _module().build_report(FIXTURES, QUESTION, 5)

    assert report["rejected"]
    for record in report["rejected"]:
        assert record["stage"] in {"ranking", "content-assessment"}
        assert record["reason"]


def test_the_demonstration_respects_a_narrowed_source_cap():
    report = _module().build_report(FIXTURES, QUESTION, 2)

    assert len(report["accepted"]) <= 2
    assert report["gate_c_checks"]["within_source_cap"]


def test_the_demonstration_writes_nothing_into_the_project_tree():
    """It snapshots to a scratch directory; a demo is not a run."""
    project_root = SCRIPT.parents[1]
    snapshots = project_root / "brain" / "00_Inbox" / "Source_Snapshots"
    before = {p.name for p in snapshots.rglob("*.md")} if snapshots.exists() else set()

    _module().build_report(FIXTURES, QUESTION, 5)

    after = {p.name for p in snapshots.rglob("*.md")} if snapshots.exists() else set()
    assert before == after


def test_the_demonstration_performs_no_network_access():
    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("urlopen", "requests.", "socket", "httpx"):
        assert forbidden not in source
