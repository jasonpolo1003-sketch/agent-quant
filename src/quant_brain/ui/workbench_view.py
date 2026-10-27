"""Workbench page data: every trial with its result, and each family's honesty counter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_brain.workbench import analysis, engine
from quant_brain.workbench.strategies import DESCRIPTIONS

RESULTS = f"{engine.WORKBENCH}/results"


class WorkbenchError(RuntimeError):
    pass


def _result(root: Path, fingerprint: str) -> dict[str, Any] | None:
    if not fingerprint.isalnum():
        raise WorkbenchError("bad run id")
    path = root / RESULTS / f"{fingerprint}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def listing(root: Path) -> dict[str, Any]:
    trials = []
    for e in reversed(engine.read_ledger(root)):
        r = _result(root, e["fingerprint"])
        v = (r or {}).get("verdict", {})
        trials.append(
            {
                "id": e["fingerprint"],
                "at": e["at"],
                "family": e["family"],
                "settings": e["settings"],
                "market": e["market"],
                "roll": e["roll"],
                "outcome": v.get("outcome"),
                "per_day": v.get("per_day"),
                "vs_random_per_day": v.get("vs_random_per_day"),
                "p_value": v.get("p_value"),
                "alpha": v.get("alpha"),
            }
        )
    families = sorted({t["family"] for t in trials})
    return {
        "trials": trials,
        "honesty": [
            analysis.honesty(root, f) | {"about": DESCRIPTIONS.get(f, "")} for f in families
        ],
        "how_to_run": 'uv run python scripts/workbench.py run --family orb --settings "{\\"range_bars\\": 30}" --market MNQ',
    }


def result(root: Path, fingerprint: str) -> dict[str, Any]:
    r = _result(root, fingerprint)
    if r is None:
        raise WorkbenchError("no saved result for that run")
    return r
