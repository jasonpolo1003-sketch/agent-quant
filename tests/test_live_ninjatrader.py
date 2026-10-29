"""NinjaTraderBroker against a fake NT8 folder: Sim-only guard, OIF lines, atomic writes,
fills, restart reconciliation, safe halts on missing or stale state, the bar CSV reader, and
practice days replayed through the broker + fake NT8 (round trips == backtest legs).

FakeNT8 does what the help guide says NT8 does: it consumes oif*.txt from `incoming`, writes
"<orderId>.txt" ("State;Filled;AvgPrice") and "<instrument> Globex_<account>_Position.txt"
("LONG; 1; 21000.25") into `outgoing`, and a restart clears `outgoing`. Market orders fill at
the open of the next bar it is shown (the FakeBroker / backtest fill). No NT8 needed.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from futures_day_builder import make_day, t

from quant_brain.config import PROJECT_ROOT
from quant_brain.live import ninjatrader as nt
from quant_brain.live.broker import FakeBroker
from quant_brain.live.calendar import sessions
from quant_brain.live.engine import Bar, SigmaHistory, bars_of, context_of
from quant_brain.live.ninjatrader import (
    BROKER_HALT,
    STALE_HALT,
    BarFileTail,
    BrokerStateError,
    GuardedRunner,
    NinjaTraderBroker,
    OneDriveFolder,
    SimOnly,
    write_oif,
)
from quant_brain.live.runner import RiskConfig
from quant_brain.workbench.noise import NoiseArea

INSTRUMENT = "MNQ 06-24"
DAY = date(2020, 1, 2)
SIGMA = {h * 60 + m: 0.02 for h in range(9, 15) for m in (0, 30)}
BREAKOUT = {"08:59": (105, 108, 105, 108)}
REVERSE = {**BREAKOUT, "10:29": (108, 108, 102, 102)}
OFF = RiskConfig(max_position=1, daily_loss_stop_cents=10**12, stale_seconds=1e9, kill_file=None)


class FakeNT8:
    def __init__(self, root: Path, account="Sim101", instrument=INSTRUMENT):
        self.incoming, self.outgoing = root / "incoming", root / "outgoing"
        self.incoming.mkdir(parents=True, exist_ok=True)
        self.outgoing.mkdir(parents=True, exist_ok=True)
        self.account, self.instrument = account, instrument
        self.position, self.avg = 0, 0.0
        self.working: dict[str, int] = {}
        self.lines: list[str] = []
        self.running = True

    def _state(self, oid, text):
        (self.outgoing / f"{oid}.txt").write_text(text, encoding="utf-8")

    def _position_file(self):
        side = "FLAT" if self.position == 0 else ("LONG" if self.position > 0 else "SHORT")
        name = f"{self.instrument} Globex_{self.account}_Position.txt"
        (self.outgoing / name).write_text(
            f"{side}; {abs(self.position)}; {self.avg}", encoding="utf-8"
        )

    def consume(self):
        if not self.running:
            return
        for path in sorted(self.incoming.glob("oif*.txt")):
            for line in path.read_text(encoding="ascii").splitlines():
                self.lines.append(line)
                f = line.split(";")
                assert len(f) == 13, line
                if f[0] == "PLACE":
                    assert f[1].startswith("Sim") and f[2] == self.instrument
                    assert f[5] == "MARKET" and f[8] == "DAY" and f[10]
                    self.working[f[10]] = int(f[4]) * (1 if f[3] == "BUY" else -1)
                    self._state(f[10], "Working;0;0")
                elif f[0] == "CANCEL" and f[10] in self.working:
                    del self.working[f[10]]
                    self._state(f[10], "Cancelled;0;0")
            path.unlink()

    def fill(self, ticks: int):
        price = ticks * 0.25
        for oid, qty in list(self.working.items()):
            new = self.position + qty
            if self.position == 0 or (new != 0 and (new > 0) != (self.position > 0)):
                self.avg = price
            elif abs(new) > abs(self.position):
                self.avg = (self.avg * abs(self.position) + price * abs(qty)) / abs(new)
            self.position = new
            if new == 0:
                self.avg = 0.0
            self._state(oid, f"Filled;{abs(qty)};{price}")
            del self.working[oid]
            self._position_file()

    def step(self, bar: Bar):
        self.consume()
        self.fill(bar.open)

    def restart(self):
        for p in self.outgoing.iterdir():
            p.unlink()
        self.working.clear()

    def places(self):
        return [x.split(";")[10] for x in self.lines if x.startswith("PLACE;")]


class Clock:
    def __init__(self, at=datetime(2020, 1, 2, 8, 0)):
        self.at = at

    def __call__(self):
        return self.at


def make_broker(folder: Path, clock=None, **kw):
    return NinjaTraderBroker(
        "Sim101",
        INSTRUMENT,
        kw.pop("trade_date", DAY),
        incoming=folder / "incoming",
        outgoing=folder / "outgoing",
        state_dir=folder / "state",
        clock=clock or datetime.now,
        **kw,
    )


def day(bars):
    d = make_day(bars, root="MNQ")
    return dataclasses.replace(d, prev_close=105, volumes={m: 1 for m in d.bars})


def trips(broker):
    return [
        (x.side, x.entry_at.time(), x.entry, x.exit_at.time(), x.exit) for x in broker.round_trips
    ]


def run_day(d, root, sigma=SIGMA, risk=OFF, bars=None, runner=None, broker=None, fake=None):
    fake = fake or FakeNT8(root)
    clock = Clock()
    broker = broker or make_broker(root, clock, root=d.root)
    runner = runner or GuardedRunner(
        context_of(d, sigma), broker, risk, now=datetime.combine(d.trade_date, datetime.min.time())
    )
    for b in bars if bars is not None else bars_of(d):
        end = datetime.combine(d.trade_date, b.minute) + timedelta(minutes=1)
        clock.at = end + timedelta(seconds=0.5)
        fake.step(b)
        runner.on_bar(b, clock.at)
    return runner, broker, fake


def kinds(r, kind):
    return [x for x in r.records if x["kind"] == kind]


# --- the guard -----------------------------------------------------------------------------


def test_sim_only_guard_has_no_override(tmp_path):
    for bad in ("Live1", "sim101", "SIM101", "", " Sim101", "Apex-1234", None, 101):
        with pytest.raises(SimOnly):
            NinjaTraderBroker(bad, INSTRUMENT, DAY, nt_dir=tmp_path)
        with pytest.raises(SimOnly):
            nt.place_market_line(bad, INSTRUMENT, 1, "X")
    params = set(inspect.signature(NinjaTraderBroker).parameters)
    assert not {p for p in params if any(w in p for w in ("live", "real", "override", "force"))}
    with pytest.raises(SimOnly):  # a hand-built line for a real account is refused at write time
        write_oif(tmp_path, "oif_x.txt", ["PLACE;Live1;MNQ 06-24;BUY;1;MARKET;0;0;DAY;;X;;"])
    with pytest.raises(SimOnly):
        write_oif(tmp_path, "oif_y.txt", ["CLOSEPOSITION;Real;MNQ 06-24;;;;;;;;;;"])
    assert list(tmp_path.glob("oif*")) == []
    assert make_broker(tmp_path).account == "Sim101"


def test_onedrive_folder_is_refused_and_nt_dir_is_configurable(tmp_path):
    od = tmp_path / "OneDrive" / "Documents" / "NinjaTrader 8"
    with pytest.raises(OneDriveFolder):
        NinjaTraderBroker("Sim101", INSTRUMENT, DAY, nt_dir=od, state_dir=tmp_path / "s")
    b = NinjaTraderBroker(
        "Sim101", INSTRUMENT, DAY, nt_dir=od, state_dir=tmp_path / "s", allow_onedrive=True
    )
    assert b.incoming == od / "incoming" and b.outgoing == od / "outgoing"
    local = tmp_path / "D" / "NinjaTrader 8"
    assert NinjaTraderBroker("Sim101", INSTRUMENT, DAY, nt_dir=local).incoming == local / "incoming"
    home = tmp_path / "home"
    assert nt.default_nt_dir(home) == home / "Documents" / "NinjaTrader 8"
    (home / "OneDrive" / "Documents" / "NinjaTrader 8").mkdir(parents=True)
    assert nt.default_nt_dir(home) == home / "OneDrive" / "Documents" / "NinjaTrader 8"
    (home / "Documents" / "NinjaTrader 8").mkdir(parents=True)
    assert nt.default_nt_dir(home) == home / "Documents" / "NinjaTrader 8"


# --- OIF lines and files -------------------------------------------------------------------


def test_oif_lines_follow_the_13_field_templates():
    assert (
        nt.place_market_line("Sim101", "MNQ 12-26", 1, "QB20261030N0001")
        == "PLACE;Sim101;MNQ 12-26;BUY;1;MARKET;0;0;DAY;;QB20261030N0001;;"
    )
    assert (
        nt.place_market_line("Sim101", "MNQ 12-26", -2, "Q2")
        == "PLACE;Sim101;MNQ 12-26;SELL;2;MARKET;0;0;DAY;;Q2;;"
    )
    assert nt.cancel_line("Q2") == "CANCEL;;;;;;;;;;Q2;;"
    assert (
        nt.close_position_line("Sim101", "MNQ 12-26") == "CLOSEPOSITION;Sim101;MNQ 12-26;;;;;;;;;;"
    )
    assert nt.cancel_all_orders_line() == "CANCELALLORDERS;;;;;;;;;;;;"
    assert nt.flatten_everything_line() == "FLATTENEVERYTHING;;;;;;;;;;;;"
    for line in (nt.cancel_line("a"), nt.flatten_everything_line()):
        assert len(line.split(";")) == nt.OIF_FIELDS
    with pytest.raises(ValueError):
        nt.place_market_line("Sim101", "MNQ;12-26", 1, "x")
    with pytest.raises(ValueError):
        nt.place_market_line("Sim101", "MNQ 12-26", 0, "x")
    assert nt.order_id_for(date(2026, 10, 30), 7) == "QB20261030N0007"


def test_oif_write_is_atomic_and_never_overwrites(tmp_path, monkeypatch):
    incoming, tmp = tmp_path / "incoming", tmp_path / "tmp"
    seen = {}
    real = os.rename

    def spy(src, dst):
        seen["incoming"] = sorted(p.name for p in incoming.iterdir())
        seen["src"] = Path(src)
        seen["tmp_text"] = Path(src).read_bytes()
        real(src, dst)

    monkeypatch.setattr(nt.os, "rename", spy)
    line = nt.place_market_line("Sim101", INSTRUMENT, 1, "A1")
    path = write_oif(incoming, "oif_A1.txt", [line], tmp)
    assert seen["incoming"] == []  # the temp file is written outside incoming (QA-L3)
    assert seen["src"].parent == tmp and not seen["src"].name.endswith(".txt")
    assert seen["tmp_text"] == (line + "\r\n").encode("ascii")
    assert sorted(p.name for p in incoming.iterdir()) == ["oif_A1.txt"]
    assert list(tmp.iterdir()) == []
    with pytest.raises(FileExistsError):
        write_oif(incoming, "oif_A1.txt", [line], tmp)
    assert path.read_bytes() == (line + "\r\n").encode("ascii")  # the original, untouched
    with pytest.raises(ValueError):
        write_oif(incoming, "order.txt", [line], tmp)
    with pytest.raises(ValueError):
        write_oif(incoming, "oif_b.txt", ["PLACE;Sim101"], tmp)
    with pytest.raises(ValueError):
        write_oif(incoming, "oif_c.txt", ["CANCEL;Sim101;;;;;;;;;X;;"], tmp)  # account on CANCEL
    assert sorted(p.name for p in incoming.iterdir()) == ["oif_A1.txt"]


def test_outgoing_parsers():
    assert nt.parse_order_state("Filled;2;21000.25\r\n") == ("FILLED", 2, 21000.25)
    assert nt.parse_order_state("PartFilled;1;5.5")[0] == nt.PART_FILLED
    assert nt.parse_order_state("Partially filled;1;5.5")[0] == nt.PART_FILLED
    assert nt.parse_order_state("") is None and nt.parse_order_state("Filled;x;1") is None
    assert nt.parse_position("LONG; 2; 21000.25") == (2, 21000.25)
    assert nt.parse_position("SHORT; 1; 21000,5") == (-1, 21000.5)
    assert nt.parse_position("FLAT; 0; 0") == (0, 0.0)
    assert nt.parse_position("SIDEWAYS; 1; 0") is None


# --- fills ---------------------------------------------------------------------------------


def test_fills_positions_and_pnl_through_the_fake_nt8(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path, fee_cents_per_side=37)
    t0 = datetime(2020, 1, 2, 9, 0)
    oid = b.place_market_order(1, t0, "long")
    assert oid == "QB20200102N0001" and b.position() == 0 and b.working() == 1
    fake.consume()
    assert b.working() == 1  # Working;0;0
    fake.fill(84000)
    (filled,) = b.on_bar(Bar(t("09:00"), 84000, 84000, 84000, 84000), t0)
    assert filled.order_id == oid and filled.fill_price == 84000 and filled.filled_at == t0
    assert b.position() == 1 and b.working() == 0
    assert b.day_pnl_cents(84004) == 4 * 50 - 37
    b.place_market_order(-2, t0, "reverse")
    fake.step(Bar(t("10:30"), 84010, 84010, 84010, 84010))
    b.on_bar(None, datetime(2020, 1, 2, 10, 30))
    assert b.position() == -1 and b.realized_cents == 500 and b.fees_cents == 3 * 37
    assert [(r.side, r.entry, r.exit) for r in b.round_trips] == [(1, 84000, 84010)]
    assert fake.places() == ["QB20200102N0001", "QB20200102N0002"]
    events = [x["event"] for x in b._ledger() if x["event"] in ("sent", "fill")]
    assert events == ["sent", "fill", "sent", "fill"]


def test_cancel_and_close_position_use_only_this_account(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    oid = b.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    fake.consume()
    b.cancel_all()
    fake.consume()
    assert fake.lines[-1] == f"CANCEL;;;;;;;;;;{oid};;" and b.working() == 0
    b.close_position()
    lines = [p.read_text(encoding="ascii").strip() for p in fake.incoming.glob("oif*.txt")]
    assert lines == ["CLOSEPOSITION;Sim101;MNQ 06-24;;;;;;;;;;"]
    assert not any(x.startswith(("FLATTENEVERYTHING", "CANCELALLORDERS")) for x in fake.lines)


# --- restarts and stale state --------------------------------------------------------------


def test_restart_mid_session_reconciles_and_never_duplicates(tmp_path):
    d = day(REVERSE)
    bars = bars_of(d)
    split = next(i for i, b in enumerate(bars) if b.minute == t("10:00"))
    whole, _, ref_fake = run_day(d, tmp_path / "ref")
    ref = trips(whole.broker)

    root = tmp_path / "live"
    r1, b1, fake = run_day(d, root, bars=bars[:split])
    assert b1.position() == 1 and fake.places() == ["QB20200102N0001"]
    r1.close()  # the process dies here; NT8 keeps running

    b2 = make_broker(root)
    rec = b2.reconciliation
    assert rec["position"] == 1 and rec["ledger_position"] == 1 and rec["pnl_exact"]
    assert rec["next_order_id"] == "QB20200102N0002"
    r2 = GuardedRunner(context_of(d, SIGMA), b2, OFF, now=datetime(2020, 1, 2, 10, 0, 30))
    nt.warm_up(r2, bars[:split], datetime(2020, 1, 2, 10, 0, 30))
    assert r2.engine.side == 1 and not kinds(r2, "order")  # engine long, broker long: no order
    run_day(d, root, bars=bars[split:], runner=r2, broker=b2, fake=fake)
    r2.end_session(datetime(2020, 1, 2, 16))
    ids = fake.places()
    assert len(ids) == len(set(ids)) == len(ref_fake.places()) == 3
    assert trips(b2) == ref  # lots rebuilt from the ledger, so the reversal books the old long
    assert b2.position() == 0 and r2.halted is None


def test_restart_when_the_engine_is_flat_only_reduces(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    b.place_market_order(1, datetime(2020, 1, 2, 9), "stray")
    fake.step(Bar(t("09:00"), 100, 100, 100, 100))
    b.on_bar(None, datetime(2020, 1, 2, 9))
    d = day({})  # no breakout: the engine stays flat
    b.close()  # the first process is gone
    b2 = make_broker(tmp_path)
    r = GuardedRunner(context_of(d, SIGMA), b2, OFF, now=datetime(2020, 1, 2, 9, 40))
    nt.warm_up(r, bars_of(d)[:60], datetime(2020, 1, 2, 9, 40))
    (order,) = kinds(r, "order")
    assert order["quantity"] == -1 and order["reason"] == "restart_reconcile"


def test_outgoing_cleared_by_an_nt8_restart_refuses_to_start(tmp_path):
    _, b, fake = run_day(day(BREAKOUT), tmp_path, bars=bars_of(day(BREAKOUT))[:40])
    assert b.position() == 1
    b.close()
    fake.restart()  # NT8 restarted: outgoing is empty, the ledger still has the fill
    before = sorted(p.name for p in fake.incoming.iterdir())
    with pytest.raises(BrokerStateError, match="no order state"):
        make_broker(tmp_path)
    assert sorted(p.name for p in fake.incoming.iterdir()) == before  # nothing sent


def test_unconsumed_oif_at_startup_refuses_to_start(tmp_path):
    fake = FakeNT8(tmp_path)
    fake.running = False
    first = make_broker(tmp_path)
    first.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    first.close()
    with pytest.raises(BrokerStateError, match="never processed"):
        make_broker(tmp_path)
    # the unconsumed OIF was moved to quarantine, so it can never fire; its order is known
    # never executed, so the next start is clean and does not reuse its ID
    assert list(fake.incoming.glob("oif*.txt")) == []
    assert len(list((tmp_path / "state" / nt.QUARANTINE).iterdir())) == 1
    again = make_broker(tmp_path)
    assert again.reconciliation["next_order_id"] == "QB20200102N0002"
    assert again.position() == 0


def test_stale_order_state_halts_the_runner_without_resending(tmp_path):
    d = day(BREAKOUT)
    fake = FakeNT8(tmp_path)
    fake.running = False  # NT8 closed or ATI off: OIFs are never consumed
    clock = Clock()
    broker = make_broker(tmp_path, clock, ack_seconds=5)
    r = GuardedRunner(context_of(d, SIGMA), broker, OFF, now=datetime(2020, 1, 2, 8))
    for b in bars_of(d):
        clock.at = datetime.combine(DAY, b.minute) + timedelta(minutes=1, seconds=0.5)
        fake.step(b)
        r.on_bar(b, clock.at)
    end = r.end_session(datetime(2020, 1, 2, 16))
    (halt,) = kinds(r, "halt")
    assert halt["reason"] == BROKER_HALT and "OIF not consumed" in halt["error"]
    assert r.halted == BROKER_HALT and len(kinds(r, "order")) == 1
    assert list(fake.incoming.glob("oif*.txt")) == []  # disarmed: moved to quarantine
    assert len(list((tmp_path / "state" / nt.QUARANTINE).iterdir())) == 1
    assert kinds(r, "quarantine")[0]["armed"] == ["oif_QB20200102N0001.txt"]
    assert end["broker_position"] == 0 and end["broker_working"] == 0  # quarantined
    assert end["halted"] == BROKER_HALT


def test_position_file_disagreeing_too_long_halts(tmp_path):
    d = day(BREAKOUT)
    fake = FakeNT8(tmp_path)
    clock = Clock()
    broker = make_broker(tmp_path, clock, mismatch_seconds=5)
    r = GuardedRunner(context_of(d, SIGMA), broker, OFF, now=datetime(2020, 1, 2, 8))
    for b in bars_of(d):
        clock.at = datetime.combine(DAY, b.minute) + timedelta(minutes=1, seconds=0.5)
        fake.step(b)
        if b.minute == t("09:30"):
            fake.position = 3  # someone trades the account by hand
            fake._position_file()
        r.on_bar(b, clock.at)
    (halt,) = kinds(r, "halt")
    assert halt["reason"] == BROKER_HALT and "NT8 position 3" in halt["error"]
    assert len(fake.places()) == 1


def test_rejected_order_halts(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    oid = b.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    fake.consume()
    fake._state(oid, "Rejected;0;0")
    with pytest.raises(BrokerStateError, match="rejected"):
        b.position()


def test_delayed_feed_halts_and_flattens():
    d = day({**BREAKOUT, "10:10": (108, 120, 108, 120)})
    broker = FakeBroker("MNQ")
    r = GuardedRunner(context_of(d, SIGMA), broker, RiskConfig(kill_file=None), now=day_t(8, 0))
    for b in bars_of(d):
        late = 120 if b.minute >= t("10:00") else 0.5  # the feed falls 2 minutes behind
        r.on_bar(b, datetime.combine(DAY, b.minute) + timedelta(minutes=1, seconds=late))
        if r.halted:
            break
    (halt,) = kinds(r, "halt")
    assert halt["reason"] == STALE_HALT and halt["source"] == "bar"
    assert b.minute == t("10:02")  # the third late bar in a row
    assert [o["reason"] for o in kinds(r, "order")] == ["long", STALE_HALT]
    assert broker.position() + broker.working() == 0
    # no bar at all for 2 x halt_lag: the heartbeat halts too
    r = GuardedRunner(context_of(d, SIGMA), FakeBroker(), RiskConfig(kill_file=None), now=day_t(8))
    r.on_bar(bars_of(d)[0], day_t(8, 31, 0.2))
    r.on_clock(day_t(8, 33, 1))  # one quiet minute: no halt
    assert r.halted is None
    r.on_clock(day_t(8, 34, 1))
    assert r.halted == STALE_HALT and kinds(r, "halt")[0]["source"] == "heartbeat"


def test_one_late_bar_is_not_a_halt_and_overnight_never_counts():
    d = day(BREAKOUT)
    r = GuardedRunner(context_of(d, SIGMA), FakeBroker(), RiskConfig(kill_file=None), now=day_t(2))
    for minute in range(30):  # overnight bars written 5 minutes late: outside the watch window
        b = Bar(_m(3, minute), 1, 1, 1, 1)
        r.on_bar(b, datetime.combine(DAY, b.minute) + timedelta(minutes=6))
    r.on_clock(day_t(5, 0))
    assert r.halted is None
    r = GuardedRunner(context_of(d, SIGMA), FakeBroker(), RiskConfig(kill_file=None), now=day_t(8))
    bars = bars_of(d)
    for b in bars[:40]:
        lag = 65 if b.minute in (t("08:40"), t("08:50")) else 0.5  # two isolated quiet minutes
        r.on_bar(b, datetime.combine(DAY, b.minute) + timedelta(minutes=1, seconds=lag))
    assert r.halted is None and kinds(r, "order")


def _m(h, m):
    return (datetime(2020, 1, 2, h, 0) + timedelta(minutes=m)).time()


def day_t(h, m=0, s=0.0):
    return datetime(2020, 1, 2, h, m) + timedelta(seconds=s)


# --- single instance, persisted halts, send failures ---------------------------------------


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


def test_one_process_per_account_through_an_os_lock(tmp_path):
    first = make_broker(tmp_path)
    with pytest.raises(nt.InstanceLocked, match="only one live_nt"):
        make_broker(tmp_path)  # a second handle, even in the same process
    lock = first.lock_file()
    assert json.loads(lock.read_text(encoding="utf-8"))["pid"] == os.getpid()
    first.close()
    make_broker(tmp_path).close()  # released: the next start runs
    lock.write_text("garbage, or a dead PID", encoding="utf-8")  # the file is not the lock
    make_broker(tmp_path).close()
    child = _hold_lock_in_child(lock)  # another process really holds it
    try:
        with pytest.raises(nt.InstanceLocked, match=f"process {child.pid}"):
            make_broker(tmp_path)
    finally:
        child.kill()
        child.wait()
    make_broker(tmp_path).close()  # the OS dropped it with the process


def test_a_halt_survives_a_restart(tmp_path):
    d = day(BREAKOUT)
    root = tmp_path
    r1, b1, fake = run_day(d, root, bars=bars_of(d)[:40])
    assert b1.position() == 1
    r1._halt(day_t(9, 10), "kill_switch")  # flattens and is written to the ledger
    fake.step(bars_of(d)[40])
    b1.on_bar(None, day_t(9, 11))
    assert b1.position() == 0
    r1.close()
    b2 = make_broker(root)
    assert b2.prior_halt == "kill_switch"
    r2 = GuardedRunner(context_of(d, SIGMA), b2, OFF, now=day_t(9, 30))
    assert r2.halted == "kill_switch" and kinds(r2, "halt_restored")
    nt.warm_up(r2, bars_of(d)[:60], day_t(9, 30))
    assert not kinds(r2, "order")  # halted: the engine's long is never re-entered
    r2.close()


def test_clear_halt_appends_an_entry_and_guards_broker_state(tmp_path):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)
    b.persist_halt("kill_switch")
    b.close()
    b = make_broker(tmp_path)
    with pytest.raises(ValueError):
        b.clear_halt("  ")
    assert b.clear_halt("STOP file removed") == "kill_switch" and b.prior_halt is None
    b.close()
    b = make_broker(tmp_path)
    assert b.prior_halt is None
    events = [e["event"] for e in b._ledger()]
    assert events == ["halt", "halt_cleared"]  # nothing deleted
    with pytest.raises(ValueError, match="no halt"):
        b.clear_halt("again")
    b.persist_halt(BROKER_HALT)
    b.close()
    fake.position = 1
    fake._position_file()
    b = make_broker(tmp_path, mismatch_seconds=1e9)
    with pytest.raises(BrokerStateError, match="FLAT"):
        b.clear_halt("fixed it")
    fake.position = 0  # flattened by hand in NT8
    fake._position_file()
    assert b.clear_halt("flattened by hand") == BROKER_HALT
    b.close()


def test_live_nt_clear_halt_cli(monkeypatch, tmp_path, capsys):
    live_nt = _live_nt()
    nt_dir = tmp_path / "NinjaTrader 8"
    b = NinjaTraderBroker("Sim101", "MNQ 12-26", date(2026, 10, 30), nt_dir=nt_dir)
    b.persist_halt("stale_data")
    b.close()
    base = ["live_nt.py", "--instrument", "MNQ 12-26", "--date", "2026-10-30",
            "--nt-dir", str(nt_dir), "--journal", str(tmp_path / "j.jsonl")]  # fmt: skip
    monkeypatch.setattr(sys, "argv", [*base, "--clear-halt", "feed glitch"])
    with pytest.raises(SystemExit, match="needs --sim"):
        live_nt.main()
    monkeypatch.setattr(sys, "argv", [*base, "--sim", "Sim101", "--clear-halt", "feed glitch"])
    assert live_nt.main() == 0
    assert "cleared today's stale_data halt" in capsys.readouterr().out
    assert not (tmp_path / "j.jsonl").exists()  # no session ran
    again = NinjaTraderBroker("Sim101", "MNQ 12-26", date(2026, 10, 30), nt_dir=nt_dir)
    assert again.prior_halt is None
    again.close()


def test_a_failed_send_halts_and_a_restart_recovers(tmp_path, monkeypatch):
    fake = FakeNT8(tmp_path)
    b = make_broker(tmp_path)

    def locked(src, dst):
        raise PermissionError(13, "locked", str(src))

    monkeypatch.setattr(nt.os, "rename", locked)
    with pytest.raises(BrokerStateError, match="NOT sent"):
        b.place_market_order(1, datetime(2020, 1, 2, 9), "long")
    monkeypatch.undo()
    assert list(fake.incoming.iterdir()) == [] and b.working() == 0
    b.close()
    again = make_broker(tmp_path)  # send_failed is known: not an unknown order
    assert again.reconciliation["next_order_id"] == "QB20200102N0002"


def test_live_nt_refuses_dates_outside_the_calendar(monkeypatch, tmp_path):
    live_nt = _live_nt()
    for when in ("2026-11-26", "2028-01-03", "2026-10-31"):  # Thanksgiving, past the end, Sat
        argv = ["live_nt.py", "--instrument", "MNQ 12-26", "--date", when, "--nt-dir",
                str(tmp_path), "--journal", str(tmp_path / "j.jsonl")]  # fmt: skip
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit, match="not an NYSE session"):
            live_nt.main()
    cal = sessions()
    assert cal[date(2026, 11, 27)].early_close and cal[date(2026, 12, 24)].early_close
    assert date(2026, 12, 25) not in cal and date(2027, 7, 5) not in cal
    assert cal[date(2027, 11, 26)].early_close and max(cal) == date(2027, 12, 31)


def _live_nt():
    spec = importlib.util.spec_from_file_location(
        "live_nt", PROJECT_ROOT / "scripts" / "live_nt.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- bar CSV -------------------------------------------------------------------------------


def test_bar_tail_reads_whole_lines_and_skips_bad_ones(tmp_path):
    path = nt.bar_file(tmp_path, "MNQ 12-26", date(2026, 10, 30))
    assert path.name == "MNQ 12-26_2026-10-30.csv"
    tail = BarFileTail(path, date(2026, 10, 30))
    assert tail.poll() == []  # no file yet
    with path.open("w", encoding="utf-8", newline="") as h:
        h.write(nt.BAR_HEADER + "\n")
        h.write("2026-10-30,08:30,21000.25,21001,20999.5,21000,812\n")
        h.write("2026-10-30,08:31,21000,21002.75,20999")  # partial line
    (b,) = tail.poll()
    assert b == Bar(t("08:30"), 84001, 84004, 83998, 84000, 812)
    with path.open("a", encoding="utf-8", newline="") as h:
        h.write(",21002,40\r\n")  # the rest of 08:31
        h.write("2026-10-30,08:31,1,1,1,1,1\n")  # duplicate (chart reload)
        h.write("2026-10-30,08:29,1,1,1,1,1\n")  # out of order
        h.write("garbage\n2026-10-30,08:32,5,4,6,5,1\n")  # malformed; high < low
        h.write("2026-10-29,15:00,1,1,1,1,1\n")  # other date
        h.write("2026-10-30,08:33,21003,21003,21003,21003,0\n")
    got = tail.poll()
    assert [x.minute for x in got] == [t("08:31"), t("08:33")]
    assert got[0] == Bar(t("08:31"), 84000, 84011, 83996, 84008, 40) and got[1].volume == 0
    assert tail.skipped == {"duplicate": 2, "malformed": 2, "other_date": 1}
    bars, vols = nt.read_session(path, date(2026, 10, 30))
    assert sorted(bars) == [t("08:30"), t("08:31"), t("08:33")] and vols[t("08:30")] == 812
    assert nt.regular_close(bars, t("08:33")) == 84008


# --- practice days through broker + fake NT8 -----------------------------------------------


def _workbench():
    spec = importlib.util.spec_from_file_location("wb", PROJECT_ROOT / "scripts" / "workbench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WB = _workbench()


@pytest.mark.skipif(not WB.DEV_DIR.exists(), reason="dev partition not on this machine")
def test_practice_days_replay_through_ninjatrader_broker_matches_backtest(tmp_path):
    days = WB.dev_loader(WB.DEV_DIR)("MNQ", date(2024, 2, 1), date(2024, 3, 15), "volume_roll_date")
    prepared = NoiseArea().prepare_all(days)
    history = SigmaHistory("MNQ")
    checked = trades = 0
    for raw, prep in zip(days, prepared, strict=True):
        sigma = history.sigma()
        history.add_session(raw.bars)
        if raw.trade_date < date(2024, 3, 8):
            continue
        batch = NoiseArea().simulate(prep)
        want = [
            (x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks)
            for x in batch.trades
        ]
        root = tmp_path / raw.trade_date.isoformat()
        clock = Clock()
        broker = make_broker(root, clock, trade_date=raw.trade_date)
        runner, broker, fake = run_day(raw, root, sigma=sigma, broker=broker)
        runner.end_session(datetime.combine(raw.trade_date, datetime.min.time()))
        assert runner.halted is None and not kinds(runner, "void")
        assert trips(broker) == want, raw.trade_date
        assert len(fake.places()) == len(set(fake.places())) == len(broker.orders)
        assert broker.position() == 0 and fake.position == 0
        checked += 1
        trades += len(want)
    assert checked == 6 and trades >= 10
