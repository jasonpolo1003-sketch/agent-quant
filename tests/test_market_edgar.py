"""EDGAR parsing on small fake payloads shaped like the SEC's JSON."""

from quant_brain.market import edgar


def fact(val, end, filed, *, start=None, form="10-K", fp="FY", fy=None):
    p = {"val": val, "end": end, "filed": filed, "form": form, "fp": fp, "fy": fy or int(filed[:4]),
         "accn": "0000-00-1"}
    if start:
        p["start"] = start
    return p


def test_ticker_map_uppercases_and_keeps_cik():
    m = edgar.ticker_map({"0": {"cik_str": 320193, "ticker": "aapl", "title": "Apple Inc."}})
    assert m == {"AAPL": {"cik": 320193, "title": "Apple Inc."}}


def test_annual_series_keeps_full_years_and_the_latest_filing():
    facts = {"entityName": "X", "facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        fact(100, "2024-12-31", "2025-02-01", start="2024-01-01"),
        fact(105, "2024-12-31", "2026-02-01", start="2024-01-01"),        # restated later: wins
        fact(30, "2024-06-30", "2024-08-01", start="2024-04-01", form="10-Q", fp="Q2"),
        fact(40, "2025-03-31", "2026-02-01", start="2025-01-01"),         # quarter inside a 10-K
        fact(120, "2025-12-31", "2026-02-01", start="2025-01-01"),
    ]}}}}}
    s = edgar.fundamentals(facts)["series"]["revenue"]
    assert [(p["fiscal_year_end"], p["value"]) for p in s["points"]] == [
        ("2024-12-31", 105), ("2025-12-31", 120)]
    assert s["concepts"] == ["Revenues"] and s["why"]


def test_falls_back_to_the_next_concept_and_reads_shares():
    facts = {"facts": {
        "us-gaap": {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            fact(50, "2025-09-30", "2025-11-01", start="2024-10-01")]}},
            "Assets": {"units": {"USD": [fact(900, "2025-09-30", "2025-11-01")]}}},
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"val": 10, "end": "2025-10-15", "filed": "2025-11-01"},
            {"val": 9, "end": "2025-07-15", "filed": "2025-08-01"}]}}}}}
    out = edgar.fundamentals(facts)
    assert out["series"]["revenue"]["concepts"] == ["RevenueFromContractWithCustomerExcludingAssessedTax"]
    assert out["series"]["assets"]["points"][0]["value"] == 900
    assert out["shares_outstanding"] == {"value": 10, "as_of": "2025-10-15", "filed": "2025-11-01"}
    assert "net_income" not in out["series"]


def test_profile_lists_wanted_forms_with_links():
    subs = {"name": "Apple Inc.", "sic": "3571", "sicDescription": "Electronic Computers",
            "filings": {"recent": {"form": ["8-K", "S-8", "10-Q"],
                                   "filingDate": ["2026-09-01", "2026-08-15", "2026-08-01"],
                                   "reportDate": ["2026-09-01", "", "2026-06-27"],
                                   "accessionNumber": ["0000320193-26-000100", "x", "0000320193-26-000090"],
                                   "primaryDocument": ["a8k.htm", "s8.htm", "a10q.htm"]}}}
    p = edgar.profile(subs, cik=320193)
    assert [f["form"] for f in p["filings"]] == ["8-K", "10-Q"]
    assert p["filings"][0]["url"] == \
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000100/a8k.htm"
    assert p["industry"] == "Electronic Computers"


def test_years_merge_across_tags_when_a_company_switches():
    facts = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [fact(10, "2017-12-31", "2018-02-01", start="2017-01-01"),
                                       fact(11, "2018-12-31", "2019-02-01", start="2018-01-01")]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            fact(99, "2018-12-31", "2019-02-01", start="2018-01-01"),   # same year: lower priority
            fact(12, "2019-12-31", "2020-02-01", start="2019-01-01")]}}}}}
    points = edgar.fundamentals(facts)["series"]["revenue"]["points"]
    assert [(p["fiscal_year_end"][:4], p["value"], p["concept"][:8]) for p in points] == [
        ("2017", 10, "Revenues"), ("2018", 11, "Revenues"), ("2019", 12, "RevenueF")]


def test_predecessor_filer_supplies_the_history():
    new = {"entityName": "NewCo Holdings", "facts": {"us-gaap": {"Assets": {"units": {"USD": [
        fact(5, "2026-06-30", "2026-08-01", form="10-Q", fp="Q2")]}}},
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"val": 7, "end": "2026-07-01", "filed": "2026-08-01"}]}}}}}
    old = {"entityName": "OldCo", "facts": {"us-gaap": {"Assets": {"units": {"USD": [
        fact(400, "2025-12-31", "2026-02-01")]}}}}}
    out = edgar.fundamentals(new, predecessors=[old])
    assert out["series"]["assets"]["points"][0]["value"] == 400
    assert out["shares_outstanding"]["value"] == 7 and out["predecessor_entities"] == ["OldCo"]
    assert "XOM" in edgar.PREDECESSORS
