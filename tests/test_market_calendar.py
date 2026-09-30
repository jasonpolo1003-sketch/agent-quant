"""Calendar parsing on an offline copy of the Fed page's markup and fake API payloads."""

from datetime import date

from quant_brain.config import PROJECT_ROOT
from quant_brain.market import calendar as cal

HTML = (PROJECT_ROOT / "tests/fixtures/fomc_calendar_snippet.html").read_text(encoding="utf-8")


def test_fomc_rows_get_their_panel_year_and_both_days():
    rows = {m["label"]: m for m in cal.parse_fomc(HTML)}
    assert rows["January 27-28"]["start"] == "2026-01-27" and rows["January 27-28"]["end"] == "2026-01-28"
    assert rows["March 17-18*"]["projections"] is True
    assert rows["January 27-28"]["projections"] is False


def test_cross_month_cross_year_and_notation_votes():
    rows = {m["label"]: m for m in cal.parse_fomc(HTML)}
    assert (rows["Apr/May 30-1"]["start"], rows["Apr/May 30-1"]["end"]) == ("2021-04-30", "2021-05-01")
    assert rows["Dec/Jan 31-1*"]["end"] == "2028-01-01"
    assert rows["August 22 (notation vote)"]["kind"] == "notation vote"
    assert rows["August 22 (notation vote)"]["start"] == "2021-08-22"


def test_fomc_events_skip_notation_votes_and_mark_upcoming():
    events = cal.fomc_events(HTML, today=date(2026, 9, 29), fetched_at="t")
    assert all(e["kind"] == "fomc" for e in events) and len(events) == 5
    status = {e["date"]: e["status"] for e in events}
    assert status["2026-10-28"] == "upcoming" and status["2026-03-18"] == "past"
    assert "projections" in next(e for e in events if e["date"] == "2026-03-18")["title"]
    assert all(len(e["source"]["page_sha256"]) == 64 for e in events)


def test_release_events_filter_to_the_window_and_never_carry_the_key():
    calls = []

    def get(url, params):
        calls.append(params)
        return {"release_dates": [{"release_id": params["release_id"], "date": d}
                                  for d in ("2026-09-01", "2026-10-14", "2027-06-01")]}

    events = cal.release_events(get, "SECRET", start=date(2026, 9, 29), end=date(2026, 12, 31),
                                fetched_at="t", release_ids=[10, 50])
    assert [e["date"] for e in events] == ["2026-10-14", "2026-10-14"]
    assert {e["title"] for e in events} == {cal.RELEASES[10]["name"], cal.RELEASES[50]["name"]}
    assert "SECRET" not in repr(events) and all(c["api_key"] == "SECRET" for c in calls)


def test_earnings_event_picks_the_next_date_only():
    cal_dict = {"Earnings Date": [date(2026, 7, 30), date(2026, 10, 29)], "Earnings Average": 1.98124}
    e = cal.earnings_event("AAPL", cal_dict, today=date(2026, 9, 29), fetched_at="t")
    assert e["date"] == "2026-10-29" and e["detail"] == "EPS estimate 1.98"
    assert cal.earnings_event("X", {"Earnings Date": [date(2026, 1, 1)]}, today=date(2026, 9, 29),
                              fetched_at="t") is None
    assert cal.earnings_event("X", None, today=date(2026, 9, 29), fetched_at="t") is None


def test_merge_sorts_by_date():
    a = [{"date": "2026-10-14", "kind": "economic", "title": "CPI"}]
    b = [{"date": "2026-10-01", "kind": "earnings", "title": "X"}]
    assert [e["title"] for e in cal.merge(a, b)] == ["X", "CPI"]
