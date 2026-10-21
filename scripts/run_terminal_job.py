"""Run one Brain Terminal schedule now. Windows Task Scheduler calls this.

    python scripts/run_terminal_job.py nightly-health --root <brain checkout>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.ui import jobs, store


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("job_id")
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument("--trigger", default="schedule", choices=("schedule", "manual"))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    terminal_db = root / "db" / "terminal.sqlite"
    job = store.get_schedule(terminal_db, args.job_id)
    if job is None:
        print(f"no schedule {args.job_id!r}", file=sys.stderr)
        return 2
    if args.trigger == "schedule" and not job["enabled"]:
        print(f"{args.job_id} is disabled; not running", file=sys.stderr)
        return 3
    ctx = jobs.JobContext(root, root / "db" / "brain.sqlite", terminal_db, sys.executable)
    run = jobs.run_job(ctx, job, args.trigger)
    print(f"{run['run_id']} {run['status']}: {run['summary']}")
    return 0 if run["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
