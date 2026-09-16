# Validated Local Qwen Runtime Workflow

## Production boundary

The registered `research_scout` discovery handler keeps the existing control plane unchanged:

```text
registry/dispatcher -> live discovery -> source snapshots -> qwen_call -> raw note
                                                        -> recommendation only
```

Live discovery always uses the validated Qwen boundary. There is no `use_qwen` or `qwen_runner` control: the production task payload rejects both keys, and the executor exposes no override parameter. Offline runs select the seeded backend (`backend: seeded` or `QUANT_BRAIN_DISCOVERY=seeded`); tests that need a stub model inject below the production task-payload boundary by rebinding `quant_brain.llm.qwen_call.qwen_call`. The Scout never dispatches or invokes the curator.

## Fixed ladder

1. `qwen3:14b`, temperature `0.0`, Ollama JSON-schema mode.
2. Run deterministic schema, source-ID, protected metadata, exact-quote, contradiction, invented-rule, and Tier-D slop checks.
3. On failure, make exactly one `qwen3:14b` repair call whose prompt lists validator reasons.
4. Validate again; on failure call `qwen3.8:27b` once.
5. Validate again; on failure raise `QwenValidationError` and let Scout fail closed.

There is no loop and no cloud fallback.

## Evidence grounding

Fields that can define a strategy, cost, timing, direction, or performance claim must be *extractive*: recoverable from the corresponding snapshot rather than asserted. A rule is either empty or a passage of its own snapshot.

Matching is over whole tokens at matching polarity, not raw substrings. Substring containment reversed meaning in both directions — it lifted `commission-free` out of `not commission-free` (scoped negation) and `profit` out of `unprofitable` (affix negation). Token-level matching with a local negation window refuses both, while faithful quotation, verb inflection, and reasonable skepticism still pass.

Model-generated `mvp_testable`, `confidence`, and `curator_recommendation` are advisory. The curator derives its own promotion condition: `main_claim` must be extractively supported by the source's exact evidence quotation. Where support cannot be established deterministically, the default is **not promotable** and a human or later curation step must confirm.

This bounds authority, not semantics. Extraction ensures a conclusion came from the source; it cannot judge whether a faithfully quoted passage genuinely supports a trading conclusion.

## Observability

Every attempt appends a `qwen_attempt` event with model, measured duration, prompt/response SHA-256 hashes, validator verdict, and reasons. Raw prompt/response content is not stored in events.

## Hermetic verification

```bash
uv run pytest tests/test_ollama_client.py tests/test_validators.py tests/test_qwen_call.py -v
uv run pytest -q
uv run ruff check . --no-cache
uv run ruff check src tests scripts
```

Tests inject clients/runners and never require Ollama or network.

## Bounded live smoke

```bash
uv run python scripts/gate_b_live_smoke.py
```

The script uses only `tests/fixtures/ollama/gate_b_snapshot.md`, a temporary SQLite event DB, and local Ollama. It writes no raw research or curated source. A validator-triggered 14B repair is acceptable; escalation is reported explicitly.
