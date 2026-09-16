---
id: PHASE-05
type: plan_phase
phase: 5
title: Ollama Qwen runtime + validators
status: complete
completed: 2026-09-07
created: 2026-08-28
---

# Phase 5 — Ollama Qwen runtime + validators

Parent plan: [../../../PLAN.md](../../../PLAN.md)
Policy: [../local_qwen_research_policy.md](../local_qwen_research_policy.md)

## Why this phase exists

The Qwen models were **evaluated** ([model_eval.py](../../../src/quant_brain/research/model_eval.py), results in `brain/00_Inbox/Model_Evaluations/`) and a policy was written. But nothing in the codebase actually calls Ollama at runtime. Every "executor" in the project today is deterministic Python.

That was correct for proving plumbing. It is now the blocker: Phase 6's whole job is turning fetched web content into structured, cited evidence, and that requires a model.

## Evaluation results this phase must honor

From the completed bounded evaluation:

```
qwen3:14b     3/3 passed, 17.740s total, 2 cases repaired
qwen3.8:27b   3/3 passed, 123.972s total, 0 cases repaired
```

Hardware: RTX 5070, 12 GB VRAM. `qwen3:14b` is 9.3 GB, `qwen3.8:27b` is 17 GB (spills past VRAM — hence ~7x slower).

The conclusion already recorded in policy: **14B is the default worker, approved only behind schema + source-ID + validator + one-repair gates. 27B is the escalation/reviewer.** A stronger validator caught a direct contradiction in an early 14B answer; one bounded repair fixed it. That is the exact architecture to implement.

## Entry gate

Phase 0 complete. Independent of Phases 1-4. Ollama installed and running, with:

```bash
ollama pull qwen3:14b
ollama pull qwen3.8:27b
ollama pull nomic-embed-text   # Phase 3 also needs this
```

## Exit gate

`qwen_call(prompt, schema, model=...)` returns validated structured output, or fails closed after: 14B → validate → one repair → validate → escalate 27B → validate → **fail**. Every step recorded as an event.

## Design

### `src/quant_brain/llm/ollama_client.py`

Minimal HTTP client against `http://localhost:11434`. No SDK dependency needed — `/api/generate` and `/api/embeddings` over plain HTTP are enough.

```python
DEFAULT_HOST = "http://localhost:11434"

def generate(prompt, model, *, host=..., temperature=0.0, timeout=300,
             format="json", system=None) -> OllamaResponse
def embed(text, model="nomic-embed-text", *, host=..., timeout=60) -> list[float]
```

Requirements:
- **`temperature=0.0` by default.** Evidence extraction is not a creative task; determinism makes validator failures reproducible.
- Use Ollama's `format="json"` mode for schema-bound calls — it constrains decoding and cuts malformed-JSON repairs substantially.
- Explicit timeouts. 14B should answer in seconds; 27B may take ~2 minutes per the eval.
- **No cloud fallback, ever.** If Ollama is down, raise. Do not silently reach for an API.
- Return duration, model, prompt hash, response hash — Phase 6 logs these.

If Phase 3 already inlined an embed call, refactor it to live here.

### `src/quant_brain/llm/validators.py`

This is the heart of the phase. The model is *assumed unreliable*; the validators are what make it usable.

Five gates, each a pure function returning `ValidationResult(ok: bool, reasons: list[str])`:

1. **Schema gate** — Pydantic model matching the JSON contract already defined in `build_scout_prompt` (research_id, sources[], open_questions[], curator_recommendation). Reuse that exact shape; it is already the project's contract and the curator already parses it.

2. **Source-ID gate** — every claim must reference a source ID that was actually in the provided evidence bundle. Reject invented IDs. This is the single most important gate: it is what prevents fabricated citations.

3. **Contradiction gate** — flag outputs where a source's `main_claim` and its `evidence` disagree, or where `confidence: high` coexists with `source_quality: discovery-only`. The eval already caught a real instance of this class of failure.

4. **Invented-rule gate** — reject `possible_strategy_rule` values containing specifics (numeric thresholds, holding periods) that appear nowhere in the source text. Substring/number-presence check against the evidence bundle is sufficient; do not use an LLM to judge this.

5. **Slop gate** — apply Tier D rejection from [../research_source_quality_policy.md](../research_source_quality_policy.md): guaranteed returns, effortless profit, screenshots without rules/data/costs, copied summaries without provenance, fake precision.

Validators are **deterministic Python**. Never use an LLM to validate an LLM at this stage — that doubles the failure surface and cannot be unit-tested.

### `src/quant_brain/llm/qwen_call.py`

Orchestrator implementing the exact escalation ladder from policy:

```
14B (temp 0, format=json)
  → validate
     ok    → return
     fail  → build repair prompt naming the failed gates + the offending fields
             → 14B once more            ← EXACTLY ONE repair. Not a loop.
                → validate
                   ok   → return (flag repaired=True)
                   fail → escalate 27B
                          → validate
                             ok   → return (flag escalated=True)
                             fail → FAIL CLOSED
```

The repair prompt must state *what failed and why*, not merely "try again." Never hand the model the expected answer.

Return a result object carrying: output, model_used, repaired, escalated, validator_reasons, durations. Phase 6 needs all of it for the run report.

## Testing strategy

**pytest must not require Ollama.**

- Record real Ollama responses once → `tests/fixtures/ollama/*.json` (a good response, a schema-violating one, one with an invented source ID, one with a contradiction).
- Inject the client (`client=` param defaulting to the real one) so tests substitute a stub returning fixtures in sequence.
- Test each validator in isolation with hand-written inputs — these are pure functions and deserve thorough coverage.
- Test the ladder: passes first time / passes after repair / escalates / fails closed. Assert **exactly one** repair attempt occurs.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/llm/__init__.py` | create |
| `src/quant_brain/llm/ollama_client.py` | create |
| `src/quant_brain/llm/validators.py` | create |
| `src/quant_brain/llm/qwen_call.py` | create |
| `tests/test_ollama_client.py` | create |
| `tests/test_validators.py` | create — most thorough test file in the phase |
| `tests/test_qwen_call.py` | create — the escalation ladder |
| `tests/fixtures/ollama/` | create (recorded responses) |
| `brain/_system/qwen_runtime_workflow.md` | create |

## Verification steps

```bash
ollama list                                  # confirm both models present
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest tests/test_validators.py -v
uv run pytest tests/test_qwen_call.py -v
uv run pytest -q
# live smoke test (not in CI):
uv run python -c "from quant_brain.llm.ollama_client import generate; print(generate('Reply with JSON {\"ok\":true}', model='qwen3:14b').text)"
```

## Definition of done

- [x] Ollama client works against local server, temp 0, JSON mode, explicit timeouts
- [x] Five validator gates implemented as pure functions with unit tests
- [x] Escalation ladder implemented with **exactly one** repair before escalation
- [x] Fail-closed path returns a structured failure, never a fabricated success
- [x] No cloud fallback anywhere in the module
- [x] Full suite green without Ollama running
- [x] `PLAN.md` §10 checkpoint updated

## Do not

- Do not add a retry loop. One repair, then escalate, then fail. Loops hide bad prompts and burn GPU time.
- Do not raise temperature to "get past" a validator failure. That is the validator working.
- Do not use an LLM as a validator in this phase.
- Do not add a paid-API fallback, even commented out.
- Do not let the 27B model become the default because it scored better. It is ~7x slower; the ladder exists precisely so the fast model handles the common case.
