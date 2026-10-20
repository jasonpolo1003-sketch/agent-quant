"""Live check that local Qwen can answer the PROP-006 window contract.

The nullable, nested ``WindowOutcome`` schema is new to Ollama's constrained
decoding, so this runs it once against qwen3:14b on a fixed synthetic source:
irrelevant filler with one relevant needle sentence in the middle. The filler
windows must come back as an explicit ``no_relevant_evidence``, the needle
window as validated evidence quoting the needle, and the merge must pass the
unchanged whole-bundle validator. Writes nothing: no database, no events, no
files. Not run by pytest.

    uv run python scripts/window_smoke.py

Exit 0 only if every check passes.
"""

from __future__ import annotations

import sys

from context_smoke import TRUNCATION_WARNING, truncation_warnings

from quant_brain.llm.qwen_call import QwenValidationError, qwen_call
from quant_brain.llm.validators import validate_research_output
from quant_brain.research.windowing import (
    WindowOutcome,
    merge_window_outcomes,
    plan_windows,
    validate_window_outcome,
    window_prompt,
)

# Must answer the smoke question directly. An earlier needle ("the synthetic
# position is closed when ...") named no ETF and no oversold entry, and qwen3:14b
# judged it irrelevant under every contract tried, including a flat list of
# passages -- a fixture ambiguity, not a schema failure.
NEEDLE = (
    "For daily ETF RSI oversold entries, the exit rule is to sell when the two-period "
    "RSI closes above seventy, or after five trading days, whichever comes first."
)
FILLER = (
    "The botanical garden keeps its glasshouse at a steady humidity so that the ferns "
    "along the north wall stay green through winter. Volunteers water the orchid "
    "benches in the morning and sweep the gravel paths before visitors arrive. "
)


def synthetic_source() -> str:
    """Deterministic ~24 KB text: filler, the needle once in the middle, filler."""
    half = "".join(f"Paragraph {i}. {FILLER}\n\n" for i in range(55))
    return half + NEEDLE + "\n\n" + half.replace("Paragraph", "Section")


def main() -> int:
    text = synthetic_source()
    item = {
        "source_id": "S1",
        "title": "Window smoke fixture",
        "url_or_citation": "https://example.invalid/window-smoke-fixture",
        "source_quality": "discovery-only",
        "snapshot_text": text,
    }
    task = {
        "research_id": "RQ-window-smoke",
        "question": "What exit rules pair with daily ETF RSI oversold entries?",
    }
    windows = plan_windows(text, "S1")
    checks: dict[str, bool] = {
        "windows deterministic": windows == plan_windows(text, "S1"),
        "fixture spans several windows": 3 <= len(windows) <= 4,
    }
    needle_windows = {w.window_id for w in windows if NEEDLE in w.text_of(text)}
    print(f"{len(text.encode('utf-8'))} bytes, {len(windows)} windows, needle in {sorted(needle_windows)}")
    before = truncation_warnings()

    outcomes = []
    for window in windows:
        try:
            result = qwen_call(
                window_prompt(task, item, window),
                [item],
                expected_research_id=task["research_id"],
                validator=lambda parsed, w=window: validate_window_outcome(
                    parsed, item, w, expected_research_id=task["research_id"]
                ),
                output_schema=WindowOutcome.model_json_schema(),
            )
        except QwenValidationError as exc:
            print(f"[{window.window_id}] failed closed: {exc}")
            checks[f"{window.window_id} validated"] = False
            continue
        outcome = result.output
        outcomes.append(outcome)
        evidence = (outcome.get("source") or {}).get("evidence")
        print(f"[{window.window_id}] {outcome['outcome']} via {result.model_used}, "
              f"repaired {result.repaired}, durations {[round(d, 1) for d in result.durations]}, "
              f"evidence {evidence!r}")
        checks[f"{window.window_id} validated"] = True
        if window.window_id in needle_windows:
            quotes = evidence if isinstance(evidence, list) else [evidence or ""]
            checks[f"{window.window_id} quotes the needle"] = (
                outcome["outcome"] == "evidence" and any(q and q in NEEDLE for q in quotes)
            )
        else:
            checks[f"{window.window_id} is explicitly no_relevant_evidence"] = (
                outcome["outcome"] == "no_relevant_evidence"
            )

    if len(outcomes) == len(windows):
        try:
            merged = merge_window_outcomes(task["research_id"], item, windows, outcomes)
            verdict = validate_research_output(
                merged, [item], expected_research_id=task["research_id"]
            )
            print(f"[merge] {merged['sources'][0]['evidence']!r}; whole-bundle ok {verdict.ok} "
                  f"{list(verdict.reasons)}")
            checks["merge passes the whole-bundle validator"] = verdict.ok
        except Exception as exc:  # reported, not hidden
            print(f"[merge] failed: {type(exc).__name__}: {exc}")
            checks["merge passes the whole-bundle validator"] = False
    else:
        checks["merge passes the whole-bundle validator"] = False

    after = truncation_warnings()
    print(f"[log] {TRUNCATION_WARNING!r} count before {before}, after {after}")
    checks["no new truncation warning in server.log"] = before is not None and before == after

    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
