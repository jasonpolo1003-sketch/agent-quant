"""Gate F: local daily price data with provenance (brain/_system/plan/gate_f_market_data.md).

Hermetic: a small committed fixture stands in for Yahoo, and no test touches
the network. The fixture has 30 trading days, the Good Friday gap, one dividend
and one 2:1 split.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from quant_brain.data import market_data as md
from quant_brain.db.init_db import init_database

FIXTURE = Path(__file__).parent / "fixtures" / "market" / "spy_sample.csv"
NOW = datetime(2026, 9, 28, 12, 0, 0, tzinfo=UTC)
META = {"provider": "yfinance", "provider_version": "test", "requested_start": "2024-03-01",
        "requested_end": "2024-04-12"}


def bars():
    return md.normalize_bars(pd.read_csv(FIXTURE))


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "brain.sqlite"
    init_database(db)
    return tmp_path, db


def ingest(env, frame=None, **kwargs):
    root, db = env
    return md.ingest(root, db, "SPY", bars() if frame is None else frame, meta=META,
                     now=kwargs.pop("now", NOW), **kwargs)


def states(env):
    root, db = env
    return {report.dataset_id: report.state for report in md.verify_datasets(root, db)}


# --- validation --------------------------------------------------------------------


def test_the_fixture_is_clean_and_its_holiday_gap_is_not_a_warning():
    problems, warnings = md.validate_bars(bars())

    assert problems == [] and warnings == []


def _broken(mutate):
    frame = bars()
    mutate(frame)
    return md.validate_bars(frame)[0]


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("duplicate", lambda f: f.loc.__setitem__((5, "date"), f.loc[4, "date"])),
        ("unsorted", lambda f: f.loc.__setitem__((5, "date"), "2024-02-01")),
        ("missing", lambda f: f.loc.__setitem__((7, "close"), float("nan"))),
        ("non-positive", lambda f: f.loc.__setitem__((8, "low"), 0.0)),
        ("high", lambda f: f.loc.__setitem__((9, "high"), f.loc[9, "close"] - 1)),
        ("low", lambda f: f.loc.__setitem__((10, "low"), f.loc[10, "open"] + 1)),
        ("volume", lambda f: f.loc.__setitem__((11, "volume"), -1)),
        ("factor", lambda f: f.loc.__setitem__((12, "adj_close"), f.loc[12, "close"] * 1.01)),
    ],
)
def test_each_impossible_bar_is_a_problem(label, mutate):
    problems = _broken(mutate)

    assert problems and any(label in problem for problem in problems), problems


def test_suspicious_but_possible_bars_are_warnings():
    frame = bars()
    frame.loc[15, "volume"] = 0
    frame.loc[16, ["open", "high", "low", "close", "adj_close"]] *= 1.4

    problems, warnings = md.validate_bars(frame)

    assert problems == []
    assert any("zero volume" in w for w in warnings) and any("move" in w for w in warnings)


def test_invalid_bars_are_refused_before_anything_is_written(env):
    root, _db = env
    frame = bars()
    frame.loc[3, "high"] = 1.0

    with pytest.raises(md.MarketDataError, match="high"):
        ingest(env, frame)

    assert not (root / "data").exists()
    assert states(env) == {}


# --- saving, identity and loading --------------------------------------------------


def test_an_ingested_dataset_is_accepted_and_loads_verified(env):
    root, db = env
    manifest = ingest(env)

    assert states(env) == {manifest["dataset_id"]: "accepted"}
    assert manifest["price_basis"] == md.PRICE_BASIS == "yahoo_split_adjusted"
    assert manifest["rows"] == 30 and manifest["first_date"] == "2024-03-01"
    loaded = md.load_dataset(root, db, manifest["dataset_id"])
    factor = loaded["adj_close"] / loaded["close"]
    assert (loaded["adj_open"] - loaded["open"] * factor).abs().max() < 1e-9
    assert loaded["dividends"].sum() == 1.75 and loaded["stock_splits"].max() == 2.0
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT symbol, source, timeframe, adjusted, checksum, path "
                           "FROM price_datasets").fetchone()
    assert row == ("SPY", "yfinance", "1d", 0, manifest["content_sha256"], manifest["path"])


def test_identical_data_downloaded_twice_in_the_same_second_gets_two_datasets(env):
    root, _ = env
    first = ingest(env)
    before = (root / first["path"]).read_bytes()

    second = ingest(env)

    assert first["dataset_id"] != second["dataset_id"]
    assert first["dataset_id"].startswith("SPY-1d-yfinance-20260928T120000Z-")
    assert first["content_sha256"] == second["content_sha256"]  # compare by hash, not ID
    assert (root / first["path"]).read_bytes() == before
    assert set(states(env).values()) == {"accepted"}


def test_the_content_hash_follows_values_not_object_identity():
    frame = bars()
    changed = frame.copy()
    changed.loc[0, "close"] += 0.01

    assert md.canonical_content_hash(frame) == md.canonical_content_hash(frame.copy())
    assert md.canonical_content_hash(frame) != md.canonical_content_hash(changed)


# --- partial failure ---------------------------------------------------------------


def test_an_interrupted_parquet_write_leaves_an_incomplete_unloadable_file(env, monkeypatch):
    root, db = env
    monkeypatch.setattr(md, "_finalise_parquet", _boom)

    with pytest.raises(RuntimeError, match="interrupted"):
        ingest(env)

    [report] = md.verify_datasets(root, db)
    assert report.state == "incomplete" and report.path.endswith(".parquet.partial")
    _assert_not_loadable(env, report.dataset_id)


def test_an_interrupted_manifest_write_leaves_no_db_row(env, monkeypatch):
    root, db = env
    monkeypatch.setattr(md, "_write_manifest", _boom)

    with pytest.raises(RuntimeError, match="interrupted"):
        ingest(env)

    [report] = md.verify_datasets(root, db)
    assert report.state == "incomplete"  # a .parquet with no manifest
    assert _db_rows(db) == 0
    _assert_not_loadable(env, report.dataset_id)


def test_an_interrupted_registration_leaves_an_unregistered_unloadable_dataset(env, monkeypatch):
    root, db = env
    monkeypatch.setattr(md, "register_dataset", _boom)

    with pytest.raises(RuntimeError, match="interrupted"):
        ingest(env)

    [report] = md.verify_datasets(root, db)
    assert report.state == "unregistered"
    _assert_not_loadable(env, report.dataset_id)


def test_a_failed_cross_check_is_recorded_not_fatal(env):
    def unavailable(symbol, start, end):
        raise ConnectionError("stooq down")

    manifest = ingest(env, cross_check_fetcher=unavailable)

    assert manifest["cross_check"]["status"] == "unavailable"
    assert "stooq down" in manifest["cross_check"]["reason"]
    assert states(env) == {manifest["dataset_id"]: "accepted"}


def test_a_cross_check_reports_agreement_with_the_second_source(env):
    frame = bars()

    def stooq(symbol, start, end):
        return pd.Series(frame["adj_close"].to_numpy(), index=pd.to_datetime(frame["date"]))

    manifest = ingest(env, cross_check_fetcher=stooq)

    check = manifest["cross_check"]
    assert check["status"] == "compared" and check["overlap_days"] == 29
    assert check["return_correlation"] > 0.999 and check["max_abs_return_diff"] < 1e-9


# --- the verifier: tampering and disagreement --------------------------------------


def test_a_changed_parquet_file_is_invalid(env):
    root, _db = env
    manifest = ingest(env)
    path = root / manifest["path"]
    frame = pd.read_parquet(path)
    frame.loc[0, "close"] += 1
    path.unlink()
    frame.to_parquet(path)

    assert states(env)[manifest["dataset_id"]] == "invalid"
    _assert_not_loadable(env, manifest["dataset_id"])


def test_a_db_row_without_its_manifest_is_invalid(env):
    root, _db = env
    manifest = ingest(env)
    (root / md.MANIFEST_DIR / f"{manifest['dataset_id']}.json").unlink()

    assert states(env)[manifest["dataset_id"]] == "invalid"


def test_a_db_row_that_disagrees_with_its_manifest_is_invalid(env):
    _root, db = env
    manifest = ingest(env)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE price_datasets SET end_date = '2030-01-01'")

    assert states(env)[manifest["dataset_id"]] == "invalid"
    _assert_not_loadable(env, manifest["dataset_id"])


def test_the_verifier_never_writes(env):
    root, db = env
    ingest(env)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    md.verify_datasets(root, db)

    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


# --- the live fetcher's shape, without the network ---------------------------------


def test_a_yfinance_shaped_frame_normalises_to_trading_dates():
    raw = pd.read_csv(FIXTURE)
    index = pd.DatetimeIndex(pd.to_datetime(raw.pop("Date"))).tz_localize("America/New_York")
    yahoo = raw.set_index(index)
    yahoo.index.name = "Date"

    frame = md.normalize_bars(yahoo)

    assert list(frame.columns) == list(md.COLUMNS)
    assert frame["date"].iloc[0] == "2024-03-01"
    assert md.canonical_content_hash(frame) == md.canonical_content_hash(bars())


def test_the_manifest_names_the_price_basis_honestly(env):
    manifest = ingest(env)

    assert "not the as-traded" in manifest["price_basis_note"]
    assert "split-adjusted" in manifest["price_basis_note"]
    assert "dividend" in manifest["adjustment_note"]


def _boom(*_args, **_kwargs):
    raise RuntimeError("interrupted")


def _db_rows(db):
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM price_datasets").fetchone()[0]


def _assert_not_loadable(env, dataset_id):
    root, db = env
    with pytest.raises(md.MarketDataError):
        md.load_dataset(root, db, dataset_id)


def test_an_existing_dataset_id_is_refused_not_overwritten(env):
    root, _db = env
    first = ingest(env, run_id="abcd1234")
    before = (root / first["path"]).read_bytes()

    with pytest.raises(md.MarketDataError, match="never overwritten"):
        ingest(env, run_id="abcd1234")

    assert (root / first["path"]).read_bytes() == before
    assert states(env) == {first["dataset_id"]: "accepted"}
    assert not list((root / md.PARQUET_DIR).rglob("*.partial"))  # a refusal leaves no debris


def test_a_file_changed_after_its_manifest_is_never_registered(env, monkeypatch):
    _root, db = env
    real = md._write_manifest

    def write_then_tamper(project_root, manifest):
        real(project_root, manifest)
        path = project_root / manifest["path"]
        frame = pd.read_parquet(path)
        frame.loc[0, "close"] += 1
        path.unlink()
        frame.to_parquet(path, index=False)

    monkeypatch.setattr(md, "_write_manifest", write_then_tamper)

    with pytest.raises(md.MarketDataError, match="not registered"):
        ingest(env)

    assert _db_rows(db) == 0
    assert set(states(env).values()) == {"invalid"}


def test_same_values_in_different_file_bytes_are_invalid(env):
    """The file hash pins the exact file; the content hash alone would not notice."""
    root, _db = env
    manifest = ingest(env)
    path = root / manifest["path"]
    frame = pd.read_parquet(path)
    path.unlink()
    frame.to_parquet(path, index=False, compression="gzip")
    assert md.canonical_content_hash(pd.read_parquet(path)) == manifest["content_sha256"]

    assert states(env)[manifest["dataset_id"]] == "invalid"


# --- review follow-ups ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("dividends", lambda f: f.loc.__setitem__((6, "dividends"), float("nan"))),
        ("dividends", lambda f: f.loc.__setitem__((6, "dividends"), -0.5)),
        ("stock_splits", lambda f: f.loc.__setitem__((6, "stock_splits"), -1.0)),
        ("weekend", lambda f: f.loc.__setitem__((0, "date"), "2024-02-24")),  # a Saturday
    ],
)
def test_corporate_actions_and_weekend_dates_are_validated(label, mutate):
    problems = _broken(mutate)

    assert any(label in problem for problem in problems), problems


def test_a_bar_for_the_download_day_or_later_is_refused(env):
    """The day's bar may still be forming; only completed sessions are stored."""
    frame = bars()
    same_day = datetime(2024, 4, 12, 18, 0, tzinfo=UTC)  # 14:00 in New York
    assert frame["date"].iloc[-1] == "2024-04-12"

    with pytest.raises(md.MarketDataError, match="incomplete"):
        ingest(env, frame, now=same_day)

    assert states(env) == {}


def test_a_corrupt_manifest_is_reported_invalid_not_a_crash(env):
    root, _db = env
    manifest = ingest(env)
    (root / md.MANIFEST_DIR / f"{manifest['dataset_id']}.json").write_text("{not json", "utf-8")

    assert states(env) == {manifest["dataset_id"]: "invalid"}


def test_the_manifest_says_volume_is_split_adjusted_too(env):
    assert "volume" in ingest(env)["price_basis_note"]
