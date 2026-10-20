"""Strategy cards: a sourced, frozen, hashed spec written before any result is seen.

Plan: ``brain/_system/plan/phase_08_strategy_card.md``. A card is a Markdown
note carrying one fenced JSON spec. Every rule clause must cite an exact
quotation from a preserved snapshot's fetched content. Anything not sourced
(costs, the next-open execution deviation) must say ``basis: "assumption"``.
Freezing checks the quotes and the pinned datasets, then records the spec
and file hashes in an append-only ledger (committed) and a ``strategy_cards``
row. After that, the card may not change: the backtest runner (step 5) will
refuse any card whose hashes no longer match the ledger.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CARD_DIR = "brain/03_Strategy_Cards"
LEDGER_PATH = f"{CARD_DIR}/freeze_ledger.json"

_STRICT = ConfigDict(extra="forbid")


class CardError(ValueError):
    """A card is unsound, unverifiable, or already frozen."""


class Quote(BaseModel):
    model_config = _STRICT
    quote: str = Field(min_length=1)
    snapshot: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)


class Assumption(BaseModel):
    model_config = _STRICT
    text: str = Field(min_length=1)
    basis: Literal["assumption"]
    rationale: str = Field(min_length=1)
    sources: list[Quote] = Field(default_factory=list)


class Clause(BaseModel):
    """One sourced part of a rule: the plain rule, its parameters, its sources.

    ``interpretation`` labels any reading the source does not state itself
    (SC-0001 presented "a move above the 5-day SMA" as a close-based exit).
    """

    model_config = _STRICT
    text: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    sources: list[Quote] = Field(min_length=1)
    interpretation: Assumption | None = None


class Rsi(BaseModel):
    """RSI method: quoted from a source, or an explicitly labelled assumption."""

    model_config = _STRICT
    period: int = Field(ge=2)
    method: Literal["wilder", "cutler"]
    basis: Literal["sourced", "assumption"]
    sources: list[Quote] = Field(default_factory=list)
    rationale: str | None = None

    @model_validator(mode="after")
    def _basis_is_backed(self) -> Rsi:
        if self.basis == "sourced" and not self.sources:
            raise ValueError("a sourced RSI method needs a quote")
        if self.basis == "assumption" and not (self.rationale or "").strip():
            raise ValueError("an assumed RSI method needs a rationale")
        return self


class Rule(BaseModel):
    model_config = _STRICT
    rule_id: str
    role: Literal["primary", "comparison"]
    name: str
    rsi: Rsi
    filter: Clause | None
    entry: Clause
    add: Clause | None = None
    exit: Clause
    stops: Clause | None = None


class Costs(BaseModel):
    model_config = _STRICT
    bps_per_side: list[float] = Field(min_length=1)
    headline_bps: float
    slippage_bps: float
    basis: Literal["assumption"]
    rationale: str

    @model_validator(mode="after")
    def _headline_is_tested(self) -> Costs:
        if self.headline_bps not in self.bps_per_side:
            raise ValueError("headline_bps must be one of bps_per_side")
        return self


class Period(BaseModel):
    model_config = _STRICT
    start: date
    end: date


class Periods(BaseModel):
    model_config = _STRICT
    in_sample: Period
    held_out: Period
    held_out_reads: Literal[1]

    @model_validator(mode="after")
    def _ordered(self) -> Periods:
        if not (self.in_sample.start < self.in_sample.end < self.held_out.start <= self.held_out.end):
            raise ValueError("periods must be ordered and non-overlapping, in-sample first")
        return self


class Dataset(BaseModel):
    model_config = _STRICT
    symbol: str
    dataset_id: str
    content_sha256: str = Field(min_length=64, max_length=64)


class Implementation(BaseModel):
    """Every choice two honest implementers could make differently, fixed up front."""

    model_config = _STRICT
    basis: Literal["assumption"]
    indicator_price: str
    fill_price: str
    warmup: str
    rsi_wilder: str
    rsi_cutler: str
    filter_scope: str
    entry_evaluation: str
    reentry_and_same_bar: str
    sizing: str
    cash_return: str
    period_boundary: str
    cost_application: str
    sma: str
    trade_return: str
    daily_returns: str
    edge_cases: str


class Criterion(BaseModel):
    model_config = _STRICT
    name: str
    metric: str
    comparator: Literal[">", ">="]
    threshold: float
    detail: str


class Verdict(BaseModel):
    """Pre-declared pass test: one rule, one period, one cost level."""

    model_config = _STRICT
    applies_to: str
    period: Literal["held_out"]
    cost_bps: float
    criteria: list[Criterion] = Field(min_length=1)
    if_all_pass: str
    otherwise: str
    other_rules: str


class StrategyCard(BaseModel):
    model_config = _STRICT
    card_id: str
    supersedes: str | None = None
    title: str
    hypothesis: str
    method_family: str
    timeframe: Literal["1d"]
    direction: Literal["long_only"]
    universe: dict[Literal["primary", "robustness"], list[str]]
    data: list[Dataset] = Field(min_length=1)
    price_basis: dict[str, str]
    execution: Assumption
    max_holding: dict[str, Any]
    rules: list[Rule] = Field(min_length=1)
    costs: Costs
    periods: Periods
    benchmarks: dict[str, Any]
    multiple_testing: dict[str, Any]
    implementation: Implementation
    verdict: Verdict

    @model_validator(mode="after")
    def _one_primary_and_pinned_data(self) -> StrategyCard:
        if [rule.role for rule in self.rules].count("primary") != 1:
            raise ValueError("a card has exactly one primary rule")
        primary = next(rule.rule_id for rule in self.rules if rule.role == "primary")
        if self.verdict.applies_to != primary:
            raise ValueError("the verdict applies to the primary rule only")
        if self.verdict.cost_bps not in self.costs.bps_per_side:
            raise ValueError("the verdict's cost level must be one the card tests")
        pinned = {dataset.symbol for dataset in self.data}
        wanted = set(self.universe.get("primary", [])) | set(self.universe.get("robustness", []))
        if wanted - pinned:
            raise ValueError(f"no pinned dataset for {sorted(wanted - pinned)}")
        return self


def read_card(path: str | Path) -> dict[str, Any]:
    """The card's JSON spec (its single fenced ``json`` block)."""
    text = Path(path).read_text(encoding="utf-8")
    blocks = text.split("```json")
    if len(blocks) != 2:
        raise CardError(f"{path}: a card has exactly one ```json block")
    return json.loads(blocks[1].split("```", 1)[0])


def spec_sha256(spec: dict[str, Any]) -> str:
    """sha256 of the spec in canonical JSON (sorted keys, no whitespace)."""
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def all_quotes(card: StrategyCard) -> list[Quote]:
    quotes = list(card.execution.sources)
    for rule in card.rules:
        quotes += rule.rsi.sources
        for clause in (rule.filter, rule.entry, rule.add, rule.exit, rule.stops):
            if clause is not None:
                quotes += clause.sources
                if clause.interpretation is not None:
                    quotes += clause.interpretation.sources
    return quotes


def verify_quotes(project_root: str | Path, card: StrategyCard) -> list[str]:
    """Every quote must be verbatim in its snapshot's fetched content, at its hash."""
    from quant_brain.discovery.live_discovery import snapshot_content

    root = Path(project_root)
    problems = []
    for quote in all_quotes(card):
        path = root / quote.snapshot
        if not path.is_file():
            problems.append(f"{quote.snapshot}: snapshot missing")
            continue
        content = snapshot_content(path.read_text(encoding="utf-8"))
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != quote.content_sha256:
            problems.append(f"{quote.snapshot}: content sha256 differs from the card")
        if quote.quote not in content:
            problems.append(f"{quote.snapshot}: quote not found: {quote.quote[:60]!r}")
    return problems


def verify_datasets_pinned(project_root: str | Path, db_path: str | Path, card: StrategyCard) -> list[str]:
    """Each pinned dataset must be accepted and match its pinned content hash."""
    from quant_brain.data.market_data import verify_datasets

    reports = {r.dataset_id: r for r in verify_datasets(project_root, db_path)}
    problems = []
    for dataset in card.data:
        report = reports.get(dataset.dataset_id)
        if report is None or report.state != "accepted":
            problems.append(f"dataset {dataset.dataset_id} is not accepted "
                            f"({report.state if report else 'missing'})")
            continue
        manifest = json.loads((Path(project_root) / "data/manifests" /
                               f"{dataset.dataset_id}.json").read_text(encoding="utf-8"))
        if manifest["content_sha256"] != dataset.content_sha256:
            problems.append(f"dataset {dataset.dataset_id}: content sha256 differs from the card")
    return problems


def _ledger(root: Path) -> dict[str, Any]:
    path = root / LEDGER_PATH
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"frozen": []}
    ledger.setdefault("superseded", [])
    return ledger


def freeze_card(project_root: str | Path, db_path: str | Path, card_path: str | Path) -> dict[str, Any]:
    """Validate, verify quotes and data, then record the freeze. Never re-freezes."""
    root = Path(project_root)
    path = Path(card_path)
    spec = read_card(path)
    try:
        card = StrategyCard.model_validate(spec)
    except ValueError as exc:
        raise CardError(f"{path.name}: schema: {exc}") from exc
    ledger = _ledger(root)
    if any(entry["card_id"] == card.card_id for entry in ledger["frozen"]):
        raise CardError(f"{card.card_id} is already frozen; a changed idea is a new card")
    if card.supersedes is not None:
        if not any(e["card_id"] == card.supersedes for e in ledger["frozen"]):
            raise CardError(f"{card.card_id} supersedes {card.supersedes}, which is not frozen")
        if any(e["card_id"] == card.supersedes for e in ledger["superseded"]):
            raise CardError(f"{card.supersedes} is already superseded")
    problems = verify_quotes(root, card) + verify_datasets_pinned(root, db_path, card)
    if problems:
        raise CardError(f"{card.card_id} not frozen: " + "; ".join(problems))

    entry = {
        "card_id": card.card_id,
        "card_path": path.resolve().relative_to(root.resolve()).as_posix(),
        "spec_sha256": spec_sha256(spec),
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "frozen_at": datetime.now(UTC).isoformat(),
    }
    ledger["frozen"].append(entry)
    if card.supersedes is not None:
        ledger["superseded"].append({
            "card_id": card.supersedes, "superseded_by": card.card_id,
            "reason": "superseded before any backtest; see the successor card",
            "at": entry["frozen_at"],
        })
    ledger_path = root / LEDGER_PATH
    temporary = ledger_path.with_name(ledger_path.name + ".tmp")
    temporary.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    temporary.replace(ledger_path)  # the ledger itself is append-only by content
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO strategy_cards (strategy_id, title, method_family, status, stage, "
            "confidence, note_path, hypothesis, markets_json, timeframe, source_ids_json) "
            "VALUES (?, ?, ?, 'frozen', 'card', 'low', ?, ?, ?, ?, ?)",
            (
                card.card_id, card.title, card.method_family, entry["card_path"], card.hypothesis,
                json.dumps(card.universe), card.timeframe,
                json.dumps(sorted({q.snapshot for q in all_quotes(card)})),
            ),
        )
        if card.supersedes is not None:
            conn.execute(
                "UPDATE strategy_cards SET status = 'superseded', updated_at = CURRENT_TIMESTAMP "
                "WHERE strategy_id = ?",
                (card.supersedes,),
            )
    return entry


def verify_frozen_card(project_root: str | Path, card_id: str) -> list[str]:
    """Problems if the card is not frozen or has changed since. Read-only."""
    root = Path(project_root)
    ledger = _ledger(root)
    entries = [e for e in ledger["frozen"] if e["card_id"] == card_id]
    if not entries:
        return [f"{card_id} is not frozen"]
    retired = [e for e in ledger["superseded"] if e["card_id"] == card_id]
    if retired:
        return [f"{card_id} is superseded by {retired[0]['superseded_by']}; it must not be run"]
    entry = entries[0]
    path = root / entry["card_path"]
    if not path.is_file():
        return [f"{entry['card_path']} is missing"]
    problems = []
    if spec_sha256(read_card(path)) != entry["spec_sha256"]:
        problems.append(f"{card_id}: spec sha256 differs from the freeze ledger")
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["file_sha256"]:
        problems.append(f"{card_id}: file sha256 differs from the freeze ledger")
    return problems
