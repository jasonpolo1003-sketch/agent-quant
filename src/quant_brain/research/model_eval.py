from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResearchEvalCase:
    case_id: str
    question: str
    evidence: list[dict[str, str]]
    expected_decision: str
    required_missing_terms: tuple[str, ...] = ()
    require_no_strategy_rules: bool = False
    reject_source_ids: tuple[str, ...] = ()
    required_topics: tuple[str, ...] = ()
    forbidden_claim_phrases: tuple[str, ...] = ()


EVAL_CASES = [
    ResearchEvalCase(
        case_id="gap_honesty",
        question=(
            "Choose an evidence-backed exit rule and maximum holding period for a daily RSI "
            "oversold strategy. Propose a strategy rule only if the supplied evidence supports it."
        ),
        evidence=[
            {
                "source_id": "S1",
                "source_type": "official documentation",
                "text": (
                    "Wilder RSI uses a 14-period default with traditional oversold level 30. "
                    "Short-term traders sometimes use RSI(2) below 20. A close-based signal may "
                    "enter no earlier than the next bar. This source does not specify an exit rule "
                    "or maximum holding period."
                ),
            }
        ],
        expected_decision="needs_more_evidence",
        required_missing_terms=("exit", "holding"),
        require_no_strategy_rules=True,
    ),
    ResearchEvalCase(
        case_id="slop_filter",
        question="Decide whether the supplied material can support a durable strategy claim.",
        evidence=[
            {
                "source_id": "S1",
                "source_type": "anonymous video description",
                "text": (
                    "Secret indicator wins 95% of trades. Screenshot proves it. Rules, dataset, "
                    "test period, losses, and transaction costs are not provided."
                ),
            },
            {
                "source_id": "S2",
                "source_type": "named institutional research",
                "text": (
                    "Prospective data should be evaluated for originality, coverage, timestamp "
                    "reliability, lineage, statistical power, economic intuition, and redundancy."
                ),
            },
        ],
        expected_decision="reject",
        require_no_strategy_rules=True,
        reject_source_ids=("S1",),
        forbidden_claim_phrases=("can support a durable strategy claim", "wins 95%"),
    ),
    ResearchEvalCase(
        case_id="cross_asset_mapping",
        question="Map the markets professional quantitative firms research or trade from this evidence.",
        evidence=[
            {
                "source_id": "S1",
                "source_type": "institutional research",
                "text": (
                    "Traditional trend-following futures and forwards include equity indices, "
                    "government bonds, major foreign exchange, and core commodities."
                ),
            },
            {
                "source_id": "S2",
                "source_type": "trading firm page",
                "text": (
                    "The firm provides liquidity in ETFs with equity, fixed-income, commodity, "
                    "and crypto underliers and trades index, ETF, and single-stock options."
                ),
            },
        ],
        expected_decision="supported",
        required_topics=("equity", "bond", "foreign exchange", "commodit", "option", "crypto"),
    ),
]


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "case_id": {"type": "string"},
        "decision": {
            "type": "string",
            "enum": ["supported", "needs_more_evidence", "reject"],
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claim", "evidence_ids"],
            },
        },
        "source_assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "quality": {
                        "type": "string",
                        "enum": ["primary", "practitioner", "discovery-only", "reject"],
                    },
                    "reason": {"type": "string"},
                },
                "required": ["source_id", "quality", "reason"],
            },
        },
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "proposed_strategy_rules": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "case_id",
        "decision",
        "claims",
        "source_assessments",
        "missing_information",
        "proposed_strategy_rules",
    ],
}


def build_eval_prompt(case: ResearchEvalCase) -> str:
    evidence = "\n\n".join(
        f"[{item['source_id']}] Type: {item['source_type']}\n{item['text']}"
        for item in case.evidence
    )
    return f"""You are evaluating research for an evidence-first quantitative finance system.

Rules:
- Use only the supplied evidence.
- Never invent a strategy rule, performance result, source, or citation.
- Every factual claim must cite one or more supplied source IDs.
- Source quality describes provenance and reliability, not whether the source fully answers the question.
- Label an official or original institutional source primary even when it is incomplete for this question.
- Label an identifiable expert or institutional interview practitioner when its method and limits are visible.
- Label an uncorroborated but traceable lead discovery-only.
- Label guaranteed returns, screenshots without methods, anonymous claims, or hidden assumptions reject.
- Choose supported only when the supplied evidence directly answers the question.
- Choose needs_more_evidence when sources are credible but required information is missing.
- Choose reject when the proposed durable claim relies on Tier D material such as an untraceable performance claim.
- If the decision is reject, claims must explain why support is absent; never state that the material supports the claim.
- A discovery source may create a lead but cannot independently support a durable strategy claim.
- Return only the requested JSON object.

Case ID: {case.case_id}
Question: {case.question}

Evidence:
{evidence}
"""


def build_repair_prompt(
    case: ResearchEvalCase,
    prior_response: dict[str, Any],
    failures: list[str],
) -> str:
    """Ask the model for one bounded correction after deterministic validation fails."""
    return f"""{build_eval_prompt(case)}

Your previous JSON response failed deterministic validation.

Previous response:
{json.dumps(prior_response, indent=2, ensure_ascii=False)}

Validator failures:
{json.dumps(failures, indent=2, ensure_ascii=False)}

Return a corrected JSON object. Fix every listed failure without adding unsupported claims.
"""


def extract_json_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
    return json.loads(stripped)


def score_research_response(case: ResearchEvalCase, payload: dict[str, Any]) -> dict[str, Any]:
    score = 0
    maximum = 0
    failures: list[str] = []
    known_ids = {item["source_id"] for item in case.evidence}

    maximum += 1
    if payload.get("case_id") == case.case_id:
        score += 1
    else:
        failures.append("case_id does not match")

    maximum += 1
    if payload.get("decision") == case.expected_decision:
        score += 1
    else:
        failures.append(
            f"decision should be {case.expected_decision}, got {payload.get('decision')}"
        )

    maximum += 1
    citation_errors = []
    for claim in payload.get("claims", []):
        cited = set(claim.get("evidence_ids") or [])
        if not cited:
            citation_errors.append("uncited claim")
        elif not cited.issubset(known_ids):
            citation_errors.append("claim cites an unknown source")
    if not citation_errors:
        score += 1
    else:
        failures.extend(citation_errors)

    if case.required_missing_terms:
        maximum += 1
        missing_text = " ".join(payload.get("missing_information") or []).lower()
        absent = [term for term in case.required_missing_terms if term.lower() not in missing_text]
        if not absent:
            score += 1
        else:
            failures.append(f"missing-information section omits: {', '.join(absent)}")

    if case.forbidden_claim_phrases:
        maximum += 1
        claims_text = " ".join(
            str(item.get("claim", "")) for item in payload.get("claims", [])
        ).lower()
        present = [
            phrase for phrase in case.forbidden_claim_phrases if phrase.lower() in claims_text
        ]
        if not present:
            score += 1
        else:
            failures.append(
                "claim contradicts the rejection decision: " + ", ".join(present)
            )

    if case.require_no_strategy_rules:
        maximum += 1
        rules = payload.get("proposed_strategy_rules") or []
        if not rules:
            score += 1
        else:
            failures.append("invented or unsupported strategy rule was proposed")

    if case.reject_source_ids:
        maximum += 1
        assessments = {
            item.get("source_id"): item.get("quality")
            for item in payload.get("source_assessments", [])
        }
        wrong = [sid for sid in case.reject_source_ids if assessments.get(sid) != "reject"]
        if not wrong:
            score += 1
        else:
            failures.append(f"failed to reject source(s): {', '.join(wrong)}")

    if case.required_topics:
        maximum += 1
        combined = json.dumps(payload, ensure_ascii=False).lower()
        absent = [topic for topic in case.required_topics if topic.lower() not in combined]
        if not absent:
            score += 1
        else:
            failures.append(f"cross-asset mapping omits: {', '.join(absent)}")

    ratio = score / maximum if maximum else 0.0
    return {
        "case_id": case.case_id,
        "score": score,
        "maximum": maximum,
        "score_ratio": ratio,
        "passed": ratio >= 0.8 and not failures,
        "failures": failures,
    }


def call_ollama(
    model: str,
    prompt: str,
    base_url: str = "http://127.0.0.1:11434",
    timeout: int = 900,
) -> tuple[dict[str, Any], dict[str, Any]]:
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "format": RESPONSE_SCHEMA,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0, "seed": 42, "num_ctx": 8192},
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
    elapsed = time.perf_counter() - started
    content = raw.get("message", {}).get("content", "")
    parsed = extract_json_response(content)
    metadata = {
        "elapsed_seconds": round(elapsed, 3),
        "total_duration_ns": raw.get("total_duration"),
        "load_duration_ns": raw.get("load_duration"),
        "prompt_eval_count": raw.get("prompt_eval_count"),
        "eval_count": raw.get("eval_count"),
        "eval_duration_ns": raw.get("eval_duration"),
    }
    return parsed, metadata


def evaluate_model(model: str) -> dict[str, Any]:
    results = []
    for case in EVAL_CASES:
        parsed, metadata = call_ollama(model, build_eval_prompt(case))
        score = score_research_response(case, parsed)
        attempts = [
            {"attempt": 1, "response": parsed, "score": score, "metadata": metadata}
        ]
        if not score["passed"]:
            repaired, repaired_metadata = call_ollama(
                model,
                build_repair_prompt(case, parsed, score["failures"]),
            )
            repaired_score = score_research_response(case, repaired)
            attempts.append(
                {
                    "attempt": 2,
                    "response": repaired,
                    "score": repaired_score,
                    "metadata": repaired_metadata,
                }
            )
            if repaired_score["score_ratio"] >= score["score_ratio"]:
                parsed, score, metadata = repaired, repaired_score, repaired_metadata
        results.append(
            {
                "case": asdict(case),
                "response": parsed,
                "score": score,
                "metadata": metadata,
                "attempts": attempts,
            }
        )
    passed = sum(1 for item in results if item["score"]["passed"])
    return {
        "model": model,
        "cases_passed": passed,
        "cases_total": len(results),
        "passed": passed == len(results),
        "results": results,
    }


def save_evaluation(path: str | Path, evaluation: dict[str, Any]) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output)
