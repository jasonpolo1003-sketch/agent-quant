"""Live check that an extraction prompt reaches local Qwen whole.

Uses a fixed synthetic snapshot (tests/fixtures/context_smoke_snapshot.md) whose
first sentence is a needle: Ollama's silent truncation keeps only a prompt's
tail, so a model that can quote the opening sentence was shown the head.
Writes nothing: no database, no events, no files. Not run by pytest.

    uv run python scripts/context_smoke.py

Exit 0 only if every check passes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.llm import ollama_client
from quant_brain.llm.qwen_call import (
    DEFAULT_MODEL,
    EXTRACTION_NUM_CTX,
    EXTRACTION_NUM_PREDICT,
    EXTRACTION_TIMEOUT,
    PROMPT_TOKEN_BUDGET,
    ContextBudgetError,
    estimate_prompt_tokens,
    qwen_call,
)
from quant_brain.research.executor import _source_extraction_prompt

FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "context_smoke_snapshot.md"
NEEDLE = (
    "Calibration needle: this synthetic fixture opens with the sentence the smoke check "
    "asks the model to quote."
)
SERVER_LOG = Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "server.log"
TRUNCATION_WARNING = "truncating input prompt"


def truncation_warnings() -> int | None:
    if not SERVER_LOG.is_file():
        return None
    return SERVER_LOG.read_text(encoding="utf-8", errors="replace").count(TRUNCATION_WARNING)


class RefusingClient:
    """Fails the check if the ladder ever reaches the model."""

    def generate(self, *_args, **_kwargs):
        raise AssertionError("an over-budget prompt reached the model")


def main() -> int:
    snapshot = FIXTURE.read_text(encoding="utf-8")
    assert NEEDLE in snapshot.splitlines()[7], "fixture no longer opens with the needle"
    item = {
        "source_id": "S1",
        "title": "Context smoke fixture",
        "url_or_citation": "https://example.invalid/context-smoke-fixture",
        "source_quality": "discovery-only",
        "snapshot_text": snapshot,
    }
    task = {
        "research_id": "RQ-context-smoke",
        "question": "Quote the calibration needle sentence that opens the snapshot.",
    }
    prompt = _source_extraction_prompt(task, item)
    checks: dict[str, bool] = {}
    before = truncation_warnings()
    print(f"num_ctx {EXTRACTION_NUM_CTX}, num_predict {EXTRACTION_NUM_PREDICT}, "
          f"budget {PROMPT_TOKEN_BUDGET}, prompt {len(prompt.encode('utf-8'))} bytes, "
          f"estimate {estimate_prompt_tokens(prompt)} tokens")

    # 1. The whole prompt is read: the head is visible and the count is real.
    head_prompt = (
        prompt + "\n\nIgnore the extraction task above. Return JSON "
        '{"first_sentence": "<the first sentence after the snapshot front matter, verbatim>"}.'
    )
    head = ollama_client.generate(
        head_prompt, DEFAULT_MODEL, num_ctx=EXTRACTION_NUM_CTX,
        num_predict=EXTRACTION_NUM_PREDICT, prompt_token_budget=PROMPT_TOKEN_BUDGET,
        timeout=EXTRACTION_TIMEOUT,
    )
    first = str(json.loads(head.text).get("first_sentence", ""))
    print(f"[head] prompt_eval_count {head.prompt_eval_count}, done_reason {head.done_reason}, "
          f"{head.duration_seconds:.1f}s, first_sentence {first!r}")
    checks["prompt read far past the old 2,050-token cut"] = (head.prompt_eval_count or 0) > 2050 * 2
    checks["head of the prompt visible (needle quoted)"] = first.strip() == NEEDLE

    # 2. The real validated ladder on the same prompt.
    try:
        result = qwen_call(prompt, [item], expected_research_id=task["research_id"])
        source = result.output["sources"][0]
        quotes = source["evidence"] if isinstance(source["evidence"], list) else [source["evidence"]]
        print(f"[ladder] validated by {result.model_used}, repaired {result.repaired}, "
              f"escalated {result.escalated}, durations {[round(d, 1) for d in result.durations]}")
        print(f"[ladder] evidence {quotes}")
        checks["full ladder validated a one-source extraction"] = True
        checks["ladder evidence quotes the needle"] = any(NEEDLE in q or q in NEEDLE for q in quotes)
    except Exception as exc:  # reported, not hidden
        print(f"[ladder] failed closed: {type(exc).__name__}: {exc}")
        checks["full ladder validated a one-source extraction"] = False

    # 3. Over budget: refused before the model is called.
    try:
        qwen_call(prompt + snapshot * 2, [item], expected_research_id=task["research_id"],
                  client=RefusingClient())
        checks["over-budget prompt refused before any call"] = False
    except ContextBudgetError as exc:
        print(f"[pre-flight] {exc}")
        checks["over-budget prompt refused before any call"] = True

    # 4. The server itself refuses a prompt larger than the window (truncate=false).
    try:
        ollama_client.generate(prompt, DEFAULT_MODEL, num_ctx=2048, num_predict=64,
                               timeout=EXTRACTION_TIMEOUT)
        checks["server refuses an oversize prompt instead of cutting it"] = False
    except ollama_client.ContextOverflowError as exc:
        print(f"[server] {exc}")
        checks["server refuses an oversize prompt instead of cutting it"] = True

    after = truncation_warnings()
    print(f"[log] {TRUNCATION_WARNING!r} count before {before}, after {after}")
    checks["no new truncation warning in server.log"] = before is not None and before == after

    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
