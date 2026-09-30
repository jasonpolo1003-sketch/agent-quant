"""Company profiles and fundamentals from SEC EDGAR (official, free) for symbol pages.

The SEC asks every client to send a User-Agent naming the requester with a
contact address, and to stay under 10 requests a second. This module reads
that User-Agent from ``SEC_USER_AGENT`` (``.env``) and never invents one.
Parsing is pure; network access is injected so tests run offline.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
MIN_SECONDS_BETWEEN_REQUESTS = 0.15  # the SEC's fair-access ceiling is 10 per second

# Plain-language metric -> XBRL concepts tried in order (companies use different tags).
METRICS: dict[str, dict[str, Any]] = {
    "revenue": {"label": "Revenue", "unit": "USD",
                "concepts": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                             "SalesRevenueNet", "RevenuesNetOfInterestExpense"],
                "why": "Total sales: how big the business is."},
    "net_income": {"label": "Net income", "unit": "USD", "concepts": ["NetIncomeLoss"],
                   "why": "Profit after all costs and taxes."},
    "eps_diluted": {"label": "EPS (diluted)", "unit": "USD/shares",
                    "concepts": ["EarningsPerShareDiluted"],
                    "why": "Profit per share, counting options and convertibles."},
    "operating_cash_flow": {"label": "Operating cash flow", "unit": "USD",
                            "concepts": ["NetCashProvidedByUsedInOperatingActivities"],
                            "why": "Cash the business actually generated; harder to flatter than profit."},
    "assets": {"label": "Total assets", "unit": "USD", "concepts": ["Assets"],
               "why": "Everything the company owns."},
    "liabilities": {"label": "Total liabilities", "unit": "USD", "concepts": ["Liabilities"],
                    "why": "Everything it owes."},
    "equity": {"label": "Shareholders' equity", "unit": "USD",
               "concepts": ["StockholdersEquity"], "why": "Assets minus liabilities: the owners' stake."},
}
SHARES_CONCEPT = ("dei", "EntityCommonStockSharesOutstanding")


def ticker_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """``company_tickers.json`` -> {TICKER: {"cik": int, "title": str}}."""
    return {row["ticker"].upper(): {"cik": int(row["cik_str"]), "title": row["title"]}
            for row in payload.values()}


def profile(submissions: dict[str, Any], *, cik: int, forms: Iterable[str] = (
        "10-K", "10-Q", "8-K", "DEF 14A", "4"), limit: int = 15) -> dict[str, Any]:
    """Company name, industry code and recent filings with direct links."""
    recent = submissions.get("filings", {}).get("recent", {})
    wanted = set(forms)
    filings = []
    for i, form in enumerate(recent.get("form", [])):
        if form not in wanted:
            continue
        accession = recent["accessionNumber"][i]
        filings.append({
            "form": form, "filed": recent["filingDate"][i],
            "report_date": recent.get("reportDate", [None] * (i + 1))[i] or None,
            "url": FILING_URL.format(cik=cik, accession=accession.replace("-", ""),
                                     document=recent["primaryDocument"][i]),
        })
        if len(filings) >= limit:
            break
    return {
        "name": submissions.get("name"), "cik": cik, "sic": submissions.get("sic"),
        "industry": submissions.get("sicDescription"),
        "exchanges": submissions.get("exchanges"), "fiscal_year_end": submissions.get("fiscalYearEnd"),
        "filings": filings,
    }


def _annual(points: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """One value per fiscal year from 10-K full-year facts; the latest filing wins."""
    by_year: dict[int, dict[str, Any]] = {}
    for p in points:
        if p.get("form") != "10-K" or p.get("fp") != "FY" or "fy" not in p:
            continue
        if "start" in p:  # duration facts: keep full-year periods only
            days = (date.fromisoformat(p["end"]) - date.fromisoformat(p["start"])).days
            if not 350 <= days <= 380:
                continue
        year = int(p["end"][:4])
        kept = by_year.get(year)
        if kept is None or p["filed"] > kept["filed"]:
            by_year[year] = {"value": p["val"], "end": p["end"], "filed": p["filed"],
                             "accession": p.get("accn")}
    return by_year


# Tickers whose current SEC filer is new, with the older filer holding the annual history.
# Observed 2026-09-29: "XOM" maps to ExxonMobil Holdings Corp (CIK 2115436, 10-Qs only so far);
# the 10-K history is under Exxon Mobil Corp (CIK 34088), whose CIK prefixes the new filings.
PREDECESSORS: dict[str, list[int]] = {"XOM": [34088]}


def fundamentals(facts: dict[str, Any], *, years: int = 10,
                 predecessors: list[dict[str, Any]] = ()) -> dict[str, Any]:
    """Annual series for each plain-language metric, plus the latest share count.

    Companies switch XBRL tags over time (Apple moved from ``Revenues`` to
    ``RevenueFromContract...`` after 2018), so each fiscal year takes the
    highest-priority tag that has it, across the filer and any predecessor
    filers; within a tag the latest filing wins (restatements).
    """
    payloads = [facts, *predecessors]
    series = {}
    for key, spec in METRICS.items():
        merged: dict[int, dict[str, Any]] = {}
        for payload in payloads:
            gaap = payload.get("facts", {}).get("us-gaap", {})
            for rank, concept in enumerate(spec["concepts"]):
                units = gaap.get(concept, {}).get("units", {}).get(spec["unit"]) or []
                for year, v in _annual(units).items():
                    kept = merged.get(year)
                    if kept is None or (rank, kept["filed"]) < (kept["rank"], v["filed"]):
                        merged[year] = {**v, "rank": rank, "concept": concept}
        if merged:
            recent = sorted(merged.items())[-years:]
            series[key] = {"label": spec["label"], "why": spec["why"], "unit": spec["unit"],
                           "concepts": sorted({v["concept"] for _, v in recent}),
                           "points": [{"fiscal_year_end": v["end"], "value": v["value"],
                                       "filed": v["filed"], "concept": v["concept"]}
                                      for _, v in recent]}
    shares = None
    for payload in payloads:
        points = payload.get("facts", {}).get(SHARES_CONCEPT[0], {}).get(SHARES_CONCEPT[1], {}) \
            .get("units", {}).get("shares", [])
        if points:
            last = max(points, key=lambda p: (p["end"], p["filed"]))
            shares = {"value": last["val"], "as_of": last["end"], "filed": last["filed"]}
            break
    return {"entity": facts.get("entityName"), "series": series, "shares_outstanding": shares,
            "predecessor_entities": [p.get("entityName") for p in predecessors],
            "note": "As reported in 10-K filings (annual). Figures can be restated later."}
