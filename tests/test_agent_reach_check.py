"""The lane-readiness diagnostic must report the real blocker, not crash on it."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "agent_reach_check.py"
FIXTURES = Path(__file__).parent / "fixtures"
DOCTOR_LIVE_JSON = (FIXTURES / "agent_reach_doctor_live.json").read_text(encoding="utf-8")


def _module():
    spec = importlib.util.spec_from_file_location("agent_reach_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lane_verdicts_reports_an_unconfigured_search_channel_as_not_usable():
    from quant_brain.discovery.agent_reach import parse_channel_health

    health = parse_channel_health(json.loads(DOCTOR_LIVE_JSON))
    rows = {row["lane"]: row for row in _module().lane_verdicts(health)}

    exa = rows["exa"]
    assert exa["channel"] == "exa_search"
    assert exa["usable_now"] is False
    assert "off" in exa["reason"]
    # GitHub is genuinely usable; the general health check must not call it
    # unhealthy merely because it suits these questions poorly.
    assert rows["github"]["usable_now"] is True


def test_the_diagnostic_does_not_crash_printing_a_non_ascii_reason():
    """A reason may be Chinese while the console is cp1252."""
    safe = _module()._console_safe("mcporter 已装但 Exa 未配置")
    assert isinstance(safe, str)
    assert "Exa" in safe


def test_doctor_failure_does_not_disable_the_independent_arxiv_lane(monkeypatch, capsys):
    from quant_brain.discovery.agent_reach import AgentReachUnavailable

    module = _module()

    class BrokenDoctor:
        def check_health(self):
            raise AgentReachUnavailable("doctor down")

    monkeypatch.setattr(module, "AgentReachAdapter", BrokenDoctor)

    assert module.main() == 0
    captured = capsys.readouterr()
    assert "arxiv" in captured.out
    assert "independent lanes remain available" in captured.err
