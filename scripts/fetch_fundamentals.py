"""Fetch company profiles and annual fundamentals from SEC EDGAR (PROP-010 phase 2).

Official and free. The SEC requires a User-Agent naming you with a contact
email: put SEC_USER_AGENT="Your Name your@email" in .env. Requests are paced
under the SEC's 10-per-second ceiling. Raw JSON goes to data/raw/edgar/ and
one processed file per symbol to data/processed/fundamentals/ (both gitignored).

    uv run python scripts/fetch_fundamentals.py              # the starter universe's stocks
    uv run python scripts/fetch_fundamentals.py --symbols AAPL MSFT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime

import requests

from quant_brain.config import PROJECT_ROOT
from quant_brain.market import edgar
from quant_brain.market.keys import get_key
from quant_brain.market.universe import load_universe

RAW = PROJECT_ROOT / "data/raw/edgar"
OUT = PROJECT_ROOT / "data/processed/fundamentals"


class Client:
    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
        self.last = 0.0

    def get(self, url: str) -> tuple[dict, str]:
        wait = edgar.MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        response = self.session.get(url, timeout=30)
        self.last = time.monotonic()
        response.raise_for_status()
        return response.json(), hashlib.sha256(response.content).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--symbols", nargs="+")
    parser.add_argument("--universe", default="starter")
    args = parser.parse_args()

    user_agent = get_key("SEC_USER_AGENT")
    if not user_agent or "@" not in user_agent:
        print('REFUSED: set SEC_USER_AGENT="Your Name your@email" in .env (the SEC requires a '
              "contact in the User-Agent: https://www.sec.gov/os/accessing-edgar-data)")
        return 2
    symbols = args.symbols or [e["symbol"] for e in load_universe(PROJECT_ROOT, args.universe)["symbols"]
                               if e["group"] == "Large caps"]
    client = Client(user_agent)
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()

    tickers, _ = client.get(edgar.TICKERS_URL)
    mapping = edgar.ticker_map(tickers)
    failed = False
    for symbol in symbols:
        entry = mapping.get(symbol.upper()) or mapping.get(symbol.upper().replace("-", "."))
        if entry is None:
            print(f"SKIP  {symbol}: not in the SEC ticker list (ETFs and funds usually are not)")
            continue
        cik = entry["cik"]
        try:
            subs, subs_sha = client.get(edgar.SUBMISSIONS_URL.format(cik=cik))
            facts, facts_sha = client.get(edgar.FACTS_URL.format(cik=cik))
        except Exception as exc:
            failed = True
            print(f"FAIL  {symbol}: {type(exc).__name__}: {exc}")
            continue
        (RAW / f"{symbol}.submissions.json").write_text(json.dumps(subs), encoding="utf-8")
        (RAW / f"{symbol}.companyfacts.json").write_text(json.dumps(facts), encoding="utf-8")
        record = {
            "symbol": symbol, "fetched_at": now,
            "source": {"name": "SEC EDGAR", "tier": "official",
                       "urls": [edgar.SUBMISSIONS_URL.format(cik=cik), edgar.FACTS_URL.format(cik=cik)],
                       "sha256": {"submissions": subs_sha, "companyfacts": facts_sha}},
            "profile": edgar.profile(subs, cik=cik),
            "fundamentals": edgar.fundamentals(facts),
        }
        (OUT / f"{symbol}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
        series = record["fundamentals"]["series"]
        revenue = series.get("revenue", {}).get("points", [])
        print(f"OK    {symbol}: {record['profile']['industry']}; {len(series)} metrics; "
              f"latest revenue {revenue[-1]['fiscal_year_end'] if revenue else 'n/a'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
