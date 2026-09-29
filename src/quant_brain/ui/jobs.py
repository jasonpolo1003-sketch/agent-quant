"""Allowlisted terminal jobs: health checks, data refresh, scheduled agent prompts.

There is no arbitrary shell. Each kind maps to fixed commands or a fixed
backend call, with a timeout, a per-day cap and one run per kind at a time.
Every run is recorded in ``db/terminal.sqlite`` and as ``agent_events`` rows in
the brain via ``quant_brain.ops.events`` (the terminal's only brain write).
"""

from __future__ import annotations

import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import frontmatter

from quant_brain.ops.events import record_event
from quant_brain.ui import readers, store
from quant_brain.ui.backends import BackendError, get_backend

AGENT_ROLE = "brain_terminal"
PROP_007_FREEZE = (
    "Research runs are frozen by PROP-007 (2026-09-28). Lifting the freeze needs Jason's "
    "approval of a plan change, not a terminal setting."
)
DEFAULT_SYMBOLS = ["SPY", "QQQ", "IWM"]


@dataclass(frozen=True)
class JobKind:
    kind: str
    label: str
    timeout: int
    description: str
    enabled: bool = True
    config_keys: tuple[str, ...] = field(default_factory=tuple)


KINDS: dict[str, JobKind] = {
    "health_check": JobKind("health_check", "Health check", 1800,
                            "pytest, ruff, receipt verifier and market-data verifier"),
    "data_refresh": JobKind("data_refresh", "Market data refresh", 900,
                            "Fetch daily bars as new immutable datasets, then verify",
                            config_keys=("symbols", "start")),
    "agent_prompt": JobKind("agent_prompt", "Agent prompt", 600,
                            "Send a saved prompt to a read-only model; output lands in "
                            "terminal/scheduled/, never promoted",
                            config_keys=("prompt", "context", "backend")),
    "research_run": JobKind("research_run", "Research run", 0, PROP_007_FREEZE, enabled=False),
}
CONTEXT_OPTIONS = {
    "git_today": "Commits and uncommitted changes from the last 24 hours",
    "events_today": "Harness events from the last 24 hours",
    "plan_next": "PLAN.md §10 checkpoint headings and the next step",
    "lab": "Strategy cards, backtests and reviews",
}


class JobRefused(RuntimeError):
    pass


@dataclass
class JobContext:
    project_root: Path
    brain_db: Path
    terminal_db: Path
    python: str = sys.executable
    record_events: bool = True


@dataclass
class StepResult:
    name: str
    exit_code: int
    output: str


def validate_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    from quant_brain.ui.winsched import validate_cadence

    job_id = str(schedule.get("job_id") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,23}", job_id):
        raise ValueError("job_id must be 2-24 lowercase letters, digits, '-' or '_'")
    kind = schedule.get("kind")
    if kind not in KINDS:
        raise ValueError(f"unknown job kind {kind!r}; allowed: {', '.join(KINDS)}")
    config = dict(schedule.get("config") or {})
    unknown = set(config) - set(KINDS[kind].config_keys)
    if unknown:
        raise ValueError(f"unexpected config for {kind}: {', '.join(sorted(unknown))}")
    if kind == "data_refresh":
        symbols = config.get("symbols") or DEFAULT_SYMBOLS
        if not all(isinstance(s, str) and re.fullmatch(r"[A-Z][A-Z0-9.^-]{0,9}", s)
                   for s in symbols):
            raise ValueError("symbols must be ticker strings like SPY")
        config["symbols"] = list(symbols)
        config["start"] = str(config.get("start") or "2000-01-01")
        datetime.strptime(config["start"], "%Y-%m-%d")
    if kind == "agent_prompt":
        if not str(config.get("prompt") or "").strip():
            raise ValueError("agent_prompt needs a prompt")
        bad = set(config.get("context") or []) - set(CONTEXT_OPTIONS)
        if bad:
            raise ValueError(f"unknown context: {', '.join(sorted(bad))}")
        config["backend"] = config.get("backend") or "claude"
    max_runs = int(schedule.get("max_runs_per_day", 4))
    if not 1 <= max_runs <= 48:
        raise ValueError("max_runs_per_day must be 1-48")
    return {
        "job_id": job_id, "name": str(schedule.get("name") or job_id)[:80], "kind": kind,
        "cadence": validate_cadence(schedule.get("cadence") or {}), "config": config,
        "enabled": bool(schedule.get("enabled")) and KINDS[kind].enabled,
        "max_runs_per_day": max_runs,
    }


def _new_run_id() -> str:
    return f"JOB-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"


def _event(ctx: JobContext, run_id: str, kind: str, status: str, event_type: str,
           message: str, payload: dict[str, Any] | None = None) -> None:
    if ctx.record_events:
        record_event(ctx.brain_db, run_id=run_id, agent_role=AGENT_ROLE, stage=kind,
                     status=status, event_type=event_type, message=message, payload=payload)


def _check_caps(ctx: JobContext, job: dict[str, Any]) -> None:
    kind = KINDS[job["kind"]]
    for run in store.running_runs(ctx.terminal_db, job["kind"]):
        started = datetime.fromisoformat(run["started_at"])
        if datetime.now(UTC) - started > timedelta(seconds=kind.timeout * 2):
            store.mark_stale(ctx.terminal_db, run["run_id"], "stale: runner never finished")
        else:
            raise JobRefused(f"another {job['kind']} job is running ({run['run_id']})")
    since = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec="seconds")
    if store.runs_started_since(ctx.terminal_db, job["job_id"], since) >= job["max_runs_per_day"]:
        raise JobRefused(f"{job['job_id']} already ran {job['max_runs_per_day']} times in 24h")


def _run(cmd: list[str], cwd: Path, timeout: int) -> StepResult:
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
        return StepResult(" ".join(cmd[1:3]), done.returncode, done.stdout + done.stderr)
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return StepResult(" ".join(cmd[1:3]), 124, f"{out}\nTIMEOUT after {timeout}s")


def _pytest_summary(output: str) -> str:
    lines = [ln.strip("= ").strip() for ln in output.splitlines()
             if re.search(r"\d+ (passed|failed|error)", ln)]
    return lines[-1] if lines else "no pytest summary"


def run_health_check(ctx: JobContext, job: dict[str, Any]) -> tuple[bool, str, str]:
    steps = [
        ("pytest", [ctx.python, "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
        ("ruff", [ctx.python, "-m", "ruff", "check", "src", "tests", "scripts"]),
        ("receipts", [ctx.python, "scripts/verify_receipts.py"]),
        ("market data", [ctx.python, "scripts/verify_market_data.py"]),
    ]
    results, parts = [], []
    budget = KINDS["health_check"].timeout
    for name, cmd in steps:
        result = _run(cmd, ctx.project_root, budget)
        results.append((name, result))
        detail = _pytest_summary(result.output) if name == "pytest" else (
            "ok" if result.exit_code == 0 else f"exit {result.exit_code}")
        parts.append(f"{name}: {detail}")
    ok = all(r.exit_code == 0 for _, r in results)
    log = "\n\n".join(f"### {n} (exit {r.exit_code})\n{r.output}" for n, r in results)
    return ok, "; ".join(parts), log


def run_data_refresh(ctx: JobContext, job: dict[str, Any]) -> tuple[bool, str, str]:
    cfg = job["config"]
    budget = KINDS["data_refresh"].timeout
    fetch = _run([ctx.python, "scripts/fetch_market_data.py", "--symbols", *cfg["symbols"],
                  "--start", cfg["start"]], ctx.project_root, budget)
    verify = _run([ctx.python, "scripts/verify_market_data.py"], ctx.project_root, 300)
    ok = fetch.exit_code == 0 and verify.exit_code == 0
    fails = [ln for ln in fetch.output.splitlines() if ln.startswith("FAIL")]
    summary = (f"fetched {', '.join(cfg['symbols'])}; " +
               (f"{len(fails)} failed; " if fails else "") +
               ("verifier ok" if verify.exit_code == 0 else f"verifier exit {verify.exit_code}"))
    return ok, summary, f"### fetch\n{fetch.output}\n\n### verify\n{verify.output}"


def _context_block(ctx: JobContext, keys: list[str]) -> str:
    since = datetime.now(UTC) - timedelta(days=1)
    parts = []
    if "plan_next" in keys:
        cp = readers.plan_checkpoint(ctx.project_root)
        parts.append("## PLAN.md §10\n" + "\n".join(f"- {e}" for e in cp["entries"]) +
                     f"\nNext: {cp['next']}")
    if "git_today" in keys:
        git = readers.git_activity(ctx.project_root, 50)
        recent = [c for c in git["commits"]
                  if datetime.fromisoformat(c["date"]).astimezone(UTC) >= since]
        parts.append("## Commits, last 24h\n" + ("\n".join(
            f"- {c['short']} {c['date'][:16]} {c['subject']}" for c in recent) or "(none)") +
            "\n## Uncommitted changes\n" + ("\n".join(
                f"- {c['code']} {c['path']}" for c in git["changes"][:60]) or "(none)"))
    if "events_today" in keys:
        evs = [e for e in readers.events(ctx.brain_db, limit=400)
               if str(e.get("created_at", "")) >= since.strftime("%Y-%m-%d %H:%M:%S")]
        parts.append("## Harness events, last 24h\n" + ("\n".join(
            f"- {e['created_at']} {e['run_id']} {e['agent_role']} {e['stage']} {e['status']}: "
            f"{(e.get('message') or '')[:160]}" for e in reversed(evs)) or "(none)"))
    if "lab" in keys:
        lab = readers.lab(ctx.project_root, ctx.brain_db)
        parts.append("## Lab\n" + "\n".join(
            [f"- card {c['strategy_id']}: {c['title']} ({c['status']})" for c in lab["cards"]] +
            [f"- backtest {b['backtest_id']} status {b['status']} sharpe {b.get('sharpe')}"
             for b in lab["backtests"]] +
            [f"- review {r['review_id']} verdict {r['verdict']}" for r in lab["reviews"]]
        ))
    return "\n\n".join(parts)


AGENT_PROMPT_SYSTEM = (
    "You write short, factual status notes for Jason's local quant research harness. "
    "Use only the context given. Say plainly when something failed or is missing. "
    "Never claim a backtest proves future profit. Plain Markdown, under 300 words."
)


def run_agent_prompt(ctx: JobContext, job: dict[str, Any]) -> tuple[bool, str, str, str]:
    cfg = job["config"]
    context = _context_block(ctx, list(cfg.get("context") or []))
    prompt = (f"<context>\n{context}\n</context>\n\n" if context else "") + cfg["prompt"]
    backend = get_backend(cfg.get("backend", "claude"))
    try:
        text = "".join(backend.stream(AGENT_PROMPT_SYSTEM, prompt,
                                      timeout=KINDS["agent_prompt"].timeout))
    except BackendError as exc:
        return False, f"backend failed: {exc}", str(exc), ""
    folder = ctx.project_root / "terminal" / "scheduled"
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    path = folder / f"{now:%Y-%m-%dT%H%M%S}-{job['job_id']}.md"
    post = frontmatter.Post(text.strip() + "\n", title=job["name"], type="scheduled_output",
                            trusted=False, job_id=job["job_id"], backend=backend.name,
                            created=now.isoformat(timespec="seconds"))
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    rel = path.relative_to(ctx.project_root).as_posix()
    return True, f"wrote {rel}", text, rel


def run_job(ctx: JobContext, job: dict[str, Any], trigger: str) -> dict[str, Any]:
    """Run one job now. Returns the finished ``job_runs`` row. Never raises for job failure."""
    run_id = _new_run_id()
    kind = KINDS.get(job["kind"])
    if kind is None or not kind.enabled:
        reason = PROP_007_FREEZE if job["kind"] == "research_run" else f"kind {job['kind']} " \
                 "is not allowed"
        store.record_refusal(ctx.terminal_db, run_id, job["job_id"], job["kind"], trigger, reason)
        _event(ctx, run_id, job["kind"], "refused", "job_refused", reason)
        return store.list_runs(ctx.terminal_db, job_id=job["job_id"], limit=1)[0]
    try:
        _check_caps(ctx, job)
    except JobRefused as exc:
        store.record_refusal(ctx.terminal_db, run_id, job["job_id"], job["kind"], trigger, str(exc))
        _event(ctx, run_id, job["kind"], "refused", "job_refused", str(exc))
        return store.list_runs(ctx.terminal_db, job_id=job["job_id"], limit=1)[0]

    store.start_run(ctx.terminal_db, run_id, job["job_id"], job["kind"], trigger)
    _event(ctx, run_id, job["kind"], "started", "job_started", f"{job['name']} ({trigger})",
           {"job_id": job["job_id"]})
    output_path = None
    try:
        if job["kind"] == "health_check":
            ok, summary, log = run_health_check(ctx, job)
        elif job["kind"] == "data_refresh":
            ok, summary, log = run_data_refresh(ctx, job)
        else:
            ok, summary, log, output_path = run_agent_prompt(ctx, job)
    except Exception as exc:  # a crashing job is recorded as failed, never left 'running'
        ok, summary, log = False, f"{type(exc).__name__}: {exc}", repr(exc)
    logs = ctx.project_root / "terminal" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{run_id}.log").write_text(log, encoding="utf-8")
    status = "completed" if ok else "failed"
    store.finish_run(ctx.terminal_db, run_id, status=status, exit_code=0 if ok else 1,
                     summary=summary, output_path=output_path, log_tail=log[-4000:])
    _event(ctx, run_id, job["kind"], status, "job_finished", summary[:500],
           {"job_id": job["job_id"], "output_path": output_path})
    return store.list_runs(ctx.terminal_db, job_id=job["job_id"], limit=1)[0]


DEFAULT_SCHEDULES = [
    {"job_id": "nightly-health", "name": "Nightly health check", "kind": "health_check",
     "cadence": {"type": "daily", "time": "02:00"}, "config": {}, "max_runs_per_day": 4},
    {"job_id": "weekly-etf-refresh", "name": "Weekly ETF bars refresh", "kind": "data_refresh",
     "cadence": {"type": "weekly", "days": ["SAT"], "time": "09:00"},
     "config": {"symbols": DEFAULT_SYMBOLS, "start": "2000-01-01"}, "max_runs_per_day": 1},
    {"job_id": "daily-digest", "name": "What changed today", "kind": "agent_prompt",
     "cadence": {"type": "daily", "time": "21:00"},
     "config": {"prompt": "Summarise what changed in the project today: what was built, what "
                          "failed, and the single next step. Cite commit hashes and run ids.",
                "context": ["git_today", "events_today", "plan_next", "lab"],
                "backend": "claude"},
     "max_runs_per_day": 2},
    {"job_id": "rsi-research", "name": "RSI exit research", "kind": "research_run",
     "cadence": {"type": "weekly", "days": ["SUN"], "time": "10:00"}, "config": {},
     "max_runs_per_day": 1},
]


def seed_defaults(terminal_db: Path) -> None:
    """Example schedules, all disabled. Enabling one registers it with Task Scheduler."""
    existing = {s["job_id"] for s in store.list_schedules(terminal_db)}
    for schedule in DEFAULT_SCHEDULES:
        if schedule["job_id"] not in existing:
            store.upsert_schedule(terminal_db, validate_schedule({**schedule, "enabled": False}))
