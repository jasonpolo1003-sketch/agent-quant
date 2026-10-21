"""What coding agents did in this repo: Claude Code and Codex session logs, read-only.

Claude Code keeps JSONL transcripts under ``~/.claude/projects/<mangled cwd>/``.
Codex keeps rollouts under ``~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl``.
Both formats are private to those tools and may change, so every parser here
skips lines it does not understand instead of failing.
"""

from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from typing import Any

_CACHE: dict[tuple[str, float, int], dict[str, Any]] = {}
MAX_ACTIVITY = 40


def claude_project_dir(claude_home: Path, project_root: Path) -> Path:
    mangled = re.sub(r"[^A-Za-z0-9]", "-", str(project_root.resolve()))
    exact = claude_home / "projects" / mangled
    if exact.is_dir():
        return exact
    projects = claude_home / "projects"
    if projects.is_dir():  # drive-letter case differs between launchers
        for candidate in projects.iterdir():
            if candidate.name.lower() == mangled.lower():
                return candidate
    return exact


def _describe_tool(name: str, data: dict[str, Any]) -> str:
    for key in ("file_path", "notebook_path", "path"):
        if isinstance(data.get(key), str):
            return f"{name} {data[key]}"
    if isinstance(data.get("command"), str):
        return f"{name}: {data['command'].splitlines()[0][:160]}"
    if isinstance(data.get("pattern"), str):
        return f"{name} {data['pattern'][:80]}"
    return name


def _cached(path: Path, parse) -> dict[str, Any] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    key = (str(path), stat.st_mtime, stat.st_size)
    if key not in _CACHE:
        try:
            _CACHE[key] = parse(path)
        except OSError:
            return None
    return _CACHE[key]


def _parse_claude(path: Path) -> dict[str, Any]:
    title = prompt = first = last = None
    activity: deque[dict[str, str]] = deque(maxlen=MAX_ACTIVITY)
    tools = edits = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = item.get("type")
            stamp = item.get("timestamp")
            if stamp:
                first = first or stamp
                last = stamp
            if kind == "ai-title":
                title = item.get("aiTitle") or title
            elif kind == "last-prompt" and not prompt:
                prompt = item.get("lastPrompt")
            elif kind == "assistant" and not item.get("isSidechain"):
                for block in (item.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools += 1
                        name = str(block.get("name"))
                        edits += name in ("Edit", "Write", "NotebookEdit")
                        activity.append({"time": stamp or "", "what": _describe_tool(
                            name, block.get("input") or {})})
    return {"agent": "Claude Code", "id": path.stem, "title": title or (prompt or "")[:80],
            "prompt": (prompt or "")[:400], "started_at": first, "last_at": last,
            "tool_calls": tools, "edits": edits, "activity": list(activity)}


def claude_sessions(claude_home: Path, project_root: Path, limit: int = 12) -> list[dict[str, Any]]:
    folder = claude_project_dir(claude_home, project_root)
    if not folder.is_dir():
        return []
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    return [s for s in (_cached(p, _parse_claude) for p in files) if s]


def _parse_codex(path: Path) -> dict[str, Any]:
    cwd = prompt = first = last = sid = None
    activity: deque[dict[str, str]] = deque(maxlen=MAX_ACTIVITY)
    tools = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            stamp = item.get("timestamp")
            if stamp:
                first = first or stamp
                last = stamp
            payload = item.get("payload") or {}
            if item.get("type") == "session_meta":
                cwd = payload.get("cwd") or cwd
                sid = payload.get("id") or sid
            elif payload.get("type") == "message" and payload.get("role") == "user" and not prompt:
                texts = [c.get("text", "") for c in payload.get("content") or []
                         if isinstance(c, dict) and c.get("type") in ("input_text", "text")]
                joined = " ".join(t for t in texts if not t.lstrip().startswith("<"))
                prompt = joined.strip() or None
            elif payload.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
                tools += 1
                raw = payload.get("arguments") or payload.get("input") or "{}"
                try:
                    args = json.loads(raw) if isinstance(raw, str) else dict(raw)
                except (json.JSONDecodeError, TypeError, ValueError):
                    args = {"command": str(raw)}
                if isinstance(args.get("command"), list):
                    args["command"] = " ".join(map(str, args["command"]))
                activity.append({"time": stamp or "", "what": _describe_tool(
                    str(payload.get("name") or "shell"), args)})
    return {"agent": "Codex", "id": sid or path.stem, "cwd": cwd, "title": (prompt or "")[:80],
            "prompt": (prompt or "")[:400], "started_at": first, "last_at": last,
            "tool_calls": tools, "edits": None, "activity": list(activity)}


def codex_sessions(codex_home: Path, project_root: Path, limit: int = 12) -> list[dict[str, Any]]:
    folder = codex_home / "sessions"
    if not folder.is_dir():
        return []
    files = sorted(folder.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime,
                   reverse=True)[: limit * 4]
    root = str(project_root.resolve()).lower()
    out = []
    for path in files:
        session = _cached(path, _parse_codex)
        if session and session.get("cwd") and str(session["cwd"]).lower().startswith(root):
            out.append(session)
        if len(out) >= limit:
            break
    return out
