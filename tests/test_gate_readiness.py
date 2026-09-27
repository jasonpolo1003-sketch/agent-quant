"""The question-specific readiness probe: can these lanes answer this question?"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gate_readiness.py"
FIXTURES = Path(__file__).parent / "fixtures"
DOCTOR_LIVE_JSON = (FIXTURES / "agent_reach_doctor_live.json").read_text(encoding="utf-8")


def _module():
    spec = importlib.util.spec_from_file_location("gate_readiness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _adapter(hit_urls: list[str]):
    from quant_brain.discovery.agent_reach import AgentReachAdapter

    healthy = json.loads(DOCTOR_LIVE_JSON)
    healthy["exa_search"]["status"] = "ok"

    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        if "doctor" in argv:
            return 0, json.dumps(healthy, ensure_ascii=False), ""
        rows = [{"url": url, "name": url} for url in hit_urls]
        return 0, json.dumps({"results": rows}), ""

    return AgentReachAdapter(runner=runner, skip_exe_check=True)


def test_gate_readiness_reports_not_ready_when_searches_return_too_few_sources():
    module = _module()
    result = module.probe(_adapter([]), "some question", "mean_reversion", min_sources=3)

    assert result["unique_urls"] == 0
    assert result["unique_urls"] < 3


def test_gate_readiness_reports_ready_when_the_minimum_is_met():
    """The probe must not be merely always-red."""
    module = _module()
    urls = [f"https://example.com/p{i}" for i in range(4)]
    result = module.probe(_adapter(urls), "some question", "mean_reversion", min_sources=3)

    assert result["unique_urls"] >= 3
    assert result["error"] is None


def test_the_probe_counts_distinct_urls_not_raw_hits():
    """Duplicates across channels must not inflate the count past the gate."""
    module = _module()
    dupes = ["https://example.com/a", "https://example.com/a/", "https://example.com/a"]
    result = module.probe(_adapter(dupes), "q", None, min_sources=3)

    assert result["unique_urls"] == 1


def test_the_phase_6_minimum_matches_the_phase_document():
    assert _module().PHASE_6_MIN_SOURCES == 3


# --- pre-registered candidate lists (PROP-004) ------------------------------


def _write_list(root: Path, research_id: str, urls: list[str]) -> str:
    from quant_brain.discovery.candidate_list import CANDIDATE_LIST_DIR

    (root / CANDIDATE_LIST_DIR).mkdir(parents=True, exist_ok=True)
    payload = {
        "research_id": research_id,
        "selection_rule": "rule",
        "screening_reference": "brain/00_Inbox/dossier.md",
        "registered_by": "test",
        "registered_on": "2026-09-26",
        "candidates": [
            {"url": url, "found_via": "dossier", "added_by": "test", "added_on": "2026-09-26"}
            for url in urls
        ],
    }
    relative = f"{CANDIDATE_LIST_DIR}/{research_id}.md"
    (root / relative).write_text(f"```json\n{json.dumps(payload)}\n```\n", encoding="utf-8")
    return relative


def test_a_candidate_list_check_counts_distinct_works_offline(tmp_path):
    module = _module()
    urls = [
        "https://doi.org/10.15405/epms.2022.10.4",
        "https://chartschool.stockcharts.com/rsi-2",
        "https://articles.stockcharts.com/hill",
    ]
    relative = _write_list(tmp_path, "RQ-1", urls)

    checked = module.check_candidate_list(tmp_path, relative, "RQ-1")

    assert checked["listed"] == 3
    assert checked["distinct_works"] == 3
    assert "doi:10.15405/epms.2022.10.4" in checked["works"]


def test_a_candidate_list_for_another_question_is_refused(tmp_path):
    import pytest

    from quant_brain.discovery.candidate_list import CandidateListError

    module = _module()
    relative = _write_list(tmp_path, "RQ-1", ["https://example.com/a"])

    with pytest.raises(CandidateListError, match="registered for RQ-1"):
        module.check_candidate_list(tmp_path, relative, "RQ-2")
