"""Exam proctor (W8): the only way to the locked 2025-01-01..2026-10-21 data.

A check takes one frozen, hash-pinned question about one frozen strategy and answers
only PASS or FAIL. Nothing else about the exam period is printed or stored: no
per-day numbers, no p-value, no charts. The budget is 3 checks for the whole exam,
each with a stricter bar (one-sided alpha 0.05, 0.025, 0.0125), and the bar carries a
little Laplace noise (on the log scale, seeded by the question's hash) so repeated
near-threshold questions leak less (Dwork et al., Science 2015, "the reusable
holdout"). Every check needs Jason's approval and is appended to an append-only
ledger; a question can be asked once.

The test is the workbench's own: strategy net (L3 by default) vs the matched random
control on the exam days, stationary-bootstrap paired test (`inference.paired_test`).
PASS needs p below the noisy bar AND a positive mean net per day.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

from quant_brain.futures import inference
from quant_brain.workbench import analysis, engine
from quant_brain.workbench.strategies import REGISTRY, Strategy, make

BUDGET = 3
ALPHAS = (0.05, 0.025, 0.0125)
NOISE_SCALE = 0.1  # Laplace scale on log(alpha): the bar moves by ~10%
EXAM = (date(2025, 1, 1), date(2026, 10, 21))
LEDGER = "brain/_system/proctor/checks.jsonl"

Statistic = Callable[[dict, engine.Loader], tuple[float, float]]


def checks_used(root: Path) -> list[dict]:
    path = root / LEDGER
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def bar(k: int, question_sha: str) -> float:
    """The noisy one-sided alpha for check number k (0-based)."""
    rng = np.random.default_rng(int(question_sha[:16], 16))
    return float(ALPHAS[k] * np.exp(rng.laplace(0.0, NOISE_SCALE)))


def build(family: str, settings: dict) -> Strategy:
    """The strategy from its constructor arguments; it must report exactly `settings` back."""
    params = inspect.signature(REGISTRY[family]).parameters
    strategy = make(family, {k: v for k, v in settings.items() if k in params})
    if strategy.settings() != settings:
        raise SystemExit(f"{family} does not reproduce the frozen settings {settings}")
    return strategy


def exam_statistic(q: dict, loader: engine.Loader) -> tuple[float, float]:
    """(p-value, mean net $/day) of the question's strategy on the exam days. Never shown."""
    strategy = build(q["family"], q["settings"])
    warmup = date.fromisoformat(q["warmup_start"])
    days = loader(q["market"], warmup, EXAM[1], engine.ROLLS[q["roll"]])
    table = engine.simulate(strategy, days)
    dates = np.array([date.fromisoformat(d) for d in table.dates])
    keep = (dates >= EXAM[0]) & (dates <= EXAM[1]) & table.evaluable
    if keep.sum() < 2:
        raise RuntimeError("no evaluable exam days")
    orb, draws = analysis._nets(table, q["market"], q.get("cost_level", "L3"))
    test = inference.paired_test(orb[keep], draws[keep].mean(axis=1))
    return float(test["p_value"]), float(orb[keep].mean() / 100)


def check(
    root: Path,
    question_path: Path,
    loader: engine.Loader,
    *,
    approved_by: str,
    statistic: Statistic = exam_statistic,
) -> bool:
    """Answer one frozen question PASS (True) or FAIL (False); spends one check."""
    raw = question_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    pin = question_path.with_suffix(".sha256")
    if not pin.exists() or pin.read_text(encoding="utf-8").split()[0] != sha:
        raise SystemExit("question does not match its pinned hash; refusing")
    if not approved_by.strip():
        raise SystemExit("every exam check needs Jason's approval")
    used = checks_used(root)
    if len(used) >= BUDGET:
        raise SystemExit(f"exam budget spent ({BUDGET} checks); refusing")
    if any(u["question_sha256"] == sha for u in used):
        raise SystemExit("this question was already asked; refusing")
    q = json.loads(raw)
    if (q.get("exam_start"), q.get("exam_end")) != tuple(d.isoformat() for d in EXAM):
        raise SystemExit("question must name the whole exam period")
    k = len(used)
    p, mean = statistic(q, loader)
    passed = bool(p < bar(k, sha) and mean > 0)
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as h:
        h.write(
            json.dumps(
                {
                    "at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "check": k + 1,
                    "question": question_path.relative_to(root).as_posix()
                    if question_path.is_relative_to(root)
                    else question_path.name,
                    "question_sha256": sha,
                    "approved_by": approved_by,
                    "result": "PASS" if passed else "FAIL",
                }
            )
            + "\n"
        )
    return passed
