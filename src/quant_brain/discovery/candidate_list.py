"""Pre-registered candidate lists: known URLs a Scout run may fetch (PROP-004).

A list names the upstream URLs for one research question, with where each was
found, before any run. It is a *discovery* input only. The Scout still
classifies, ranks, fetches, content-checks, snapshots and extracts every entry
through the unchanged live path, and the validators and curator still decide
what is supported. So an entry can carry a URL and its provenance, and nothing
else: unknown fields are rejected rather than ignored, which is what stops a
list from supplying a tier, a title, a claim or evidence.

Not to be confused with ``SeededDiscoveryBackend``, the offline starter-catalog
stub. That backend never fetches and never runs the model; this list feeds the
live backend.

File format -- Markdown under ``brain/00_Inbox/Scout_Candidates/`` holding
exactly one fenced ``json`` block::

    {"research_id": "RQ-...", "selection_rule": "...",
     "screening_reference": "brain/00_Inbox/...", "registered_by": "...",
     "registered_on": "YYYY-MM-DD",
     "candidates": [{"url": "https://...", "found_via": "...",
                     "added_by": "...", "added_on": "YYYY-MM-DD"}]}

"Frozen" is procedural: the file's sha256 is recorded in the run's events,
raw note and any failure receipt, so an edit after registration is detectable
against the committed blob. This module does not inspect git.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

CANDIDATE_LIST_DIR = "brain/00_Inbox/Scout_Candidates"
MAX_CANDIDATES = 10
LANE = "preregistered_candidate_list"

_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class CandidateListError(ValueError):
    """A candidate list that cannot be trusted as a pre-registration."""


class _Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    url: str = Field(min_length=1)
    found_via: str = Field(min_length=1)
    added_by: str = Field(min_length=1)
    added_on: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def _absolute_http_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError(f"candidate url must be absolute http(s) with a host: {value!r}")
        return value


class _ListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    research_id: str = Field(min_length=1)
    selection_rule: str = Field(min_length=1)
    screening_reference: str = Field(min_length=1)
    registered_by: str = Field(min_length=1)
    registered_on: str = Field(min_length=1)
    candidates: list[_Entry] = Field(min_length=1, max_length=MAX_CANDIDATES)


@dataclass(frozen=True)
class CandidateList:
    path: str
    sha256: str
    research_id: str
    selection_rule: str
    entries: tuple[dict[str, str], ...]

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(entry["url"] for entry in self.entries)

    def as_provenance(self) -> dict[str, Any]:
        """Identity of the list, for events, notes and failure receipts."""
        return {
            "lane": LANE,
            "candidate_list_path": self.path,
            "candidate_list_sha256": self.sha256,
            "candidate_count": len(self.entries),
            "candidate_urls": list(self.urls),
        }


def _resolve_inside_list_dir(project_root: Path, relative_path: str | Path) -> Path:
    base = (project_root / CANDIDATE_LIST_DIR).resolve()
    candidate = Path(relative_path)
    target = (candidate if candidate.is_absolute() else project_root / candidate).resolve()
    # Resolved on both sides, so ``..`` segments and symlinks cannot point a run
    # at a list outside the registration directory.
    if not target.is_relative_to(base):
        raise CandidateListError(
            f"candidate list must live under {CANDIDATE_LIST_DIR}/: {relative_path}"
        )
    if target.suffix.lower() != ".md":
        raise CandidateListError(f"candidate list must be a .md file: {relative_path}")
    if not target.is_file():
        raise CandidateListError(f"candidate list does not exist: {relative_path}")
    return target


def load_candidate_list(project_root: str | Path, relative_path: str | Path) -> CandidateList:
    """Load and validate one pre-registered list. Every problem fails loudly."""
    from quant_brain.discovery.work_identity import upstream_work_key

    root = Path(project_root).resolve()
    target = _resolve_inside_list_dir(root, relative_path)
    raw = target.read_bytes()
    blocks = _JSON_BLOCK.findall(raw.decode("utf-8"))
    if len(blocks) != 1:
        raise CandidateListError(
            f"candidate list must contain exactly one ```json block, found {len(blocks)}"
        )
    try:
        payload = _ListPayload.model_validate(json.loads(blocks[0]))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise CandidateListError(f"invalid candidate list {relative_path}: {exc}") from exc

    # A list that names one work twice would let it inflate the source minimum
    # before a single page is fetched.
    seen: dict[str, str] = {}
    for entry in payload.candidates:
        key = upstream_work_key(entry.url)
        if key in seen:
            raise CandidateListError(
                f"candidate list names one upstream work twice: {seen[key]} and {entry.url}"
            )
        seen[key] = entry.url

    return CandidateList(
        path=target.relative_to(root).as_posix(),
        sha256=hashlib.sha256(raw).hexdigest(),
        research_id=payload.research_id,
        selection_rule=payload.selection_rule,
        entries=tuple(entry.model_dump() for entry in payload.candidates),
    )
