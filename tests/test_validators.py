from copy import deepcopy

import pytest

from quant_brain.llm.validators import validate_research_output


@pytest.fixture
def evidence():
    return [
        {
            "source_id": "S1",
            "title": "Official RSI note",
            "url_or_citation": "https://example.test/rsi",
            "source_quality": "primary",
            "snapshot_text": "The study uses RSI below 30 and exits after 5 trading days. Exact quote.",
        }
    ]


@pytest.fixture
def payload():
    return {
        "research_id": "RQ-test",
        "status": "raw_saved",
        "sources": [
            {
                "source_id": "S1",
                "title": "Official RSI note",
                "source_type": "paper",
                "url_or_citation": "https://example.test/rsi",
                "main_claim": "The study uses RSI below 30.",
                "evidence": "Exact quote.",
                "possible_strategy_rule": "RSI below 30; exit after 5 trading days.",
                "risks": ["Results may not generalize."],
                "confidence": "high",
                "source_quality": "primary",
                "asset_classes": ["equity"],
                "data_required": ["daily close"],
                "data_access": "available-now",
                "mvp_testable": True,
            }
        ],
        "open_questions": [],
        "curator_recommendation": "promote_source",
    }


def test_valid_output_passes_all_deterministic_gates(payload, evidence):
    result = validate_research_output(payload, evidence, expected_research_id="RQ-test")
    assert result.ok
    assert result.reasons == ()


def test_schema_gate_reuses_raw_research_contract(payload, evidence):
    del payload["status"]
    result = validate_research_output(payload, evidence, expected_research_id="RQ-test")
    assert not result.ok
    assert any(reason.startswith("schema:") for reason in result.reasons)


def test_rejects_unknown_source_id(payload, evidence):
    payload["sources"][0]["source_id"] = "S999"
    result = validate_research_output(payload, evidence)
    assert "source_id: unknown source S999" in result.reasons


def test_rejects_duplicate_output_source_ids(payload, evidence):
    payload["sources"].append(deepcopy(payload["sources"][0]))
    result = validate_research_output(payload, evidence)
    assert "source_id: duplicate source S1" in result.reasons


def test_rejects_omitted_supplied_source(payload, evidence):
    evidence.append({
        "source_id": "S2",
        "title": "Second study",
        "url_or_citation": "https://example.test/second",
        "source_quality": "primary",
        "snapshot_text": "A second supplied snapshot.",
    })
    result = validate_research_output(payload, evidence)
    assert "source_id: omitted supplied source S2" in result.reasons


@pytest.mark.parametrize("field", ["title", "url_or_citation", "source_quality"])
def test_rejects_model_changes_to_protected_source_metadata(payload, evidence, field):
    payload["sources"][0][field] = (
        "practitioner" if field == "source_quality" else "invented"
    )
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith(f"protected:{field}:") for reason in result.reasons)


def test_rejects_quote_not_present_in_corresponding_snapshot(payload, evidence):
    payload["sources"][0]["evidence"] = "A fabricated quotation."
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith("quote:S1:") for reason in result.reasons)


def test_rejects_high_confidence_discovery_only_contradiction(payload, evidence):
    evidence[0]["source_quality"] = "discovery-only"
    payload["sources"][0]["source_quality"] = "discovery-only"
    result = validate_research_output(payload, evidence)
    assert any("high confidence" in reason for reason in result.reasons)


def test_rejects_claim_that_denies_corresponding_evidence(payload, evidence):
    payload["sources"][0]["main_claim"] = "The source does not specify an exit rule."
    payload["sources"][0]["possible_strategy_rule"] = ""
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith("contradiction:S1:") for reason in result.reasons)


def test_rejects_invented_numeric_rule_absent_from_evidence(payload, evidence):
    payload["sources"][0]["possible_strategy_rule"] = "RSI below 17; exit after 11 days."
    result = validate_research_output(payload, evidence)
    assert any("unsupported numeric/rule values" in reason for reason in result.reasons)


@pytest.mark.parametrize(
    "rule",
    [
        "Exit commission-free on Monday.",
        "This rule is risk-free.",
    ],
)
def test_rejects_non_numeric_high_risk_strategy_rule(payload, evidence, rule):
    """A rule can smuggle cost/prescriptive/Tier-D claims without using any digits.

    The invented-rule gate only diffs numerics, so a digit-free rule reached the
    raw note ungrounded until this class was checked too.
    """
    payload["sources"][0]["possible_strategy_rule"] = rule
    result = validate_research_output(payload, evidence)
    assert not result.ok
    assert any(
        reason.startswith("grounding:S1:possible_strategy_rule:") for reason in result.reasons
    )


@pytest.fixture
def reversal_evidence():
    """A snapshot that mentions a weekday and negates a cost property.

    Class-level matching treats this as authorizing any weekday and any cost
    claim; extractive grounding must not.
    """
    return [
        {
            "source_id": "S1",
            "title": "Official RSI note",
            "url_or_citation": "https://example.test/rsi",
            "source_quality": "primary",
            "snapshot_text": (
                "The study says buy on Tuesday. The results are not commission-free."
            ),
        }
    ]


@pytest.mark.parametrize(
    ("rule", "why"),
    [
        ("Exit commission-free on Monday.", "different weekday and reversed cost polarity"),
        ("Exit on Monday.", "Tuesday evidence must not authorize Monday"),
        ("Exit commission-free.", "'not commission-free' must not authorize the positive"),
    ],
)
def test_strategy_rule_requires_extractive_support(payload, reversal_evidence, rule, why):
    """A rule must be an exact passage of its snapshot, not a class-level match."""
    payload["sources"][0]["evidence"] = "The study says buy on Tuesday."
    payload["sources"][0]["main_claim"] = "The study describes a weekday entry."
    payload["sources"][0]["possible_strategy_rule"] = rule
    result = validate_research_output(payload, reversal_evidence)
    assert not result.ok, why
    assert any(
        reason.startswith("extractive:S1:possible_strategy_rule") for reason in result.reasons
    )


def test_strategy_rule_passes_when_quoted_verbatim_from_snapshot(payload, reversal_evidence):
    """The escape hatch stays open: an exact passage is still promotable."""
    payload["sources"][0]["evidence"] = "The study says buy on Tuesday."
    payload["sources"][0]["main_claim"] = "The study says buy on Tuesday."
    payload["sources"][0]["possible_strategy_rule"] = "buy on Tuesday"
    result = validate_research_output(payload, reversal_evidence)
    assert result.ok, result.reasons


def test_generic_ungrounded_strategy_rule_is_rejected(payload, reversal_evidence):
    """A rule cannot bypass extractive grounding by avoiding known keywords."""
    payload["sources"][0]["evidence"] = "The study says buy on Tuesday."
    payload["sources"][0]["main_claim"] = "The study says buy on Tuesday."
    payload["sources"][0]["possible_strategy_rule"] = "This method works reliably."

    result = validate_research_output(payload, reversal_evidence)

    assert not result.ok
    assert any(
        reason.startswith("extractive:S1:possible_strategy_rule") for reason in result.reasons
    )


def test_empty_strategy_rule_remains_allowed(payload, reversal_evidence):
    """Declining to propose a rule is the conservative default and must pass."""
    payload["sources"][0]["evidence"] = "The study says buy on Tuesday."
    payload["sources"][0]["main_claim"] = "The study says buy on Tuesday."
    payload["sources"][0]["possible_strategy_rule"] = ""
    result = validate_research_output(payload, reversal_evidence)
    assert result.ok, result.reasons


def test_unsupported_main_claim_cannot_be_marked_mvp_testable(payload, reversal_evidence):
    """Benign exact evidence must not support an invented 'robust strategy' claim.

    The model may still say this, but not while asserting the fields that drive
    durable promotion.
    """
    payload["sources"][0]["evidence"] = "The study says buy on Tuesday."
    payload["sources"][0]["main_claim"] = "A robust strategy is supported."
    payload["sources"][0]["mvp_testable"] = True
    payload["curator_recommendation"] = "promote_source"
    result = validate_research_output(payload, reversal_evidence)
    assert not result.ok
    assert any(reason.startswith("ungrounded-promotion:S1") for reason in result.reasons)


def test_skepticism_remains_allowed_without_promotion_fields(payload, reversal_evidence):
    """Reasonable interpretation is fine when it does not claim promotion authority."""
    payload["sources"][0]["evidence"] = "The study says buy on Tuesday."
    payload["sources"][0]["main_claim"] = "A robust strategy is supported."
    payload["sources"][0]["mvp_testable"] = False
    payload["sources"][0]["possible_strategy_rule"] = ""
    payload["curator_recommendation"] = "needs_more_work"
    result = validate_research_output(payload, reversal_evidence)
    assert result.ok, result.reasons


def test_rejects_non_numeric_high_risk_claim_in_open_questions(payload, evidence):
    """open_questions was numeric-only checked, so digit-free Tier-D claims passed."""
    payload["open_questions"] = ["Is this strategy risk-free?"]
    result = validate_research_output(payload, evidence)
    assert not result.ok
    assert any(
        reason.startswith("grounding:payload:open_questions:") for reason in result.reasons
    )


@pytest.mark.parametrize("field", ["main_claim", "risks", "data_required"])
def test_rejects_unsupported_high_risk_claims_across_source_fields(payload, evidence, field):
    invented = "Guaranteed 83.7% annual return with zero costs by buying every Tuesday."
    payload["sources"][0][field] = [invented] if field in {"risks", "data_required"} else invented
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith(f"grounding:S1:{field}:") for reason in result.reasons)


def test_rejects_unsupported_high_risk_claim_in_open_questions(payload, evidence):
    payload["open_questions"] = [
        "Can the guaranteed 83.7% annual return with zero costs every Tuesday be replicated?"
    ]
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith("grounding:payload:open_questions:") for reason in result.reasons)


def test_rejects_prescriptive_recommendation_without_grounded_rule(payload, evidence):
    payload["sources"][0]["possible_strategy_rule"] = ""
    payload["curator_recommendation"] = "create_strategy_card"
    result = validate_research_output(payload, evidence)
    assert "grounding:payload:curator_recommendation: prescriptive recommendation lacks a grounded rule" in result.reasons


def test_allows_reasonable_non_numeric_paraphrase(payload, evidence):
    payload["sources"][0]["main_claim"] = "The paper describes an oversold RSI setup."
    result = validate_research_output(payload, evidence)
    assert result.ok


@pytest.mark.parametrize(
    ("field", "claim"),
    [
        ("main_claim", "This strategy is risk-free and always profitable."),
        ("risks", "The backtest assumes zero transaction costs."),
        ("data_required", "Buy every Tuesday using daily close data."),
    ],
)
def test_rejects_unsupported_tier_d_cost_and_prescriptive_classes(
    payload, evidence, field, claim
):
    payload["sources"][0][field] = [claim] if field in {"risks", "data_required"} else claim
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith(f"grounding:S1:{field}:") for reason in result.reasons)


def test_rejects_positive_cost_claim_when_snapshot_explicitly_denies_it(payload, evidence):
    evidence[0]["snapshot_text"] += " The study does not include transaction costs."
    payload["sources"][0]["main_claim"] = "The study includes transaction costs."
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith("contradiction:S1:") for reason in result.reasons)


def test_rejects_tier_d_promotional_slop(payload, evidence):
    payload["sources"][0]["main_claim"] = "Guaranteed effortless profit with a 95% win rate."
    payload["sources"][0]["possible_strategy_rule"] = ""
    payload["sources"][0]["confidence"] = "low"
    result = validate_research_output(payload, evidence)
    assert any(reason.startswith("slop:S1:") for reason in result.reasons)


def test_validation_does_not_mutate_payload(payload, evidence):
    original = deepcopy(payload)
    validate_research_output(payload, evidence)
    assert payload == original


# --- Token-boundary and negation-scope grounding (independent review R2) ---


@pytest.mark.parametrize(
    ("claim", "snapshot", "why"),
    [
        (
            "commission-free",
            "The results are not commission-free.",
            "negated evidence must not authorize the positive claim",
        ),
        (
            "profit",
            "The strategy was unprofitable.",
            "'profit' inside 'unprofitable' is a substring, not support",
        ),
        (
            "The strategy is profitable.",
            "The strategy is unprofitable.",
            "affix negation reverses meaning",
        ),
        (
            "costs are included",
            "costs are not included",
            "explicit negation reverses meaning",
        ),
        (
            "we recommend the rule",
            "we do not recommend the rule",
            "'do not' scopes over the following claim",
        ),
    ],
)
def test_extractive_support_respects_token_boundaries_and_negation(claim, snapshot, why):
    from quant_brain.llm.validators import claim_is_extractively_supported

    assert not claim_is_extractively_supported(claim, snapshot), why


@pytest.mark.parametrize(
    ("claim", "snapshot", "why"),
    [
        ("buy on Tuesday", "The study says buy on Tuesday.", "verbatim support still passes"),
        (
            "not commission-free",
            "The results are not commission-free.",
            "quoting the negation faithfully is still extractive",
        ),
        (
            "the strategy was unprofitable",
            "The strategy was unprofitable.",
            "a negated word quoted whole is supported",
        ),
        (
            "exit after 5 trading days",
            "The study exits after 5 trading days.",
            "verb inflection alone must not break support",
        ),
    ],
)
def test_faithful_quotation_still_supported(claim, snapshot, why):
    from quant_brain.llm.validators import claim_is_extractively_supported

    assert claim_is_extractively_supported(claim, snapshot), why
