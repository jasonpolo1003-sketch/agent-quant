"""Does buying short-dated Nasdaq-100 options (risk ~30% of an account per bet) pay?

    .venv/Scripts/python.exe scripts/weekly_options_test.py

Data (FRED, key in .env; VXNCLS is Cboe data, private use): NASDAQ100 close, VXNCLS (30-day
implied vol), 2005-01-01..2024-12-31 (2025+ untouched). Each week: buy at the last close of
the week a call (or put) expiring 5 trading days later, struck k% out of the money, priced
Black-Scholes with sigma = VXN (flat: no skew, no event premium), r = 0; settle at intrinsic.
Event weeks/days: CPI or FOMC from brain/_system/futures/macro_release_days_2019_2024.csv.
Costs: `--spread` round-trip fraction of the premium (default 0.10).
Account: each bet stakes 30% of the account; 52-week runs from every start week.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import date
from math import erf, log, sqrt

import numpy as np

from quant_brain.config import PROJECT_ROOT

CACHE = PROJECT_ROOT.parent / "data" / "fred"


def key() -> str:
    for line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("FRED_API_KEY="):
            return line.split("=", 1)[1].strip()
    return os.environ["FRED_API_KEY"]


def series(sid: str) -> dict[date, float]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{sid}.json"
    if not path.exists():
        url = (
            "https://api.stlouisfed.org/fred/series/observations?series_id="
            f"{sid}&observation_start=2005-01-01&observation_end=2024-12-31"
            f"&file_type=json&api_key={key()}"
        )
        path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    obs = json.loads(path.read_text())["observations"]
    return {date.fromisoformat(o["date"]): float(o["value"]) for o in obs if o["value"] != "."}


def ncdf(x: float) -> float:
    return 0.5 * (1 + erf(x / sqrt(2)))


def bs(s: float, k: float, t: float, v: float, call: bool) -> float:
    d1 = (log(s / k) + 0.5 * v * v * t) / (v * sqrt(t))
    d2 = d1 - v * sqrt(t)
    return s * ncdf(d1) - k * ncdf(d2) if call else k * ncdf(-d2) - s * ncdf(-d1)


def returns(px, iv, dates, entries, hold, k, call, spread):
    out = []
    for i in entries:
        j = i + hold
        if j >= len(dates):
            break
        s, v = px[i], iv[i] / 100
        strike = s * (1 + k) if call else s * (1 - k)
        prem = bs(s, strike, hold / 252, v, call) * (1 + spread / 2)
        pay = max(px[j] - strike, 0) if call else max(strike - px[j], 0)
        out.append(pay * (1 - spread / 2) / prem - 1)
    return np.array(out)


def account(r: np.ndarray, stake=0.30, weeks=52):
    ends = []
    for a in range(0, len(r) - weeks):
        eq = 1.0
        for x in r[a : a + weeks]:
            eq *= 1 + stake * x
        ends.append(eq)
    return np.array(ends)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spread", type=float, default=0.10)
    a = ap.parse_args()
    ndx, vxn = series("NASDAQ100"), series("VXNCLS")
    dates = sorted(set(ndx) & set(vxn))
    px = np.array([ndx[d] for d in dates])
    iv = np.array([vxn[d] for d in dates])
    weekly = [i for i in range(len(dates) - 1) if dates[i + 1].isocalendar()[1] != dates[i].isocalendar()[1]]
    print(f"{len(dates)} days {dates[0]}..{dates[-1]}; {len(weekly)} weeks; spread {a.spread:.0%}")
    lr = np.diff(np.log(px))
    print(f"realized vol {lr.std() * sqrt(252):.1%} vs average VXN {iv.mean():.1f}%")
    print("\nweekly options, 30% of the account per bet, 52-week runs:")
    for call in (True, False):
        for k in (0.0, 0.01, 0.02, 0.03):
            r = returns(px, iv, dates, weekly, 5, k, call, a.spread)
            ends = account(r)
            print(
                f"  {'call' if call else 'put '} {k:.0%} OTM: avg return/bet {r.mean():+.1%}, "
                f"pays >=5x {np.mean(r >= 4):.1%}, expires worthless {np.mean(r <= -0.99):.0%} | "
                f"1-yr median x{np.median(ends):.2f}, P(up) {np.mean(ends > 1):.0%}, "
                f"P(lost 75%+) {np.mean(ends < 0.25):.0%}"
            )
    with (PROJECT_ROOT / "brain/_system/futures/macro_release_days_2019_2024.csv").open() as h:
        ev = {date.fromisoformat(r["release_date"]) for r in csv.DictReader(h) if r["release"] in ("CPI", "FOMC")}
    idx = {d: i for i, d in enumerate(dates)}
    pre = [idx[d] - 1 for d in sorted(ev) if d in idx and idx[d] >= 1]
    quiet = [i for i in range(len(dates) - 1) if dates[i] >= date(2019, 5, 1) and dates[i + 1] not in ev]
    move = lambda ids: np.mean([abs(lr[i]) for i in ids if i < len(lr)])
    imp = lambda ids: np.mean([iv[i] / 100 / sqrt(252) * sqrt(2 / np.pi) for i in ids])
    print(f"\nCPI/FOMC days 2019-2024 ({len(pre)}): avg |move| {move(pre):.2%} vs VXN-implied {imp(pre):.2%}; "
          f"other days {move(quiet):.2%} vs {imp(quiet):.2%}")
    print("1-day options bought the evening before CPI/FOMC (flat VXN pricing = no event premium):")
    for call in (True, False):
        for k in (0.0, 0.01):
            r = returns(px, iv, dates, pre, 1, k, call, a.spread)
            print(f"  {'call' if call else 'put '} {k:.0%} OTM: n={len(r)}, avg return {r.mean():+.1%}, "
                  f">=5x {np.mean(r >= 4):.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
