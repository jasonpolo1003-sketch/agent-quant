from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.ops.events import record_event
from quant_brain.research.intake import update_research_status
from quant_brain.research.live_discovery import (
    DiscoveryCandidate,
    dedupe_and_rank,
    fetch_with_jina,
    run_yahoo_search,
    save_source_snapshot,
)
from quant_brain.research.live_worker import extract_research_with_models

AGENT_REACH_EXE = Path("C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe")


def run_agent_reach_doctor() -> dict[str, Any]:
    command = str(AGENT_REACH_EXE) if AGENT_REACH_EXE.exists() else "agent-reach"
    completed = subprocess.run(
        [command, "doctor", "--json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return json.loads(completed.stdout)


def _get_task(db_path: str | Path, research_id: str) -> dict[str, Any]:
    init_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM research_questions WHERE research_id = ?", (research_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"research_id not found: {research_id}")
    return dict(row)


def _curator_payload(worker_payload: dict[str, Any]) -> dict[str, Any]:
    sources = []
    for item in worker_payload.get("sources", []):
        source = dict(item)
        source["url_or_citation"] = source.pop("url")
        source["evidence"] = source.pop("evidence_quote")
        source.pop("source_id", None)
        sources.append(source)
    return {
        "research_id": worker_payload["research_id"],
        "status": "raw_saved",
        "sources": sources,
        "open_questions": list(worker_payload.get("open_questions") or []),
        "curator_recommendation": worker_payload.get(
            "curator_recommendation", "needs_more_work"
        ),
    }


def _write_raw_note(
    project_root: str | Path,
    task: dict[str, Any],
    run_id: str,
    worker_result: dict[str, Any],
) -> str:
    root = Path(project_root)
    out_dir = root / "brain" / "00_Inbox" / "Raw_Research"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task['research_id']}.md"
    payload = _curator_payload(worker_result["payload"])
    attempts = worker_result.get("attempts", [])
    attempt_lines = "\n".join(
        f"- {item.get('model', 'unknown')}: {item.get('validation', {}).get('passed', False)}"
        for item in attempts
    ) or "- None"
    text = f"""---
id: {task['research_id']}
type: raw_research
status: raw_saved
method_family: {task.get('method_family') or 'unclassified'}
assigned_agent: live_research_executor
run_id: {run_id}
---

# Raw Research Note — {task['research_id']}

## Research Question

{task['question']}

## Live Research Run

- Run ID: `{run_id}`
- Discovery router: Agent Reach / upstream web search
- Evidence worker attempts:
{attempt_lines}

## Scout Decision

{worker_result['payload'].get('decision', 'needs_more_work')}

## Required JSON Block

```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```
"""
    path.write_text(text, encoding="utf-8")
    return str(path)


def execute_live_research(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    research_id: str,
    run_id: str | None = None,
    searcher: Callable[[str], list[DiscoveryCandidate]] = run_yahoo_search,
    fetcher: Callable[[str], str] = fetch_with_jina,
    worker: Callable[[str, str, list[dict[str, Any]]], dict[str, Any]] = extract_research_with_models,
    doctor: Callable[[], dict[str, Any]] = run_agent_reach_doctor,
    max_candidates: int = 15,
    max_sources: int = 5,
) -> dict[str, Any]:
    task = _get_task(db_path, research_id)
    run_id = run_id or f"RUN-{uuid4().hex[:10]}"
    update_research_status(db_path, research_id, "researching")

    record_event(
        db_path,
        run_id=run_id,
        task_id=research_id,
        agent_role="orchestrator",
        stage="run",
        status="running",
        event_type="run_started",
        message=task["question"],
    )

    try:
        health = doctor()
        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="research_scout",
            stage="discovery",
            status="running",
            event_type="health_checked",
            message="Agent Reach health check completed",
            payload={"channels": health},
        )

        candidates = dedupe_and_rank(
            searcher(task["question"]), task["question"], limit=max_candidates
        )
        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="research_scout",
            stage="discovery",
            status="running",
            event_type="candidates_ranked",
            message=f"Ranked {len(candidates)} candidate sources",
            payload={
                "candidates": [
                    {
                        "title": item.title,
                        "url": item.url,
                        "quality": item.source_quality,
                        "score": item.score,
                    }
                    for item in candidates
                ]
            },
        )

        snapshots = []
        for candidate in candidates:
            if len(snapshots) >= max_sources:
                break
            try:
                fetched = fetcher(candidate.url)
            except Exception as exc:
                record_event(
                    db_path,
                    run_id=run_id,
                    task_id=research_id,
                    agent_role="research_scout",
                    stage="fetch",
                    status="warning",
                    event_type="source_fetch_failed",
                    message=f"{candidate.url}: {exc}",
                )
                continue
            source_id = f"S{len(snapshots) + 1}"
            snapshot = save_source_snapshot(
                project_root,
                research_id=research_id,
                source_id=source_id,
                candidate=candidate,
                fetched_text=fetched,
            )
            snapshots.append(snapshot)
            record_event(
                db_path,
                run_id=run_id,
                task_id=research_id,
                agent_role="research_scout",
                stage="fetch",
                status="running",
                event_type="source_snapshotted",
                message=f"{source_id}: {candidate.title}",
                payload={
                    "source_id": source_id,
                    "url": candidate.url,
                    "snapshot_path": snapshot["snapshot_path"],
                },
            )

        if not snapshots:
            raise ValueError("no source snapshots were fetched")

        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="research_scout",
            stage="fetch",
            status="completed",
            event_type="handoff_completed",
            message=f"Handed {len(snapshots)} source snapshots to the evidence worker",
        )

        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="qwen3:14b",
            stage="evidence_extraction",
            status="running",
            event_type="handoff_received",
            message=f"Received {len(snapshots)} bounded source snapshots",
        )
        worker_result = worker(research_id, task["question"], snapshots)
        if not worker_result.get("passed"):
            raise ValueError(
                "local model evidence extraction failed: "
                + "; ".join(worker_result.get("validation", {}).get("failures", []))
            )
        attempts = worker_result.get("attempts", [])
        for index, attempt in enumerate(attempts, start=1):
            attempt_validation = attempt.get("validation")
            if not isinstance(attempt_validation, dict):
                attempt_validation = worker_result.get("validation", {})
            attempt_passed = bool(attempt_validation.get("passed"))
            model_name = attempt.get("model", "qwen3:14b")
            record_event(
                db_path,
                run_id=run_id,
                task_id=research_id,
                agent_role=model_name,
                stage="evidence_extraction",
                status="completed" if attempt_passed else "failed",
                event_type="validated_output" if attempt_passed else "validation_failed",
                message=(
                    f"Attempt {index} passed deterministic validation"
                    if attempt_passed
                    else f"Attempt {index} failed deterministic validation"
                ),
                payload={
                    "attempt": index,
                    "elapsed_seconds": attempt.get("elapsed_seconds"),
                    "failures": attempt_validation.get("failures", []),
                },
            )

        raw_note_path = _write_raw_note(project_root, task, run_id, worker_result)
        update_research_status(
            db_path, research_id, "raw_saved", raw_note_path=raw_note_path
        )
        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="knowledge_curator",
            stage="curation",
            status="waiting",
            event_type="handoff_ready",
            message="Validated raw research is ready for curator review",
            payload={"raw_note_path": raw_note_path},
        )
        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="orchestrator",
            stage="run",
            status="completed",
            event_type="run_completed",
            message="Live research run completed",
        )
        return {
            "run_id": run_id,
            "research_id": research_id,
            "status": "raw_saved",
            "raw_note_path": raw_note_path,
            "sources_fetched": len(snapshots),
            "model_attempts": len(attempts),
        }
    except Exception as exc:
        record_event(
            db_path,
            run_id=run_id,
            task_id=research_id,
            agent_role="orchestrator",
            stage="run",
            status="failed",
            event_type="run_failed",
            message=str(exc),
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live bounded research with Agent Reach and Qwen.")
    parser.add_argument("--research-id", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--max-candidates", type=int, default=15)
    parser.add_argument("--max-sources", type=int, default=5)
    args = parser.parse_args()
    result = execute_live_research(
        args.project_root,
        args.db,
        research_id=args.research_id,
        run_id=args.run_id,
        max_candidates=args.max_candidates,
        max_sources=args.max_sources,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
