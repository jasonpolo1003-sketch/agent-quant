"""QA reproductions for the NT8 Sim bridge (brain/05_Reviews/nt8-bridge-QA-2026-10-29.md).

Each test named after a finding ID (H1..H4, M1..M4, L1) was a strict xfail reproducing an open
bug; all are fixed and the marks removed (2026-10-29). Where the fix changed the interface the
test was adapted, and says so: H3 (a second broker now refuses to start), H4 (the calendar is
live/calendar.sessions(), not the frozen file), H2_full_day_effect (asserts the fixed result),
and an explicit close() where a test simulated a process ending (the instance lock).
The re-review's N1-N4 strict xfails are fixed and unmarked too. The re-review's lock test
was adapted to the N1 fix (an OS lock): the child process now holds the lock itself, since a
file that only names a live PID no longer blocks anything.
Plain tests confirm behaviour the review checked and found safe.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from futures_day_builder import t
from test_live_ninjatrader import (
    BREAKOUT,
    DAY,
    OFF,
    REVERSE,
    SIGMA,
    Clock,
    FakeNT8,
    day,
    day_t,
    kinds,
    make_broker,
    run_day,
    trips,
)

from quant_brain.config import PROJECT_ROOT
from quant_brain.live import ninjatrader as nt
from quant_brain.live.broker import FakeBroker
from quant_brain.live.calendar import sessions
from quant_brain.live.engine import Bar, bars_of, context_of
from quant_brain.live.ninjatrader import (
    BROKER_HALT,
    BrokerStateError,
    GuardedRunner,
    SimOnly,
    write_oif,
)
from quant_brain.live.runner import RiskConfig


def _live_nt():
    spec = importlib.util.spec_from_file_location(
        "live_nt", PROJECT_ROOT / "scripts" / "live_nt.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _flat(ticks: int) -> Bar:
    return Bar(t("09:00"), ticks, ticks, ticks, ticks)


# --- H1: an unconsumed OIF stays armed ----------------------------------------------------


def test_H1_unconsumed_oif_is_disarmed_when_the_broker_halts(tmp_path):
    d = day(BREAKOUT)
    fake = FakeNT8(tmp_path)
    fake.running = False  # ATI off / NT8 closed at 09:00
    clock = Clock()
    broker = make_broker(tmp_path, clock, ack_seconds=5)
    r = GuardedRunner(context_of(d, SIGMA), broker, OFF, now=day_t(8))
    for b in bars_of(d):
        clock.at = datetime.combine(DAY, b.minute) + timedelta(minutes=1, seconds=0.5)
        fake.step(b)
        r.on_bar(b, clock.at)
        if r.halted:
            break
    assert r.halted == BROKER_HALT
    # Hours later Jason turns ATI on (or NT8 finishes starting). Nothing manages the account.
    fake.running = True
    fake.step(Bar(t("13:00"), 120, 120, 120, 120))
    assert fake.position == 0  # today: 1, a market BUY from a halted session


def test_H1_yesterdays_unconsumed_oif_blocks_startup(tmp_path):
    fake = FakeNT8(tmp_path)
    fake.running = False
    yesterday = make_broker(tmp_path, trade_date=date(2020, 1, 1))
    yesterday.place_market_order(1, datetime(2020, 1, 1, 9), "long")
    assert len(list(fake.incoming.glob("oif*.txt"))) == 1
    with pytest.raises(BrokerStateError):  # today: starts cleanly, the OIF still armed
        make_broker(tmp_path)


# --- H2: restart between a check and its fill bar ------------------------------------------


def _reverse_day():
    d = day(REVERSE)
    bars = bars_of(d)
    return d, bars, next(i for i, b in enumerate(bars) if b.minute == t("10:30"))


def test_H2_restart_after_a_check_bar_still_sends_the_exit(tmp_path):
    d, bars, i = _reverse_day()
    r1, _, _ = run_day(d, tmp_path, bars=bars[: i - 1])  # dies before the 10:29 bar arrives
    r1.close()
    start = datetime(2020, 1, 2, 10, 30, 15)  # back 15 s after the 10:30 check
    b2 = make_broker(tmp_path)
    r2 = GuardedRunner(context_of(d, SIGMA), b2, OFF, now=start)
    nt.warm_up(r2, bars[:i], start)  # live_nt: the 10:29 bar is > stale_seconds old
    # The engine reversed at 10:30: the exit must go (exits are never refused); the new short
    # is refused as stale. Today nothing is sent and the broker stays long.
    assert b2.position() + b2.working() == 0


def test_H2_restart_after_the_reversal_filled_sends_nothing(tmp_path):
    d, bars, i = _reverse_day()
    r1, _, fake = run_day(d, tmp_path, bars=bars[:i])  # the 10:29 bar sends the reversal
    fake.step(bars[i])  # NT8 fills it at once; the process dies before booking it
    r1.close()  # also releases the instance lock
    start = datetime(2020, 1, 2, 10, 30, 15)
    b2 = make_broker(tmp_path)
    assert b2.position() == -1  # NT8 holds the engine's short
    r2 = GuardedRunner(context_of(d, SIGMA), b2, OFF, now=start)
    nt.warm_up(r2, bars[:i], start)
    assert not kinds(r2, "order")  # today: BUY 1 'restart_reconcile', flattening the short


def test_H2_full_day_effect(tmp_path):
    """The H2a restart end to end, fixed: the exit goes at the restart and fills at the 10:30
    open, so the long leg equals the backtest's; the new short is refused (stale), as the
    runner refuses any late entry, so the afternoon short is missed, not held the wrong way."""
    d, bars, i = _reverse_day()
    whole, _, _ = run_day(d, tmp_path / "ref")
    ref = trips(whole.broker)
    root = tmp_path / "live"
    r1, _, fake = run_day(d, root, bars=bars[: i - 1])
    r1.close()
    start = datetime(2020, 1, 2, 10, 30, 15)
    b2 = make_broker(root)
    r2 = GuardedRunner(context_of(d, SIGMA), b2, OFF, now=start)
    nt.warm_up(r2, bars[:i], start)
    run_day(d, root, bars=bars[i:], runner=r2, broker=b2, fake=fake)
    got = trips(b2)
    assert [x[0] for x in ref] == [1, -1] and ref[0][3] == t("10:30")
    assert got == ref[:1] and b2.position() == 0  # was: long 09:00 -> 15:00


# --- H3: two processes on one account ------------------------------------------------------


def test_H3_second_process_on_the_same_account_is_refused(tmp_path):
    fake = FakeNT8(tmp_path)
    a = make_broker(tmp_path)
    with pytest.raises(nt.InstanceLocked):  # a second live_nt.py --sim Sim101 (or a zombie)
        make_broker(tmp_path)
    a.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    fake.step(_flat(400))
    assert fake.places() == ["QB20200102N0001"]  # was: N0001 twice, NT8 position 2
    assert fake.position == 1


# --- H4: session calendar / holidays -------------------------------------------------------


def test_H4_calendar_covers_the_next_early_close():
    days = sessions()  # frozen calendar + the live one (the frozen file itself stays frozen)
    assert date(2026, 11, 27) in days and days[date(2026, 11, 27)].early_close
    assert date(2026, 11, 26) not in days  # Thanksgiving


def _write_bars(path, d, close_points, until="15:07"):
    end = datetime.combine(d, t(until))
    m = datetime.combine(d, t("08:30"))
    lines = [nt.BAR_HEADER]
    while m <= end:
        p = close_points
        lines.append(f"{d},{m:%H:%M},{p},{p},{p},{p},10")
        m += timedelta(minutes=1)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_H4_holiday_session_is_not_the_previous_close(tmp_path):
    live_nt = _live_nt()
    inst = "MNQ 12-25"
    # 2025-11-26 is an NYSE session; 2025-11-27 (Thanksgiving) is not, but CME equity
    # futures trade to 12:00 CT and NT8's exporter writes that file too.
    _write_bars(nt.bar_file(tmp_path, inst, date(2025, 11, 26)), date(2025, 11, 26), 25.0)
    _write_bars(nt.bar_file(tmp_path, inst, date(2025, 11, 27)), date(2025, 11, 27), 50.0, "11:59")
    ctx = live_nt.history_context(tmp_path, inst, date(2025, 11, 28), True)
    assert ctx.prev_close == 100  # 25.00 = 100 ticks (backtest); today 200 (the holiday)


# --- Medium -------------------------------------------------------------------------------


def test_M1_day_pnl_survives_a_restart_with_an_unbooked_fill(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    b.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    fake.step(_flat(400))
    b.on_bar(None, datetime(2020, 1, 2, 9, 0))
    b.place_market_order(-1, datetime(2020, 1, 2, 9, 30), "exit")
    fake.step(_flat(360))
    b.on_bar(None, datetime(2020, 1, 2, 9, 30))
    assert b.day_pnl_cents(360) == -40 * 50
    b.place_market_order(1, datetime(2020, 1, 2, 10), "long")
    fake.step(_flat(360))  # NT8 fills; the process dies before the next bar books it
    b.close()  # (a crashed process's lock is taken over once its PID is dead)
    b2 = make_broker(tmp_path)
    assert b2.day_pnl_cents(360) == -40 * 50  # today: 0, the loss stop starts over


def test_M2_a_bar_delayed_by_a_tradeless_minute_does_not_kill_the_day():
    d = day(BREAKOUT)
    r = GuardedRunner(
        context_of(d, SIGMA), FakeBroker(), RiskConfig(kill_file=None), now=day_t(2, 0)
    )
    r.on_bar(Bar(t("03:00"), 105, 105, 105, 105), day_t(3, 1, 0.2))
    # 03:02 has no trades; OnBarClose writes the 03:01 bar at the first tick, 03:03:05
    r.on_bar(Bar(t("03:01"), 105, 105, 105, 105), day_t(3, 3, 5))
    assert r.halted is None  # today: stale_data at 03:03, five hours before the open


@pytest.mark.parametrize(
    "line",
    [
        nt.flatten_everything_line(),
        nt.cancel_all_orders_line(),
        "place;Live1;MNQ 06-24;BUY;1;MARKET;0;0;DAY;;X;;",
        " PLACE;Live1;MNQ 06-24;BUY;1;MARKET;0;0;DAY;;X;;",
    ],
)
def test_M3_write_oif_refuses_account_wide_and_disguised_commands(tmp_path, line):
    with pytest.raises((SimOnly, ValueError)):
        write_oif(tmp_path, "oif_z.txt", [line])


def test_M4_an_os_error_writing_the_oif_halts_instead_of_crashing(tmp_path, monkeypatch):
    d = day(BREAKOUT)
    fake = FakeNT8(tmp_path)
    clock = Clock()
    broker = make_broker(tmp_path, clock)
    r = GuardedRunner(context_of(d, SIGMA), broker, OFF, now=day_t(8))

    def locked(src, dst):  # antivirus / indexer holding the temp file
        raise PermissionError(13, "The process cannot access the file", str(src))

    monkeypatch.setattr(nt.os, "rename", locked)
    for b in bars_of(d):
        clock.at = datetime.combine(DAY, b.minute) + timedelta(minutes=1, seconds=0.5)
        fake.step(b)
        r.on_bar(b, clock.at)  # today: PermissionError escapes at 08:59 and kills live_nt
        if r.halted:
            break
    assert r.halted == BROKER_HALT


# --- Low ----------------------------------------------------------------------------------


def test_L1_second_partial_fill_is_booked_at_its_own_price(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    oid = b.place_market_order(2, datetime(2020, 1, 2, 9), "long")
    fake.consume()
    fake._state(oid, "PartFilled;1;100")  # 1 @ 100.00
    fake.position, fake.avg = 1, 100.0
    fake._position_file()
    b.on_bar(None, datetime(2020, 1, 2, 9, 0))
    fake._state(oid, "Filled;2;100.5")  # second @ 101.00, average 100.50
    fake.position, fake.avg = 2, 100.5
    fake._position_file()
    b.on_bar(None, datetime(2020, 1, 2, 9, 1))
    assert [lot.price for lot in b._lots] == [400, 404]  # today [400, 402]


# --- confirmed safe -----------------------------------------------------------------------


def test_crash_between_ledger_write_and_oif_rename_never_sends(tmp_path, monkeypatch):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    real = nt.os.rename

    def die(src, dst):
        raise KeyboardInterrupt  # the process is killed between the ledger and the rename

    monkeypatch.setattr(nt.os, "rename", die)
    with pytest.raises(KeyboardInterrupt):
        b.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    monkeypatch.setattr(nt.os, "rename", real)
    assert list(fake.incoming.glob("oif*.txt")) == []
    b.close()
    with pytest.raises(BrokerStateError, match="no order state"):
        make_broker(tmp_path)  # refuses (safe) for the rest of the day: no recovery path
    fake.consume()
    assert fake.places() == []


def test_restart_ids_continue_and_differ_across_days(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    b.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    fake.step(_flat(400))
    b.on_bar(None, datetime(2020, 1, 2, 9))
    b.close()
    assert make_broker(tmp_path).reconciliation["next_order_id"] == "QB20200102N0002"
    other = make_broker(tmp_path / "x", trade_date=date(2020, 1, 3))
    assert other.reconciliation["next_order_id"] == "QB20200103N0001"


@pytest.mark.parametrize(
    "argv",
    [
        ["--sim", "Live1"],
        ["--sim", "sim101"],
        ["--sim", ""],
        ["--sim", " Sim101"],
        ["--sim", "Sim101", "--replay"],
    ],
)
def test_live_nt_arguments_cannot_bypass_the_sim_guard(argv, monkeypatch, tmp_path):
    live_nt = _live_nt()
    monkeypatch.setattr(sys, "argv", ["live_nt.py", "--instrument", "MNQ 12-26", *argv])
    built = []
    monkeypatch.setattr(live_nt, "NinjaTraderBroker", lambda *a, **k: built.append(a))
    with pytest.raises(SystemExit):
        live_nt.main()
    assert built == []


# --- re-review 2026-10-29: new findings (N*) and checks of the fixes ------------------------


_HOLD = (
    "import os, sys, time\n"
    "from quant_brain.live.ninjatrader import ProcessLock\n"
    "print(ProcessLock(sys.argv[1]).acquire({'pid': os.getpid()}), flush=True)\n"
    "time.sleep(60)\n"
)


def _hold_lock_in_child(lock):
    """A real second process holding the OS lock, as a running live_nt would."""
    import site

    # the base interpreter, not the venv launcher (which would run the holder as a grandchild)
    path = os.pathsep.join([str(PROJECT_ROOT / "src"), *site.getsitepackages()])
    python = getattr(sys, "_base_executable", sys.executable)
    child = subprocess.Popen(
        [python, "-c", _HOLD, str(lock)],
        stdout=subprocess.PIPE,
        text=True,
        env=os.environ | {"PYTHONPATH": path},
    )
    assert child.stdout.readline().strip() == "True"
    return child


def test_lock_refuses_a_live_other_process_and_takes_over_after_a_hard_kill(tmp_path):
    # adapted for the OS lock (N1 fix): the child now holds the lock itself; a file that only
    # names a live PID no longer blocks anything
    import json

    probe = make_broker(tmp_path)
    lock = probe.lock_file()
    probe.close()
    child = _hold_lock_in_child(lock)
    try:
        assert nt.pid_alive(child.pid) is True
        with pytest.raises(nt.InstanceLocked, match=f"process {child.pid}"):
            make_broker(tmp_path)
    finally:
        child.kill()  # TerminateProcess: no cleanup runs, the OS drops the lock
        child.wait()
    assert nt.pid_alive(child.pid) is False
    b = make_broker(tmp_path)
    assert json.loads(lock.read_text(encoding="utf-8"))["pid"] == os.getpid()
    b.close()


def test_N1_two_processes_taking_over_one_dead_lock_cannot_both_run(tmp_path, monkeypatch):
    import json
    import subprocess

    probe = make_broker(tmp_path)
    lock = probe.lock_file()
    probe.close()
    done = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"],
                          capture_output=True, text=True, check=True)  # fmt: skip
    stale = json.dumps({"pid": int(done.stdout)})
    lock.write_text(stale, encoding="utf-8")  # the crashed process's lock
    a = make_broker(tmp_path)  # process A takes it over
    # Process B read the lock a moment earlier (still the dead PID), then renames "it" aside:
    # by now the file is A's live lock.
    real = nt._read
    monkeypatch.setattr(nt, "_read", lambda p: stale if Path(p) == lock else real(p))
    with pytest.raises(nt.InstanceLocked):
        make_broker(tmp_path)  # today: B succeeds, A's lock is renamed to .dead<pid>
    a.close()


def _bars_file(path, d, closes):
    lines = [nt.BAR_HEADER] + [f"{d},{m},{c},{c},{c},{c},10" for m, c in closes]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _early_day_closes():
    # 2025-11-28 is an early close (calendar: close 12:15, exit 12:12). Closes rise by one
    # point a minute from 08:30, so 12:12 -> 222 + 100, 12:14 -> 224 + 100 points.
    out, minute = [], datetime(2025, 11, 28, 8, 30)
    while minute.time() <= t("12:14"):
        out.append(
            (f"{minute:%H:%M}", 100 + (minute - datetime(2025, 11, 28, 8, 30)).seconds // 60)
        )
        minute += timedelta(minutes=1)
    return out


def test_N3_live_prev_close_after_an_early_close_matches_the_backtest(tmp_path):
    live_nt = _live_nt()
    inst = "MNQ 12-25"
    closes = _early_day_closes()
    _bars_file(nt.bar_file(tmp_path, inst, date(2025, 11, 28)), date(2025, 11, 28), closes)
    ctx = live_nt.history_context(tmp_path, inst, date(2025, 12, 1), False)
    # futures/bars._sessions: last bar before 12:15 of the whole day (not capped at 12:12)
    assert ctx.prev_close == closes[-1][1] * 4  # 12:14; today the 12:12 close (8 ticks lower)


def test_N4_forward_log_prev_close_after_an_early_close_matches_the_backtest():
    import pandas as pd

    spec = importlib.util.spec_from_file_location(
        "forward_log", PROJECT_ROOT / "scripts" / "forward_log.py"
    )
    fl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fl)
    closes = _early_day_closes()
    idx = [pd.Timestamp(f"2025-11-28 {m}", tz="America/Chicago") for m, _ in closes]
    idx += [pd.Timestamp("2025-12-01 08:30", tz="America/Chicago")]
    px = [float(c) for _, c in closes] + [500.0]
    df = pd.DataFrame({"Open": px, "High": px, "Low": px, "Close": px, "Volume": 10}, index=idx)
    (early, _), (nxt, _) = fl.build_days(df)
    assert early.trade_date == date(2025, 11, 28) and nxt.trade_date == date(2025, 12, 1)
    assert nxt.prev_close == closes[-1][1] * 4  # 12:14 bar; today the 11:59 bar


def test_N2_a_refused_second_start_leaves_the_live_journal_alone(tmp_path, monkeypatch):
    live_nt = _live_nt()
    nt_dir = tmp_path / "NinjaTrader 8"
    day_ = date(2026, 10, 30)
    first = nt.NinjaTraderBroker("Sim101", "MNQ 12-26", day_, nt_dir=nt_dir)  # running session
    journal = tmp_path / "2026-10-30_sim-Sim101.jsonl"  # live_nt's default name for both
    journal.write_text('{"kind": "startup"}\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["live_nt.py", "--instrument", "MNQ 12-26", "--sim",
                                      "Sim101", "--date", "2026-10-30", "--nt-dir", str(nt_dir),
                                      "--journal", str(journal)])  # fmt: skip
    with pytest.raises(SystemExit, match="not starting"):
        live_nt.main()
    first.close()
    assert '"halt"' not in journal.read_text(encoding="utf-8")  # today: halt broker_state
