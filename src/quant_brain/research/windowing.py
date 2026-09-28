"""Deterministic windows for a single source too large for one extraction prompt.

PROP-006. The full snapshot stays the source of truth: a window is only a
recorded slice of it (offsets plus a sha256), every window is read in document
order, and each must return an explicit validated outcome. ``no_relevant_evidence``
exists because the raw-research contract cannot say "nothing here" without a
quotation and a claim, and inventing either is exactly what the validators
forbid. The window contract is internal to extraction: it is never written to a
note and the curator never reads it. Windows merge into one ordinary
``RawResearchSource`` by fixed rules that copy text verbatim and generate none.
"""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from quant_brain.llm.validators import ValidationResult, validate_research_output
from quant_brain.research.schema import RawResearchSource

# Sized in UTF-8 bytes at a deliberately pessimistic 1.5 bytes per token: the
# worst snapshot measured (NAAIM PDF mojibake) ran 1.77. ~6,000 window tokens
# leave room inside the 11,571-token budget for the instructions and for a
# repair prompt, which embeds the previous response.
WINDOW_BYTES_PER_TOKEN = 1.5
WINDOW_TOKEN_TARGET = 6000
WINDOW_MAX_BYTES = int(WINDOW_TOKEN_TARGET * WINDOW_BYTES_PER_TOKEN)
# A passage of at most this many bytes always lies wholly inside some window.
WINDOW_OVERLAP_BYTES = 1200
# A cut moves back to a line (else word) break found within this last fraction
# of the window, and is a hard cut only when there is none.
SNAP_FRACTION = 0.1
# Refused before any model call above this: ~8 windows for NAAIM, and each
# window is a full ladder under the one shared run deadline.
MAX_WINDOWS_PER_SOURCE = 10
# A windowed source's recommendation is fixed, never asked of the model. It is
# the most conservative value (it asserts nothing a validator did not already
# check), the one the merge already fell back to on any disagreement, and the
# curator does not read it. Asking each window for it gave the model a
# required-yet-nullable field to leave null, which failed E4 (RUN-d67b1d121b).
WINDOW_RECOMMENDATION = "needs_more_work"

_CONFIDENCE_ORDER = ("low", "medium", "high")
_ACCESS_ORDER = ("available-now", "available-later", "not-realistic")


class WindowMergeError(ValueError):
    """Window outcomes cannot become one source record without inventing one."""


@dataclass(frozen=True)
class SourceWindow:
    source_id: str
    window_id: str
    index: int
    count: int
    start: int
    end: int
    text_sha256: str

    def text_of(self, full_text: str) -> str:
        return full_text[self.start : self.end]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_windows(
    text: str,
    source_id: str,
    *,
    max_bytes: int = WINDOW_MAX_BYTES,
    overlap_bytes: int = WINDOW_OVERLAP_BYTES,
) -> list[SourceWindow]:
    """Split ``text`` into ordered, overlapping windows of at most ``max_bytes``.

    Pure and deterministic. Offsets are code-point indexes into ``text``; the
    first window starts at 0 and the last ends at ``len(text)``. Each next
    window starts at the earliest character within ``overlap_bytes`` of the
    previous end, so any passage no longer than the overlap is never split.
    Content is never inspected for relevance: every window exists.
    """
    snap_bytes = int(max_bytes * SNAP_FRACTION)
    if overlap_bytes < 0 or overlap_bytes + snap_bytes + 4 >= max_bytes:
        raise ValueError(
            f"overlap_bytes {overlap_bytes} must leave room inside max_bytes {max_bytes}"
        )
    prefix = [0]
    for char in text:
        prefix.append(prefix[-1] + len(char.encode("utf-8")))
    total = len(text)

    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        limit = prefix[start] + max_bytes
        if prefix[total] <= limit:
            spans.append((start, total))
            break
        hard = bisect_right(prefix, limit) - 1
        floor = max(bisect_left(prefix, limit - snap_bytes), start + 1)
        end = hard
        newline = text.rfind("\n", floor - 1, hard)
        if newline >= 0:
            end = newline + 1
        else:
            for position in range(hard - 1, floor - 2, -1):
                if text[position].isspace():
                    end = position + 1
                    break
        spans.append((start, end))
        start = max(bisect_left(prefix, prefix[end] - overlap_bytes), start + 1)

    count = len(spans)
    return [
        SourceWindow(
            source_id=source_id,
            window_id=f"{source_id}-W{index:02d}",
            index=index,
            count=count,
            start=begin,
            end=finish,
            text_sha256=_sha256(text[begin:finish]),
        )
        for index, (begin, finish) in enumerate(spans, start=1)
    ]


class WindowSource(RawResearchSource):
    """A source record whose identity is required, not legacy-optional.

    ``RawResearchSource.source_id`` stays optional for old manual notes. Here it
    is required in the schema sent to the model, so constrained decoding cannot
    emit a source without it (E4's repair and escalation attempts both did).
    """

    source_id: str = Field(min_length=1)


class WindowOutcome(BaseModel):
    """One window's answer. Every field is required so "nothing here" is explicit."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    research_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    window_id: str = Field(min_length=1)
    outcome: Literal["evidence", "no_relevant_evidence"]
    source: WindowSource | None
    open_questions: list[str]

    @model_validator(mode="after")
    def _outcome_matches_content(self) -> WindowOutcome:
        if self.outcome == "evidence":
            if self.source is None:
                raise ValueError("an evidence outcome needs a source")
        elif self.source is not None or self.open_questions:
            raise ValueError(
                "a no_relevant_evidence outcome asserts nothing: source must be null "
                "and open_questions empty"
            )
        return self


def window_prompt(task: dict[str, Any], item: dict[str, Any], window: SourceWindow) -> str:
    """The extraction prompt for one window: only that window's text is shown."""
    source_id = item["source_id"]
    metadata = {key: item[key] for key in ("source_id", "title", "url_or_citation", "source_quality")}
    return (
        "Extract evidence from ONE WINDOW of a longer source, using only the window text "
        f"below. This is window {window.index} of {window.count} ({window.window_id}), "
        f"characters {window.start}-{window.end} of source {source_id}. Every window of "
        "this source is read separately.\n"
        f"Return research_id, source_id and window_id exactly as given. If this window "
        "holds no passage relevant to the question, return outcome "
        '"no_relevant_evidence" with source null and open_questions []. That is an '
        "honest, acceptable answer: do not quote an unrelated sentence. Otherwise return "
        'outcome "evidence" with exactly one source whose source_id is '
        f"{source_id}, preserving its source_id, title, URL, and source_quality exactly. Evidence values must be exact quotations of this "
        "window's text. Do not invent rules, thresholds, holding periods, or costs.\n\n"
        f"Research ID: {task['research_id']}\nQuestion: {task['question']}\n"
        f"Window ID: {window.window_id}\n"
        f"Source metadata:\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n"
        f"Window text for {window.window_id}:\n"
        f"<<<BEGIN WINDOW {window.window_id}>>>\n{window.text_of(item['snapshot_text'])}\n"
        f"<<<END WINDOW {window.window_id}>>>"
    )


def _quotes(value: Any) -> list[str]:
    return [value] if isinstance(value, str) else [str(item) for item in value or []]


def validate_window_outcome(
    payload: Any,
    item: dict[str, Any],
    window: SourceWindow,
    *,
    expected_research_id: str,
) -> ValidationResult:
    """Validate one window's outcome against the window shown and the full snapshot."""
    full_text = str(item.get("snapshot_text") or "")
    shown = window.text_of(full_text)
    if _sha256(shown) != window.text_sha256:
        return ValidationResult(
            False,
            (f"window:{window.window_id}: window text does not match its recorded hash",),
        )
    try:
        outcome = WindowOutcome.model_validate(payload)
    except (ValidationError, TypeError, ValueError) as exc:
        return ValidationResult(False, (f"schema: window outcome: {exc}",))

    reasons: list[str] = []
    if outcome.research_id != expected_research_id:
        reasons.append(
            f"schema: research_id must be {expected_research_id}, got {outcome.research_id}"
        )
    if outcome.source_id != item["source_id"]:
        reasons.append(f"window: source_id must be {item['source_id']}, got {outcome.source_id}")
    if outcome.window_id != window.window_id:
        reasons.append(f"window: window_id must be {window.window_id}, got {outcome.window_id}")
    if outcome.outcome == "no_relevant_evidence":
        return ValidationResult(not reasons, tuple(reasons), None if reasons else outcome.model_dump())

    if outcome.source is None:  # unreachable: the model validator requires it
        return ValidationResult(False, ("schema: window outcome: evidence without a source",))
    verdict = validate_research_output(
        {
            "research_id": outcome.research_id,
            "status": "raw_saved",
            "sources": [outcome.source.model_dump()],
            "open_questions": outcome.open_questions,
            "curator_recommendation": WINDOW_RECOMMENDATION,
        },
        [{**item, "snapshot_text": shown}],
        expected_research_id=expected_research_id,
    )
    reasons.extend(verdict.reasons)
    # Redundant by construction (the window is a slice of the full text), and
    # kept on purpose: it is the check that the slice shown was the real one.
    for quote in _quotes(outcome.source.evidence):
        if quote.strip() and quote.strip() not in full_text:
            reasons.append(
                f"quote-full:{item['source_id']}: exact evidence is absent from the full snapshot"
            )
    return ValidationResult(not reasons, tuple(reasons), None if reasons else outcome.model_dump())


def _union(values: Any) -> list[Any]:
    merged: list[Any] = []
    for value in values:
        if value not in merged:
            merged.append(value)
    return merged


def merge_window_outcomes(
    research_id: str,
    item: dict[str, Any],
    windows: list[SourceWindow],
    outcomes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fold validated window outcomes into one per-source payload, in window order.

    Nothing is generated: text is copied verbatim, lists are order-preserving
    unions, and ordered judgments take their most conservative value. Where a
    single honest value cannot be chosen (no evidence anywhere, or windows that
    disagree on ``source_type``), the source fails rather than being arbitrated.
    """
    source_id = item["source_id"]
    # Parsed first, so IDs are compared exactly as validate_window_outcome
    # accepted them (the contract strips surrounding whitespace).
    try:
        parsed = [WindowOutcome.model_validate(outcome) for outcome in outcomes]
    except ValidationError as exc:
        raise WindowMergeError(f"window: {source_id} has an invalid window outcome: {exc}") from exc
    expected = [window.window_id for window in windows]
    received = [outcome.window_id for outcome in parsed]
    if received != expected:
        raise WindowMergeError(
            f"window: accounting for {source_id}: expected outcomes for {expected}, got {received}"
        )
    if any(outcome.source_id != source_id for outcome in parsed):
        raise WindowMergeError(f"window: accounting for {source_id}: outcome for another source")

    found = [outcome for outcome in parsed if outcome.outcome == "evidence"]
    if not found:
        raise WindowMergeError(
            f"window: {source_id} had no relevant evidence in any of {len(windows)} windows; "
            "a source record cannot be built without fabricating one"
        )
    sources = [outcome.source.model_dump() for outcome in found if outcome.source is not None]
    source_types = _union(source["source_type"] for source in sources)
    if len(source_types) != 1:
        raise WindowMergeError(
            f"window: {source_id} windows disagree on source_type {source_types}; not arbitrated"
        )
    merged = {
        "source_id": source_id,
        "title": item["title"],
        "source_type": source_types[0],
        "url_or_citation": item["url_or_citation"],
        "main_claim": "; ".join(_union(source["main_claim"] for source in sources)),
        "evidence": _union(
            quote for source in sources for quote in _quotes(source["evidence"]) if quote.strip()
        ),
        "possible_strategy_rule": "; ".join(
            _union(
                source["possible_strategy_rule"]
                for source in sources
                if source["possible_strategy_rule"].strip()
            )
        ),
        "risks": _union(risk for source in sources for risk in source["risks"]),
        "confidence": min(
            (source["confidence"] for source in sources), key=_CONFIDENCE_ORDER.index
        ),
        "source_quality": item["source_quality"],
        "asset_classes": _union(value for source in sources for value in source["asset_classes"]),
        "data_required": _union(value for source in sources for value in source["data_required"]),
        "data_access": max((source["data_access"] for source in sources), key=_ACCESS_ORDER.index),
        "mvp_testable": all(source["mvp_testable"] for source in sources),
    }
    return {
        "research_id": research_id,
        "status": "raw_saved",
        "sources": [merged],
        "open_questions": _union(q for outcome in found for q in outcome.open_questions),
        "curator_recommendation": WINDOW_RECOMMENDATION,
    }


def window_manifest(
    item: dict[str, Any],
    windows: list[SourceWindow],
    *,
    snapshot_path: str,
    snapshot_sha256: str,
) -> dict[str, Any]:
    """Everything needed to rebuild each window from the immutable snapshot."""
    full_text = str(item["snapshot_text"])
    return {
        "source_id": item["source_id"],
        "url_or_citation": item["url_or_citation"],
        "snapshot_path": snapshot_path,
        "snapshot_sha256": snapshot_sha256,
        "snapshot_text_derivation": (
            "snapshot file decoded as UTF-8 with universal newlines (Path.read_text: "
            "CRLF and CR become LF); offsets are character indexes into that text"
        ),
        "snapshot_text_sha256": _sha256(full_text),
        "snapshot_text_length": len(full_text),
        "window_max_bytes": WINDOW_MAX_BYTES,
        "window_overlap_bytes": WINDOW_OVERLAP_BYTES,
        "window_count": len(windows),
        "windows": [
            {
                "window_id": window.window_id,
                "index": window.index,
                "start": window.start,
                "end": window.end,
                "text_sha256": window.text_sha256,
                "outcome": "not_run",
                "validator_ok": None,
                "attempts": [],
            }
            for window in windows
        ],
    }


def window_manifest_markdown(manifests: list[dict[str, Any]]) -> str:
    """Human-readable window record, kept outside the curator's JSON block."""
    lines = [
        "## Extraction Windows",
        "",
        "Sources too large for one prompt were read in deterministic, overlapping windows "
        "of the immutable snapshot (PROP-006). Every window has an explicit validated "
        "outcome; offsets are character positions in the snapshot text.",
        "",
    ]
    for manifest in manifests:
        lines.extend(
            [
                f"### {manifest['source_id']}: {manifest['url_or_citation']}",
                "",
                f"- Snapshot: `{manifest['snapshot_path']}`",
                f"- Snapshot sha256 (file bytes): `{manifest['snapshot_sha256']}`",
                f"- Snapshot text sha256: `{manifest['snapshot_text_sha256']}` "
                f"({manifest['snapshot_text_length']} characters)",
                f"- Offsets index: {manifest['snapshot_text_derivation']}",
                f"- Windows: {manifest['window_count']} (max {manifest['window_max_bytes']} "
                f"bytes, overlap {manifest['window_overlap_bytes']} bytes)",
                "",
                "| Window | Start | End | sha256 | Outcome | Attempts |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for window in manifest["windows"]:
            lines.append(
                f"| {window['window_id']} | {window['start']} | {window['end']} | "
                f"`{window['text_sha256']}` | {window['outcome']} | {len(window['attempts'])} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"
