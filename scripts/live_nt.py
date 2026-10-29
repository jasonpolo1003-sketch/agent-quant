"""One SC-FUT-0005 session on NinjaTrader 8 bars: dry run (FakeBroker) by default, --sim to send.

Bars come from ninjatrader/QuantBarExporter.cs (<nt-dir>\\quant_bars\\<instrument>_<date>.csv).
The sigma table and previous close are built from the earlier days' files in the same folder
(the exporter writes the chart's history too), so load at least 15 sessions on the chart.
Only NYSE sessions run: the date must be in the session calendar (live/calendar.py: the
frozen backtest calendar plus the live one to 2027-12-31), early closes flatten at 12:00 as
the calendar says, and only calendar sessions feed the sigma table and the previous close
(CME trades some NYSE holidays; the backtest never sees those days).
Bars already old when the first bars are read (at startup, or when the chart is loaded later)
only warm up the engine (no orders, journaled as catch_up); then the broker is moved toward
the engine's target with exits only, and live bars go through GuardedRunner
(live/ninjatrader.py), which also halts on a delayed feed. One process per account,
instrument and day (the broker's lock file).

--sim ACCOUNT sends ATI order files to NT8 for that account. Sim accounts only: the broker
refuses any account not starting with "Sim", and there is no override. The NT8 folder must not
be inside OneDrive (ATI file processing is reported to break there) unless --allow-onedrive.
Every event goes to a JSONL journal (default reports/generated/live_nt/<date>_<mode>.jsonl).
--replay feeds an existing bar file as if live (dry run only), to test the plumbing offline.
Halts persist for the day (in the broker's ledger). After fixing the cause, with no session
running: --sim ACCOUNT --clear-halt "why" appends a halt_cleared entry and exits; a
broker_state halt is only cleared when NT8's position file shows FLAT (flatten by hand first).

Usage: .venv/Scripts/python.exe scripts/live_nt.py --instrument "MNQ 12-26" [--sim Sim101]
       [--date 2026-10-30] [--nt-dir "D:\\NinjaTrader 8"] [--contracts 1] [--loss-stop 500]
       [--journal out.jsonl] [--kill-file STOP] [--replay] [--clear-halt "why"]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time as clock
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures.bars import CalendarDay
from quant_brain.live.broker import FakeBroker
from quant_brain.live.calendar import NYSE_SOURCE, sessions
from quant_brain.live.engine import SessionContext, SigmaHistory
from quant_brain.live.ninjatrader import (
    BAR_FOLDER,
    BROKER_HALT,
    BarFileTail,
    BrokerStateError,
    GuardedRunner,
    InstanceLocked,
    NinjaTraderBroker,
    OneDriveFolder,
    SimOnly,
    bar_file,
    check_sim,
    default_nt_dir,
    read_session,
    regular_close,
    under_onedrive,
    warm_up,
)
from quant_brain.live.runner import RiskConfig, _jsonable

CHICAGO = ZoneInfo("America/Chicago")


def now_ct() -> datetime:
    return datetime.now(CHICAGO).replace(tzinfo=None)


def history_context(
    bars_dir: Path,
    instrument: str,
    day: date,
    early: bool,
    calendar: dict[date, CalendarDay] | None = None,
) -> SessionContext:
    """Sigma table (last 14 sessions with bars) and previous regular close from earlier files,
    calendar sessions only (as futures/bars.build_days: a CME-only holiday is not a session)."""
    calendar = sessions() if calendar is None else calendar
    past = []
    for f in sorted(bars_dir.glob(f"{instrument}_*.csv")):
        try:
            d = date.fromisoformat(f.stem.rsplit("_", 1)[1])
        except ValueError:
            continue
        if d < day and d in calendar:
            past.append((d, f))
    history = SigmaHistory("MNQ")
    prev_close = None
    for d, f in past[-30:]:
        whole, _ = read_session(f, d, end=time(23, 59))
        bars = {m: b for m, b in whole.items() if m <= calendar[d].exit_minute}
        history.add_session(bars)  # the DayInput view: capped at the exit minute
        close = regular_close(whole, calendar[d].regular_close)  # bars._sessions: uncapped
        prev_close = close if close is not None else prev_close
    return SessionContext(day, "MNQ", prev_close, history.sigma(), early)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instrument", required=True, help='NT8 name, e.g. "MNQ 12-26"')
    parser.add_argument("--sim", metavar="ACCOUNT", help="send orders to this NT8 Sim account")
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    parser.add_argument("--nt-dir", type=Path, default=None)
    parser.add_argument("--allow-onedrive", action="store_true")
    parser.add_argument("--contracts", type=int, default=1)
    parser.add_argument("--max-position", type=int, default=2)
    parser.add_argument("--loss-stop", type=float, default=500.0, help="daily loss stop, dollars")
    parser.add_argument("--halt-lag", type=float, default=60.0, help="halt on bars this late, s")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--kill-file", type=Path, default=Path("STOP"))
    parser.add_argument("--replay", action="store_true", help="dry run over an existing file")
    parser.add_argument(
        "--clear-halt",
        metavar="WHY",
        help="with --sim: clear today's persisted halt (appends halt_cleared), then exit",
    )
    parser.add_argument("--poll", type=float, default=0.25)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    if args.clear_halt is not None and args.sim is None:
        raise SystemExit("--clear-halt needs --sim ACCOUNT (the halt lives in that ledger)")
    if args.sim is not None:
        try:
            check_sim(args.sim)
        except SimOnly as error:
            raise SystemExit(str(error)) from None
        if args.replay:
            raise SystemExit("--replay is dry run only: never send orders on old bars")
    day = args.date or now_ct().date()
    nt_dir = args.nt_dir or default_nt_dir()
    if under_onedrive(nt_dir):
        message = (
            f"{nt_dir} is inside OneDrive: NT8's ATI file processing is reported to break "
            "there. Move the NinjaTrader 8 folder to a local drive and pass --nt-dir."
        )
        if args.sim is not None and not args.allow_onedrive:
            raise SystemExit(message)
        logging.warning(message)
    calendar = sessions()
    if day not in calendar:
        raise SystemExit(
            f"{day} is not an NYSE session in the calendar (ends {max(calendar)}; source "
            f"{NYSE_SOURCE}): not trading"
        )
    early = calendar[day].early_close
    bars_dir = nt_dir / BAR_FOLDER
    ctx = history_context(bars_dir, args.instrument, day, early, calendar)
    mode = f"sim-{args.sim}" if args.sim else ("replay" if args.replay else "dry")
    journal = args.journal or PROJECT_ROOT / "reports/generated/live_nt" / f"{day}_{mode}.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    risk = RiskConfig(
        contracts=args.contracts,
        max_position=args.max_position,
        daily_loss_stop_cents=round(args.loss_stop * 100),
        kill_file=args.kill_file,
    )

    if args.sim:
        try:
            broker = NinjaTraderBroker(
                args.sim,
                args.instrument,
                day,
                nt_dir=nt_dir,
                clock=now_ct,
                allow_onedrive=args.allow_onedrive,
            )
        except InstanceLocked as error:  # another session runs: leave its journal alone
            raise SystemExit(f"not starting: {error}") from None
        except (BrokerStateError, OneDriveFolder) as error:
            if args.clear_halt is None:  # we hold no lock here, but nothing else runs
                with journal.open("a", encoding="utf-8") as handle:
                    rec = {"ts": now_ct().isoformat(), "kind": "halt", "reason": BROKER_HALT}
                    handle.write(json.dumps(rec | {"error": str(error)}) + "\n")
            raise SystemExit(f"not starting: {error}") from None
        if args.clear_halt is not None:
            try:
                cleared = broker.clear_halt(args.clear_halt)
            except (ValueError, BrokerStateError) as error:
                raise SystemExit(f"halt not cleared: {error}") from None
            finally:
                broker.close()
            print(f"cleared today's {cleared} halt for {args.sim} ({args.clear_halt!r})")
            return 0
    else:
        broker = FakeBroker("MNQ")

    tail = BarFileTail(bar_file(bars_dir, args.instrument, day), day)
    start = now_ct()
    runner = GuardedRunner(ctx, broker, risk, journal, now=start, halt_lag_seconds=args.halt_lag)
    if args.sim:
        runner._record(start, "reconcile", **_jsonable(broker.reconciliation))
    if not ctx.sigma or ctx.prev_close is None:
        runner._record(
            start, "warning", message="no sigma table or previous close: the engine will not trade"
        )

    def bar_end(b):
        return datetime.combine(day, b.minute) + timedelta(minutes=1)

    try:
        if args.replay:
            for b in tail.poll():
                runner.on_bar(b, bar_end(b) + timedelta(seconds=0.5))
        else:
            stop_at = datetime.combine(day, time(0)) + timedelta(minutes=runner.engine._flat_n + 5)
            while now_ct() < stop_at and runner.halted != BROKER_HALT:
                polled = tail.poll()
                if polled and runner.engine._last < 0:  # first bars: past ones only warm up
                    now = now_ct()
                    old = [
                        b for b in polled if (now - bar_end(b)).total_seconds() > risk.stale_seconds
                    ]
                    warm_up(runner, old, now, risk.contracts)  # engine only, exits only
                    polled = polled[len(old) :]
                for b in polled:
                    runner.on_bar(b, now_ct())
                runner.on_clock(now_ct())
                clock.sleep(args.poll)
        end = runner.end_session(now_ct() if not args.replay else None)
    finally:
        runner.close()  # also releases the broker's lock
    print(f"journal: {journal}")
    print(
        f"engine {end['engine_status']}, legs {len(end['model_legs'])}, broker position "
        f"{end['broker_position']}, halted {end['halted']}, skipped lines {dict(tail.skipped)}"
    )
    return 2 if runner.halted == BROKER_HALT else 0


if __name__ == "__main__":
    sys.exit(main())
