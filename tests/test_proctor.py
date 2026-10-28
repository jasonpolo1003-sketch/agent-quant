"""W8 exam proctor: budget, one bit per check, frozen questions only."""

from __future__ import annotations

import hashlib
import json

import pytest

from quant_brain.workbench import proctor


def _question(tmp_path, name="q1", **extra):
    q = {"exam_start": "2025-01-01", "exam_end": "2026-10-21"} | extra
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(q), encoding="utf-8")
    path.with_suffix(".sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + "\n", encoding="utf-8"
    )
    return path


def _stat(p, mean):
    return lambda q, loader: (p, mean)


def test_answers_one_bit_and_logs_no_numbers(tmp_path):
    q = _question(tmp_path)
    assert proctor.check(tmp_path, q, None, approved_by="J", statistic=_stat(0.001, 5.0)) is True
    (entry,) = proctor.checks_used(tmp_path)
    assert entry["result"] == "PASS" and entry["check"] == 1
    assert not {"p_value", "mean", "per_day"} & set(entry)


def test_needs_a_positive_mean_and_a_small_p(tmp_path):
    a, b = _question(tmp_path, "a", x=1), _question(tmp_path, "b", x=2)
    assert proctor.check(tmp_path, a, None, approved_by="J", statistic=_stat(0.001, -1.0)) is False
    assert proctor.check(tmp_path, b, None, approved_by="J", statistic=_stat(0.9, 5.0)) is False


def test_budget_repeats_hash_and_approval_are_enforced(tmp_path):
    qs = [_question(tmp_path, f"q{i}", i=i) for i in range(4)]
    with pytest.raises(SystemExit, match="approval"):
        proctor.check(tmp_path, qs[0], None, approved_by=" ", statistic=_stat(0.5, 1))
    proctor.check(tmp_path, qs[0], None, approved_by="J", statistic=_stat(0.5, 1))
    with pytest.raises(SystemExit, match="already asked"):
        proctor.check(tmp_path, qs[0], None, approved_by="J", statistic=_stat(0.5, 1))
    proctor.check(tmp_path, qs[1], None, approved_by="J", statistic=_stat(0.5, 1))
    proctor.check(tmp_path, qs[2], None, approved_by="J", statistic=_stat(0.5, 1))
    with pytest.raises(SystemExit, match="budget"):
        proctor.check(tmp_path, qs[3], None, approved_by="J", statistic=_stat(0.5, 1))
    qs[3].write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="pinned hash"):
        proctor.check(tmp_path, qs[3], None, approved_by="J", statistic=_stat(0.5, 1))


def test_question_must_cover_the_whole_exam(tmp_path):
    q = _question(tmp_path, exam_start="2025-06-01")
    with pytest.raises(SystemExit, match="whole exam"):
        proctor.check(tmp_path, q, None, approved_by="J", statistic=_stat(0.001, 1))


def test_bars_tighten_and_the_noise_is_small_and_fixed_per_question():
    sha = "ab" * 32
    bars = [proctor.bar(k, sha) for k in range(3)]
    assert bars == sorted(bars, reverse=True)
    assert proctor.bar(0, sha) == proctor.bar(0, sha)
    for k, b in enumerate(bars):
        assert 0.5 * proctor.ALPHAS[k] < b < 2 * proctor.ALPHAS[k]
