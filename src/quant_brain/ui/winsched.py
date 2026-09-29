"""Always-on schedules through Windows Task Scheduler (``schtasks``).

The terminal DB is the source of truth. An enabled schedule becomes the task
``\\QuantBrain\\<job_id>``, which runs ``scripts/run_terminal_job.py <job_id>``
with ``pythonw.exe``, so no console window flashes. Disabling or deleting a
schedule deletes its task. ``drift`` reports any mismatch.
"""

from __future__ import annotations

import csv
import io
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

TASK_FOLDER = "QuantBrain"
DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
MAX_TR_LENGTH = 261  # schtasks /TR limit


class SchedulerError(RuntimeError):
    pass


def validate_cadence(cadence: dict[str, Any]) -> dict[str, Any]:
    kind = cadence.get("type")
    time = str(cadence.get("time") or "")
    if kind in ("daily", "weekdays", "weekly") and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d",
                                                                     time):
        raise ValueError("time must be HH:MM (24h)")
    if kind in ("daily", "weekdays"):
        return {"type": kind, "time": time}
    if kind == "weekly":
        days = [str(d).upper()[:3] for d in cadence.get("days") or []]
        if not days or any(d not in DAYS for d in days):
            raise ValueError(f"weekly needs days from {', '.join(DAYS)}")
        return {"type": "weekly", "days": sorted(set(days), key=DAYS.index), "time": time}
    if kind == "hourly":
        every = int(cadence.get("every") or 1)
        if not 1 <= every <= 23:
            raise ValueError("hourly 'every' must be 1-23")
        return {"type": "hourly", "every": every}
    raise ValueError("cadence type must be daily, weekdays, weekly or hourly")


def describe_cadence(cadence: dict[str, Any]) -> str:
    kind = cadence["type"]
    if kind == "daily":
        return f"daily {cadence['time']}"
    if kind == "weekdays":
        return f"weekdays {cadence['time']}"
    if kind == "weekly":
        return f"{','.join(d.title() for d in cadence['days'])} {cadence['time']}"
    return f"every {cadence['every']}h"


def task_name(job_id: str) -> str:
    return f"\\{TASK_FOLDER}\\{job_id}"


def pythonw(python: str = sys.executable) -> str:
    exe = Path(python)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.is_file() else exe)


def task_command(job_id: str, project_root: Path, python: str = sys.executable,
                 runner: Path | None = None) -> str:
    # The runner ships with this code, which may live in a different checkout from the brain.
    runner = runner or Path(__file__).resolve().parents[3] / "scripts" / "run_terminal_job.py"
    command = f'"{pythonw(python)}" "{runner}" {job_id} --root "{project_root}"'
    if len(command) > MAX_TR_LENGTH:
        raise SchedulerError(f"task command is {len(command)} chars; schtasks allows "
                             f"{MAX_TR_LENGTH}. Move the project to a shorter path.")
    return command


def create_args(job_id: str, cadence: dict[str, Any], command: str) -> list[str]:
    args = ["schtasks", "/Create", "/F", "/TN", task_name(job_id), "/TR", command]
    kind = cadence["type"]
    if kind == "daily":
        args += ["/SC", "DAILY", "/ST", cadence["time"]]
    elif kind == "weekdays":
        args += ["/SC", "WEEKLY", "/D", ",".join(DAYS[:5]), "/ST", cadence["time"]]
    elif kind == "weekly":
        args += ["/SC", "WEEKLY", "/D", ",".join(cadence["days"]), "/ST", cadence["time"]]
    else:
        args += ["/SC", "HOURLY", "/MO", str(cadence["every"])]
    return args


def _schtasks(args: list[str]) -> subprocess.CompletedProcess:
    if sys.platform != "win32":
        raise SchedulerError("Windows Task Scheduler is only available on Windows")
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=30, check=False)


def register(job: dict[str, Any], project_root: Path, python: str = sys.executable) -> None:
    done = _schtasks(create_args(job["job_id"], job["cadence"],
                                 task_command(job["job_id"], project_root, python)))
    if done.returncode != 0:
        raise SchedulerError((done.stderr or done.stdout).strip())


def unregister(job_id: str) -> bool:
    done = _schtasks(["schtasks", "/Delete", "/F", "/TN", task_name(job_id)])
    return done.returncode == 0


def parse_query_csv(text: str) -> dict[str, dict[str, str]]:
    """``schtasks /Query /FO CSV /V`` output -> {job_id: {next_run, status, last_run, ...}}."""
    tasks: dict[str, dict[str, str]] = {}
    prefix = f"\\{TASK_FOLDER}\\"
    for row in csv.DictReader(io.StringIO(text)):
        name = row.get("TaskName") or ""
        if not name.startswith(prefix) or row.get("TaskName") == "TaskName":
            continue
        job_id = name[len(prefix):]
        tasks[job_id] = {
            "next_run": row.get("Next Run Time", ""),
            "status": row.get("Status", ""),
            "last_run": row.get("Last Run Time", ""),
            "last_result": row.get("Last Result", ""),
            "command": row.get("Task To Run", ""),
        }
    return tasks


def registered() -> dict[str, dict[str, str]]:
    try:
        done = _schtasks(["schtasks", "/Query", "/FO", "CSV", "/V"])
    except SchedulerError:
        return {}
    return parse_query_csv(done.stdout) if done.returncode == 0 else {}


def drift(schedules: list[dict[str, Any]], tasks: dict[str, dict[str, str]]) -> list[str]:
    problems = []
    by_id = {s["job_id"]: s for s in schedules}
    for s in schedules:
        if s["enabled"] and s["job_id"] not in tasks:
            problems.append(f"{s['job_id']} is enabled but has no Task Scheduler task")
        if not s["enabled"] and s["job_id"] in tasks:
            problems.append(f"{s['job_id']} is disabled but still has a task")
    for job_id in tasks:
        if job_id not in by_id:
            problems.append(f"task {task_name(job_id)} has no schedule in the terminal")
    return problems


def sync(job: dict[str, Any], project_root: Path, python: str = sys.executable) -> None:
    if job["enabled"]:
        register(job, project_root, python)
    else:
        unregister(job["job_id"])
