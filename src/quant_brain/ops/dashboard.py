from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.ops.events import list_events, summarize_run

DASHBOARD_HTML = PROJECT_ROOT / "ui" / "agent_dashboard.html"


def list_recent_runs(
    db_path: str | Path = DEFAULT_DB_PATH, limit: int = 25
) -> list[dict[str, Any]]:
    init_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT e.run_id, e.task_id, e.status, e.stage, e.agent_role,
                   e.event_type, e.message, e.created_at, e.event_id,
                   counts.event_count
            FROM agent_events e
            JOIN (
                SELECT run_id, MAX(event_id) AS latest_event_id, COUNT(*) AS event_count
                FROM agent_events
                GROUP BY run_id
            ) counts
              ON counts.run_id = e.run_id AND counts.latest_event_id = e.event_id
            ORDER BY e.event_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def load_run_dashboard(
    db_path: str | Path, run_id: str
) -> dict[str, Any]:
    events = list_events(db_path, run_id=run_id)
    state = summarize_run(events)
    task_id = state.get("task_id")
    task: dict[str, Any] | None = None
    if task_id:
        with connect(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM research_questions WHERE research_id = ?", (task_id,)
            ).fetchone()
        task = dict(row) if row else {"research_id": task_id, "status": "unknown"}
    return {"state": state, "events": events, "task": task}


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def make_handler(db_path: str | Path, html_path: str | Path = DASHBOARD_HTML):
    db = str(db_path)
    page = Path(html_path)

    class DashboardHandler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                if not page.exists():
                    self._send(404, b"Dashboard HTML not found", "text/plain; charset=utf-8")
                    return
                self._send(200, page.read_bytes(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/runs":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["25"])[0])
                self._send(200, _json_bytes(list_recent_runs(db, limit)), "application/json")
                return
            if parsed.path == "/api/run":
                query = parse_qs(parsed.query)
                run_id = query.get("run_id", [""])[0]
                if not run_id:
                    self._send(400, _json_bytes({"error": "run_id is required"}), "application/json")
                    return
                self._send(200, _json_bytes(load_run_dashboard(db, run_id)), "application/json")
                return
            if parsed.path == "/api/health":
                self._send(200, _json_bytes({"status": "ok"}), "application/json")
                return
            self._send(404, _json_bytes({"error": "not found"}), "application/json")

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DashboardHandler


def create_server(
    db_path: str | Path = DEFAULT_DB_PATH,
    host: str = "127.0.0.1",
    port: int = 8765,
    html_path: str | Path = DASHBOARD_HTML,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(db_path, html_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local Agent Operations dashboard.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--html", default=str(DASHBOARD_HTML))
    args = parser.parse_args()
    server = create_server(args.db, args.host, args.port, args.html)
    print(f"Agent Operations dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
