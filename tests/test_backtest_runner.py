"""The two-phase runner: gates, append-only ledger, one held-out read, verdict.

A synthetic project: three verified random-walk datasets and a test card built
from SC-0002's spec (same rules, pins pointed at the synthetic data), frozen
the real way. No network and no real results.
"""

import json
import shutil
import sqlite3
import subprocess
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from quant_brain.backtest import engine, reference
from quant_brain.backtest import run as rn
from quant_brain.config import PROJECT_ROOT
from quant_brain.data import market_data as md
from quant_brain.db.init_db import init_database
from quant_brain.strategy import card as sc

SC0002 = PROJECT_ROOT / "brain/03_Strategy_Cards/SC-0002-rsi2-connors-spy.md"


def synthetic_bars(seed, days=700):
    rng = np.random.default_rng(seed)
    closes = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.013, days)))
    opens = np.concatenate([[100.0], closes[:-1]]) * (1 + rng.normal(0, 0.002, days))
    return pd.DataFrame({
        "Date": pd.bdate_range("2000-01-03", periods=days).strftime("%Y-%m-%d"),
        "Open": opens, "High": np.maximum(opens, closes) * 1.003,
        "Low": np.minimum(opens, closes) * 0.997, "Close": closes, "Adj Close": closes,
        "Volume": 1_000_000, "Dividends": 0.0, "Stock Splits": 0.0,
    })


@pytest.fixture
def project(tmp_path, monkeypatch):
    db = tmp_path / "brain.sqlite"
    init_database(db)
    spec = sc.read_card(SC0002)
    pins = []
    for seed, symbol in enumerate(("SPY", "QQQ", "IWM")):
        manifest = md.ingest(tmp_path, db, symbol, synthetic_bars(seed), meta={
            "provider": "yfinance", "provider_version": "test", "requested_start": "2000-01-03",
            "requested_end": "2002-09-01"}, now=datetime(2026, 9, 29, tzinfo=UTC))
        pins.append({"symbol": symbol, "dataset_id": manifest["dataset_id"],
                     "content_sha256": manifest["content_sha256"]})
    last = pd.bdate_range("2000-01-03", periods=700)[-1].strftime("%Y-%m-%d")
    spec.update(card_id="SC-9001", supersedes=None, data=pins, periods={
        "in_sample": {"start": "2000-01-03", "end": "2001-06-29"},
        "held_out": {"start": "2001-07-02", "end": last}, "held_out_reads": 1})
    card = sc.StrategyCard.model_validate(spec)
    for relative in {q.snapshot for q in sc.all_quotes(card)}:
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, tmp_path / relative)
    card_path = tmp_path / "brain/03_Strategy_Cards/SC-9001.md"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(f"# test card\n\n```json\n{json.dumps(spec, indent=2)}\n```\n",
                         encoding="utf-8")
    sc.freeze_card(tmp_path, db, card_path)
    monkeypatch.setattr(rn, "code_commit", lambda root: "test-commit")
    # The synthetic project is not a git repository; the ledger-commit gate has its own test.
    monkeypatch.setattr(rn, "ledger_committed", lambda root, path: True)
    monkeypatch.setattr(rn, "code_unchanged_since", lambda root, commit: True)
    return tmp_path, db, card_path


def events(root, name):
    return [r for r in rn.read_ledger(root, "SC-9001") if r.get("event") == name]


def test_in_sample_runs_every_trial_cross_checks_and_stops(project):
    root, db, _ = project

    outcome = rn.run_in_sample(root, db, "SC-9001")

    ledger = rn.read_ledger(root, "SC-9001")
    rules = [r for r in ledger if r.get("kind") == "rule"]
    holds = [r for r in ledger if r.get("kind") == "buy_and_hold"]
    assert len(rules) == 27 and len(holds) == 9
    assert {r["phase"] for r in rules + holds} == {"in_sample"}
    assert all(r["code_commit"] == "test-commit" and r["spec_sha256"] for r in rules)
    checks = events(root, "reference_check")
    assert len(checks) == 9 and all(c["match"] for c in checks)
    assert outcome["reference_match"] is True
    assert sum(c["engine_trades"] for c in checks) > 0  # the cross-check compared real trades
    assert not events(root, "held_out_started")
    report = (root / rn.REPORT_DIR / "SC-9001-in-sample.md").read_text(encoding="utf-8")
    assert rn.NOT_PROOF in report and "Verdict" not in report
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM backtests").fetchone()[0] == 36
        assert conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0] == 36


def test_the_held_out_period_needs_approval_and_is_read_exactly_once(project):
    root, db, _ = project
    rn.run_in_sample(root, db, "SC-9001")

    with pytest.raises(rn.RunnerError, match="not approved"):
        rn.run_held_out(root, db, "SC-9001")
    rn.approve_in_sample(root, "SC-9001", by="Jason")
    outcome = rn.run_held_out(root, db, "SC-9001")

    assert [c["name"] for c in outcome["verdict"]["criteria"]] == [
        "positive average trade", "beats random entry", "deflated Sharpe",
        "beats buy-and-hold risk-adjusted"]
    assert all(isinstance(c["passed"], bool) for c in outcome["verdict"]["criteria"])
    assert outcome["verdict"]["random_entry"]["completed"] > 0
    assert outcome["verdict"]["verdict"] in {"promising (not proof of future profit)", "no edge shown"}
    with pytest.raises(rn.RunnerError, match="read once"):
        rn.run_held_out(root, db, "SC-9001")
    assert len(events(root, "held_out_started")) == 1
    report = (root / rn.REPORT_DIR / "SC-9001-held-out.md").read_text(encoding="utf-8")
    assert "## Verdict" in report and rn.NOT_PROOF in report


def test_a_crash_after_the_held_out_start_still_counts_as_the_one_read(project, monkeypatch):
    root, db, _ = project
    rn.run_in_sample(root, db, "SC-9001")
    rn.approve_in_sample(root, "SC-9001", by="Jason")
    monkeypatch.setattr(rn, "compute_verdict", lambda *a: (_ for _ in ()).throw(RuntimeError("crash")))

    with pytest.raises(RuntimeError, match="crash"):
        rn.run_held_out(root, db, "SC-9001")
    with pytest.raises(rn.RunnerError, match="read once"):
        rn.run_held_out(root, db, "SC-9001")


def test_a_failed_cross_check_blocks_the_held_out_read(project):
    root, db, _ = project
    rn.run_in_sample(root, db, "SC-9001")
    rn.append_ledger(root, "SC-9001", {"event": "reference_check", "match": False})
    rn.approve_in_sample(root, "SC-9001", by="Jason")

    with pytest.raises(rn.RunnerError, match="second implementation"):
        rn.run_held_out(root, db, "SC-9001")


def test_approval_needs_a_completed_in_sample_run(project):
    root, _, _ = project

    with pytest.raises(rn.RunnerError, match="no completed in-sample"):
        rn.approve_in_sample(root, "SC-9001", by="Jason")


def test_an_edited_or_superseded_card_is_refused(project):
    root, db, card_path = project
    card_path.write_text(card_path.read_text(encoding="utf-8").replace('"headline_bps": 5',
                                                                       '"headline_bps": 10'),
                         encoding="utf-8")

    with pytest.raises(rn.RunnerError, match="refused"):
        rn.run_in_sample(root, db, "SC-9001")
    with pytest.raises(rn.RunnerError, match="superseded"):
        rn.gated_inputs(PROJECT_ROOT, db, "SC-0001")


def test_the_ledger_is_append_only(project):
    root, db, _ = project
    rn.run_in_sample(root, db, "SC-9001")
    before = rn.ledger_path(root, "SC-9001").read_bytes()

    rn.approve_in_sample(root, "SC-9001", by="Jason")

    after = rn.ledger_path(root, "SC-9001").read_bytes()
    assert after.startswith(before) and len(after) > len(before)


def test_uncommitted_backtest_code_is_refused(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    code = tmp_path / "src/quant_brain/backtest/x.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(rn.RunnerError, match="uncommitted"):
        rn.code_commit(tmp_path)


def test_the_reference_implementation_matches_the_engine_on_a_random_walk():
    frame = md.normalize_bars(synthetic_bars(11, days=1500))
    rule_a = next(r for r in sc.StrategyCard.model_validate(sc.read_card(SC0002)).rules
                  if r.rule_id == "A")
    spec = engine.RuleSpec.from_card_rule(rule_a)
    frame["adj_open"] = frame["open"]
    result = engine.simulate(frame, spec, cost_bps=5, start="2000-01-03", end="2005-09-30")
    p0, p1 = engine.period_bounds(frame["date"], "2000-01-03", "2005-09-30")

    expected = reference.rule_a_trades(frame["open"].tolist(), frame["adj_close"].tolist(),
                                       rsi_period=2, entry_below=10, filter_sma=200, exit_sma=5,
                                       cost=0.0005, p0=p0, p1=p1)

    got = [(t.signal_index, t.entry_index, t.exit_index, t.trade_return) for t in result.trades]
    assert len(got) > 20
    assert [g[:3] for g in got] == [e[:3] for e in expected]
    assert all(abs(g[3] - e[3]) < 1e-12 for g, e in zip(got, expected, strict=True))


# --- review follow-ups: tie the held-out read to the approved in-sample run --------------


def approved(project):
    root, db, _ = project
    rn.run_in_sample(root, db, "SC-9001")
    rn.approve_in_sample(root, "SC-9001", by="Jason")
    return root, db


def test_an_approval_older_than_the_latest_in_sample_run_does_not_count(project):
    root, db = approved(project)
    rn.run_in_sample(root, db, "SC-9001")  # re-run after the approval

    with pytest.raises(rn.RunnerError, match="not approved"):
        rn.run_held_out(root, db, "SC-9001")


def test_only_the_latest_in_sample_cross_check_counts(project):
    root, db, _ = project
    rn.run_in_sample(root, db, "SC-9001")
    rn.append_ledger(root, "SC-9001", {"event": "reference_check", "match": False})
    rn.approve_in_sample(root, "SC-9001", by="Jason")

    with pytest.raises(rn.RunnerError, match="second implementation"):
        rn.run_held_out(root, db, "SC-9001")


def test_the_trial_ledger_must_be_committed_before_the_held_out_read(project, monkeypatch):
    root, db = approved(project)
    monkeypatch.setattr(rn, "ledger_committed", lambda root, path: False)

    with pytest.raises(rn.RunnerError, match="commit the trial ledger"):
        rn.run_held_out(root, db, "SC-9001")


def test_a_crash_during_the_held_out_read_is_recorded_as_failed(project, monkeypatch):
    root, db = approved(project)
    monkeypatch.setattr(rn, "compute_verdict", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        rn.run_held_out(root, db, "SC-9001")

    [failed] = events(root, "held_out_failed")
    assert "boom" in failed["error"]


def test_the_held_out_report_does_not_claim_a_cross_check_it_did_not_run(project):
    root, db = approved(project)
    rn.run_held_out(root, db, "SC-9001")

    report = (root / rn.REPORT_DIR / "SC-9001-held-out.md").read_text(encoding="utf-8")
    assert "cross-check of rule A: **match**" not in report
    assert "in-sample cross-check matched" in report


def test_the_code_gate_covers_everything_the_run_depends_on(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for relative in ("src/quant_brain/strategy/card.py", "scripts/run_backtest.py", "uv.lock"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
        with pytest.raises(rn.RunnerError, match="uncommitted"):
            rn.code_commit(tmp_path)
        target.unlink()


# --- re-review follow-ups: compare code, not commits; a durable read-once marker ----------


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd,
                   check=True, capture_output=True)


def test_committing_the_ledger_does_not_count_as_a_code_change(tmp_path):
    _git(tmp_path, "init", "-q")
    code = tmp_path / "src/quant_brain/backtest/engine.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "code")
    in_sample = rn.code_commit(tmp_path)
    ledger = tmp_path / rn.REPORT_DIR / "SC-9001.trials.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "ledger")

    assert rn.code_unchanged_since(tmp_path, in_sample) is True

    code.write_text("x = 2\n", encoding="utf-8")
    _git(tmp_path, "commit", "-qam", "engine change")
    assert rn.code_unchanged_since(tmp_path, in_sample) is False


def test_the_held_out_read_is_refused_when_code_changed_since_in_sample(project, monkeypatch):
    root, db = approved(project)
    monkeypatch.setattr(rn, "code_unchanged_since", lambda root, commit: False)

    with pytest.raises(rn.RunnerError, match="code changed"):
        rn.run_held_out(root, db, "SC-9001")


def test_restoring_the_ledger_cannot_reset_the_one_held_out_read(project):
    root, db = approved(project)
    before = rn.ledger_path(root, "SC-9001").read_bytes()
    rn.run_held_out(root, db, "SC-9001")
    rn.ledger_path(root, "SC-9001").write_bytes(before)  # as if `git restore` of the ledger

    with pytest.raises(rn.RunnerError, match="read once"):
        rn.run_held_out(root, db, "SC-9001")
