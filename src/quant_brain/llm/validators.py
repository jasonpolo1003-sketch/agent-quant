"""Deterministic validation gates for bounded Qwen research output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from quant_brain.research.schema import RawResearchSchemaError, validate_raw_research_payload

_NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
_SLOP_RE = re.compile(
    r"guaranteed (?:returns?|profits?)|effortless profit|secret (?:indicator|strategy)|"
    r"\b(?:9[0-9]|100)% (?:win|accuracy)|screenshot (?:proves|proof)",
    re.IGNORECASE,
)
_NEGATION_RE = re.compile(r"\b(?:does not|doesn't|no|not|never|without|absent|missing)\b", re.I)
_RULE_TOPIC_RE = re.compile(
    r"\b(?:exit\w*|holding period|threshold|cost\w*|commission\w*|slippage)\b", re.I
)
_HIGH_RISK_CLASSES = (
    ("Tier-D performance", re.compile(r"\b(?:risk[- ]free|always profitable|can't lose)\b", re.I)),
    (
        "cost",
        re.compile(
            r"\b(?:zero|no) (?:transaction )?costs?\b|\bcommission[- ]free\b|\bwithout slippage\b",
            re.I,
        ),
    ),
    (
        "prescriptive weekday rule",
        re.compile(
            r"\b(?:buy|sell|enter|exit|trade)\b[^.]{0,60}\b"
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday)\b",
            re.I,
        ),
    ),
)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reasons: tuple[str, ...] = ()
    normalized: dict[str, Any] | None = None


def _quotes(value: Any) -> list[str]:
    return [value] if isinstance(value, str) else [str(item) for item in value or []]


def _unsupported_numbers(value: Any, snapshot: str) -> list[str]:
    text = " ".join(_quotes(value))
    return sorted(set(_NUMBER_RE.findall(text)) - set(_NUMBER_RE.findall(snapshot)))


def _unsupported_high_risk_classes(value: Any, snapshot: str) -> list[str]:
    text = " ".join(_quotes(value))
    return [name for name, pattern in _HIGH_RISK_CLASSES if pattern.search(text) and not pattern.search(snapshot)]


def _normalize_passage(text: str) -> str:
    """Collapse whitespace/punctuation so quoting survives harmless reformatting.

    Deliberately conservative: it normalizes shape, never meaning. Negation and
    every content word are preserved, so "commission-free" cannot normalize to
    "not commission-free" or vice versa.
    """
    lowered = re.sub(r"[\s]+", " ", str(text or "").lower())
    cleaned = re.sub(r"[^a-z0-9%\- ]+", "", lowered)
    # Fold verb inflection only ("exit"/"exits", "day"/"days"). This changes the
    # form of a word, never its polarity or identity, so meaning reversal is
    # still detected while a faithful restatement is not punished for grammar.
    cleaned = re.sub(r"\b(\w{3,}?)(?:es|s)\b", r"\1", cleaned)
    return cleaned.strip()


# Words that flip the polarity of the claim they scope over. A clause is only
# supported by a snapshot span carrying the same negation state, so "costs are
# included" cannot be lifted out of "costs are not included".
_NEGATORS = frozenset({"not", "no", "never", "without", "cannot", "cant", "nor", "neither"})

def _tokens(text: str) -> list[str]:
    return [tok for tok in _normalize_passage(text).split(" ") if tok]


def _polarity_of(tokens: list[str], index: int) -> bool:
    """True when the token at `index` sits inside a negation scope.

    Scope is the small window of preceding tokens in the same clause, which is
    where English negation actually attaches. This is intentionally local: a
    negator three tokens back governs the claim, one at the far end of a
    paragraph does not.
    """
    window = tokens[max(0, index - 4) : index]
    return any(tok in _NEGATORS for tok in window)


def _token_span_matches(claim_tokens: list[str], hay_tokens: list[str], start: int) -> bool:
    """Whole-token equality for a candidate span.

    Affix negation needs no special case here: "unprofitable" is simply a
    different token from "profit", so requiring whole-token equality already
    refuses it. Scoped negation ("not commission-free") is handled separately by
    the polarity check, since there the tokens do match.
    """
    return all(
        claim_tok == hay_tokens[start + offset]
        for offset, claim_tok in enumerate(claim_tokens)
    )


def _clause_is_supported(clause: str, hay_tokens: list[str]) -> bool:
    """True when `clause` appears in the snapshot as whole tokens at equal polarity.

    Token-level rather than substring: "profit" no longer matches inside
    "unprofitable", and "commission-free" no longer matches inside "not
    commission-free". Polarity of the matched span must equal the polarity of
    the clause itself, so a faithfully quoted negation is still supported while
    a reversed one is not.
    """
    claim_tokens = _tokens(clause)
    if not claim_tokens:
        return True
    # Strip leading negators from the claim, remembering that it was negated, so
    # the comparison is claim-content vs snapshot-content at matching polarity.
    claim_negated = False
    while claim_tokens and claim_tokens[0] in _NEGATORS:
        claim_negated = True
        claim_tokens = claim_tokens[1:]
    if not claim_tokens:
        return True

    width = len(claim_tokens)
    for start in range(len(hay_tokens) - width + 1):
        if not _token_span_matches(claim_tokens, hay_tokens, start):
            continue
        if _polarity_of(hay_tokens, start) == claim_negated:
            return True
    return False


def _is_extractive(value: str, snapshot: str) -> bool:
    """True when every clause of `value` is a same-polarity passage of `snapshot`.

    Checked clause-by-clause rather than whole-string so a faithful restatement
    that merely rejoins or reorders sourced clauses still passes, while an
    invented clause fails on its own.

    Matching is over whole tokens with negation scope, not raw substrings.
    Substring containment accepted meaning reversal in both directions --
    "commission-free" out of "not commission-free" (scoped negation) and
    "profit" out of "unprofitable" (affix negation) -- which let a model invert
    its source and still look grounded.

    Every non-empty clause is checked. Earlier versions skipped clauses that did
    not match a keyword regex, which let invented rules evade grounding simply
    by avoiding the known vocabulary.
    """
    hay_tokens = _tokens(snapshot)
    clauses = [part for part in re.split(r"[;,.]| and | then ", str(value or "")) if part.strip()]
    for clause in clauses:
        if not _clause_is_supported(clause, hay_tokens):
            return False
    return bool(clauses)


def claim_is_extractively_supported(claim: str, evidence: Any) -> bool:
    """Return whether the complete claim is recoverable from exact evidence.

    Promotion uses a stricter boundary than advisory Scout analysis: every
    non-empty claim must be a normalized passage of the source quotation,
    regardless of whether a keyword regex recognizes it. Otherwise a generic
    invented claim such as "this method works reliably" could authorize
    promotion simply by avoiding the known strategy/performance vocabulary.
    """
    return _is_extractive(str(claim or ""), " ".join(_quotes(evidence)))


# Fields that can define a strategy, cost, timing, direction, or performance
# claim. A model assertion here is only credible if it is extractive.
_CLAIM_BEARING_RE = re.compile(
    r"\b(?:buy|sell|enter|exit|long|short|hold|stop|target|threshold|"
    r"cost\w*|commission\w*|slippage|fee\w*|return\w*|profit\w*|loss\w*|"
    r"sharpe|drawdown|win rate|robust|outperform\w*|"
    r"Monday|Tuesday|Wednesday|Thursday|Friday|day\w*|week\w*|month\w*)\b",
    re.I,
)


def validate_research_output(
    payload: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    expected_research_id: str | None = None,
) -> ValidationResult:
    """Run all research gates and return every deterministic rejection reason."""
    reasons: list[str] = []
    try:
        normalized = validate_raw_research_payload(payload)
    except (RawResearchSchemaError, TypeError, ValueError) as exc:
        return ValidationResult(False, (f"schema: {exc}",))

    if expected_research_id and normalized["research_id"] != expected_research_id:
        reasons.append(
            f"schema: research_id must be {expected_research_id}, got {normalized['research_id']}"
        )

    supplied = {str(item.get("source_id")): item for item in evidence if item.get("source_id")}
    output_ids = [source.get("source_id") for source in normalized["sources"]]
    seen_ids: set[str] = set()
    for source_id in output_ids:
        if source_id in seen_ids:
            reasons.append(f"source_id: duplicate source {source_id}")
        elif source_id:
            seen_ids.add(source_id)
    for source_id in supplied.keys() - seen_ids:
        reasons.append(f"source_id: omitted supplied source {source_id}")

    for source in normalized["sources"]:
        source_id = source.get("source_id")
        if not source_id or source_id not in supplied:
            reasons.append(f"source_id: unknown source {source_id or '<missing>'}")
            continue
        original = supplied[source_id]
        for field in ("title", "url_or_citation", "source_quality"):
            if source.get(field) != original.get(field):
                reasons.append(
                    f"protected:{field}:{source_id}: expected {original.get(field)!r}, "
                    f"got {source.get(field)!r}"
                )

        snapshot = str(original.get("snapshot_text") or "")
        for quote in _quotes(source.get("evidence")):
            if quote.strip() and quote.strip() not in snapshot:
                reasons.append(f"quote:{source_id}: exact evidence is absent from snapshot")

        if source.get("confidence") == "high" and source.get("source_quality") == "discovery-only":
            reasons.append(f"contradiction:{source_id}: high confidence is forbidden for discovery-only")

        claim = str(source.get("main_claim") or "")
        claim_negative = bool(_NEGATION_RE.search(claim) and _RULE_TOPIC_RE.search(claim))
        snapshot_positive = bool(_RULE_TOPIC_RE.search(snapshot) and not _NEGATION_RE.search(snapshot))
        if claim_negative and snapshot_positive:
            reasons.append(f"contradiction:{source_id}: claim denies rule information present in evidence")
        if re.search(r"\bincludes? (?:transaction )?costs?\b", claim, re.I) and re.search(
            r"\b(?:does not|doesn't|no|without)\b[^.]{0,40}\b(?:transaction )?costs?\b",
            snapshot,
            re.I,
        ):
            reasons.append(f"contradiction:{source_id}: claim reverses the evidence's cost statement")

        rule = str(source.get("possible_strategy_rule") or "")
        missing_numbers = sorted(set(_NUMBER_RE.findall(rule)) - set(_NUMBER_RE.findall(snapshot)))
        if missing_numbers:
            reasons.append(
                f"invented-rule:{source_id}: unsupported numeric/rule values: "
                + ", ".join(missing_numbers)
            )
        # Extract first, interpret later. A rule that defines strategy, timing,
        # direction, or cost must be an exact passage of its own snapshot.
        # Class-level matching cannot distinguish Tuesday from Monday, or
        # "commission-free" from "not commission-free"; containment can.
        if rule.strip() and not claim_is_extractively_supported(rule, snapshot):
            reasons.append(
                f"extractive:{source_id}:possible_strategy_rule: not an exact passage of the "
                "snapshot; quote the source or leave the rule empty"
            )
        # A rule needs no digits to smuggle a cost, prescriptive, or Tier-D claim,
        # so the numeric diff above is not sufficient on its own.
        unsupported_rule_classes = _unsupported_high_risk_classes(rule, snapshot)
        if unsupported_rule_classes:
            reasons.append(
                f"grounding:{source_id}:possible_strategy_rule: unsupported high-risk content: "
                + ", ".join(unsupported_rule_classes)
            )

        for field in ("main_claim", "risks", "data_required"):
            unsupported = _unsupported_numbers(source.get(field), snapshot)
            if unsupported:
                reasons.append(
                    f"grounding:{source_id}:{field}: unsupported numeric content: "
                    + ", ".join(unsupported)
                )
            unsupported_classes = _unsupported_high_risk_classes(source.get(field), snapshot)
            if unsupported_classes:
                reasons.append(
                    f"grounding:{source_id}:{field}: unsupported high-risk content: "
                    + ", ".join(unsupported_classes)
                )

        # Model judgment alone cannot authorize durable promotion. The model may
        # assert anything it likes in main_claim, but the moment it also asserts
        # the fields the curator reads as promotion authority, the claim itself
        # must be extractively supported. Declining to promote stays free.
        claims_promotion = bool(source.get("mvp_testable")) or (
            normalized["curator_recommendation"] == "promote_source"
        )
        if claims_promotion and _CLAIM_BEARING_RE.search(claim) and not _is_extractive(
            claim, snapshot
        ):
            reasons.append(
                f"ungrounded-promotion:{source_id}: main_claim asserts a strategy/performance "
                "claim that is not an exact passage of the snapshot, so it cannot carry "
                "mvp_testable or promote_source"
            )

        combined = json.dumps(source, ensure_ascii=False)
        if _SLOP_RE.search(combined):
            reasons.append(f"slop:{source_id}: Tier-D promotional/performance language detected")

    all_snapshots = "\n".join(str(item.get("snapshot_text") or "") for item in evidence)
    unsupported_questions = _unsupported_numbers(normalized["open_questions"], all_snapshots)
    if unsupported_questions:
        reasons.append(
            "grounding:payload:open_questions: unsupported numeric content: "
            + ", ".join(unsupported_questions)
        )
    unsupported_question_classes = _unsupported_high_risk_classes(
        normalized["open_questions"], all_snapshots
    )
    if unsupported_question_classes:
        reasons.append(
            "grounding:payload:open_questions: unsupported high-risk content: "
            + ", ".join(unsupported_question_classes)
        )
    if normalized["curator_recommendation"] == "create_strategy_card" and not any(
        source.get("possible_strategy_rule", "").strip() for source in normalized["sources"]
    ):
        reasons.append(
            "grounding:payload:curator_recommendation: prescriptive recommendation lacks a "
            "grounded rule"
        )

    return ValidationResult(not reasons, tuple(reasons), normalized if not reasons else None)
