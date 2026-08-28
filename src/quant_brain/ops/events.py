from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database


def _decode_payload(raw: str | None) -> dict[str, Any]:
    """Decode a stored payload, tolerating nulls and legacy/malformed rows."""
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def record_event(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    run_id: str,
    task_id: str | None = None,
    agent_role: str,
    stage: str,
    status: str,
    event_type: str,
    message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    """Append one ordered event for a harness run and return its event id."""
    if not run_id:
        raise ValueError("run_id cannot be empty")
    if not agent_role:
        raise ValueError("agent_role cannot be empty")

    init_database(db_path)
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO agent_events (
                run_id, task_id, agent_role, stage, status, event_type, message, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                task_id,
                agent_role,
                stage,
                status,
                event_type,
                message,
                json.dumps(payload or {}),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_events(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    run_id: str,
    after_event_id: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return events for one run in id order, optionally only those after an id.

    Passing ``after_event_id`` supports incremental polling: a caller keeps the
    last id it saw and asks only for what happened since.
    """
    init_database(db_path)
    sql = "SELECT * FROM agent_events WHERE run_id = ?"
    params: list[Any] = [run_id]
    if after_event_id is not None:
        sql += " AND event_id > ?"
        params.append(after_event_id)
    sql += " ORDER BY event_id ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    with connect(db_path) as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()

    events = []
    for row in rows:
        event = dict(row)
        event["payload"] = _decode_payload(event.pop("payload_json", None))
        events.append(event)
    return events


def summarize_run(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold an ordered event list into current run state.

    Per agent role the most recent event wins, so the summary answers "where is
    each agent right now" without replaying the whole trail.
    """
    if not events:
        return {
            "run_id": None,
            "task_id": None,
            "latest_event_id": None,
            "event_count": 0,
            "agents": {},
        }

    ordered = sorted(events, key=lambda event: event["event_id"])
    latest = ordered[-1]
    agents: dict[str, dict[str, Any]] = {}
    for event in ordered:
        agents[event["agent_role"]] = {
            "status": event["status"],
            "stage": event["stage"],
            "event_type": event["event_type"],
            "message": event.get("message"),
            "event_id": event["event_id"],
        }

    task_id = next(
        (event["task_id"] for event in reversed(ordered) if event.get("task_id")), None
    )
    return {
        "run_id": latest["run_id"],
        "task_id": task_id,
        "latest_event_id": latest["event_id"],
        "event_count": len(ordered),
        "agents": agents,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect harness run events.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    tail_cmd = sub.add_parser("tail", help="Show events for one run.")
    tail_cmd.add_argument("--run-id", required=True)
    tail_cmd.add_argument("--db", default=str(DEFAULT_DB_PATH))
    tail_cmd.add_argument("--after", type=int, default=None)
    tail_cmd.add_argument("--limit", type=int, default=None)
    tail_cmd.add_argument("--json", action="store_true")

    summary_cmd = sub.add_parser("summary", help="Show current state of one run.")
    summary_cmd.add_argument("--run-id", required=True)
    summary_cmd.add_argument("--db", default=str(DEFAULT_DB_PATH))

    args = parser.parse_args()
    events = list_events(
        args.db,
        run_id=args.run_id,
        after_event_id=getattr(args, "after", None),
        limit=getattr(args, "limit", None),
    )

    if args.cmd == "summary":
        print(json.dumps(summarize_run(events), indent=2))
        return

    if args.json:
        print(json.dumps(events, indent=2))
        return

    if not events:
        print(f"No events for run {args.run_id}")
        return
    for event in events:
        line = (
            f"[{event['event_id']:>5}] {event['created_at']}  "
            f"{event['agent_role']}/{event['stage']}  "
            f"{event['event_type']} ({event['status']})"
        )
        if event.get("message"):
            # ASCII separator: the Windows console default codepage mangles em dashes.
            line += f" | {event['message']}"
        print(line)


if __name__ == "__main__":
    main()
