"""FastAPI app for the Brain Terminal. Local only: bind to 127.0.0.1."""

from __future__ import annotations

import asyncio
import json
import math
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from quant_brain.data.market_data import MarketDataError
from quant_brain.market import calendar as market_cal
from quant_brain.market import live_crypto, risk, screener
from quant_brain.market.universe import latest_accepted, load_universe, provenance, read_frame
from quant_brain.ui import (
    chartdata,
    jobs,
    readers,
    sessions,
    skills,
    store,
    study,
    summary,
    tutor,
    winsched,
)
from quant_brain.ui.backends import BACKENDS, BackendError, get_backend

STATIC_DIR = Path(__file__).resolve().parents[3] / "ui" / "static"

MARKET_NUMERIC_FIELDS = {
    "close", "change_1d_pct", "change_1w_pct", "change_1m_pct", "change_3m_pct",
    "change_1y_pct", "change_ytd_pct", "rsi_2", "rsi_14", "sma_50", "sma_200",
    "vs_sma_50_pct", "vs_sma_200_pct", "volatility_20d_pct", "high_52w", "low_52w",
    "from_52w_high_pct", "from_52w_low_pct", "avg_dollar_volume_20d",
    "drawdown_from_peak_pct", "bars",
}


def _market_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_market_snapshot(snapshot: Any) -> dict[str, Any]:
    """Fail closed when a cached or rebuilt snapshot could fabricate rendered market facts."""
    if not isinstance(snapshot, dict):
        raise ValueError("root must be an object")
    if not isinstance(snapshot.get("rows"), list):
        raise ValueError("rows must be a list")
    if not isinstance(snapshot.get("missing"), list) or not all(
            _market_text(symbol) for symbol in snapshot["missing"]):
        raise ValueError("missing must be a list of symbols")
    if not _market_text(snapshot.get("universe")):
        raise ValueError("universe is required")
    if not isinstance(snapshot.get("presets"), (list, dict)):
        raise ValueError("presets must be a list or object")

    seen: set[str] = set()
    for index, row in enumerate(snapshot["rows"]):
        if not isinstance(row, dict) or not _market_text(row.get("symbol")):
            raise ValueError(f"row {index} needs a symbol")
        if row["symbol"] in seen:
            raise ValueError(f"duplicate symbol {row['symbol']}")
        seen.add(row["symbol"])
        for field_name in MARKET_NUMERIC_FIELDS:
            value = row.get(field_name)
            if value is not None and (
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))):
                raise ValueError(f"row {index} has invalid {field_name}")
        if row.get("last_date") is not None and not _market_text(row["last_date"]):
            raise ValueError(f"row {index} has invalid last_date")
        provenance = row.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(f"row {index} needs provenance")
        for field_name in ("source", "freshness", "last_date"):
            if not _market_text(provenance.get(field_name)):
                raise ValueError(f"row {index} provenance needs {field_name}")
    return snapshot


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
        counts = readers.effective_counts(root, config.brain_db)
        notes = readers.review_notes(root)
        git = readers.git_activity(root, 12)
        job_runs = store.list_runs(config.terminal_db, limit=12)
        last_health = next((r for r in job_runs if r["kind"] == "health_check"
                            and r["status"] in ("completed", "failed")), None)
        return {
            "headline": summary.headline(counts, notes[0] if notes else None),
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

    # --- SC-FUT-0001 study ----------------------------------------------------------

    def _study(fn, *args):
        try:
            return fn(*args)
        except study.StudyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/study")
    def study_overview():
        return study.overview(root)

    @app.get("/api/study/series")
    def study_series(phase: str = "development", key: str = "MNQ.development"):
        return _study(study.series, root, phase, key)

    @app.get("/api/study/days")
    def study_days(phase: str = "development", key: str = "MNQ.development"):
        return study.day_list(root, phase, key)

    @app.get("/api/study/replay")
    def study_replay(day: str, market: str = "MNQ"):
        return _study(study.replay, root, market, day)

    # --- chart workspace ------------------------------------------------------------

    charts = chartdata.ChartData(root, config.brain_db)

    def _chart(fn, *args):
        try:
            return fn(*args)
        except chartdata.ChartError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/chart/watchlist")
    def chart_watchlist(name: str = "starter"):
        return _chart(charts.watchlist, name)

    @app.get("/api/chart/bars")
    def chart_bars(symbol: str, tf: str = "D", basis: str = "split"):
        return _chart(charts.bars, symbol, tf, basis)

    @app.get("/api/chart/indicator-catalog")
    def chart_indicator_catalog():
        return {k: {kk: v[kk] for kk in ("label", "pane", "params", "engine", "about")}
                | {"levels": v.get("levels", [])} for k, v in chartdata.INDICATORS.items()}

    @app.post("/api/chart/indicators")
    async def chart_indicators(request: Request):
        body = await request.json()
        return await run_in_threadpool(
            _chart, charts.indicators, str(body.get("symbol", "")), str(body.get("tf", "D")),
            str(body.get("basis", "split")), list(body.get("specs") or []))

    @app.get("/api/chart/formula")
    def chart_formula(f: str, tf: str = "D", basis: str = "split"):
        return _chart(charts.formula, f, tf, basis)

    @app.get("/api/chart/compare")
    def chart_compare(symbols: str, start: str | None = None, tf: str = "D"):
        return _chart(charts.compare, [s for s in symbols.split(",") if s.strip()], start, tf)

    @app.get("/api/chart/stats")
    def chart_stats(symbol: str, start: str, end: str, benchmark: str = "SPY"):
        return _chart(charts.stats, symbol, start, end, benchmark)

    @app.get("/api/replays")
    def replays():
        return chartdata.list_replays(root)

    @app.get("/api/replays/{replay_id}")
    def replay(replay_id: str):
        try:
            return chartdata.get_replay(root, replay_id)
        except chartdata.ChartError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/drawings")
    def drawings(symbol: str):
        return store.list_drawings(config.terminal_db, symbol)

    @app.post("/api/drawings")
    async def add_drawing(request: Request):
        body = await request.json()
        data = {k: body[k] for k in ("points", "price", "color") if k in body}
        try:
            new_id = store.add_drawing(config.terminal_db, str(body.get("symbol", "")),
                                       str(body.get("kind", "")), data)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"id": new_id}

    @app.delete("/api/drawings")
    def delete_drawings(symbol: str, id: int | None = None):
        return {"deleted": store.delete_drawings(config.terminal_db, symbol, id)}

    # --- risk center ----------------------------------------------------------------

    @app.post("/api/risk/position-size")
    async def risk_position_size(request: Request):
        body = await request.json()
        try:
            account = float(body.get("account", 10000))
            risk_pct = float(body.get("risk_pct", 1))
            entry = float(body.get("entry", 100))
            stop = float(body.get("stop", 98))
            return risk.position_size(account, risk_pct, entry, stop)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/risk/drawdown-table")
    def risk_drawdown_table():
        return {"table": risk.drawdown_table()}

    @app.post("/api/risk/kelly")
    async def risk_kelly(request: Request):
        body = await request.json()
        try:
            win_rate = float(body.get("win_rate", 0.5))
            payoff = float(body.get("payoff", 1.5))
            return risk.kelly_fraction(win_rate, payoff)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/risk/ruin-sim")
    async def risk_ruin_sim(request: Request):
        body = await request.json()
        try:
            win_rate = float(body.get("win_rate", 0.5))
            payoff = float(body.get("payoff", 1.5))
            risk_pct = float(body.get("risk_pct", 2.0))
            trades = int(body.get("trades", 200))
            paths = int(body.get("paths", 2000))
            ruin_drawdown_pct = float(body.get("ruin_drawdown_pct", 50.0))
            return await run_in_threadpool(
                risk.simulate_paths,
                win_rate, payoff, risk_pct,
                trades=trades, paths=paths, ruin_drawdown_pct=ruin_drawdown_pct
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/risk/portfolio-heat")
    async def risk_portfolio_heat(request: Request):
        body = await request.json()
        try:
            account = float(body.get("account", 10000))
            positions = list(body.get("positions", []))
            return risk.portfolio_heat(account, positions)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    # --- market screener & calendar -------------------------------------------------

    @app.get("/api/market/snapshot")
    def market_snapshot(universe_name: str = "starter"):
        path = root / "data" / "processed" / "market_snapshot.json"
        if path.is_file():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                return validate_market_snapshot(cached)
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                raise HTTPException(503, f"Invalid cached market snapshot: {exc}") from exc
        try:
            universe = load_universe(root, universe_name)
            manifests = latest_accepted(root, config.brain_db)
            rows, closes, missing = [], {}, []
            for entry in universe.get("symbols", []):
                manifest = manifests.get(entry["symbol"])
                if manifest is None:
                    missing.append(entry["symbol"])
                    continue
                frame = read_frame(root, manifest)
                rows.append({**entry, **screener.screen_row(frame), "provenance": provenance(manifest)})
                closes[entry["symbol"]] = frame.set_index("date")["adj_close"]
            snapshot = {
                "generated_at": datetime.now(UTC).isoformat(),
                "universe": universe_name,
                "survivorship_note": universe.get("survivorship_note", ""),
                "missing": missing,
                "rows": rows,
                "presets": screener.presets_public(),
                "correlation_1y": risk.correlation_matrix(closes, window=252) if closes else {},
                "note": "End-of-day data. Nothing here is a recommendation to trade.",
            }
            return validate_market_snapshot(snapshot)
        except Exception as exc:
            raise HTTPException(500, f"Unable to load market snapshot: {exc}") from exc

    @app.get("/api/market/calendar")
    def market_calendar():
        path = root / "data" / "processed" / "calendar.json"
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        fomc_events = []
        for d in [
            "2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
            "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"
        ]:
            fomc_events.append({
                "date": d,
                "title": "FOMC Rate Decision & Press Conference",
                "source": "Federal Reserve (Official Calendar)",
                "why": market_cal.FOMC_WHY,
                "importance": "high",
            })
        return {
            "events": fomc_events,
            "note": "To add FRED economic releases (CPI, Jobs, GDP) run 'python scripts/fetch_calendar.py' with FRED_API_KEY in .env.",
        }

    # --- live streaming feeds -------------------------------------------------------

    @app.get("/api/live/crypto")
    async def live_crypto_stream(request: Request, products: str = "BTC-USD,ETH-USD"):
        product_list = [p.strip() for p in products.split(",") if p.strip()]
        async def gen():
            yield "retry: 3000\n\n"
            try:
                async for ev in live_crypto.stream(product_list):
                    if await request.is_disconnected():
                        break
                    yield f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev, default=str)}\n\n"
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                yield f"event: status\ndata: {json.dumps({'type': 'status', 'state': 'error', 'detail': str(exc)})}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

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
        screen = str(body.get("screen_context") or "").strip()
        if screen:  # what the user is looking at right now, sent by an "Explain this" button
            virtual["screen:what-you-are-looking-at"] = screen[:20000]
            sources.insert(0, "screen:what-you-are-looking-at")
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
