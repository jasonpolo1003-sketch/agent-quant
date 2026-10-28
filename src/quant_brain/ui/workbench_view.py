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


def _current(root: Path, r: dict[str, Any] | None, family: str) -> dict[str, Any]:
    """The saved verdict judged against the family's pass bar as it stands now.

    The bar only tightens as trials are added, so a saved pass can become a fail."""
    v = dict((r or {}).get("verdict", {}))
    if not v:
        return v
    alpha = analysis.honesty(root, family)["alpha"]
    if v.get("outcome") == "pass_to_execution_calibration" and (v.get("p_value") or 1) >= alpha:
        v["outcome"] = "not_demonstrated"
        v["reasons"] = [
            *v.get("reasons", []),
            "the pass bar tightened after more variations were tried",
        ]
    return v | {"alpha": alpha}


def listing(root: Path) -> dict[str, Any]:
    trials = []
    for e in reversed(engine.read_ledger(root)):
        r = _result(root, e["fingerprint"])
        v = _current(root, r, e["family"])
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
    family = (r.get("run") or {}).get("family") or next(
        (e["family"] for e in engine.read_ledger(root) if e["fingerprint"] == fingerprint), ""
    )
    return r | {"verdict": _current(root, r, family)}
