"""Build the terminal's market calendar from free sources (PROP-010 phase 2).

FOMC meetings from the Federal Reserve's page, economic release dates from
FRED (needs FRED_API_KEY in .env), and next earnings dates for the universe's
stocks from yfinance. Writes data/processed/calendar.json (gitignored). A
source that fails is reported and skipped; the others are still written.

    uv run python scripts/fetch_calendar.py
    uv run python scripts/fetch_calendar.py --days 60 --no-earnings
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta

import requests

from quant_brain.config import PROJECT_ROOT
from quant_brain.market import calendar as cal
from quant_brain.market.keys import get_key, redact
from quant_brain.market.universe import load_universe

OUT = "data/processed/calendar.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=90, help="how far ahead to list releases")
    parser.add_argument("--universe", default="starter")
    parser.add_argument("--no-earnings", action="store_true")
    args = parser.parse_args()

    today = date.today()
    now = datetime.now(UTC).isoformat()
    session = requests.Session()
    session.headers["User-Agent"] = cal.USER_AGENT
    groups, problems = [], []

    try:
        response = session.get(cal.FOMC_URL, timeout=30)
        response.raise_for_status()
        groups.append(cal.fomc_events(response.text, today=today, fetched_at=now))
    except Exception as exc:
        problems.append(f"FOMC: {type(exc).__name__}: {exc}")

    key = get_key("FRED_API_KEY")
    if key is None:
        problems.append("FRED: no FRED_API_KEY in .env; economic releases skipped")
    else:
        def get(url: str, params: dict) -> dict:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        try:
            groups.append(cal.release_events(get, key, start=today,
                                             end=today + timedelta(days=args.days), fetched_at=now))
        except Exception as exc:
            problems.append(redact(f"FRED: {type(exc).__name__}: {exc}", key))

    if not args.no_earnings:
        import yfinance

        stocks = [e["symbol"] for e in load_universe(PROJECT_ROOT, args.universe)["symbols"]
                  if e["group"] == "Large caps"]
        found = []
        for symbol in stocks:
            try:
                event = cal.earnings_event(symbol, yfinance.Ticker(symbol).calendar,
                                           today=today, fetched_at=now)
            except Exception as exc:
                problems.append(f"earnings {symbol}: {type(exc).__name__}: {exc}")
                continue
            if event:
                found.append(event)
        groups.append(found)

    events = cal.merge(*groups)
    payload = {"generated_at": now, "today": today.isoformat(), "events": events,
               "problems": problems,
               "note": "Dates can change. Official sources: Federal Reserve and FRED. "
                       "Earnings dates: Yahoo (unofficial)."}
    path = PROJECT_ROOT / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    for e in [e for e in events if e["status"] == "upcoming"][:25]:
        print(f"{e['date']}  {e['kind']:9} {e['title']}")
    for p in problems:
        print(f"WARN  {p}")
    print(f"wrote {OUT}: {len(events)} events ({sum(e['status'] == 'upcoming' for e in events)} upcoming)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
