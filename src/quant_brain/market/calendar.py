"""Market calendar for the learning terminal (PROP-010 phase 2): free, official where possible.

- FOMC meetings: parsed from the Federal Reserve's calendar page (official).
- Economic releases: FRED ``release/dates`` for a short list of market-moving
  releases (official; needs the free ``FRED_API_KEY``).
- Earnings: yfinance's per-ticker calendar (unofficial; personal use only).

Network access is injected (``get``), so tests run offline on fixtures.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from datetime import date
from typing import Any

FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FRED_RELEASE_DATES_URL = "https://api.stlouisfed.org/fred/release/dates"
USER_AGENT = "quant-agent-brain local learning terminal (personal, non-commercial)"

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# FRED release id -> plain-language note. Ids checked against fred/releases on 2026-09-29.
RELEASES: dict[int, dict[str, str]] = {
    10: {"name": "Consumer Price Index (CPI)",
         "why": "The main inflation reading. Higher-than-expected inflation can push rate expectations and bond yields up."},
    50: {"name": "Employment Situation (jobs report)",
         "why": "Payrolls and the unemployment rate: the clearest monthly read on the economy's health."},
    53: {"name": "Gross Domestic Product (GDP)",
         "why": "The broadest measure of economic output, reported quarterly and revised later."},
    54: {"name": "Personal Income and Outlays (PCE inflation)",
         "why": "Contains PCE inflation, the measure the Fed's 2% target refers to."},
    46: {"name": "Producer Price Index (PPI)",
         "why": "Prices businesses receive; sometimes an early hint for consumer inflation."},
    9: {"name": "Retail Sales (advance)",
        "why": "How much consumers spent last month; consumer spending is most of US GDP."},
    192: {"name": "Job Openings and Labor Turnover (JOLTS)",
          "why": "Job openings and quits: how tight the labour market is."},
    180: {"name": "Initial Jobless Claims (weekly)",
          "why": "A weekly, fast-moving signal of layoffs."},
    27: {"name": "Housing Starts",
         "why": "New home construction; sensitive to interest rates."},
}

FOMC_WHY = ("The Federal Reserve's rate-setting meeting. The decision and the chair's press conference "
            "can move stocks, bonds and the dollar within minutes.")

_YEAR = re.compile(r'<h4><a id="\d+">(\d{4}) FOMC Meetings</a></h4>')
_ROW = re.compile(
    r'fomc-meeting__month[^>]*><strong>([^<]+)</strong></div>\s*'
    r'<div class="fomc-meeting__date[^>]*>([^<]+)</div>')


def _month(text: str) -> int:
    return MONTHS[text.strip()[:3].lower()]


def parse_fomc(html: str) -> list[dict[str, Any]]:
    """Every meeting row on the Fed's page, with start/end dates and flags."""
    years = [(m.start(), int(m.group(1))) for m in _YEAR.finditer(html)]
    meetings = []
    for m in _ROW.finditer(html):
        prior = [y for pos, y in years if pos < m.start()]
        if not prior:
            continue
        year = prior[-1]
        months = [_month(x) for x in m.group(1).split("/")]
        raw = m.group(2).strip()
        projections = "*" in raw
        notation = "notation vote" in raw.lower()
        unscheduled = "unscheduled" in raw.lower()
        days = [int(d) for d in re.findall(r"\d+", raw.split("(")[0])]
        start_day, end_day = days[0], days[-1]
        start_month = months[0]
        end_month = months[-1] if len(months) > 1 else start_month
        start = date(year, start_month, start_day)
        end_year = year + 1 if end_month < start_month else year
        end = date(end_year, end_month, end_day)
        meetings.append({
            "start": start.isoformat(), "end": end.isoformat(), "label": f"{m.group(1).strip()} {raw}",
            "projections": projections,
            "kind": "notation vote" if notation else "unscheduled" if unscheduled else "meeting",
        })
    return sorted(meetings, key=lambda x: x["start"])


def fomc_events(html: str, *, today: date, fetched_at: str) -> list[dict[str, Any]]:
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    events = []
    for m in parse_fomc(html):
        if m["kind"] == "notation vote":
            continue
        events.append({
            "date": m["end"], "kind": "fomc", "title": "FOMC rate decision"
            + (" + economic projections" if m["projections"] else ""),
            "detail": f"Meeting {m['start']} to {m['end']}", "why": FOMC_WHY,
            "status": "upcoming" if m["end"] >= today.isoformat() else "past",
            "source": {"name": "Federal Reserve", "url": FOMC_URL, "tier": "official",
                       "fetched_at": fetched_at, "page_sha256": digest,
                       "note": "Future dates are tentative until confirmed at the preceding meeting."},
        })
    return events


def release_events(
    get: Callable[[str, dict], dict], api_key: str, *, start: date, end: date, fetched_at: str,
    release_ids: Iterable[int] = RELEASES,
) -> list[dict[str, Any]]:
    """Scheduled FRED release dates between ``start`` and ``end`` (inclusive)."""
    events = []
    for rid in release_ids:
        payload = get(FRED_RELEASE_DATES_URL, {
            "api_key": api_key, "file_type": "json", "release_id": rid,
            "realtime_start": start.isoformat(), "realtime_end": "9999-12-31",
            "include_release_dates_with_no_data": "true", "sort_order": "asc", "limit": 1000,
        })
        for row in payload.get("release_dates", []):
            if start.isoformat() <= row["date"] <= end.isoformat():
                events.append({
                    "date": row["date"], "kind": "economic", "title": RELEASES[rid]["name"],
                    "detail": f"FRED release {rid}", "why": RELEASES[rid]["why"], "status": "upcoming",
                    "source": {"name": "FRED (St. Louis Fed)", "tier": "official",
                               "url": f"https://fred.stlouisfed.org/releases/calendar?rid={rid}",
                               "fetched_at": fetched_at},
                })
    return events


def earnings_event(symbol: str, calendar: dict[str, Any] | None, *, today: date,
                   fetched_at: str) -> dict[str, Any] | None:
    """The next earnings date from a yfinance ``Ticker.calendar`` dict, if any."""
    if not calendar:
        return None
    dates = calendar.get("Earnings Date") or []
    upcoming = sorted(d for d in dates if isinstance(d, date) and d >= today)
    if not upcoming:
        return None
    estimate = calendar.get("Earnings Average")
    return {
        "date": upcoming[0].isoformat(), "kind": "earnings", "symbol": symbol,
        "title": f"{symbol} earnings",
        "detail": (f"EPS estimate {estimate:.2f}" if isinstance(estimate, (int, float)) else ""),
        "why": "Earnings reports often cause the biggest single-day moves in a stock. "
               "The price reacts to the result versus what was expected.",
        "status": "upcoming",
        "source": {"name": "Yahoo Finance via yfinance", "tier": "unofficial",
                   "note": "personal use only; dates can shift", "fetched_at": fetched_at},
    }


def merge(*groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((e for g in groups for e in g), key=lambda e: (e["date"], e["kind"], e["title"]))
