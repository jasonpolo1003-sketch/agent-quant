"""Strategy cards: schema, sourced rules, and an immutable freeze (PROP-007 step 4).

Plan: brain/_system/plan/phase_08_strategy_card.md. Light by design: the
schema's refusals, a stable freeze hash, quote verification against preserved
snapshots, supersession, and the real SC-0002 card. SC-0001 was frozen before
review and is retired by SC-0002; it is kept for the record, not validated
against the tightened schema.
"""

import copy
import json
import shutil
import sqlite3

import pytest

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import init_database
from quant_brain.strategy import card as sc

CARDS = PROJECT_ROOT / "brain" / "03_Strategy_Cards"
REAL_CARD = CARDS / "SC-0002-rsi2-connors-spy.md"


def real_spec():
    return sc.read_card(REAL_CARD)


def test_the_real_card_satisfies_the_schema():
    card = sc.StrategyCard.model_validate(real_spec())

    assert card.card_id == "SC-0002" and card.supersedes == "SC-0001"
    assert [rule.rule_id for rule in card.rules] == ["A", "B", "D"]
    assert [rule.rsi.basis for rule in card.rules] == ["assumption", "assumption", "sourced"]
    assert card.rules[0].exit.interpretation.basis == "assumption"
    assert card.verdict.applies_to == "A" and card.verdict.cost_bps == 5
    assert card.multiple_testing["trials_counted"] == 3


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
        lambda s: s["rules"][0]["rsi"].__setitem__("basis", "sourced"),  # no quote behind it
        lambda s: s["rules"][0]["rsi"].__setitem__("rationale", ""),  # assumption, unexplained
        lambda s: s["verdict"].__setitem__("applies_to", "B"),
        lambda s: s["verdict"].__setitem__("cost_bps", 7),
        lambda s: s["implementation"].pop("reentry_and_same_bar"),
    ],
    ids=["unknown-field", "unsourced-exit", "cost-not-assumption", "overlap", "two-primaries",
         "rsi-sourced-without-quote", "rsi-assumed-without-reason", "verdict-not-primary",
         "verdict-untested-cost", "implementation-gap"],
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


# --- freezing and supersession -----------------------------------------------------


@pytest.fixture
def project(tmp_path):
    """What freezing reads: the cards, their snapshots, the ledger holding SC-0001."""
    card = sc.StrategyCard.model_validate(real_spec())
    for relative in {q.snapshot for q in sc.all_quotes(card)}:
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, tmp_path / relative)
    target_dir = tmp_path / CARDS.relative_to(PROJECT_ROOT)
    target_dir.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((CARDS / "freeze_ledger.json").read_text(encoding="utf-8"))
    ledger["frozen"] = [e for e in ledger["frozen"] if e["card_id"] == "SC-0001"]
    ledger.pop("superseded", None)
    (target_dir / "freeze_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    shutil.copyfile(CARDS / "SC-0001-rsi2-connors-spy.md", target_dir / "SC-0001-rsi2-connors-spy.md")
    target = target_dir / REAL_CARD.name
    shutil.copyfile(REAL_CARD, target)
    db = tmp_path / "brain.sqlite"
    init_database(db)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO strategy_cards (strategy_id, title, method_family, status, stage, "
                     "note_path) VALUES ('SC-0001', 't', 'mean_reversion', 'frozen', 'card', 'p')")
    return tmp_path, db, target


def _accept_all(monkeypatch):
    monkeypatch.setattr(sc, "verify_datasets_pinned", lambda root, db, card: [])


def test_freezing_a_successor_records_it_and_retires_its_predecessor(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)
    assert sc.verify_frozen_card(root, "SC-0001") == []

    entry = sc.freeze_card(root, db, card_path)

    assert entry["spec_sha256"] == sc.spec_sha256(sc.read_card(card_path))
    ledger = json.loads((root / sc.LEDGER_PATH).read_text(encoding="utf-8"))
    assert [e["card_id"] for e in ledger["frozen"]] == ["SC-0001", "SC-0002"]
    assert [(e["card_id"], e["superseded_by"]) for e in ledger["superseded"]] == [
        ("SC-0001", "SC-0002")
    ]
    with sqlite3.connect(db) as conn:
        rows = dict(conn.execute("SELECT strategy_id, status FROM strategy_cards").fetchall())
    assert rows == {"SC-0001": "superseded", "SC-0002": "frozen"}
    assert sc.verify_frozen_card(root, "SC-0002") == []
    assert any("superseded" in p for p in sc.verify_frozen_card(root, "SC-0001"))

    with pytest.raises(sc.CardError, match="already frozen"):
        sc.freeze_card(root, db, card_path)


def test_a_card_cannot_supersede_one_that_was_never_frozen(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)
    text = card_path.read_text(encoding="utf-8")
    card_path.write_text(text.replace('"supersedes": "SC-0001"', '"supersedes": "SC-0999"'),
                         encoding="utf-8")

    with pytest.raises(sc.CardError, match="not frozen"):
        sc.freeze_card(root, db, card_path)


def test_a_frozen_card_edited_afterwards_fails_verification(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)
    sc.freeze_card(root, db, card_path)
    text = card_path.read_text(encoding="utf-8")
    card_path.write_text(text.replace('"headline_bps": 5', '"headline_bps": 10'), encoding="utf-8")

    problems = sc.verify_frozen_card(root, "SC-0002")

    assert any("spec" in p for p in problems) and any("file" in p for p in problems)


def test_a_card_with_an_unverifiable_quote_is_not_frozen(project, monkeypatch):
    root, db, card_path = project
    _accept_all(monkeypatch)
    before = (root / sc.LEDGER_PATH).read_bytes()
    text = card_path.read_text(encoding="utf-8")
    quote = "exiting long positions on a move above the 5-day SMA"
    edited = text.replace(quote, quote.replace("5-day", "9-day"))
    assert edited != text  # the tamper must actually happen
    card_path.write_text(edited, encoding="utf-8")

    with pytest.raises(sc.CardError, match="not found"):
        sc.freeze_card(root, db, card_path)

    assert (root / sc.LEDGER_PATH).read_bytes() == before


def test_a_card_whose_data_is_not_accepted_is_not_frozen(project):
    root, db, card_path = project  # no market data in this temp project

    with pytest.raises(sc.CardError, match="dataset"):
        sc.freeze_card(root, db, card_path)
