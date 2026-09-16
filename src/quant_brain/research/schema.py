"""Raw research note contract shared by scout output and curator intake.

The live worker prompt in ``scout_runner.build_scout_prompt`` is the source of
truth for field names and enums. Manual notes and seeded catalogs must satisfy
the same contract; illegal values fail closed instead of reaching promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DATA_ACCESS_VALUES = ("available-now", "available-later", "not-realistic")
CONFIDENCE_VALUES = ("low", "medium", "high")
SOURCE_QUALITY_VALUES = ("primary", "practitioner", "discovery-only", "reject")
# ``web`` is used by the seeded catalog and maps to ``brain/01_Sources/web/``.
SOURCE_TYPE_VALUES = ("book", "paper", "blog", "repo", "docs", "other", "web")
NOTE_STATUS_VALUES = ("raw_saved",)
CURATOR_RECOMMENDATION_VALUES = (
    "promote_source",
    "update_door",
    "create_strategy_card",
    "needs_more_work",
    "rejected",
)

DataAccess = Literal["available-now", "available-later", "not-realistic"]
Confidence = Literal["low", "medium", "high"]
SourceQuality = Literal["primary", "practitioner", "discovery-only", "reject"]
SourceType = Literal["book", "paper", "blog", "repo", "docs", "other", "web"]
NoteStatus = Literal["raw_saved"]
CuratorRecommendation = Literal[
    "promote_source",
    "update_door",
    "create_strategy_card",
    "needs_more_work",
    "rejected",
]


class RawResearchSchemaError(ValueError):
    """Raised when a raw research payload violates the output contract."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        self.errors = errors or []
        super().__init__(message)


class RawResearchSource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Legacy/manual notes predate source IDs. The validated Qwen boundary
    # requires this field, while the shared curator contract remains backward compatible.
    source_id: str | None = None
    title: str = Field(min_length=1)
    source_type: SourceType
    url_or_citation: str = Field(min_length=1)
    main_claim: str = Field(min_length=1)
    evidence: str | list[str]
    possible_strategy_rule: str = ""
    risks: list[str]
    confidence: Confidence
    source_quality: SourceQuality
    asset_classes: list[str]
    data_required: list[str]
    data_access: DataAccess
    mvp_testable: bool

    @field_validator("evidence")
    @classmethod
    def evidence_must_not_be_empty(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("evidence must be a non-empty string")
            return value
        if not value or not any(str(item).strip() for item in value):
            raise ValueError("evidence must include at least one non-empty passage")
        return value


class RawResearchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    research_id: str = Field(min_length=1)
    status: NoteStatus
    sources: list[RawResearchSource]
    open_questions: list[str]
    curator_recommendation: CuratorRecommendation


def _format_pydantic_error(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ())) or "payload"
        parts.append(f"{location}: {error.get('msg')}")
    return "raw research payload failed schema validation: " + "; ".join(parts)


def validate_raw_research_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw-note JSON object and return a normalized dict.

    Illegal enums (for example ``data_access: "partial"``), missing required
    fields, and extra unknown fields all fail closed.
    """
    if not isinstance(payload, dict):
        raise RawResearchSchemaError(
            f"raw research payload must be an object, got {type(payload).__name__}"
        )
    try:
        model = RawResearchPayload.model_validate(payload)
    except ValidationError as exc:
        raise RawResearchSchemaError(_format_pydantic_error(exc), errors=exc.errors()) from exc
    return model.model_dump()


def validate_raw_research_note(path: str | Path) -> dict[str, Any]:
    """Extract the final fenced JSON block from a raw note and validate it."""
    from quant_brain.curation.executor import extract_scout_json

    payload = extract_scout_json(path)
    return validate_raw_research_payload(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a raw research note or JSON payload against the scout contract."
    )
    parser.add_argument("path", help="Path to a raw research markdown note or a JSON file.")
    args = parser.parse_args(argv)
    target = Path(args.path)
    if not target.exists():
        print(f"file not found: {target}", file=sys.stderr)
        return 2
    try:
        if target.suffix.lower() == ".json":
            payload = json.loads(target.read_text(encoding="utf-8"))
            validate_raw_research_payload(payload)
        else:
            validate_raw_research_note(target)
    except (RawResearchSchemaError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"ok: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
