"""Model backends reached only through official, already-logged-in CLIs (or local Ollama).

The terminal never reads, stores or forwards a token. ``claude -p`` uses the
login Claude Code already holds. Tutor calls run with every tool disabled and
no MCP servers, from an empty working directory, so the model can only answer
from the text it is given.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from quant_brain.llm import ollama_client


class BackendError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackendStatus:
    name: str
    label: str
    available: bool
    detail: str
    sign_in: str


class Backend(Protocol):
    name: str

    def status(self) -> BackendStatus: ...

    def stream(self, system: str, prompt: str, *, timeout: int = 300) -> Iterator[str]: ...


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    # Claude Code refuses to start when it thinks it is nested inside another session.
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    return env


class ClaudeCLI:
    name = "claude"

    def __init__(self, executable: str | None = None, model: str | None = None) -> None:
        self.executable = executable or shutil.which("claude")
        self.model = model

    def status(self) -> BackendStatus:
        sign_in = "Uses your existing Claude Code login. Run `claude` once in a terminal to sign in."
        if not self.executable:
            return BackendStatus(self.name, "Claude (subscription CLI)", False,
                                 "claude not found on PATH", sign_in)
        try:
            done = subprocess.run([self.executable, "--version"], capture_output=True, text=True,
                                  timeout=20, env=_clean_env(), check=False)
            version = (done.stdout or done.stderr).strip().splitlines()[0]
        except (OSError, subprocess.TimeoutExpired, IndexError) as exc:
            return BackendStatus(self.name, "Claude (subscription CLI)", False, str(exc), sign_in)
        return BackendStatus(self.name, "Claude (subscription CLI)", True, version, sign_in)

    def command(self, system: str) -> list[str]:
        if not self.executable:
            raise BackendError("claude CLI not found on PATH")
        cmd = [
            self.executable, "-p",
            "--tools", "",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--system-prompt", system,
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--verbose",
        ]
        if self.model:
            cmd += ["--model", self.model]
        return cmd

    def stream(self, system: str, prompt: str, *, timeout: int = 300) -> Iterator[str]:
        cmd = self.command(system)
        with tempfile.TemporaryDirectory(prefix="brain-terminal-") as empty_cwd:
            proc = subprocess.Popen(
                cmd, cwd=empty_cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                env=_clean_env(),
            )
            timer = threading.Timer(timeout, proc.kill)
            timer.start()
            try:
                yield from parse_stream_json(_feed(proc, prompt))
                proc.wait()
            finally:
                timer.cancel()
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
            if proc.returncode not in (0, None):
                err = (proc.stderr.read() if proc.stderr else "").strip()
                raise BackendError(f"claude exited {proc.returncode}: {err[:500]}")


def _feed(proc: subprocess.Popen, prompt: str) -> Iterator[str]:
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(prompt)
    proc.stdin.close()
    yield from proc.stdout


def parse_stream_json(lines: Iterator[str]) -> Iterator[str]:
    """Text deltas from Claude Code's ``stream-json`` output; raises on an error result."""
    streamed = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = item.get("type")
        if kind == "stream_event":
            event = item.get("event") or {}
            delta = event.get("delta") or {}
            if event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                streamed = True
                yield delta.get("text", "")
        elif kind == "result":
            if item.get("is_error"):
                raise BackendError(str(item.get("result") or item.get("subtype") or "error"))
            if not streamed and item.get("result"):
                yield str(item["result"])


class CodexCLI:
    """Slot for the Codex CLI. Jason chose Claude-only for now (2026-09-28)."""

    name = "codex"

    def status(self) -> BackendStatus:
        found = shutil.which("codex")
        return BackendStatus(
            self.name, "Codex (subscription CLI)", False,
            "installed, but not wired up yet" if found else "codex not found on PATH",
            "Later: npm i -g @openai/codex, then codex login (ChatGPT sign-in).",
        )

    def stream(self, system: str, prompt: str, *, timeout: int = 300) -> Iterator[str]:
        raise BackendError("The Codex backend is not enabled yet. Use Claude.")


class Ollama:
    name = "ollama"

    def __init__(self, model: str = "qwen3:14b", num_ctx: int = 32768) -> None:
        self.model = model
        self.num_ctx = num_ctx

    def status(self) -> BackendStatus:
        up = ollama_client.is_available(timeout=2)
        models = ollama_client.available_models(timeout=3) if up else []
        return BackendStatus(
            self.name, "Local Ollama", up and self.model in models,
            (f"{self.model} ready" if self.model in models else f"{self.model} not pulled")
            if up else "Ollama is not running",
            "No sign-in. Start Ollama locally.",
        )

    def stream(self, system: str, prompt: str, *, timeout: int = 300) -> Iterator[str]:
        response = ollama_client.generate(
            prompt, self.model, num_ctx=self.num_ctx, num_predict=2048, format="",
            system=system, timeout=timeout, temperature=0.2,
        )
        yield response.text


BACKENDS: dict[str, Backend] = {"claude": ClaudeCLI(), "codex": CodexCLI(), "ollama": Ollama()}


def get_backend(name: str) -> Backend:
    if name not in BACKENDS:
        raise BackendError(f"unknown backend {name!r}")
    return BACKENDS[name]
