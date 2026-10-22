"""Run dependency-free JavaScript behavior tests through Node's built-in test runner."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_ui_state_javascript_contracts():
    result = subprocess.run(
        ["node", "--test", "tests/js/test_ui_state.cjs"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
