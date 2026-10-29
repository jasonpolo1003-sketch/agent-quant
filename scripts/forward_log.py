"""Free forward paper log for SC-FUT-0005 (fresh, never-seen evidence; no orders).

    .venv/Scripts/python.exe scripts/forward_log.py          # fetch, log new days, print totals

Each run pulls Yahoo Finance 1-minute NQ=F bars (free, delayed; personal research use;
MNQ trades at the same prices), builds RTH days (08:30-15:00 CT), runs the frozen
SC-FUT-0005 rule (workbench NoiseArea, proven identical to the live engine) and its
matched random-direction control, and appends one row per completed session from
2026-10-22 (the day after the locked exam period) to
brain/04_Backtest_Reports/forward/sc-fut-0005-forward.csv. Idempotent: logged days are
skipped. Yahoo keeps ~30 days of 1-minute bars, so a missed run is caught up later.

Warm-up: sigma needs the previous 14 sessions' moves. Sessions before 2026-10-22 are used
for that only; no profit or loss is computed or shown for them.
Caveats: NQ=F is Yahoo's continuous front month (its roll date can differ from our volume
roll); Yahoo minute bars can have gaps (logged as missing bars).
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, date, datetime, time, timedelta

import numpy as np
import pandas as pd

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures.orb import L3_ROUND_TRIP_CENTS, DayInput
from quant_brain.workbench.noise import NoiseArea

FIRST_FORWARD = date(2026, 10, 22)
WARMUP_FROM = date(2026, 9, 29)
OUT = PROJECT_ROOT / "brain" / "04_Backtest_Reports" / "forward" / "sc-fut-0005-forward.csv"
RAW = PROJECT_ROOT.parent / "data" / "yahoo" / "NQ_F_1m"
FIELDS = [
    "trade_date",
    "status",
    "trades",
    "net_usd",
    "control_mean_net_usd",
    "bars",
    "early_close",
    "logged_at",
]
DRAWS = 500


def fetch() -> pd.DataFrame:
    """1-minute NQ=F bars from WARMUP_FROM to now (Yahoo serves 1m in <= 8-day windows)."""
    import yfinance as yf

    frames = []
    start = max(WARMUP_FROM, date.today() - timedelta(days=29))
    while start <= date.today():
        end = start + timedelta(days=7)
        df = yf.download(
            "NQ=F",
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1m",
            progress=False,
            auto_adjust=False,
            prepost=True,
        )
        if len(df):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            frames.append(df)
        start = end
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index = df.index.tz_convert("America/Chicago")
    RAW.mkdir(parents=True, exist_ok=True)
    for d, g in df.groupby(df.index.date):
        g.to_csv(RAW / f"{d.isoformat()}.csv")
    # Older raw days (beyond Yahoo's 30-day window) come back from the local cache.
    cached = []
    for p in sorted(RAW.glob("*.csv")):
        d = date.fromisoformat(p.stem)
        if d >= WARMUP_FROM and d not in set(df.index.date):
            c = pd.read_csv(p, index_col=0)
            c.index = pd.to_datetime(c.index, utc=True).tz_convert("America/Chicago")
            cached.append(c)
    return pd.concat([*cached, df]).sort_index() if cached else df


def build_days(df: pd.DataFrame) -> list[DayInput]:
    rth = df[(df.index.time >= time(8, 30)) & (df.index.time <= time(15, 0))]
    days, prev_close = [], None
    now = datetime.now(tz=df.index.tz)
    for d, g in rth.groupby(rth.index.date):
        if d.weekday() >= 5:
            continue
        last = g.index.max().time()
        early = last < time(12, 15)
        exit_minute = time(12, 0) if early else time(15, 0)
        complete = now >= datetime.combine(d, exit_minute, tzinfo=df.index.tz) + timedelta(
            minutes=5
        )
        bars, vols = {}, {}
        for ts, r in g.iterrows():
            ticks = [int(round(r[k] * 4)) for k in ("Open", "High", "Low", "Close")]
            bars[ts.time()] = tuple(ticks)
            vols[ts.time()] = int(r["Volume"]) if not np.isnan(r["Volume"]) else 0
        if complete:
            days.append(
                (
                    DayInput(d, "MNQ", bars, exit_minute, None, None, prev_close, None, vols),
                    early,
                )
            )
        before_close = [t for t in bars if t < exit_minute]
        prev_close = bars[max(before_close)][3] if before_close else prev_close
    return days


def main() -> int:
    df = fetch()
    days = build_days(df)
    rule = NoiseArea()
    prepared = rule.prepare_all([d for d, _ in days])
    done = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as h:
            done = {r["trade_date"] for r in csv.DictReader(h)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new = not OUT.exists()
    cost = L3_ROUND_TRIP_CENTS["MNQ"]
    added = 0
    with OUT.open("a", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, FIELDS, lineterminator="\n")
        if new:
            w.writeheader()
        for day, (_, early) in zip(prepared, days, strict=True):
            if day.trade_date < FIRST_FORWARD or day.trade_date.isoformat() in done:
                continue  # warm-up sessions: sigma only, never scored
            r = rule.simulate(day)
            gross, n, _, _ = rule.matched_control(day, r, DRAWS)
            ctrl = float(np.mean([g - cost * k for g, k in zip(gross, n, strict=True)])) / 100
            w.writerow(
                {
                    "trade_date": day.trade_date.isoformat(),
                    "status": r.status,
                    "trades": len(r.trades),
                    "net_usd": f"{r.net_cents / 100:.2f}",
                    "control_mean_net_usd": f"{ctrl:.2f}",
                    "bars": len(day.bars),
                    "early_close": early,
                    "logged_at": datetime.now(UTC).isoformat(timespec="seconds"),
                }
            )
            added += 1
    with OUT.open(encoding="utf-8") as h:
        rows = [r for r in csv.DictReader(h) if r["status"] in ("traded", "no_trade")]
    net = np.array([float(r["net_usd"]) for r in rows])
    ctl = np.array([float(r["control_mean_net_usd"]) for r in rows])
    print(f"forward log: +{added} new day(s); {len(rows)} scored days since {FIRST_FORWARD}")
    if len(rows):
        print(
            f"  SC-FUT-0005 1 MNQ: total ${net.sum():.2f}, ${net.mean():.2f}/day; "
            f"luck ${ctl.mean():.2f}/day; practice expectation ~$11.49/day"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
