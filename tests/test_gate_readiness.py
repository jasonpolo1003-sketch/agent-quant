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
