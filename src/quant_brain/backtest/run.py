"""Run a frozen card in two phases, with gates, an append-only trial ledger and reports.

Plan: ``brain/_system/plan/phase_08_backtest_runner.md``.

- Gates: the card must pass ``verify_frozen_card``; every dataset must load as
  accepted and match the content hash pinned on the card; the backtest code
  must be committed (clean tree), and its commit is recorded.
- Phase ``in_sample``: every rule x cost x symbol, plus buy-and-hold, plus the
  second-implementation cross-check of rule A. Then stop.
- Phase ``held_out``: only after a recorded in-sample approval and a fully
  matching cross-check; recorded as started *before* anything is computed,
  and refused if it was ever started before. It computes the card's verdict.
- The ledger (``brain/04_Backtest_Reports/<card>.trials.jsonl``) is only ever
  appended to.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_brain.backtest import benchmarks, engine, reference, stats
from quant_brain.backtest.indicators import sma
from quant_brain.data.market_data import load_dataset
from quant_brain.strategy import card as sc

REPORT_DIR = "brain/04_Backtest_Reports"
# Everything a run depends on: all package code (card checks, data loading, the
# engine), the runner script, and the locked dependency set.
CODE_PATHS = ("src/quant_brain", "scripts/run_backtest.py", "pyproject.toml", "uv.lock")
REPLAY_TRIAL_CODE_PATHS = (
    "src/quant_brain/backtest/engine.py",
    "src/quant_brain/backtest/indicators.py",
    "src/quant_brain/backtest/reference.py",
    "src/quant_brain/data/market_data.py",
    "src/quant_brain/strategy/card.py",
)
# The historical trial commit must match the execution core above. The renderer
# was added later, so it is instead pinned to the clean current commit in every
# exported artifact.
REPLAY_CURRENT_PATHS = (
    *REPLAY_TRIAL_CODE_PATHS,
    "src/quant_brain/backtest/run.py",
    "src/quant_brain/market/replay.py",
    "scripts/export_trade_replay.py",
    "pyproject.toml",
    "uv.lock",
)
NOT_PROOF = "A backtest is not proof of future profit."


class RunnerError(RuntimeError):
    """A gate refused the run."""


# --- ledger ----------------------------------------------------------------------------


def ledger_path(root: Path, card_id: str) -> Path:
    return root / REPORT_DIR / f"{card_id}.trials.jsonl"


def read_ledger(root: Path, card_id: str) -> list[dict[str, Any]]:
    path = ledger_path(root, card_id)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def append_ledger(root: Path, card_id: str, record: dict[str, Any]) -> dict[str, Any]:
    path = ledger_path(root, card_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": datetime.now(UTC).isoformat(), **record}
    with path.open("a", encoding="utf-8", newline="\n") as handle:  # append only
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def record_db(db_path: Path, record: dict[str, Any], report_path: str) -> None:
    """Mirror one trial into the existing backtests and metrics tables."""
    m = record["metrics"]
    config = {k: record.get(k) for k in ("kind", "rule", "symbol", "cost_bps", "phase", "period",
                                         "spec_sha256")}
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO backtests (backtest_id, strategy_id, dataset_id, code_commit, config_json, "
            "status, report_path, started_at, completed_at) VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?)",
            (record["trial_id"], record["card_id"], record["dataset_id"], record["code_commit"],
             json.dumps(config), report_path, record["at"], record["at"]),
        )
        conn.execute(
            "INSERT INTO metrics (backtest_id, total_return, cagr, sharpe, max_drawdown, exposure, "
            "win_rate, profit_factor, number_of_trades, fees) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record["trial_id"], m["total_return"], m["cagr"], m["sharpe"], m["max_drawdown"],
             m["exposure"], m["win_rate"], m["profit_factor"], m["trades"], record["cost_bps"]),
        )


def _events(root: Path, card_id: str, event: str) -> list[dict[str, Any]]:
    return [r for r in read_ledger(root, card_id) if r.get("event") == event]


# --- gates -----------------------------------------------------------------------------


def code_commit(root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *CODE_PATHS], cwd=root,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if status:
        raise RunnerError(f"uncommitted backtest code; commit it first:\n{status}")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                          text=True, check=True).stdout.strip()


def code_unchanged_since(root: Path, commit: str) -> bool:
    """True when no file under CODE_PATHS differs between ``commit`` and HEAD.

    Compares code, not commit IDs: committing the ledger or a report after the
    in-sample run moves HEAD without changing anything the run depends on.
    """
    result = subprocess.run(["git", "diff", "--quiet", commit, "HEAD", "--", *CODE_PATHS],
                            cwd=root, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RunnerError(f"cannot compare code with {commit}: {result.stderr.strip()}")
    return result.returncode == 0


def replay_code_unchanged_since(root: Path, commit: str) -> bool:
    """True when the code that determines replay trades matches the recorded trial."""
    result = subprocess.run(
        ["git", "diff", "--quiet", commit, "HEAD", "--", *REPLAY_TRIAL_CODE_PATHS],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RunnerError(f"cannot compare replay code with {commit}: {result.stderr.strip()}")
    return result.returncode == 0


def replay_code_commit(root: Path) -> str:
    """Current commit for a replay, refusing dirty execution, render, or lock inputs."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *REPLAY_CURRENT_PATHS],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise RunnerError(f"uncommitted replay code; commit it first:\n{status}")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


HELD_OUT_MARKER = "{card_id}:held_out_started"


def _held_out_marked(db_path: Path, card_id: str) -> bool:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT 1 FROM backtests WHERE backtest_id = ?",
                            (HELD_OUT_MARKER.format(card_id=card_id),)).fetchone() is not None


def _mark_held_out(db_path: Path, card: sc.StrategyCard, commit: str) -> None:
    """A durable read-once marker outside the ledger (a ledger restore cannot undo it)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO backtests (backtest_id, strategy_id, dataset_id, code_commit, config_json, "
            "status, started_at) VALUES (?, ?, ?, ?, ?, 'held_out_started', ?)",
            (HELD_OUT_MARKER.format(card_id=card.card_id), card.card_id, card.data[0].dataset_id,
             commit, json.dumps({"event": "held_out_started"}), datetime.now(UTC).isoformat()),
        )


def ledger_committed(root: Path, path: Path) -> bool:
    """True when the trial ledger is tracked by git and has no uncommitted change.

    Deleting or editing an uncommitted ledger would otherwise reset the gates
    that depend on it (approval, cross-check, held-out-once).
    """
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", relative], cwd=root,
                             capture_output=True, text=True).returncode == 0
    clean = not subprocess.run(["git", "status", "--porcelain", "--", relative], cwd=root,
                               capture_output=True, text=True, check=True).stdout.strip()
    return tracked and clean


def _latest_in_sample(root: Path, card_id: str) -> tuple[list[dict[str, Any]], int]:
    """The ledger, and the index of the latest in_sample_started record (or -1)."""
    ledger = read_ledger(root, card_id)
    starts = [i for i, r in enumerate(ledger) if r.get("event") == "in_sample_started"]
    return ledger, (starts[-1] if starts else -1)


def gated_inputs(root: Path, db_path: Path, card_id: str) -> tuple[sc.StrategyCard, dict, dict]:
    problems = sc.verify_frozen_card(root, card_id)
    if problems:
        raise RunnerError(f"{card_id} refused: " + "; ".join(problems))
    entry = next(e for e in sc._ledger(root)["frozen"] if e["card_id"] == card_id)
    card = sc.StrategyCard.model_validate(sc.read_card(root / entry["card_path"]))
    frames = {}
    for dataset in card.data:
        frame = load_dataset(root, db_path, dataset.dataset_id)  # accepted datasets only
        manifest = json.loads((root / "data/manifests" / f"{dataset.dataset_id}.json")
                              .read_text(encoding="utf-8"))
        if manifest["content_sha256"] != dataset.content_sha256:
            raise RunnerError(f"{dataset.dataset_id}: content hash differs from the card")
        frames[dataset.symbol] = frame
    return card, entry, frames


def authorized_replay_trial(
    root: Path,
    card: sc.StrategyCard,
    entry: dict[str, Any],
    *,
    phase: str,
    rule_id: str,
    symbol: str,
    cost_bps: float,
) -> dict[str, Any]:
    """Return the exact completed trial that authorizes a replay export.

    A replay is a rendering of a recorded trial, not a new way to read or
    recompute a period. Match every material input inside a completed phase
    boundary; held-out replays additionally prove the approval and independent
    cross-check that authorized the one-time read.
    """
    if phase not in {"in_sample", "held_out"}:
        raise RunnerError(f"unsupported replay phase: {phase}")
    ledger = read_ledger(root, card.card_id)
    if not ledger_committed(root, ledger_path(root, card.card_id)):
        raise RunnerError(f"{card.card_id}: commit the trial ledger before exporting a replay")
    current_replay_commit = replay_code_commit(root)

    started_event = f"{phase}_started"
    completed_event = f"{phase}_completed"
    starts = [i for i, row in enumerate(ledger) if row.get("event") == started_event]
    if not starts:
        raise RunnerError(
            f"{card.card_id}: no matching completed {phase.replace('_', '-')} trial"
        )
    start_index = starts[-1]
    completions = [
        i for i in range(start_index + 1, len(ledger))
        if ledger[i].get("event") == completed_event
    ]
    if not completions:
        raise RunnerError(
            f"{card.card_id}: no matching completed {phase.replace('_', '-')} trial"
        )
    completed_index = completions[0]
    segment = ledger[start_index:completed_index + 1]
    if any(row.get("event") == f"{phase}_failed" for row in segment):
        raise RunnerError(
            f"{card.card_id}: no matching completed {phase.replace('_', '-')} trial"
        )

    if phase == "held_out":
        in_sample_starts = [
            i for i, row in enumerate(ledger[:start_index])
            if row.get("event") == "in_sample_started"
        ]
        if not in_sample_starts:
            raise RunnerError(f"{card.card_id}: held-out replay has no approved in-sample run")
        in_sample_start = in_sample_starts[-1]
        prior = ledger[in_sample_start:start_index]
        completed = [i for i, row in enumerate(prior) if row.get("event") == "in_sample_completed"]
        approvals = [i for i, row in enumerate(prior) if row.get("event") == "in_sample_approved"]
        checks = [row for row in prior if row.get("event") == "reference_check"]
        if (
            not completed
            or not approvals
            or approvals[-1] < completed[-1]
            or not checks
            or not all(row.get("match") is True for row in checks)
        ):
            raise RunnerError(f"{card.card_id}: held-out replay has no approved in-sample run")

    dataset = next((item for item in card.data if item.symbol == symbol), None)
    if dataset is None:
        raise RunnerError(f"{card.card_id}: symbol {symbol} is not pinned on the card")
    period = list(_period(card, phase))
    matches = [
        row for row in segment
        if row.get("kind") == "rule"
        and row.get("card_id") == card.card_id
        and row.get("spec_sha256") == entry["spec_sha256"]
        and row.get("phase") == phase
        and row.get("rule") == rule_id
        and row.get("symbol") == symbol
        and row.get("dataset_id") == dataset.dataset_id
        and row.get("period") == period
        and float(row.get("cost_bps", float("nan"))) == float(cost_bps)
        and row.get("trial_id")
        and row.get("code_commit")
    ]
    if len(matches) != 1:
        raise RunnerError(
            f"{card.card_id}: no matching completed {phase.replace('_', '-')} trial"
        )
    trial = matches[0]
    if not replay_code_unchanged_since(root, trial["code_commit"]):
        raise RunnerError(
            f"{card.card_id}: replay code changed since recorded trial {trial['trial_id']}"
        )
    return {**trial, "replay_code_commit": current_replay_commit}


# --- one trial -------------------------------------------------------------------------


def _metrics(result: engine.Result, *, bars: int) -> dict[str, Any]:
    in_market = sum(
        (t.exit_index - t.entry_index + (1 if t.forced else 0)) for t in result.trades
    )
    summary = stats.trade_summary([t.trade_return for t in result.trades],
                                  [t.holding_days for t in result.trades])
    return {
        "total_return": float(result.equity.iloc[-1] - 1),
        "cagr": stats.cagr(result.equity),
        "sharpe": stats.annualised_sharpe(result.daily_returns),
        "sharpe_per_period": stats.sharpe_per_period(result.daily_returns),
        "max_drawdown": stats.max_drawdown(result.equity),
        "exposure": in_market / bars,
        **summary,
    }


def _trades_table(frame: pd.DataFrame, result: engine.Result) -> list[dict[str, Any]]:
    dates = frame["date"].tolist()
    return [{"signal": dates[t.signal_index], "entry": dates[t.entry_index],
             "exit": dates[t.exit_index], "holding_days": t.holding_days,
             "return": t.trade_return, "forced": t.forced, "units": len(t.unit_indices)}
            for t in result.trades]


def _period(card: sc.StrategyCard, phase: str) -> tuple[str, str]:
    period = card.periods.in_sample if phase == "in_sample" else card.periods.held_out
    return period.start.isoformat(), period.end.isoformat()


def _run_grid(root, db_path, card, entry, frames, phase, commit) -> dict[str, Any]:
    start, end = _period(card, phase)
    symbols = card.universe["primary"] + card.universe.get("robustness", [])
    base = {"card_id": card.card_id, "spec_sha256": entry["spec_sha256"],
            "file_sha256": entry["file_sha256"], "code_commit": commit, "phase": phase,
            "period": [start, end]}
    results: dict[str, Any] = {"trials": [], "buy_and_hold": [], "raw": {}}
    report = f"{REPORT_DIR}/{card.card_id}-{phase.replace('_', '-')}.md"
    for symbol in symbols:
        frame = frames[symbol].reset_index(drop=True)
        dataset = next(d for d in card.data if d.symbol == symbol)
        p0, p1 = engine.period_bounds(frame["date"], start, end)
        for cost in card.costs.bps_per_side:
            hold = engine.buy_and_hold(frame["adj_open"].to_numpy(float),
                                       frame["adj_close"].to_numpy(float),
                                       cost=cost / 10_000, p0=p0, p1=p1)
            record = {**base, "trial_id": uuid.uuid4().hex, "kind": "buy_and_hold",
                      "symbol": symbol, "dataset_id": dataset.dataset_id, "cost_bps": cost,
                      "metrics": _metrics(hold, bars=p1 - p0 + 1)}
            record = append_ledger(root, card.card_id, record)
            record_db(db_path, record, report)
            results["buy_and_hold"].append(record)
            results["raw"][("B&H", symbol, cost)] = hold
            for rule in card.rules:
                spec = engine.RuleSpec.from_card_rule(rule)
                result = engine.simulate(frame, spec, cost_bps=cost, start=start, end=end)
                record = {**base, "trial_id": uuid.uuid4().hex, "kind": "rule",
                          "rule": rule.rule_id, "symbol": symbol,
                          "dataset_id": dataset.dataset_id, "cost_bps": cost,
                          "metrics": _metrics(result, bars=p1 - p0 + 1)}
                record = append_ledger(root, card.card_id, record)
                record_db(db_path, record, report)
                results["trials"].append(record)
                results["raw"][(rule.rule_id, symbol, cost)] = result
    return results


def _reference_check(root, card, frames, results, phase) -> bool:
    start, end = _period(card, phase)
    rule_a = next(r for r in card.rules if r.role == "primary")
    spec = engine.RuleSpec.from_card_rule(rule_a)
    all_match = True
    for (rule_id, symbol, cost), result in results["raw"].items():
        if rule_id != rule_a.rule_id:
            continue
        frame = frames[symbol].reset_index(drop=True)
        p0, p1 = engine.period_bounds(frame["date"], start, end)
        expected = reference.rule_a_trades(
            frame["adj_open"].tolist(), frame["adj_close"].tolist(),
            rsi_period=spec.rsi_period, entry_below=spec.entry_below,
            filter_sma=spec.filter_sma, exit_sma=int(spec.exit_value),
            cost=cost / 10_000, p0=p0, p1=p1,
        )
        got = [(t.signal_index, t.entry_index, t.exit_index, t.trade_return) for t in result.trades]
        match = len(got) == len(expected) and all(
            g[:3] == e[:3] and abs(g[3] - e[3]) < 1e-12 for g, e in zip(got, expected, strict=True)
        )
        all_match &= match
        append_ledger(root, card.card_id, {"event": "reference_check", "phase": phase,
                                           "symbol": symbol, "cost_bps": cost, "match": match,
                                           "engine_trades": len(got),
                                           "reference_trades": len(expected)})
    return all_match


# --- phases ----------------------------------------------------------------------------


def run_in_sample(root: Path, db_path: Path, card_id: str) -> dict[str, Any]:
    card, entry, frames = gated_inputs(root, db_path, card_id)
    commit = code_commit(root)
    append_ledger(root, card_id, {"event": "in_sample_started", "code_commit": commit})
    results = _run_grid(root, db_path, card, entry, frames, "in_sample", commit)
    match = _reference_check(root, card, frames, results, "in_sample")
    append_ledger(root, card_id, {"event": "in_sample_completed", "reference_match": match})
    write_report(root, card, frames, results, "in_sample", verdict=None, reference_match=match)
    return {"results": results, "reference_match": match}


def approve_in_sample(root: Path, card_id: str, by: str) -> dict[str, Any]:
    if not _events(root, card_id, "in_sample_completed"):
        raise RunnerError("no completed in-sample run to approve")
    return append_ledger(root, card_id, {"event": "in_sample_approved", "by": by})


def run_held_out(root: Path, db_path: Path, card_id: str) -> dict[str, Any]:
    card, entry, frames = gated_inputs(root, db_path, card_id)
    commit = code_commit(root)
    if _events(root, card_id, "held_out_started") or _held_out_marked(db_path, card_id):
        raise RunnerError(f"{card_id}: the held-out period was already read; it is read once")
    ledger, start = _latest_in_sample(root, card_id)
    if start < 0:
        raise RunnerError(f"{card_id}: no in-sample run")
    latest = ledger[start:]
    if not code_unchanged_since(root, ledger[start]["code_commit"]):
        raise RunnerError(
            f"{card_id}: code changed since the approved in-sample run "
            f"({ledger[start]['code_commit']}); re-run in-sample and re-approve"
        )
    completed = [i for i, r in enumerate(latest) if r.get("event") == "in_sample_completed"]
    approvals = [i for i, r in enumerate(latest) if r.get("event") == "in_sample_approved"]
    if not completed or not approvals or approvals[-1] < completed[-1]:
        raise RunnerError(f"{card_id}: in-sample results are not approved")
    checks = [r for r in latest if r.get("event") == "reference_check"]
    if not checks or not all(c["match"] for c in checks):
        raise RunnerError(f"{card_id}: the second implementation has not matched the engine")
    if not ledger_committed(root, ledger_path(root, card_id)):
        raise RunnerError(f"{card_id}: commit the trial ledger before the held-out read")
    _mark_held_out(db_path, card, commit)
    append_ledger(root, card_id, {"event": "held_out_started", "code_commit": commit,
                                  "in_sample_commit": ledger[start]["code_commit"]})
    try:
        results = _run_grid(root, db_path, card, entry, frames, "held_out", commit)
        verdict = compute_verdict(card, frames, results)
    except Exception as exc:
        append_ledger(root, card_id, {"event": "held_out_failed",
                                      "error": f"{type(exc).__name__}: {exc}"})
        raise
    append_ledger(root, card_id, {"event": "held_out_completed", "verdict": verdict["verdict"],
                                  "criteria": verdict["criteria"]})
    write_report(root, card, frames, results, "held_out", verdict=verdict, reference_match=None)
    return {"results": results, "verdict": verdict}


def compute_verdict(card: sc.StrategyCard, frames: dict, results: dict) -> dict[str, Any]:
    v = card.verdict
    symbol = card.universe["primary"][0]
    cost = v.cost_bps
    start, end = _period(card, "held_out")
    primary = results["raw"][(v.applies_to, symbol, cost)]
    hold = results["raw"][("B&H", symbol, cost)]
    frame = frames[symbol].reset_index(drop=True)
    p0, p1 = engine.period_bounds(frame["date"], start, end)
    returns = [t.trade_return for t in primary.trades]
    if not returns:
        return {"verdict": v.otherwise, "criteria": [], "reason": "zero held-out trades",
                "note": NOT_PROOF}

    spec = engine.RuleSpec.from_card_rule(next(r for r in card.rules if r.rule_id == v.applies_to))
    closes = frame["adj_close"]
    trend = sma(closes, spec.filter_sma) if spec.filter_sma else None
    filter_ok = (closes > trend).to_numpy(bool) & trend.notna().to_numpy(bool) if trend is not None \
        else np.ones(len(frame), dtype=bool)
    random_cfg = card.benchmarks["random_entry"]
    random = benchmarks.random_entry(
        opens=frame["adj_open"].to_numpy(float), filter_ok=filter_ok,
        holding_times=[t.holding_days for t in primary.trades], cost=cost / 10_000,
        p0=p0, p1=p1, runs=random_cfg["runs"], seed_start=random_cfg["seed_start"],
    )
    average = float(np.mean(returns))
    percentile = stats.percentile_strictly_below(random.average_returns, average)
    trial_sharpes = [stats.sharpe_per_period(results["raw"][(r.rule_id, symbol, cost)].daily_returns)
                     for r in card.rules]
    dsr = stats.deflated_sharpe(primary.daily_returns.to_numpy(float), trial_sharpes)
    sharpe_gap = stats.annualised_sharpe(primary.daily_returns) - stats.annualised_sharpe(
        hold.daily_returns)
    values = {"positive average trade": average,
              "beats random entry": percentile,
              "deflated Sharpe": dsr["dsr"],
              "beats buy-and-hold risk-adjusted": sharpe_gap}
    criteria = []
    for criterion in v.criteria:
        value = values[criterion.name]
        passed = value is not None and (
            value > criterion.threshold if criterion.comparator == ">" else value >= criterion.threshold
        )
        criteria.append({"name": criterion.name, "value": value, "comparator": criterion.comparator,
                         "threshold": criterion.threshold, "passed": bool(passed)})
    verdict = v.if_all_pass if all(c["passed"] for c in criteria) else v.otherwise
    return {"verdict": verdict, "criteria": criteria, "dsr": dsr,
            "random_entry": {"completed": random.completed, "discarded": random.discarded},
            "note": NOT_PROOF}


# --- report ----------------------------------------------------------------------------


def _fmt(value: Any, pct: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%" if pct else f"{value:.3f}"


def write_report(root, card, frames, results, phase, *, verdict, reference_match) -> Path:
    start, end = _period(card, phase)
    lines = [f"# {card.card_id}: {phase.replace('_', '-')} report ({start}..{end})", "",
             f"> {NOT_PROOF}", "",
             ("Second-implementation cross-check of rule A: not re-run on this period; the "
              "in-sample cross-check matched (required before the held-out read)."
              if reference_match is None else
              f"Second-implementation cross-check of rule A: **{'match' if reference_match else 'MISMATCH'}**."),
             ""]
    if verdict is not None:
        lines += [f"## Verdict: **{verdict['verdict']}**", "",
                  "| Criterion | Value | Test | Passed |", "| --- | --- | --- | --- |"]
        for c in verdict["criteria"]:
            lines.append(f"| {c['name']} | {_fmt(c['value'])} | {c['comparator']} {c['threshold']} "
                         f"| {'yes' if c['passed'] else 'no'} |")
        lines.append("")
    lines += ["## Trials", "", "| Rule | Symbol | Cost bps | Trades | Avg trade | Win rate | "
              "Total return | CAGR | Sharpe | Max DD | Days held |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for record in results["buy_and_hold"] + results["trials"]:
        m = record["metrics"]
        rule = record.get("rule", "buy&hold")
        lines.append(f"| {rule} | {record['symbol']} | {record['cost_bps']} | {m['trades']} | "
                     f"{_fmt(m['average_trade'], True)} | {_fmt(m['win_rate'], True)} | "
                     f"{_fmt(m['total_return'], True)} | {_fmt(m['cagr'], True)} | "
                     f"{_fmt(m['sharpe'])} | {_fmt(m['max_drawdown'], True)} | "
                     f"{_fmt(m['exposure'], True)} |")
    primary = card.verdict.applies_to
    symbol = card.universe["primary"][0]
    frame = frames[symbol].reset_index(drop=True)
    data = {
        "card_id": card.card_id, "phase": phase, "period": [start, end],
        "trials": results["buy_and_hold"] + results["trials"],
        "primary_trades": _trades_table(frame, results["raw"][(primary, symbol, card.verdict.cost_bps)]),
        "verdict": verdict, "reference_match": reference_match,
    }
    series = {
        "dates": frame["date"].iloc[results["raw"][("B&H", symbol, card.verdict.cost_bps)].equity.index].tolist(),
        "primary_equity": results["raw"][(primary, symbol, card.verdict.cost_bps)].equity.tolist(),
        "buy_and_hold_equity": results["raw"][("B&H", symbol, card.verdict.cost_bps)].equity.tolist(),
    }
    lines += ["", "## Data", "", "```json", json.dumps(data, indent=1, default=str), "```", ""]
    path = root / REPORT_DIR / f"{card.card_id}-{phase.replace('_', '-')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    (root / REPORT_DIR / f"{card.card_id}-{phase.replace('_', '-')}.series.json").write_text(
        json.dumps(series), encoding="utf-8")
    return path
