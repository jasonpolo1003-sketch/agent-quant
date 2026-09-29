"""Strategy cards: schema, sourced rules, and an immutable freeze (PROP-007 step 4).

Plan: brain/_system/plan/phase_08_strategy_card.md. Light by design: the
schema's refusals, a stable freeze hash, quote verification against preserved
snapshots, and the real SC-0001 card.
"""

import copy
import json
import shutil
import sqlite3

import pytest

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import init_database
from quant_brain.strategy import card as sc

REAL_CARD = PROJECT_ROOT / "brain" / "03_Strategy_Cards" / "SC-0001-rsi2-connors-spy.md"


def real_spec():
    return sc.read_card(REAL_CARD)


def test_the_real_card_satisfies_the_schema():
    card = sc.StrategyCard.model_validate(real_spec())

    assert card.card_id == "SC-0001"
    assert [rule.rule_id for rule in card.rules] == ["A", "B", "D"]
    assert [rule.role for rule in card.rules] == ["primary", "comparison", "comparison"]
    assert card.costs.basis == "assumption" and card.costs.headline_bps == 5


def test_every_quote_on_the_real_card_is_verbatim_in_its_preserved_snapshot():
    problems = sc.verify_quotes(PROJECT_ROOT, sc.StrategyCard.model_validate(real_spec()))

    assert problems == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.__setitem__("unexpected", 1),
        lambda s: s["rules"][0]["exit"].__setitem__("sources", []),
        lambda s: s["costs"].__setitem__("basis", "sourced"),
        lambda s: s["periods"]["held_out"].__setitem__("start", "2015-06-01"),
        lambda s: s["rules"][1].__setitem__("role", "primary"),
    ],
    ids=["unknown-field", "unsourced-exit", "cost-not-assumption", "overlap", "two-primaries"],
)
def test_the_schema_refuses_an_unsound_card(mutate):
    spec = real_spec()
    mutate(spec)

    with pytest.raises(ValueError):
        sc.StrategyCard.model_validate(spec)


def test_the_freeze_hash_is_stable_and_follows_the_spec():
    spec = real_spec()
    changed = copy.deepcopy(spec)
    changed["costs"]["headline_bps"] = 10

    assert sc.spec_sha256(spec) == sc.spec_sha256(copy.deepcopy(spec))
    assert sc.spec_sha256(spec) != sc.spec_sha256(changed)


def test_a_quote_missing_from_its_snapshot_is_refused():
    spec = real_spec()
    spec["rules"][0]["exit"]["sources"][0]["quote"] = "exit whenever it feels right"

    problems = sc.verify_quotes(PROJECT_ROOT, sc.StrategyCard.model_validate(spec))

    assert any("not found" in problem for problem in problems)


# --- freezing ----------------------------------------------------------------------


@pytest.fixture
def project(tmp_path):
    """A copy of just what freezing reads: the card, its snapshots and data manifests."""
    card = sc.StrategyCard.model_validate(real_spec())
    for relative in {q.snapshot for q in sc.all_quotes(card)}:
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, tmp_path / relative)
    target = tmp_path / REAL_CARD.relative_to(PROJECT_ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REAL_CARD, target)
    db = tmp_path / "brain.sqlite"
    init_database(db)
    return tmp_path, db, target


def _accept_all(monkeypatch):
    monkeypatch.setattr(sc, "verify_datasets_pinned", lambda root, db, card: [])


def test_freezing_records_the_card_once_and_in_the_db(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)

    entry = sc.freeze_card(root, db, card_path)

    assert entry["spec_sha256"] == sc.spec_sha256(sc.read_card(card_path))
    ledger = json.loads((root / sc.LEDGER_PATH).read_text(encoding="utf-8"))
    assert [e["card_id"] for e in ledger["frozen"]] == ["SC-0001"]
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT strategy_id, status, stage, timeframe FROM strategy_cards").fetchone()
    assert row == ("SC-0001", "frozen", "card", "1d")
    assert sc.verify_frozen_card(root, "SC-0001") == []

    with pytest.raises(sc.CardError, match="already frozen"):
        sc.freeze_card(root, db, card_path)


def test_a_frozen_card_edited_afterwards_fails_verification(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)
    sc.freeze_card(root, db, card_path)
    text = card_path.read_text(encoding="utf-8")
    card_path.write_text(text.replace('"headline_bps": 5', '"headline_bps": 10'), encoding="utf-8")

    problems = sc.verify_frozen_card(root, "SC-0001")

    assert any("spec" in p for p in problems) and any("file" in p for p in problems)


def test_a_card_with_an_unverifiable_quote_is_not_frozen(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)
    text = card_path.read_text(encoding="utf-8")
    card_path.write_text(text.replace("move above the 5-day SMA", "move above the 9-day SMA"),
                         encoding="utf-8")

    with pytest.raises(sc.CardError, match="not found"):
        sc.freeze_card(root, db, card_path)

    assert not (root / sc.LEDGER_PATH).exists()


def test_a_card_whose_data_is_not_accepted_is_not_frozen(project):
    root, db, card_path = project  # no market data in this temp project

    with pytest.raises(sc.CardError, match="dataset"):
        sc.freeze_card(root, db, card_path)
