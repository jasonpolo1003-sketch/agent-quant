from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.request import Request, urlopen

LIVE_RESEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "research_id": {"type": "string"},
        "decision": {
            "type": "string",
            "enum": ["ready_for_curation", "needs_more_work", "rejected"],
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "source_type": {"type": "string"},
                    "source_quality": {
                        "type": "string",
                        "enum": ["primary", "practitioner", "discovery-only", "reject"],
                    },
                    "main_claim": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                    "possible_strategy_rule": {"type": "string"},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "asset_classes": {"type": "array", "items": {"type": "string"}},
                    "data_required": {"type": "array", "items": {"type": "string"}},
                    "data_access": {
                        "type": "string",
                        "enum": ["available-now", "available-later", "not-realistic"],
                    },
                    "mvp_testable": {"type": "boolean"},
                },
                "required": [
                    "source_id",
                    "title",
                    "url",
                    "source_type",
                    "source_quality",
                    "main_claim",
                    "evidence_quote",
                    "possible_strategy_rule",
                    "risks",
                    "confidence",
                    "asset_classes",
                    "data_required",
                    "data_access",
                    "mvp_testable",
                ],
            },
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "curator_recommendation": {
            "type": "string",
            "enum": ["promote_source", "update_door", "needs_more_work", "rejected"],
        },
    },
    "required": [
        "research_id",
        "decision",
        "sources",
        "open_questions",
        "curator_recommendation",
    ],
}


def _bounded_text(text: str, limit: int = 6000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[TRUNCATED]"


def build_research_prompt(
    research_id: str,
    question: str,
    snapshots: list[dict[str, Any]],
) -> str:
    source_blocks = []
    for item in snapshots:
        source_blocks.append(
            f"""[{item['source_id']}]
Title: {item['title']}
URL: {item['url']}
Assigned source quality: {item['source_quality']}
Content hash: {item.get('content_hash', '')}
Snapshot path: {item.get('snapshot_path', '')}

{_bounded_text(str(item.get('text', '')))}"""
        )
    return f"""You are the evidence-processing worker for Quant Agent Brain.

Research ID: {research_id}
Research question: {question}

Rules:
- Use only the supplied snapshots.
- Do not invent URLs, citations, performance results, or strategy rules.
- Preserve each supplied source_id, title, URL, and assigned source quality exactly.
- Evidence quotes must appear verbatim in the corresponding fetched content.
- An incomplete primary source remains primary; source quality is provenance, not relevance.
- A discovery-only source cannot independently support a durable strategy rule.
- If evidence does not resolve an exit, holding period, cost, or other requested rule, leave possible_strategy_rule empty and list the gap.
- Return only the requested JSON object.

Snapshots:

{chr(10).join(source_blocks)}
"""


def _normalize_evidence(text: str) -> str:
    text = re.sub(r"[`*_>#\[\]()]", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_research_payload(
    research_id: str,
    payload: dict[str, Any],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    known = {item["source_id"]: item for item in snapshots}
    if payload.get("research_id") != research_id:
        failures.append("research_id does not match")

    seen: set[str] = set()
    for source in payload.get("sources", []):
        source_id = source.get("source_id")
        snapshot = known.get(source_id)
        if snapshot is None:
            failures.append(f"unknown source id: {source_id}")
            continue
        if source_id in seen:
            failures.append(f"duplicate source id: {source_id}")
        seen.add(source_id)
        for field in ("title", "url", "source_quality"):
            if source.get(field) != snapshot.get(field):
                failures.append(f"{source_id} changed protected field: {field}")
        quote = str(source.get("evidence_quote") or "").strip()
        if not quote:
            failures.append(f"{source_id} has no evidence quote")
        elif _normalize_evidence(quote) not in _normalize_evidence(str(snapshot.get("text", ""))):
            failures.append(f"{source_id} evidence quote is not in the snapshot")

    missing_sources = sorted(set(known).difference(seen))
    if missing_sources:
        failures.append(f"output omitted source(s): {', '.join(missing_sources)}")

    return {"passed": not failures, "failures": failures}


def _call_ollama_json(
    model: str,
    prompt: str,
    schema: dict[str, Any] = LIVE_RESEARCH_SCHEMA,
    base_url: str = "http://127.0.0.1:11434",
    timeout: int = 900,
) -> tuple[dict[str, Any], dict[str, Any]]:
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "format": schema,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0, "seed": 42, "num_ctx": 16384},
    }
    request = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))
    payload = json.loads(raw.get("message", {}).get("content", "{}"))
    return payload, {
        "model": model,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "prompt_eval_count": raw.get("prompt_eval_count"),
        "eval_count": raw.get("eval_count"),
    }


def extract_research_with_models(
    research_id: str,
    question: str,
    snapshots: list[dict[str, Any]],
    default_model: str = "qwen3:14b",
    escalation_model: str = "qwen3.8:27b",
) -> dict[str, Any]:
    prompt = build_research_prompt(research_id, question, snapshots)
    attempts = []
    payload, metadata = _call_ollama_json(default_model, prompt)
    validation = validate_research_payload(research_id, payload, snapshots)
    attempts.append({"model": default_model, "payload": payload, "validation": validation, **metadata})

    if not validation["passed"]:
        repair_prompt = (
            prompt
            + "\n\nYour previous response failed deterministic validation:\n"
            + json.dumps(validation["failures"], indent=2)
            + "\nPrevious response:\n"
            + json.dumps(payload, indent=2)
            + "\nReturn corrected JSON only."
        )
        payload, metadata = _call_ollama_json(default_model, repair_prompt)
        validation = validate_research_payload(research_id, payload, snapshots)
        attempts.append(
            {"model": default_model, "payload": payload, "validation": validation, **metadata}
        )

    if not validation["passed"]:
        escalation_prompt = (
            prompt
            + "\n\nThe smaller model failed validation. Produce a corrected response that passes:\n"
            + json.dumps(validation["failures"], indent=2)
        )
        payload, metadata = _call_ollama_json(escalation_model, escalation_prompt)
        validation = validate_research_payload(research_id, payload, snapshots)
        attempts.append(
            {
                "model": escalation_model,
                "payload": payload,
                "validation": validation,
                **metadata,
            }
        )

    return {
        "passed": validation["passed"],
        "payload": payload,
        "validation": validation,
        "attempts": attempts,
    }
