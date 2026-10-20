"""Read API keys from the environment or the git-ignored project ``.env``.

Keys are returned to the caller only. They are never logged, printed, or
written to manifests or reports; use ``redact`` on anything that may echo a
request URL.
"""

from __future__ import annotations

import os
from pathlib import Path

from quant_brain.config import PROJECT_ROOT


def get_key(name: str, env_file: Path | None = None) -> str | None:
    value = os.environ.get(name)
    if value:
        return value.strip()
    path = env_file or PROJECT_ROOT / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        if key.strip() == name:
            value = raw.strip().strip('"').strip("'")
            return value or None
    return None


def redact(text: str, *secrets: str | None) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text
