from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_EMBED_TIMEOUT = 60
DEFAULT_GENERATE_TIMEOUT = 300


@dataclass(frozen=True)
class OllamaResponse:
    text: str
    model: str
    duration_seconds: float
    prompt_hash: str
    response_hash: str
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    done_reason: str | None = None
    num_ctx: int | None = None


class OllamaError(RuntimeError):
    """Raised when the local Ollama server cannot serve a request.

    There is deliberately no cloud fallback: a research pipeline that silently
    swaps in a paid API when the local model is down is not budget-first and
    not reproducible. See PLAN.md section 9.
    """


class ContextOverflowError(OllamaError):
    """The prompt or the response did not fit the requested context window.

    Ollama's default is to cut an oversized prompt silently, keeping only its
    tail (observed: ``truncating input prompt limit=2050`` for ``num_ctx`` 4096,
    i.e. ``num_ctx // 2 + 2``). Both Scout runs before this guard existed were
    truncated that way. A response produced from a cut prompt is never valid
    evidence, so every overflow signal raises instead of returning text.
    """


def silent_truncation_limit(num_ctx: int) -> int:
    """Prompt length Ollama 0.34.3 silently truncates to (measured, not documented)."""
    return num_ctx // 2 + 2


def _post(path: str, payload: dict[str, Any], host: str, timeout: int) -> dict[str, Any]:
    url = f"{host.rstrip('/')}{path}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        if "exceed_context_size" in detail or "exceeds the available context size" in detail:
            raise ContextOverflowError(
                f"context: Ollama refused the prompt as larger than the context window: {detail}"
            ) from exc
        raise OllamaError(f"Ollama returned HTTP {exc.code} for {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"cannot reach Ollama at {host} ({exc.reason}); start it with `ollama serve`"
        ) from exc
    except TimeoutError as exc:
        raise OllamaError(f"Ollama request to {path} timed out after {timeout}s") from exc
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama returned malformed JSON for {path}") from exc


def generate(
    prompt: str,
    model: str,
    *,
    num_ctx: int,
    num_predict: int,
    prompt_token_budget: int | None = None,
    host: str = DEFAULT_HOST,
    temperature: float = 0.0,
    timeout: int = DEFAULT_GENERATE_TIMEOUT,
    format: str | dict[str, Any] = "json",
    system: str | None = None,
) -> OllamaResponse:
    """Generate through local Ollama with deterministic schema decoding.

    The context window is required, never the server default. ``truncate`` and
    ``shift`` are disabled so the server refuses an oversized prompt (HTTP 400,
    verified on 0.34.3) instead of cutting it, and cannot drop the prompt's head
    to make room while generating. The response is then checked on its own
    evidence, so a server that ignored those flags would still be caught.
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "format": format,
        "truncate": False,
        "shift": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict},
    }
    if system is not None:
        payload["system"] = system
    started = time.perf_counter()
    data = _post("/api/generate", payload, host, timeout)
    duration = time.perf_counter() - started
    text = data.get("response")
    if not isinstance(text, str):
        raise OllamaError(f"Ollama returned no response text for model {model!r}")
    prompt_eval_count = data.get("prompt_eval_count")
    done_reason = data.get("done_reason")
    _check_context_use(
        model,
        num_ctx=num_ctx,
        prompt_eval_count=prompt_eval_count,
        prompt_token_budget=prompt_token_budget,
        done_reason=done_reason,
    )
    return OllamaResponse(
        text=text,
        model=model,
        duration_seconds=duration,
        prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        response_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        prompt_eval_count=prompt_eval_count,
        eval_count=data.get("eval_count"),
        done_reason=done_reason,
        num_ctx=num_ctx,
    )


def _check_context_use(
    model: str,
    *,
    num_ctx: int,
    prompt_eval_count: Any,
    prompt_token_budget: int | None,
    done_reason: Any,
) -> None:
    """Refuse any response whose own accounting shows the context was exceeded."""
    if not isinstance(prompt_eval_count, int) or prompt_eval_count <= 0:
        raise ContextOverflowError(
            f"context: {model} reported no prompt_eval_count, so it cannot be shown "
            "that the whole prompt was read"
        )
    if prompt_eval_count == silent_truncation_limit(num_ctx):
        raise ContextOverflowError(
            f"context: {model} read exactly {prompt_eval_count} prompt tokens, Ollama's "
            f"silent-truncation length for num_ctx {num_ctx}; the prompt was cut"
        )
    if prompt_token_budget is not None and prompt_eval_count > prompt_token_budget:
        raise ContextOverflowError(
            f"context: {model} read {prompt_eval_count} prompt tokens, above the "
            f"{prompt_token_budget}-token budget for num_ctx {num_ctx}"
        )
    if done_reason == "length":
        raise ContextOverflowError(
            f"context: {model} stopped at the output limit (done_reason=length); "
            "the response is cut"
        )


def embed(
    text: str,
    model: str = DEFAULT_EMBED_MODEL,
    *,
    host: str = DEFAULT_HOST,
    timeout: int = DEFAULT_EMBED_TIMEOUT,
) -> list[float]:
    """Return one embedding vector from the local Ollama server."""
    if not text.strip():
        raise ValueError("cannot embed empty text")
    data = _post("/api/embeddings", {"model": model, "prompt": text}, host, timeout)
    vector = data.get("embedding")
    if not isinstance(vector, list) or not vector:
        raise OllamaError(f"Ollama returned no embedding for model {model!r}")
    return [float(value) for value in vector]


def is_available(host: str = DEFAULT_HOST, timeout: int = 5) -> bool:
    """Report whether the local Ollama server answers. Never raises."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout):
            return True
    except Exception:
        return False


def available_models(host: str = DEFAULT_HOST, timeout: int = 10) -> list[str]:
    """List models the local server has pulled."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise OllamaError(f"cannot list Ollama models at {host}: {exc}") from exc
    return [model["name"] for model in data.get("models", [])]
