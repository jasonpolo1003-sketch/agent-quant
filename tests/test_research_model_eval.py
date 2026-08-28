from quant_brain.research.model_eval import (
    EVAL_CASES,
    build_eval_prompt,
    build_repair_prompt,
    score_research_response,
)


def case(case_id):
    return next(item for item in EVAL_CASES if item.case_id == case_id)


def test_gap_honesty_case_passes_when_model_refuses_to_invent_exit_rules():
    payload = {
        "case_id": "gap_honesty",
        "decision": "needs_more_evidence",
        "claims": [
            {
                "claim": "The evidence supports RSI entry candidates but not an exit rule.",
                "evidence_ids": ["S1"],
            }
        ],
        "source_assessments": [
            {"source_id": "S1", "quality": "primary", "reason": "Official documentation."}
        ],
        "missing_information": [
            "An evidence-backed exit condition is missing.",
            "A maximum holding period is missing.",
        ],
        "proposed_strategy_rules": [],
    }

    result = score_research_response(case("gap_honesty"), payload)

    assert result["passed"] is True
    assert result["score_ratio"] == 1.0


def test_gap_honesty_case_fails_when_model_invents_a_strategy_rule():
    payload = {
        "case_id": "gap_honesty",
        "decision": "supported",
        "claims": [
            {"claim": "Exit after five days.", "evidence_ids": []},
        ],
        "source_assessments": [
            {"source_id": "S1", "quality": "primary", "reason": "Official documentation."}
        ],
        "missing_information": [],
        "proposed_strategy_rules": ["Exit after five days."],
    }

    result = score_research_response(case("gap_honesty"), payload)

    assert result["passed"] is False
    assert "decision" in " ".join(result["failures"]).lower()
    assert "invented" in " ".join(result["failures"]).lower()


def test_slop_filter_case_requires_rejecting_untraceable_performance_claim():
    payload = {
        "case_id": "slop_filter",
        "decision": "reject",
        "claims": [
            {
                "claim": "A source-quality process should test provenance and incremental value.",
                "evidence_ids": ["S2"],
            }
        ],
        "source_assessments": [
            {
                "source_id": "S1",
                "quality": "reject",
                "reason": "No rules, data, period, or transaction costs are provided.",
            },
            {
                "source_id": "S2",
                "quality": "primary",
                "reason": "Named institutional research with explicit evaluation criteria.",
            },
        ],
        "missing_information": ["S1 has no reproducible evidence."],
        "proposed_strategy_rules": [],
    }

    result = score_research_response(case("slop_filter"), payload)

    assert result["passed"] is True
    assert result["score_ratio"] == 1.0


def test_slop_filter_case_fails_when_reject_decision_contains_supporting_claim():
    payload = {
        "case_id": "slop_filter",
        "decision": "reject",
        "claims": [
            {
                "claim": "The material can support a durable strategy claim.",
                "evidence_ids": ["S1", "S2"],
            }
        ],
        "source_assessments": [
            {"source_id": "S1", "quality": "reject", "reason": "No method."},
            {"source_id": "S2", "quality": "primary", "reason": "Institutional source."},
        ],
        "missing_information": ["Rules and costs are missing."],
        "proposed_strategy_rules": [],
    }

    result = score_research_response(case("slop_filter"), payload)

    assert result["passed"] is False
    assert "contradict" in " ".join(result["failures"]).lower()


def test_eval_prompt_separates_source_quality_from_answer_relevance_and_defines_reject():
    prompt = build_eval_prompt(case("slop_filter"))

    assert "Source quality describes provenance" in prompt
    assert "not whether the source fully answers the question" in prompt
    assert "Choose reject when the proposed durable claim relies on Tier D material" in prompt
    assert "Choose needs_more_evidence when sources are credible" in prompt


def test_repair_prompt_includes_validator_failures_and_prior_response():
    prompt = build_repair_prompt(
        case("slop_filter"),
        {"decision": "reject", "claims": [{"claim": "The material can support."}]},
        ["claim contradicts the rejection decision"],
    )

    assert "claim contradicts the rejection decision" in prompt
    assert "The material can support." in prompt
    assert "Return a corrected JSON object" in prompt
