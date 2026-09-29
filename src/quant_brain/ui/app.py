"""FastAPI app for the Brain Terminal. Local only: bind to 127.0.0.1."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from quant_brain.data.market_data import MarketDataError
from quant_brain.ui import jobs, readers, sessions, skills, store, summary, tutor, winsched
from quant_brain.ui.backends import BACKENDS, BackendError, get_backend

STATIC_DIR = Path(__file__).resolve().parents[3] / "ui" / "static"


@dataclass
class TerminalConfig:
    project_root: Path
    brain_db: Path
    terminal_db: Path
    claude_home: Path = field(default_factory=lambda: Path.home() / ".claude")
    codex_home: Path = field(default_factory=lambda: Path.home() / ".codex")
    python: str = sys.executable
    port: int = 8765
    scheduler_enabled: bool = sys.platform == "win32"
    record_events: bool = True

    def job_context(self) -> jobs.JobContext:
        return jobs.JobContext(self.project_root, self.brain_db, self.terminal_db, self.python,
                               self.record_events)


def create_app(config: TerminalConfig) -> FastAPI:
    app = FastAPI(title="Brain Terminal", docs_url=None, redoc_url=None, openapi_url=None)
    root = config.project_root
    jobs.seed_defaults(config.terminal_db)
    backend_cache: dict[str, Any] = {"at": 0.0, "value": None}

    def _probe_backends() -> None:
        backend_cache["value"] = [vars(b.status()) for b in BACKENDS.values()]
        backend_cache["at"] = time.monotonic()

    # Warm the slow CLI probe in the background so LEARN opens instantly.
    threading.Thread(target=_probe_backends, daemon=True).start()

    allowed_hosts = {f"127.0.0.1:{config.port}", f"localhost:{config.port}"}

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        # DNS-rebinding guard: only answer to our own host names.
        if request.headers.get("host") not in allowed_hosts:
            return JSONResponse({"detail": "forbidden host"}, status_code=403)
        # Cross-site request guard for anything that changes state.
        if request.method not in ("GET", "HEAD"):
            origin = request.headers.get("origin")
            if origin and origin.split("://", 1)[-1] not in allowed_hosts:
                return JSONResponse({"detail": "forbidden origin"}, status_code=403)
            if request.headers.get("x-brain-terminal") != "1":
                return JSONResponse({"detail": "missing terminal header"}, status_code=403)
        return await call_next(request)

    # --- overview -----------------------------------------------------------------

    @app.get("/api/home")
    def home() -> dict[str, Any]:
        counts = readers.brain_counts(config.brain_db)
        git = readers.git_activity(root, 8)
        health = store.list_runs(config.terminal_db, limit=200)
        last_health = next((r for r in health if r["kind"] == "health_check"
                            and r["status"] in ("completed", "failed")), None)
        return {
            "counts": counts, "pipeline": readers.pipeline(counts),
            "checkpoint": readers.plan_checkpoint(root), "git": git,
            "last_health": last_health, "recent_jobs": health[:6],
            "runs": readers.runs(config.brain_db, 6),
            "project_root": str(root),
        }

    def _described_runs(limit: int) -> list[dict[str, Any]]:
        out = []
        for run in readers.runs(config.brain_db, limit):
            evs = readers.events(config.brain_db, run_id=run["run_id"], limit=5000)
            if evs:
                out.append(summary.describe_run(evs))
        return out

    @app.get("/api/today")
    def today() -> dict[str, Any]:
        counts = readers.brain_counts(config.brain_db)
        git = readers.git_activity(root, 12)
        job_runs = store.list_runs(config.terminal_db, limit=12)
        last_health = next((r for r in job_runs if r["kind"] == "health_check"
                            and r["status"] in ("completed", "failed")), None)
        return {
            "headline": summary.headline(counts),
            "steps": summary.steps(counts),
            "next": readers.plan_checkpoint(root)["next"],
            "timeline": summary.timeline(git["commits"], _described_runs(8), job_runs),
            "health": last_health,
            "git": {"branch": git["branch"], "head": git["head"],
                    "uncommitted": len(git["changes"])},
        }

    @app.get("/api/runs/described")
    def described_runs(limit: int = 40):
        return _described_runs(min(limit, 200))

    # --- runs & events ---------------------------------------------------------------

    @app.get("/api/events")
    def events(after: int | None = None, run_id: str | None = None, limit: int = 200):
        return readers.events(config.brain_db, after_id=after, run_id=run_id,
                              limit=min(limit, 1000))

    @app.get("/api/runs")
    def runs(limit: int = 50):
        return readers.runs(config.brain_db, min(limit, 500))

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str):
        evs = readers.events(config.brain_db, run_id=run_id, limit=2000)
        if not evs:
            raise HTTPException(404, "no such run")
        receipt = root / "brain/00_Inbox/Failed_Runs" / f"{run_id}.md"
        return {"run_id": run_id, "events": evs, "summary": summary.describe_run(evs),
                "receipt": receipt.relative_to(root).as_posix() if receipt.is_file() else None}

    @app.get("/api/activity")
    def activity():
        return {
            "git": readers.git_activity(root, 30),
            "claude": sessions.claude_sessions(config.claude_home, root, 10),
            "codex": sessions.codex_sessions(config.codex_home, root, 10),
        }

    @app.get("/api/stream")
    async def stream(request: Request, after: int | None = None):
        async def gen():
            last = after if after is not None else await run_in_threadpool(
                readers.max_event_id, config.brain_db)
            last_job = None
            last_head = None
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                new = await run_in_threadpool(readers.events, config.brain_db, after_id=last,
                                              limit=200)
                for ev in new:
                    last = ev["event_id"]
                    yield f"event: harness\ndata: {json.dumps(ev, default=str)}\n\n"
                recent = await run_in_threadpool(store.list_runs, config.terminal_db, limit=1)
                marker = (recent[0]["run_id"], recent[0]["status"]) if recent else None
                if marker != last_job:
                    if last_job is not None and recent:
                        yield f"event: job\ndata: {json.dumps(recent[0], default=str)}\n\n"
                    last_job = marker
                head = await run_in_threadpool(readers._git, root, "rev-parse", "--short", "HEAD")
                head = head.strip()
                if head != last_head:
                    if last_head is not None:
                        yield f"event: git\ndata: {json.dumps({'head': head})}\n\n"
                    last_head = head
                yield ": keepalive\n\n"
                await asyncio.sleep(1.5)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    # --- tasks & schedules -----------------------------------------------------------

    @app.get("/api/tasks")
    def tasks():
        return {"agent_tasks": readers.agent_tasks(config.brain_db),
                "research_questions": readers.research_questions(config.brain_db)}

    @app.get("/api/schedules")
    def schedules():
        items = store.list_schedules(config.terminal_db)
        registered = winsched.registered() if config.scheduler_enabled else {}
        for item in items:
            item["cadence_text"] = winsched.describe_cadence(item["cadence"])
            item["task"] = registered.get(item["job_id"])
            item["kind_enabled"] = jobs.KINDS[item["kind"]].enabled
        return {
            "schedules": items,
            "runs": store.list_runs(config.terminal_db, limit=60),
            "kinds": [{"kind": k.kind, "label": k.label, "description": k.description,
                       "enabled": k.enabled, "timeout": k.timeout} for k in jobs.KINDS.values()],
            "context_options": jobs.CONTEXT_OPTIONS,
            "scheduler": {"available": config.scheduler_enabled,
                          "drift": winsched.drift(items, registered)
                          if config.scheduler_enabled else []},
        }

    def _save(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            job = jobs.validate_schedule(payload)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if payload.get("enabled") and not jobs.KINDS[job["kind"]].enabled:
            raise HTTPException(409, jobs.KINDS[job["kind"]].description)
        if config.scheduler_enabled:
            try:
                winsched.sync(job, root, config.python)
            except winsched.SchedulerError as exc:
                raise HTTPException(502, f"Task Scheduler refused: {exc}") from exc
        return store.upsert_schedule(config.terminal_db, job)

    @app.post("/api/schedules")
    async def create_schedule(request: Request):
        payload = await request.json()
        if store.get_schedule(config.terminal_db, str(payload.get("job_id"))):
            raise HTTPException(409, "a schedule with that id exists")
        return await run_in_threadpool(_save, payload)

    @app.put("/api/schedules/{job_id}")
    async def update_schedule(job_id: str, request: Request):
        current = store.get_schedule(config.terminal_db, job_id)
        if not current:
            raise HTTPException(404, "no such schedule")
        payload = {**current, **(await request.json()), "job_id": job_id}
        return await run_in_threadpool(_save, payload)

    @app.delete("/api/schedules/{job_id}")
    def delete_schedule(job_id: str):
        if config.scheduler_enabled:
            winsched.unregister(job_id)
        return {"deleted": store.delete_schedule(config.terminal_db, job_id)}

    @app.post("/api/schedules/{job_id}/run")
    async def run_now(job_id: str):
        job = store.get_schedule(config.terminal_db, job_id)
        if not job:
            raise HTTPException(404, "no such schedule")
        # Run in the background so the page stays responsive; the stream reports the result.
        asyncio.get_running_loop().run_in_executor(
            None, jobs.run_job, config.job_context(), job, "manual")
        return {"started": True}

    @app.get("/api/job-runs/{run_id}/log")
    def job_log(run_id: str):
        path = root / "terminal" / "logs" / f"{run_id}.log"
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise HTTPException(404, "no log")
        return {"run_id": run_id, "log": path.read_text(encoding="utf-8", errors="replace")}

    # --- skills ---------------------------------------------------------------------

    @app.get("/api/skills")
    def skills_catalog():
        return skills.skills(root, config.claude_home, config.codex_home)

    # --- markets & lab --------------------------------------------------------------

    @app.get("/api/datasets")
    def datasets():
        return readers.datasets(root, config.brain_db)

    @app.get("/api/datasets/{dataset_id}/bars")
    def bars(dataset_id: str):
        try:
            return readers.bars(root, config.brain_db, dataset_id)
        except MarketDataError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/lab")
    def lab():
        return readers.lab(root, config.brain_db)

    @app.get("/api/lab/{backtest_id}/equity")
    def equity(backtest_id: str):
        found = [b for b in readers.lab(root, config.brain_db)["backtests"]
                 if b["backtest_id"] == backtest_id]
        if not found:
            raise HTTPException(404, "no such backtest")
        return readers.equity_series(root, found[0])

    # --- learn ----------------------------------------------------------------------

    @app.get("/api/learn/sources")
    def learn_sources():
        return tutor.list_sources(root)

    @app.get("/api/file")
    def read_file(path: str):
        try:
            return {"path": path, "text": tutor.read_source(root, path)}
        except tutor.SourceError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/journal")
    def journal():
        return readers.journal(root)

    @app.post("/api/learn/ask")
    async def ask(request: Request):
        body = await request.json()
        question = str(body.get("question") or "").strip()
        if not question:
            raise HTTPException(422, "ask a question")
        sources = [str(s) for s in body.get("sources") or []]
        virtual = {}
        for name in sources:
            if name.startswith("run:"):
                evs = readers.events(config.brain_db, run_id=name[4:], limit=2000)
                virtual[name] = "\n".join(
                    f"{e['created_at']} #{e['event_id']} {e['agent_role']} {e['stage']} "
                    f"{e['event_type']} {e['status']}: {e.get('message') or ''}"
                    + (f" payload={json.dumps(e['payload'])[:1500]}" if e.get("payload") else "")
                    for e in evs) or "(no events recorded for this run)"
        try:
            backend = get_backend(str(body.get("backend") or "claude"))
            context, report = tutor.build_context(root, sources, virtual=virtual)
        except (tutor.SourceError, BackendError) as exc:
            raise HTTPException(422, str(exc)) from exc
        prompt = tutor.build_prompt(context, question, body.get("history") or [])

        def chunks():
            yield json.dumps({"type": "sources", "sources": report}) + "\n"
            try:
                for text in backend.stream(tutor.TEACHER_SYSTEM, prompt):
                    yield json.dumps({"type": "text", "text": text}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
            except Exception as exc:  # surface backend failures to the page
                yield json.dumps({"type": "error", "error": str(exc)}) + "\n"

        return StreamingResponse(iterate_in_threadpool(chunks()),
                                 media_type="application/x-ndjson")

    @app.get("/api/learn/notes")
    def notes():
        return tutor.list_notes(root)

    @app.post("/api/learn/notes")
    async def save_note(request: Request):
        body = await request.json()
        if not str(body.get("answer") or "").strip():
            raise HTTPException(422, "nothing to save")
        path = tutor.save_note(root, title=str(body.get("title") or body.get("question") or
                                               "Study note")[:100],
                               question=str(body.get("question") or ""),
                               answer=str(body["answer"]),
                               sources=list(body.get("sources") or []),
                               backend=str(body.get("backend") or "claude"))
        return {"path": path}

    # --- settings -------------------------------------------------------------------

    @app.get("/api/backends")
    def backends(refresh: bool = False):
        # Probing CLIs takes seconds; cache for a minute so screens stay quick.
        if refresh or backend_cache["value"] is None or time.monotonic() - backend_cache["at"] > 60:
            _probe_backends()
        return backend_cache["value"]

    # --- static ---------------------------------------------------------------------

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
