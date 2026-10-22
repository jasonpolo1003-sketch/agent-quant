"""Brain Terminal (PROP-008): read-only views, guards, tutor, jobs and scheduler.

Hermetic: a temporary brain, a fake model backend, and no Task Scheduler,
network or real CLI calls.
"""

import hashlib
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quant_brain.data import market_data as md
from quant_brain.db.init_db import init_database
from quant_brain.ops.events import record_event
from quant_brain.ui import backends, jobs, readers, sessions, store, summary, tutor, winsched
from quant_brain.ui.app import TerminalConfig, create_app

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "market" / "spy_sample.csv"
BASE = "http://127.0.0.1:8765"
HDR = {"X-Brain-Terminal": "1"}

PLAN = """# Plan

## 10. Handoff checkpoint

### Newest entry (2026-09-28)

- **Next bounded step:** freeze one strategy card.

### Older entry

## 11. Other
"""
PROPOSALS = """# Plan Change Proposals

## Proposals
### PROP-001 — First change
- **Date:** 2026-09-07
- **Status:** accepted

### PROP-002 — Second change
- **Date:** 2026-09-18
- **Status:** proposed

---

## Accepted changes log
"""


class FakeBackend:
    name = "claude"

    def __init__(self, chunks=("Hello ", "[PLAN.md:3]")):
        self.chunks = chunks
        self.calls = []

    def status(self):
        return backends.BackendStatus("claude", "Fake", True, "fake", "none")

    def stream(self, system, prompt, *, timeout=300):
        self.calls.append((system, prompt))
        yield from self.chunks


@pytest.fixture
def brain(tmp_path):
    root = tmp_path / "brain-root"
    root.mkdir()
    (root / "PLAN.md").write_text(PLAN, encoding="utf-8")
    (root / "AGENTS.md").write_text("# Rules\n\nNo live trades.\n", encoding="utf-8")
    plan_dir = root / "brain/_system/plan"
    plan_dir.mkdir(parents=True)
    (plan_dir / "plan_change_proposals.md").write_text(PROPOSALS, encoding="utf-8")
    dec = root / "brain/07_Decision_Log"
    dec.mkdir(parents=True)
    (dec / "DEC-2026-09-07-first.md").write_text("---\ntitle: First decision\nstatus: accepted\n"
                                                 "---\n\n# First\n", encoding="utf-8")
    shutil.copytree(REPO / "agents", root / "agents")
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    db = root / "db" / "brain.sqlite"
    init_database(db)
    record_event(db, run_id="RUN-abc", agent_role="research_scout", stage="discovery",
                 status="failed", event_type="discovery_failed", message="boom")
    return root, db


@pytest.fixture
def client(brain, tmp_path):
    root, db = brain
    cfg = TerminalConfig(project_root=root, brain_db=db, terminal_db=root / "db/terminal.sqlite",
                         claude_home=tmp_path / "claude-home", codex_home=tmp_path / "codex-home",
                         scheduler_enabled=False)
    return TestClient(create_app(cfg), base_url=BASE), cfg


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- read-only guarantee and local-only guards -------------------------------------------

def test_every_read_endpoint_leaves_brain_db_untouched(client):
    c, cfg = client
    before = sha(cfg.brain_db)
    for path in ("/api/home", "/api/events", "/api/runs", "/api/runs/RUN-abc", "/api/activity",
                 "/api/tasks", "/api/schedules", "/api/skills", "/api/datasets", "/api/lab",
                 "/api/learn/sources", "/api/journal", "/api/learn/notes", "/"):
        assert c.get(path).status_code == 200, path
    assert sha(cfg.brain_db) == before


def test_foreign_host_is_refused(client):
    c, _ = client
    assert c.get("/api/home", headers={"host": "evil.example:8765"}).status_code == 403


def test_state_change_needs_terminal_header_and_same_origin(client):
    c, _ = client
    body = {"job_id": "x1", "name": "x", "kind": "health_check",
            "cadence": {"type": "daily", "time": "02:00"}}
    assert c.post("/api/schedules", json=body).status_code == 403
    assert c.post("/api/schedules", json=body,
                  headers={**HDR, "origin": "https://evil.example"}).status_code == 403
    assert c.post("/api/schedules", json=body,
                  headers={**HDR, "origin": BASE}).status_code == 200


# --- readers --------------------------------------------------------------------------

def test_pipeline_lights_stages_from_counts():
    stages = readers.pipeline({"sources": 7, "price_datasets": 3, "strategy_cards": 0,
                               "backtests": 2, "reviews": 0})
    assert [s["state"] for s in stages] == ["done", "done", "next", "waiting", "waiting"]


def test_plan_checkpoint_and_journal(brain):
    root, _ = brain
    cp = readers.plan_checkpoint(root)
    assert cp["entries"] == ["Newest entry (2026-09-28)", "Older entry"]
    assert cp["next"] == "freeze one strategy card."
    items = readers.journal(root)
    assert [i["id"] for i in items] == ["PROP-002", "PROP-001", "DEC-2026-09-07-first"]
    assert items[0]["status"] == "proposed"
    assert items[2]["title"] == "First decision"


def test_runs_report_final_status(brain):
    _, db = brain
    record_event(db, run_id="RUN-abc", agent_role="research_scout", stage="dispatch",
                 status="completed", event_type="done", message="ok")
    run = readers.runs(db)[0]
    assert (run["run_id"], run["event_count"], run["final_status"]) == ("RUN-abc", 2, "completed")
    assert [e["event_id"] for e in readers.events(db, after_id=1)] == [2]


def test_readers_tolerate_a_missing_database(tmp_path):
    missing = tmp_path / "none.sqlite"
    assert readers.brain_counts(missing)["sources"] == 0
    assert readers.events(missing) == []
    assert not missing.exists()


def test_bars_only_for_accepted_datasets(client):
    c, cfg = client
    manifest = md.ingest(cfg.project_root, cfg.brain_db, "SPY",
                         md.normalize_bars(pd.read_csv(FIXTURE)),
                         meta={"provider": "yfinance", "provider_version": "t",
                               "requested_start": "2024-03-01", "requested_end": "2024-04-12"},
                         now=datetime(2026, 9, 28, 12, tzinfo=UTC))
    listed = c.get("/api/datasets").json()
    assert listed[0]["state"] == "accepted"
    bars = c.get(f"/api/datasets/{manifest['dataset_id']}/bars").json()
    assert len(bars) == manifest["rows"] and set(bars[0]) >= {"time", "open", "close", "volume"}
    (cfg.project_root / manifest["path"]).write_bytes(b"corrupt")
    assert c.get(f"/api/datasets/{manifest['dataset_id']}/bars").status_code == 409
    # The Gate F verifier raises on a corrupt Parquet file; the terminal must still render.
    listed = c.get("/api/datasets").json()
    assert listed[0]["state"] in ("invalid", "unverified") and listed[0]["problems"]


def test_equity_series_must_stay_inside_the_project(brain, tmp_path):
    root, _ = brain
    outside = tmp_path / "evil.equity.csv"
    outside.write_text("date,equity\n2024-01-02,1\n", encoding="utf-8")
    assert readers.equity_path(root, {"config": {"equity_path": str(outside)}}) is None
    report = root / "brain/04_Backtest_Reports/BT-1.md"
    report.parent.mkdir(parents=True)
    report.write_text("x", encoding="utf-8")
    (report.parent / "BT-1.equity.csv").write_text(
        "date,strategy,buy_hold\n2024-01-02,100,100\n2024-01-03,101,99.5\n", encoding="utf-8")
    series = readers.equity_series(root, {"report_path": "brain/04_Backtest_Reports/BT-1.md"})
    assert set(series) == {"strategy", "buy_hold"}
    assert series["buy_hold"][1] == {"time": "2024-01-03", "value": 99.5}


# --- tutor ----------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["../outside.md", ".env", "db/brain.sqlite", "C:/Windows/win.ini",
                                 "brain/../../x.md"])
def test_tutor_refuses_sources_outside_the_allowlist(brain, bad):
    root, _ = brain
    with pytest.raises(tutor.SourceError):
        tutor.read_source(root, bad)


def test_tutor_context_is_line_numbered_and_reports_truncation(brain):
    root, _ = brain
    context, report = tutor.build_context(root, ["PLAN.md", "AGENTS.md"])
    assert '<source path="PLAN.md">' in context and "3: ## 10. Handoff checkpoint" in context
    assert not any(r["truncated"] for r in report)
    _, cut = tutor.build_context(root, ["PLAN.md"], max_chars=40)
    assert cut[0]["truncated"] and cut[0]["included_lines"] < cut[0]["lines"]
    with pytest.raises(tutor.SourceError):
        tutor.build_context(root, [])


def test_study_notes_live_outside_brain_and_are_untrusted(brain):
    root, _ = brain
    rel = tutor.save_note(root, title="Look-ahead bias", question="q?", answer="a.",
                          sources=["PLAN.md"], backend="claude")
    assert rel.startswith("terminal/learning/") and not rel.startswith("brain/")
    text = (root / rel).read_text(encoding="utf-8")
    assert "trusted: false" in text and "type: study_note" in text
    assert tutor.list_notes(root)[0]["title"] == "Look-ahead bias"


def test_ask_streams_answer_from_fake_backend_with_run_log(client, monkeypatch):
    c, _ = client
    fake = FakeBackend()
    monkeypatch.setitem(backends.BACKENDS, "claude", fake)
    res = c.post("/api/learn/ask", headers=HDR,
                 json={"question": "why?", "sources": ["PLAN.md", "run:RUN-abc"]})
    lines = [json.loads(x) for x in res.text.splitlines()]
    assert lines[0]["type"] == "sources" and [s["path"] for s in lines[0]["sources"]] == [
        "PLAN.md", "run:RUN-abc"]
    assert "".join(x["text"] for x in lines if x["type"] == "text") == "Hello [PLAN.md:3]"
    assert lines[-1]["type"] == "done"
    system, prompt = fake.calls[0]
    assert "come ONLY from" in system and "General background" in system
    assert "discovery_failed failed: boom" in prompt and "<question>\nwhy?" in prompt


def test_ask_refuses_disallowed_source(client):
    c, _ = client
    assert c.post("/api/learn/ask", headers=HDR,
                  json={"question": "q", "sources": [".env"]}).status_code == 422


# --- claude CLI backend -------------------------------------------------------------------

def test_claude_command_disables_every_tool():
    cmd = backends.ClaudeCLI(executable="claude").command("SYS")
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in cmd and "--no-session-persistence" in cmd
    assert cmd[cmd.index("--system-prompt") + 1] == "SYS"


def test_clean_env_drops_nesting_guard(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert "CLAUDECODE" not in backends._clean_env()


def test_parse_stream_json():
    def ev(t):
        return json.dumps({"type": "stream_event", "event": {
            "type": "content_block_delta", "delta": {"type": "text_delta", "text": t}}})
    ok = [ev("a"), "not json", ev("b"), json.dumps({"type": "result", "result": "ab"})]
    assert "".join(backends.parse_stream_json(iter(ok))) == "ab"
    only_result = [json.dumps({"type": "result", "result": "whole"})]
    assert list(backends.parse_stream_json(iter(only_result))) == ["whole"]
    with pytest.raises(backends.BackendError):
        list(backends.parse_stream_json(iter([json.dumps(
            {"type": "result", "is_error": True, "result": "limit"})])))


def test_codex_slot_is_honestly_disabled():
    assert backends.CodexCLI().status().available is False
    with pytest.raises(backends.BackendError):
        list(backends.CodexCLI().stream("s", "p"))


# --- Task Scheduler -----------------------------------------------------------------------

def test_create_args_per_cadence():
    daily = winsched.create_args("j", {"type": "daily", "time": "02:00"}, "cmd")
    assert daily[:7] == ["schtasks", "/Create", "/F", "/TN", "\\QuantBrain\\j", "/TR", "cmd"]
    assert daily[7:] == ["/SC", "DAILY", "/ST", "02:00"]
    assert winsched.create_args("j", {"type": "weekdays", "time": "18:30"}, "c")[7:] == [
        "/SC", "WEEKLY", "/D", "MON,TUE,WED,THU,FRI", "/ST", "18:30"]
    weekly = winsched.validate_cadence({"type": "weekly", "days": ["sun", "Sat"], "time": "09:00"})
    assert weekly["days"] == ["SAT", "SUN"]
    assert winsched.create_args("j", {"type": "hourly", "every": 6}, "c")[7:] == [
        "/SC", "HOURLY", "/MO", "6"]


@pytest.mark.parametrize("bad", [{"type": "daily", "time": "25:00"}, {"type": "weekly",
                         "days": ["XYZ"], "time": "09:00"}, {"type": "hourly", "every": 30},
                         {"type": "monthly"}])
def test_bad_cadence_is_rejected(bad):
    with pytest.raises(ValueError):
        winsched.validate_cadence(bad)


def test_task_command_refuses_overlong_paths(tmp_path):
    deep = tmp_path / ("x" * 240)
    with pytest.raises(winsched.SchedulerError):
        winsched.task_command("job", deep)


def test_parse_query_and_drift():
    csv_text = ('"HostName","TaskName","Next Run Time","Status","Last Run Time","Last Result",'
                '"Task To Run"\n'
                '"PC","\\QuantBrain\\nightly-health","9/29/2026 2:00:00 AM","Ready","N/A","1","x"\n'
                '"PC","\\Microsoft\\Other","N/A","Ready","N/A","0","y"\n'
                '"PC","\\QuantBrain\\orphan","N/A","Ready","N/A","0","z"\n')
    tasks = winsched.parse_query_csv(csv_text)
    assert set(tasks) == {"nightly-health", "orphan"}
    assert tasks["nightly-health"]["next_run"] == "9/29/2026 2:00:00 AM"
    problems = winsched.drift([{"job_id": "nightly-health", "enabled": True},
                               {"job_id": "digest", "enabled": True}], tasks)
    assert any("digest is enabled" in p for p in problems)
    assert any("orphan" in p for p in problems)


# --- jobs -------------------------------------------------------------------------------

@pytest.fixture
def ctx(brain):
    root, db = brain
    return jobs.JobContext(root, db, root / "db/terminal.sqlite", "python")


def job(**over):
    base = {"job_id": "health", "name": "Health", "kind": "health_check",
            "cadence": {"type": "daily", "time": "02:00"}, "config": {}, "max_runs_per_day": 2}
    return jobs.validate_schedule({**base, **over})


@pytest.mark.parametrize("over", [{"job_id": "Bad Id"}, {"job_id": "x" * 30},
                                  {"kind": "shell"}, {"config": {"cmd": "rm"}},
                                  {"kind": "agent_prompt", "config": {"prompt": ""}},
                                  {"kind": "data_refresh", "config": {"symbols": ["spy;rm"]}}])
def test_schedule_validation_rejects(over):
    with pytest.raises(ValueError):
        job(**over)


def test_research_run_is_refused_while_frozen(ctx):
    j = job(job_id="research", kind="research_run", enabled=True)
    assert j["enabled"] is False
    run = jobs.run_job(ctx, j, "manual")
    assert run["status"] == "refused" and "PROP-007" in run["summary"]
    assert readers.events(ctx.brain_db, limit=1)[0]["event_type"] == "job_refused"


def test_health_check_records_run_log_and_events(ctx, monkeypatch):
    monkeypatch.setattr(jobs, "_run", lambda cmd, cwd, timeout: jobs.StepResult(
        "x", 0, "=== 5 passed, 1 skipped in 1.0s ===" if "pytest" in cmd else "ok"))
    run = jobs.run_job(ctx, job(), "manual")
    assert run["status"] == "completed" and "pytest: 5 passed, 1 skipped" in run["summary"]
    assert (ctx.project_root / "terminal/logs" / f"{run['run_id']}.log").is_file()
    kinds = [e["event_type"] for e in readers.events(ctx.brain_db, run_id=run["run_id"])]
    assert kinds == ["job_started", "job_finished"]


def test_failed_step_fails_the_job(ctx, monkeypatch):
    monkeypatch.setattr(jobs, "_run", lambda cmd, cwd, timeout: jobs.StepResult(
        "x", 1 if "ruff" in cmd else 0, "boom"))
    assert jobs.run_job(ctx, job(), "manual")["status"] == "failed"


def test_caps_refuse_concurrent_and_over_daily_limit(ctx, monkeypatch):
    monkeypatch.setattr(jobs, "_run", lambda cmd, cwd, timeout: jobs.StepResult("x", 0, "ok"))
    store.start_run(ctx.terminal_db, "JOB-live", "other", "health_check", "manual")
    assert jobs.run_job(ctx, job(), "manual")["status"] == "refused"
    store.finish_run(ctx.terminal_db, "JOB-live", status="completed", exit_code=0, summary="")
    assert jobs.run_job(ctx, job(), "manual")["status"] == "completed"
    assert jobs.run_job(ctx, job(), "manual")["status"] == "completed"
    third = jobs.run_job(ctx, job(), "manual")
    assert third["status"] == "refused" and "2 times" in third["summary"]


def test_stale_running_row_does_not_block_forever(ctx, monkeypatch):
    monkeypatch.setattr(jobs, "_run", lambda cmd, cwd, timeout: jobs.StepResult("x", 0, "ok"))
    old = (datetime.now(UTC) - timedelta(hours=5)).isoformat(timespec="seconds")
    with store.connect(ctx.terminal_db) as conn:
        conn.execute("INSERT INTO job_runs (run_id, job_id, kind, trigger, status, started_at)"
                     " VALUES ('JOB-old', 'other', 'health_check', 'schedule', 'running', ?)",
                     (old,))
    assert jobs.run_job(ctx, job(), "manual")["status"] == "completed"
    assert store.list_runs(ctx.terminal_db, job_id="other")[0]["status"] == "failed"


def test_agent_prompt_writes_untrusted_output_outside_brain(ctx, monkeypatch):
    fake = FakeBackend(("All quiet. ", "Next: backtest."))
    monkeypatch.setitem(backends.BACKENDS, "claude", fake)
    j = job(job_id="digest", kind="agent_prompt",
            config={"prompt": "Summarise today", "context": ["plan_next", "events_today"]})
    run = jobs.run_job(ctx, j, "schedule")
    assert run["status"] == "completed" and run["output_path"].startswith("terminal/scheduled/")
    text = (ctx.project_root / run["output_path"]).read_text(encoding="utf-8")
    assert "trusted: false" in text and "All quiet. Next: backtest." in text
    _, prompt = fake.calls[0]
    assert "Next: freeze one strategy card." in prompt and "Summarise today" in prompt


def test_seeded_schedules_start_disabled(ctx):
    jobs.seed_defaults(ctx.terminal_db)
    seeded = store.list_schedules(ctx.terminal_db)
    assert {s["job_id"] for s in seeded} >= {"nightly-health", "daily-digest", "rsi-research"}
    assert not any(s["enabled"] for s in seeded)


def test_api_refuses_enabling_frozen_kind(client):
    c, _ = client
    res = c.put("/api/schedules/rsi-research", headers=HDR, json={"enabled": True})
    assert res.status_code == 409


# --- sessions ---------------------------------------------------------------------------

def test_claude_and_codex_session_parsing(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    home = tmp_path / "claude"
    folder = sessions.claude_project_dir(home, project)
    folder.mkdir(parents=True)
    lines = [
        {"type": "ai-title", "aiTitle": "Build the UI"},
        {"type": "last-prompt", "lastPrompt": "work on the ui"},
        {"type": "assistant", "timestamp": "2026-09-28T10:00:00Z", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "src/a.py"}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q\nmore"}}]}},
        "garbage line",
    ]
    (folder / "s1.jsonl").write_text("\n".join(
        x if isinstance(x, str) else json.dumps(x) for x in lines), encoding="utf-8")
    s = sessions.claude_sessions(home, project)[0]
    assert (s["title"], s["tool_calls"], s["edits"]) == ("Build the UI", 2, 1)
    assert [a["what"] for a in s["activity"]] == ["Edit src/a.py", "Bash: pytest -q"]

    codex = tmp_path / "codex"
    day = codex / "sessions/2026/09/28"
    day.mkdir(parents=True)
    rollout = [
        {"type": "session_meta", "timestamp": "t1", "payload": {"id": "c1", "cwd": str(project)}},
        {"type": "response_item", "timestamp": "t2", "payload": {
            "type": "message", "role": "user", "content": [{"type": "input_text",
                                                             "text": "add a test"}]}},
        {"type": "response_item", "timestamp": "t3", "payload": {
            "type": "function_call", "name": "shell",
            "arguments": json.dumps({"command": ["bash", "-lc", "pytest"]})}},
    ]
    (day / "rollout-1.jsonl").write_text("\n".join(json.dumps(x) for x in rollout),
                                         encoding="utf-8")
    other = dict(rollout[0], payload={"id": "c2", "cwd": str(tmp_path / "elsewhere")})
    (day / "rollout-2.jsonl").write_text(json.dumps(other), encoding="utf-8")
    found = sessions.codex_sessions(codex, project)
    assert [x["id"] for x in found] == ["c1"]
    assert found[0]["prompt"] == "add a test"
    assert found[0]["activity"][0]["what"] == "shell: bash -lc pytest"


# --- plain-language summaries -------------------------------------------------------------


def test_steps_and_headline_point_at_the_first_empty_step():
    counts = {"sources": 7, "price_datasets": 3, "strategy_cards": 2, "backtests": 0, "reviews": 0}
    assert [s["state"] for s in summary.steps(counts)] == ["done", "done", "done", "now", "later"]
    h = summary.headline(counts)
    assert h["title"] == "Step 4 of 5: backtest"
    assert "2 strategies are written and frozen" in h["detail"]
    everything = dict.fromkeys(("sources", "price_datasets", "strategy_cards", "backtests",
                                "reviews"), 1)
    assert summary.steps(everything)[-1]["state"] == "now"


def ev(i, stage, status, message="", event_type="x", role="research_scout", at="2026-09-28 04:11:0"):
    return {"event_id": i, "run_id": "RUN-1", "agent_role": role, "stage": stage,
            "status": status, "event_type": event_type, "message": message,
            "created_at": f"{at}{i}"}


def test_describe_run_gives_title_outcome_and_reason():
    evs = [ev(1, "dispatch", "running", "Routing discovery to research_scout"),
           ev(2, "discovery", "running", "Scout discovery started for RQ-6d9c12f4"),
           ev(3, "qwen_validation", "failed", "14b validation failed"),
           ev(4, "qwen_validation", "completed", "27b passed"),
           ev(5, "discovery", "failed", "'possible_strategy_rule'"),
           ev(6, "discovery", "failed", "Wrote Failed_Runs receipt x.md")]
    d = summary.describe_run(evs)
    assert d["title"] == "Research run for RQ-6d9c12f4"
    assert d["status"] == "failed" and d["outcome"] == "Stopped with an error."
    assert d["reason"] == "'possible_strategy_rule'"
    assert d["steps"] == 6 and d["seconds"] == 5
    checks = next(p for p in d["phases"] if p["stage"] == "qwen_validation")
    assert (checks["label"], checks["ok"], checks["failed"]) == (
        "Checking the model's answers", 1, 1)
    done = summary.describe_run([ev(1, "health_check", "completed", role="brain_terminal")])
    assert done["title"] == "Terminal job: health check" and done["reason"] is None


def test_timeline_merges_sources_newest_first():
    items = summary.timeline(
        [{"date": "2026-09-28T22:00:00-05:00", "subject": "feat: x", "short": "abc1234"}],
        [{"ended_at": "2026-09-29 04:00:00", "title": "Research run", "outcome": "Stopped.",
          "reason": "boom", "run_id": "RUN-1", "status": "failed"}],
        [{"started_at": "2026-09-29T02:00:00+00:00", "finished_at": "2026-09-29T02:01:00+00:00",
          "job_id": "nightly", "summary": "pytest ok", "run_id": "JOB-1", "status": "completed"}])
    assert [i["kind"] for i in items] == ["run", "commit", "job"]
    assert (items[1]["who"], items[1]["text"]) == ("Built", "x")
    assert items[0]["text"] == "Stopped. boom"


def test_today_endpoint_is_plain_and_read_only(client):
    c, cfg = client
    before = sha(cfg.brain_db)
    t = c.get("/api/today").json()
    assert t["headline"]["title"].startswith("Step 1 of 5")
    assert t["steps"][0]["key"] == "research"
    assert any(i["kind"] == "run" and i["ref"] == "RUN-abc" for i in t["timeline"])
    assert c.get("/api/runs/described").json()[0]["title"] == "Research run"
    assert c.get("/api/runs/RUN-abc").json()["summary"]["status"] == "failed"
    assert sha(cfg.brain_db) == before


@pytest.mark.parametrize(("subject", "expected"), [
    ("feat(backtest): two-phase runner", ("Built: backtest", "two-phase runner")),
    ("[verified] fix(scout): ground evidence", ("Fixed: scout", "ground evidence")),
    ("docs: plan Gate F", ("Plan or notes updated", "plan Gate F")),
    ("Preserve experimental work", ("Code change", "Preserve experimental work")),
])
def test_commit_subjects_become_plain_labels(subject, expected):
    assert summary.describe_commit(subject) == expected


def test_review_notes_count_and_drive_the_headline(brain):
    root, db = brain
    reviews = root / "brain" / "05_Reviews"
    reviews.mkdir(parents=True)
    (reviews / "SC-0002-adversarial-review.md").write_text(
        "---\ncard: brain/03_Strategy_Cards/SC-0002-rsi2.md\ndate: 2026-09-29\nreviewer: Claude\n---\n\n"
        "# Review\n\n## Review verdict: **reject — \"no edge shown\" is upheld**\n", encoding="utf-8")
    notes = readers.review_notes(root)
    assert notes[0]["strategy_id"] == "SC-0002" and notes[0]["verdict"] == "reject"
    assert notes[0]["verdict_text"] == 'reject: "no edge shown" is upheld'
    assert readers.effective_counts(root, db)["reviews"] == 1
    assert readers.lab(root, db)["reviews"][0]["source"] == "note"
    counts = dict.fromkeys(("sources", "price_datasets", "strategy_cards", "backtests",
                            "reviews"), 1)
    h = summary.headline(counts, notes[0])
    assert h["title"] == "SC-0002 finished all 5 steps"
    assert h["detail"].startswith('The review rejected it ("no edge shown" is upheld).')
    assert "normal, honest result" in h["detail"]


# --- Phase A market snapshot truthfulness -----------------------------------------------


def _write_snapshot(cfg, payload: object) -> None:
    path = cfg.project_root / "data/processed/market_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")


def test_terminal_loads_tested_state_helpers_before_the_main_script(client):
    c, _ = client

    html = c.get("/").text

    assert html.index('/static/state.js') < html.index('/static/app.js')
    assert c.get("/static/state.js").status_code == 200


def test_market_snapshot_returns_cached_provenance_and_missing_symbols(client):
    c, cfg = client
    payload = {
        "generated_at": "2026-10-22T12:00:00+00:00",
        "universe": "starter",
        "missing": ["IWM"],
        "rows": [{
            "symbol": "SPY",
            "close": 765.61,
            "change_1d_pct": -0.74,
            "last_date": "2026-09-28",
            "provenance": {
                "source": "yfinance",
                "freshness": "END OF DAY",
                "last_date": "2026-09-28",
            },
        }],
        "presets": [],
    }
    _write_snapshot(cfg, payload)

    response = c.get("/api/market/snapshot")

    assert response.status_code == 200
    assert response.json()["rows"][0]["provenance"]["source"] == "yfinance"
    assert response.json()["missing"] == ["IWM"]


@pytest.mark.parametrize("payload", [
    "{not-json",
    {
        "generated_at": "2026-10-22T12:00:00+00:00",
        "universe": "starter",
        "missing": [],
        "rows": [{
            "symbol": "SPY",
            "close": "NaN",
            "change_1d_pct": 0,
            "last_date": "2026-09-28",
            "provenance": {"source": "yfinance", "freshness": "END OF DAY",
                           "last_date": "2026-09-28"},
        }],
        "presets": [],
    },
])
def test_market_snapshot_fails_closed_on_invalid_cache(client, payload):
    c, cfg = client
    _write_snapshot(cfg, payload)

    response = c.get("/api/market/snapshot")

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Invalid cached market snapshot:")
