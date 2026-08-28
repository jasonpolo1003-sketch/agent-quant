"""Dispatch one typed task to the agent qualified to run it."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from uuid import uuid4

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH
from quant_brain.harness.dispatcher import DispatchError, Task, dispatch
from quant_brain.harness.handlers import register_default_handlers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, dest="task_type", help="Task type, e.g. discovery")
    parser.add_argument("--research-id", default=None)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explain the routing decision without executing the handler.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    register_default_handlers()

    payload = {}
    if args.research_id:
        payload["research_id"] = args.research_id

    task = Task(
        task_id=args.task_id or f"TASK-{uuid4().hex[:10]}",
        task_type=args.task_type,
        payload=payload,
        run_id=args.run_id,
    )

    try:
        result = dispatch(
            task,
            project_root=args.project_root,
            db_path=args.db,
            dry_run=args.dry_run,
        )
    except DispatchError as exc:
        print(f"dispatch failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
        return

    print(f"run_id:   {result.run_id}")
    print(f"task:     {result.task_id} ({result.task_type})")
    print(f"agent:    {result.agent}")
    print(f"status:   {result.status}")
    if args.dry_run:
        print(f"model:    {result.detail.get('model') or 'deterministic'}")
        print(f"contract: {result.detail.get('output_contract')}")
        print(f"handler:  {'registered' if result.detail.get('handler_registered') else 'MISSING'}")
        print("writes:")
        for path in result.detail.get("allowed_write_paths", []):
            print(f"  - {path}")
        return
    print(f"duration: {result.duration_seconds:.2f}s")
    if result.outputs:
        print("outputs:")
        for path in result.outputs:
            print(f"  - {path}")
    if result.recommendation:
        print(f"recommends next: {result.recommendation}")


if __name__ == "__main__":
    main()
