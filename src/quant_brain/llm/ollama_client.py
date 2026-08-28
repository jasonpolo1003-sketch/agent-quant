from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_EMBED_TIMEOUT = 60


class OllamaError(RuntimeError):
    """Raised when the local Ollama server cannot serve a request.

    There is deliberately no cloud fallback: a research pipeline that silently
    swaps in a paid API when the local model is down is not budget-first and
    not reproducible. See PLAN.md section 9.
    """


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
        raise OllamaError(f"Ollama returned HTTP {exc.code} for {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(
            f"cannot reach Ollama at {host} ({exc.reason}); start it with `ollama serve`"
        ) from exc
    except TimeoutError as exc:
        raise OllamaError(f"Ollama request to {path} timed out after {timeout}s") from exc
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama returned malformed JSON for {path}") from exc


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
