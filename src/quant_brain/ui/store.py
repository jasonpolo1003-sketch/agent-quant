"""The terminal's own SQLite store. It never touches ``brain.sqlite``'s schema."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_brain.config import DB_DIR, PROJECT_ROOT

TERMINAL_DB_PATH = DB_DIR / "terminal.sqlite"
TERMINAL_DIR = PROJECT_ROOT / "terminal"

SCHEMA = """
CREATE TABLE IF NOT EXISTS schedules (
    job_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    cadence_json TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 0,
    max_runs_per_day INTEGER NOT NULL DEFAULT 4,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    trigger TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    exit_code INTEGER,
    summary TEXT,
    output_path TEXT,
    log_tail TEXT
);
CREATE INDEX IF NOT EXISTS job_runs_job ON job_runs(job_id, started_at);
CREATE TABLE IF NOT EXISTS drawings (
    drawing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    kind TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS drawings_symbol ON drawings(symbol);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(db_path: str | Path = TERMINAL_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _schedule_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["cadence"] = json.loads(item.pop("cadence_json"))
    item["config"] = json.loads(item.pop("config_json"))
    item["enabled"] = bool(item["enabled"])
    return item


def list_schedules(db_path: str | Path = TERMINAL_DB_PATH) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        return [_schedule_row(r) for r in conn.execute("SELECT * FROM schedules ORDER BY job_id")]


def get_schedule(db_path: str | Path, job_id: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM schedules WHERE job_id = ?", (job_id,)).fetchone()
    return _schedule_row(row) if row else None


def upsert_schedule(db_path: str | Path, schedule: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO schedules (job_id, name, kind, cadence_json, config_json, enabled,
                                   max_runs_per_day, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                name = excluded.name, kind = excluded.kind, cadence_json = excluded.cadence_json,
                config_json = excluded.config_json, enabled = excluded.enabled,
                max_runs_per_day = excluded.max_runs_per_day, updated_at = excluded.updated_at
            """,
            (
                schedule["job_id"], schedule["name"], schedule["kind"],
                json.dumps(schedule["cadence"]), json.dumps(schedule.get("config") or {}),
                int(bool(schedule.get("enabled"))), int(schedule.get("max_runs_per_day", 4)),
                now, now,
            ),
        )
    found = get_schedule(db_path, schedule["job_id"])
    assert found is not None
    return found


def delete_schedule(db_path: str | Path, job_id: str) -> bool:
    with connect(db_path) as conn:
        return conn.execute("DELETE FROM schedules WHERE job_id = ?", (job_id,)).rowcount > 0


def start_run(db_path: str | Path, run_id: str, job_id: str, kind: str, trigger: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO job_runs (run_id, job_id, kind, trigger, status, started_at)"
            " VALUES (?, ?, ?, ?, 'running', ?)",
            (run_id, job_id, kind, trigger, utc_now()),
        )


def finish_run(
    db_path: str | Path, run_id: str, *, status: str, exit_code: int | None, summary: str,
    output_path: str | None = None, log_tail: str | None = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE job_runs SET status = ?, finished_at = ?, exit_code = ?, summary = ?,"
            " output_path = ?, log_tail = ? WHERE run_id = ?",
            (status, utc_now(), exit_code, summary, output_path, log_tail, run_id),
        )


def record_refusal(db_path: str | Path, run_id: str, job_id: str, kind: str, trigger: str,
                   reason: str) -> None:
    now = utc_now()
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO job_runs (run_id, job_id, kind, trigger, status, started_at, finished_at,"
            " summary) VALUES (?, ?, ?, ?, 'refused', ?, ?, ?)",
            (run_id, job_id, kind, trigger, now, now, reason),
        )


def list_runs(db_path: str | Path = TERMINAL_DB_PATH, *, job_id: str | None = None,
              limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT * FROM job_runs"
    params: list[Any] = []
    if job_id:
        sql += " WHERE job_id = ?"
        params.append(job_id)
    sql += " ORDER BY started_at DESC, rowid DESC LIMIT ?"
    params.append(limit)
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def running_runs(db_path: str | Path, kind: str) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM job_runs WHERE kind = ? AND status = 'running'", (kind,))]


def runs_started_since(db_path: str | Path, job_id: str, since_iso: str) -> int:
    with connect(db_path) as conn:
        return int(conn.execute(
            "SELECT COUNT(*) FROM job_runs WHERE job_id = ? AND started_at >= ?"
            " AND status != 'refused'",
            (job_id, since_iso),
        ).fetchone()[0])


def mark_stale(db_path: str | Path, run_id: str, reason: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE job_runs SET status = 'failed', finished_at = ?, summary = ?"
            " WHERE run_id = ? AND status = 'running'",
            (utc_now(), reason, run_id),
        )


DRAWING_KINDS = {"trend", "hline"}


def list_drawings(db_path: str | Path, symbol: str) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM drawings WHERE symbol = ? ORDER BY drawing_id",
                            (symbol.upper(),)).fetchall()
    return [{"id": r["drawing_id"], "symbol": r["symbol"], "kind": r["kind"],
             **json.loads(r["data_json"])} for r in rows]


def add_drawing(db_path: str | Path, symbol: str, kind: str, data: dict[str, Any]) -> int:
    if kind not in DRAWING_KINDS:
        raise ValueError(f"unknown drawing kind {kind!r}")
    with connect(db_path) as conn:
        return int(conn.execute(
            "INSERT INTO drawings (symbol, kind, data_json, created_at) VALUES (?, ?, ?, ?)",
            (symbol.upper(), kind, json.dumps(data), utc_now())).lastrowid)


def delete_drawings(db_path: str | Path, symbol: str, drawing_id: int | None = None) -> int:
    with connect(db_path) as conn:
        if drawing_id is None:
            return conn.execute("DELETE FROM drawings WHERE symbol = ?", (symbol.upper(),)).rowcount
        return conn.execute("DELETE FROM drawings WHERE symbol = ? AND drawing_id = ?",
                            (symbol.upper(), drawing_id)).rowcount
