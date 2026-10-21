"""Chart workspace backend: bars, indicators, formulas, stats, replays, drawings.

Hermetic: two small datasets ingested from the committed Gate F fixture, no network.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from quant_brain.backtest import indicators as engine_ind
from quant_brain.data import market_data as md
from quant_brain.db.init_db import init_database
from quant_brain.ui import chartdata
from quant_brain.ui.app import TerminalConfig, create_app

FIXTURE = Path(__file__).parent / "fixtures" / "market" / "spy_sample.csv"
BASE = "http://127.0.0.1:8765"
HDR = {"X-Brain-Terminal": "1"}
META = {"provider": "yfinance", "provider_version": "t", "requested_start": "2024-03-01",
        "requested_end": "2024-04-12"}


def bars(scale: float = 1.0) -> pd.DataFrame:
    frame = md.normalize_bars(pd.read_csv(FIXTURE))
    for col in ("open", "high", "low", "close", "adj_close"):
        frame[col] = frame[col] * scale
    return frame


@pytest.fixture
def root(tmp_path):
    db = tmp_path / "db" / "brain.sqlite"
    init_database(db)
    now = datetime(2026, 9, 28, 12, tzinfo=UTC)
    md.ingest(tmp_path, db, "SPY", bars(), meta=META, now=now)
    md.ingest(tmp_path, db, "TLT", bars(0.2), meta=META, now=now)
    (tmp_path / "data" / "universe").mkdir(parents=True)
    (tmp_path / "data" / "universe" / "starter.json").write_text(json.dumps({
        "name": "starter", "survivorship_note": "learn, not prove",
        "symbols": [{"symbol": "SPY", "name": "S&P 500 ETF", "group": "Benchmarks"},
                    {"symbol": "TLT", "name": "Long bonds", "group": "Bonds"},
                    {"symbol": "ZZZ", "name": "Missing", "group": "Other"}]}), encoding="utf-8")
    reports = tmp_path / "brain" / "04_Backtest_Reports"
    reports.mkdir(parents=True)
    (reports / "SC-9-held-out-A-SPY-5bps.replay.json").write_text(json.dumps({
        "card_id": "SC-9", "phase": "held_out", "symbol": "SPY", "rule_id": "A",
        "cost_bps_per_side": 5.0, "period": ["2024-03-01", "2024-04-12"],
        "reference_check": "match (1 trades)", "indicators": {"rsi": "RSI(2)"},
        "bars": [{"date": "2024-03-01", "open": 1, "high": 1, "low": 1, "close": 1, "rsi": 5}],
        "trades": [{"number": 1, "signal_date": "2024-03-01", "entry_date": "2024-03-04"}]}),
        encoding="utf-8")
    return tmp_path, db


@pytest.fixture
def svc(root):
    return chartdata.ChartData(*root)


@pytest.fixture
def client(root, tmp_path):
    r, db = root
    cfg = TerminalConfig(project_root=r, brain_db=db, terminal_db=r / "db" / "terminal.sqlite",
                         claude_home=tmp_path / "c", codex_home=tmp_path / "x",
                         scheduler_enabled=False)
    return TestClient(create_app(cfg), base_url=BASE)


def test_catalog_is_cached_until_datasets_change(svc, root, monkeypatch):
    calls = []
    real = chartdata.uni.latest_accepted
    monkeypatch.setattr(chartdata.uni, "latest_accepted", lambda *a: calls.append(1) or real(*a))
    assert set(svc.catalog()) == {"SPY", "TLT"}
    svc.catalog()
    assert len(calls) == 1
    md.ingest(root[0], root[1], "IEF", bars(0.3), meta=META, now=datetime(2026, 9, 29, tzinfo=UTC))
    assert "IEF" in svc.catalog() and len(calls) == 2


def test_bars_daily_weekly_monthly_and_basis(svc):
    d = svc.bars("spy", "D", "split")
    assert d["symbol"] == "SPY" and len(d["bars"]) == 30
    assert d["provenance"]["freshness"] == "END OF DAY"
    w = svc.bars("SPY", "W", "split")["bars"]
    m = svc.bars("SPY", "M", "split")["bars"]
    assert len(w) < 30 and len(m) == 2
    daily = pd.DataFrame(d["bars"])
    march = daily[daily["time"] < "2024-04-01"]
    assert m[0]["time"] == march["time"].iloc[-1]
    assert m[0]["high"] == march["high"].max() and m[0]["open"] == march["open"].iloc[0]
    total = svc.bars("SPY", "D", "total")["bars"]
    assert total[0]["close"] != d["bars"][0]["close"]  # dividends make the adjusted basis differ
    with pytest.raises(chartdata.ChartError):
        svc.bars("SPY", "H")
    with pytest.raises(chartdata.ChartError):
        svc.bars("NOPE")


def test_sma_and_rsi_are_the_engines_own_values(svc):
    res = svc.indicators("SPY", "D", "total", [{"kind": "rsi", "params": {"n": 2}},
                                               {"kind": "sma", "params": {"n": 5}}])
    close = svc.frame("SPY", "D", "total")["close"].astype(float)
    want_rsi = engine_ind.rsi_wilder(close, 2).dropna().round(6).tolist()
    want_sma = engine_ind.sma(close, 5).dropna().round(6).tolist()
    assert [p["value"] for p in res[0]["lines"]["rsi"]] == want_rsi
    assert [p["value"] for p in res[1]["lines"]["sma"]] == want_sma
    assert res[0]["engine_parity"] and res[0]["pane"] == "own" and res[0]["levels"] == [30, 70]


def test_display_indicators_and_param_validation(svc):
    res = svc.indicators("SPY", "D", "split", [{"kind": "bb", "params": {"n": 5, "k": 2}},
                                               {"kind": "macd", "params": {"fast": 3, "slow": 6,
                                                                           "signal": 3}},
                                               {"kind": "atr", "params": {"n": 5}},
                                               {"kind": "ema", "params": {"n": 5}}])
    bb = res[0]["lines"]
    assert set(bb) == {"upper", "middle", "lower"}
    assert all(u["value"] >= low["value"] for u, low in zip(bb["upper"], bb["lower"], strict=True))
    assert set(res[1]["lines"]) == {"macd", "signal", "histogram"}
    assert all(p["value"] > 0 for p in res[2]["lines"]["atr"])
    for bad in ({"kind": "rsi", "params": {"n": 0}}, {"kind": "rsi", "params": {"x": 1}},
                {"kind": "macd", "params": {"fast": 9, "slow": 5}}, {"kind": "eval"}):
        with pytest.raises(chartdata.ChartError):
            svc.indicators("SPY", "D", "split", [bad])


@pytest.mark.parametrize(("text", "known", "tree"), [
    ("SPY/TLT", {"SPY", "TLT"}, ("/", ("sym", "SPY"), ("sym", "TLT"))),
    ("SPY-V", {"SPY", "V"}, ("-", ("sym", "SPY"), ("sym", "V"))),
    ("BRK-B/SPY", {"SPY", "BRK-B"}, ("/", ("sym", "BRK-B"), ("sym", "SPY"))),
    ("-(SPY+2)*3", {"SPY"}, ("*", ("neg", ("+", ("sym", "SPY"), ("num", 2.0))), ("num", 3.0))),
])
def test_formula_parser(text, known, tree):
    assert chartdata.parse_formula(text, known)[0] == tree


@pytest.mark.parametrize("bad", ["", "SPY/", "(SPY", "SPY TLT", "__import__('os')", "2+3",
                                 "SPY;DROP", "A+B+C+D+E+F+G", "x" * 200])
def test_formula_parser_rejects(bad):
    with pytest.raises(chartdata.ChartError):
        chartdata.parse_formula(bad, {"SPY", "TLT"})


def test_formula_values_and_unknown_symbols(svc):
    f = svc.formula("SPY/TLT")
    assert all(abs(p["value"] - 5.0) < 1e-6 for p in f["points"])  # TLT fixture is SPY * 0.2
    assert len(f["provenance"]) == 2
    with pytest.raises(chartdata.ChartError):
        svc.formula("SPY/QQQ")


def test_compare_rebases_to_100(svc):
    c = svc.compare(["SPY", "TLT"], None)
    assert [s["symbol"] for s in c["series"]] == ["SPY", "TLT"]
    assert all(s["points"][0]["value"] == 100 for s in c["series"])
    assert c["series"][0]["change_pct"] == pytest.approx(c["series"][1]["change_pct"])


def test_selection_stats(svc):
    frame = svc.frame("SPY", "D", "total")
    a, b = frame["time"].iloc[2], frame["time"].iloc[20]
    s = svc.stats("SPY", b, a)  # reversed on purpose
    sel = s["selection"]
    assert (sel["from"], sel["to"], sel["days"]) == (a, b, 18)
    expect = (frame["close"].iloc[20] / frame["close"].iloc[2] - 1) * 100
    assert sel["return_pct"] == pytest.approx(expect, abs=1e-5)
    assert sel["max_drawdown_pct"] <= 0 and s["benchmark"] is None  # SPY is its own benchmark
    t = svc.stats("TLT", a, b)
    assert t["benchmark"]["symbol"] == "SPY"
    with pytest.raises(chartdata.ChartError):
        svc.stats("SPY", a, a)


def test_watchlist_marks_missing_symbols(svc):
    w = svc.watchlist()
    rows = {r["symbol"]: r for r in w["symbols"]}
    assert rows["SPY"]["available"] and rows["SPY"]["last"] is not None
    assert rows["ZZZ"]["available"] is False
    assert w["note"] == "learn, not prove"


def test_replays_list_and_get(root):
    r, _ = root
    lst = chartdata.list_replays(r)
    assert lst[0]["id"] == "SC-9-held-out-A-SPY-5bps" and lst[0]["trades"] == 1
    assert chartdata.get_replay(r, lst[0]["id"])["card_id"] == "SC-9"
    for bad in ("../secrets", "x/y", "nope"):
        with pytest.raises(chartdata.ChartError):
            chartdata.get_replay(r, bad)


def test_chart_endpoints(client):
    assert client.get("/api/chart/bars?symbol=SPY&tf=W").status_code == 200
    assert client.get("/api/chart/bars?symbol=NOPE").status_code == 422
    cat = client.get("/api/chart/indicator-catalog").json()
    assert cat["rsi"]["engine"] is True and cat["macd"]["engine"] is False
    ind = client.post("/api/chart/indicators", headers=HDR,
                      json={"symbol": "SPY", "specs": [{"id": "a", "kind": "rsi"}]}).json()
    assert ind[0]["id"] == "a"
    assert client.get("/api/chart/formula?f=SPY/TLT").json()["formula"] == "SPY/TLT"
    assert client.get("/api/chart/formula?f=import os").status_code == 422
    assert len(client.get("/api/chart/compare?symbols=SPY,TLT").json()["series"]) == 2
    assert client.get("/api/chart/stats?symbol=SPY&start=2024-03-01&end=2024-04-01").status_code == 200
    assert client.get("/api/replays").json()[0]["card_id"] == "SC-9"
    assert client.get("/api/replays/..%2Fx").status_code == 404
    assert client.get("/api/chart/watchlist").json()["symbols"][0]["symbol"] == "SPY"


def test_drawings_round_trip(client):
    r = client.post("/api/drawings", headers=HDR, json={"symbol": "spy", "kind": "hline", "price": 500})
    assert r.status_code == 200
    client.post("/api/drawings", headers=HDR, json={"symbol": "SPY", "kind": "trend", "points": [
        {"time": "2024-03-01", "value": 1}, {"time": "2024-03-05", "value": 2}]})
    got = client.get("/api/drawings?symbol=SPY").json()
    assert [d["kind"] for d in got] == ["hline", "trend"] and got[0]["price"] == 500
    assert client.post("/api/drawings", headers=HDR,
                       json={"symbol": "SPY", "kind": "script"}).status_code == 422
    assert client.post("/api/drawings", json={"symbol": "SPY", "kind": "hline"}).status_code == 403
    assert client.delete("/api/drawings?symbol=SPY", headers=HDR).json()["deleted"] == 2


def test_screen_context_reaches_the_tutor(client, monkeypatch):
    from quant_brain.ui import backends

    seen = {}

    class Fake:
        name = "claude"

        def stream(self, system, prompt, *, timeout=300):
            seen["prompt"] = prompt
            yield "ok"

    monkeypatch.setitem(backends.BACKENDS, "claude", Fake())
    res = client.post("/api/learn/ask", headers=HDR,
                      json={"question": "what is this?", "sources": [],
                            "screen_context": "Chart of SPY, RSI(14) last=50.5"})
    assert res.status_code == 200
    assert "screen:what-you-are-looking-at" in seen["prompt"]
    assert "RSI(14) last=50.5" in seen["prompt"]
