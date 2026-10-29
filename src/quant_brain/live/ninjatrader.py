"""NinjaTrader 8 Sim bridge: ATI order instruction files out, order and position files back.

SIM ACCOUNTS ONLY. Constructing NinjaTraderBroker raises SimOnly unless the account name
starts with "Sim" (Sim101 and the like); there is no override. Every OIF line is checked
again before it is written. FLATTENEVERYTHING and CANCELALLORDERS act on every account and
connection, so the broker never sends them (the line builders exist for the fake NT8 only).

Formats, from NinjaTrader's NT8 help guide (read 2026-10-29):
  https://ninjatrader.com/support/helpGuides/nt8/order_instruction_files_oif.htm
  https://ninjatrader.com/support/helpGuides/nt8/commands_and_valid_parameters.htm
  https://ninjatrader.com/support/helpGuides/nt8/information_update_files.htm
  https://ninjatrader.com/support/helpGuides/nt8/order_state_definitions.htm
  (the server redirects these to static.ninjatrader.com/support/helpGuides/nt8/...)
Incoming. OIFs go in "My Documents\\<NinjaTrader Folder>\\incoming", named oif*.txt; NT8
  processes a file the instant it is written, so write elsewhere and move it in (the guide
  warns that copying files in causes locking problems; it suggests oif1.txt, oif2.txt...).
  One instruction per line, 13 semicolon-separated fields (<> required, [] optional):
    PLACE;<ACCOUNT>;<INSTRUMENT>;<ACTION>;<QTY>;<ORDER TYPE>;[LIMIT PRICE];[STOP PRICE];<TIF>;
          [OCO ID];[ORDER ID];[STRATEGY];[STRATEGY ID]
    CANCEL;;;;;;;;;;<ORDER ID>;;[STRATEGY ID]
    CLOSEPOSITION;<ACCOUNT>;<INSTRUMENT>;;;;;;;;;;
    CANCELALLORDERS;;;;;;;;;;;;        FLATTENEVERYTHING;;;;;;;;;;;;
  ACTION BUY | SELL; ORDER TYPE MARKET | LIMIT | STOPMARKET | STOPLIMIT; TIF DAY | GTC;
  decimal prices use a period; order IDs must be unique.
Outgoing. "My Documents\\<NinjaTrader Folder>\\outgoing", deleted when NT8 restarts:
  <orderId>.txt, one per order placed with an ORDER ID, rewritten on every state change:
      "Order State;Filled Amount;Average FillPrice"
  <Instrument Name> <Exchange>_<AccountName>_Position.txt (example "ES 0914
      Globex_Sim101_Position.txt"), rewritten on every position update:
      "Market Position; Quantity; Average Entry Price", position LONG | SHORT | FLAT.
  Order states (definitions page): Initialized, Submitted, Accepted, Working, Suspended,
  Change submitted, Cancel pending, Cancelled, Rejected, Partially filled, Filled, Trigger
  pending.

NOT CONFIRMED by the help pages (each is one constant below, easy to change):
- MARKET_PRICE: what to put in the price fields of a MARKET order. The guide marks them
  optional; "0" follows the NinjaTrader forum example "PLACE;Sim101;NQ 03-24;BUY;1;MARKET;
  0;0;DAY;;;;".
- EXCHANGE: the exchange part of an NT8 position file name. The guide's example is NT7-era
  ("ES 0914 Globex"); NT8 instruments look like "MNQ 12-26", so "MNQ 12-26 Globex" is
  assumed. The broker also accepts any "<instrument> *_<account>_Position.txt".
- The spelling and case of states in order files: parsed case-blind with spaces dropped,
  so "FILLED", "Filled", "PartFilled" and "Partially filled" all read.
- Whether NT8 deletes an OIF after processing it. The broker never relies on it: an OIF
  still in `incoming` only matters while its order file is missing.
- The contract month (instrument, e.g. "MNQ 12-26") is a parameter; when NT8 rolls to the
  next month is not verified here, so the caller picks it each session.
OneDrive. NinjaTrader support reports that ATI file processing breaks when the NinjaTrader 8
folder is inside a OneDrive-synced Documents folder. The broker refuses such a path unless
`allow_onedrive=True` (scripts/live_nt.py --allow-onedrive); the fix is to move the folder to
a local drive and pass it as `nt_dir`.

Safety model (after the QA review brain/05_Reviews/nt8-bridge-QA-2026-10-29.md).
- One process per (account, instrument, date): an O_CREAT|O_EXCL lock file with the PID in
  state_dir. A second process refuses to start; a lock whose PID Windows confirms is gone is
  renamed aside and taken over; anything unclear refuses with a message (InstanceLocked).
- Order IDs are "<prefix><yyyymmdd>N<seq>", unique and deterministic per (date, sequence).
  Each send goes to a ledger (state_dir, JSONL) before its OIF is written to state_dir/tmp
  and renamed into `incoming` (never overwriting). write_oif allows only PLACE, CANCEL and
  CLOSEPOSITION, in exact case, PLACE / CLOSEPOSITION only for a "Sim" account. A failed write
  is logged as send_failed (known not sent) and raised as BrokerStateError.
- Startup: every oif*.txt left in `incoming` (any date, any name) is moved to
  state_dir/quarantine first; if any was never processed by NT8 the broker refuses to start
  (so it cannot fire later) and the next start is clean. Then it reconciles: next sequence =
  1 + the highest seen in the ledger, outgoing, incoming and quarantine; fills NT8 made that
  the ledger never booked are booked from the order files; today's realized P&L is rebuilt
  from the ledger (and never starts better than the last day P&L logged); the position comes
  from the NT8 position file; the last halt of the day is restored (prior_halt). Anything it
  cannot account for raises BrokerStateError instead of guessing: an order with no state file
  (NT8 restarted and cleared `outgoing`, or never processed it), an order still in flight, a
  position file missing while the ledger has fills.
- During the session the same error is raised when an order has no state file `ack_seconds`
  after it was sent, when an order is rejected, and when the position file disagrees with the
  broker's own count for longer than `mismatch_seconds`.
- GuardedRunner turns that error into a halt that sends nothing (a blind flatten could double
  an order whose state is unknown), halts and flattens on a delayed feed within the session
  window, quarantines `incoming` on every halt, and records every halt in the ledger.
- A halt stands for the rest of the day, across restarts. To resume after fixing the cause,
  run scripts/live_nt.py --sim <ACCOUNT> --clear-halt "<why>" (no session may be running):
  it appends a halt_cleared ledger entry (nothing is deleted) and refuses a broker_state halt
  unless NT8's position file shows FLAT.
- Single instance: one process per (account, instrument, date) through an OS lock on an
  open handle (ProcessLock), which the OS drops when the process ends; nothing to clean up.

Known limitations. Quarantine can race NT8 (QA N6): a non-broker halt (kill switch, daily
loss stop) in the same bar as a check order runs disarm() milliseconds after that order's OIF
was written. If NT8 has already read the file but not yet written its order state, the move
can succeed, the order is marked QUARANTINED, and NT8 still executes it; the position check
then halts on the mismatch and leaves that position open for a manual flatten. The window
depends on NT8's ATI latency, which is not verified. Also open from the QA review: no check
of the PC clock against NT8's (L4); the exporter is uncompiled (L5); a crash between the
ledger write and the OIF rename still blocks restarts that day (L8).

Bars. ninjatrader/QuantBarExporter.cs appends each completed 1-minute bar to
<nt_dir>\\quant_bars\\<instrument>_<yyyy-mm-dd>.csv as "date,time,open,high,low,close,volume"
(bar start, CT). BarFileTail reads whole lines only, skips malformed, duplicate and
out-of-order lines, and yields engine Bars with ticks = round(price / tick_size).
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from quant_brain.futures import orb
from quant_brain.live.broker import OrderRecord, RoundTrip
from quant_brain.live.engine import Bar, ModelFill, Signal, Void
from quant_brain.live.runner import Runner
from quant_brain.workbench.noise import _t

SIM_PREFIX = "Sim"
NT_FOLDER = "NinjaTrader 8"
INCOMING = "incoming"
OUTGOING = "outgoing"
BAR_FOLDER = "quant_bars"
STATE_FOLDER = "quant_brain"
OIF_FIELDS = 13
OIF_GLOB = "oif*.txt"
MARKET_PRICE = "0"  # unconfirmed: price fields of a MARKET order (forum example uses 0)
EXCHANGE = "Globex"  # unconfirmed for NT8 position file names
TIF = "DAY"
BAR_HEADER = "date,time,open,high,low,close,volume"
FILLED, PART_FILLED, CANCELLED, REJECTED = "FILLED", "PARTFILLED", "CANCELLED", "REJECTED"
QUARANTINED, SEND_FAILED = "QUARANTINED", "SENDFAILED"  # the bot's own: never reached NT8
TERMINAL = frozenset({FILLED, CANCELLED, REJECTED, QUARANTINED, SEND_FAILED})
OIF_COMMANDS = ("PLACE", "CANCEL", "CLOSEPOSITION")  # the only commands write_oif lets out
QUARANTINE = "quarantine"


class SimOnly(RuntimeError):
    """Raised for any account whose name does not start with "Sim"."""


class OneDriveFolder(RuntimeError):
    """Raised when the NinjaTrader 8 folder is inside OneDrive (ATI file processing breaks)."""


class BrokerStateError(RuntimeError):
    """NT8's order or position state is missing, stale or inconsistent: do not send orders."""


class InstanceLocked(BrokerStateError):
    """Another process holds this account / instrument / date: refuse to start."""


LOCK_OFFSET = 1 << 20  # the locked byte lies past the PID text, so others can still read it


class ProcessLock:
    """An OS lock on one byte of `path`, held through a handle kept open for the process
    lifetime (msvcrt.locking on Windows, fcntl.flock elsewhere). The OS drops it when the
    process ends, however it ends, so there is no stale lock to judge and no takeover race:
    one handle holds it, every other attempt fails at once. The file only carries the
    holder's PID for messages; it is never deleted."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._fd: int | None = None

    def acquire(self, info: dict) -> bool:
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, json.dumps(info).ljust(255).encode("ascii") + b"\n")
        os.fsync(fd)
        return True

    def holder(self) -> int | None:
        text = _read(self.path)
        try:
            return int(json.loads(text)["pid"]) if text else None
        except (ValueError, KeyError, TypeError):
            return None

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            os.close(fd)  # closing the handle releases the lock in any case


def pid_alive(pid: int) -> bool | None:
    """True / False when the OS says so; None when it cannot tell (treated as alive)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            error = ctypes.get_last_error()
            return False if error == 87 else (True if error == 5 else None)  # 87: no such PID
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def check_sim(account: object) -> str:
    if not isinstance(account, str) or not account.startswith(SIM_PREFIX):
        raise SimOnly(f"NinjaTraderBroker trades Sim accounts only, not {account!r}")
    return account


def under_onedrive(path: Path) -> bool:
    return any(part.lower().startswith("onedrive") for part in Path(path).parts)


def default_nt_dir(home: Path | None = None) -> Path:
    """Documents\\NinjaTrader 8, else OneDrive\\Documents\\NinjaTrader 8 (whichever exists;
    the local one when neither does)."""
    home = Path.home() if home is None else home
    local = home / "Documents" / NT_FOLDER
    for candidate in (local, home / "OneDrive" / "Documents" / NT_FOLDER):
        if candidate.is_dir():
            return candidate
    return local


# --- OIF lines -----------------------------------------------------------------------------


def oif_line(command: str, **fields: str) -> str:
    """One 13-field instruction; `fields` by name: account, instrument, action, qty,
    order_type, limit, stop, tif, oco, order_id, strategy, strategy_id."""
    names = (
        "account instrument action qty order_type limit stop tif oco order_id strategy strategy_id"
    ).split()
    unknown = set(fields) - set(names)
    if unknown:
        raise ValueError(f"unknown OIF fields {sorted(unknown)}")
    values = [command] + [str(fields.get(n, "")) for n in names]
    if any(";" in v or "\n" in v or "\r" in v for v in values):
        raise ValueError("OIF fields may not contain ';' or line breaks")
    return ";".join(values)


def place_market_line(account: str, instrument: str, quantity: int, order_id: str) -> str:
    if quantity == 0:
        raise ValueError("zero-quantity order")
    return oif_line(
        "PLACE",
        account=check_sim(account),
        instrument=instrument,
        action="BUY" if quantity > 0 else "SELL",
        qty=abs(quantity),
        order_type="MARKET",
        limit=MARKET_PRICE,
        stop=MARKET_PRICE,
        tif=TIF,
        order_id=order_id,
    )


def cancel_line(order_id: str) -> str:
    return oif_line("CANCEL", order_id=order_id)


def close_position_line(account: str, instrument: str) -> str:
    return oif_line("CLOSEPOSITION", account=check_sim(account), instrument=instrument)


def cancel_all_orders_line() -> str:  # every account: never sent by the broker
    return oif_line("CANCELALLORDERS")


def flatten_everything_line() -> str:  # every account and connection: never sent
    return oif_line("FLATTENEVERYTHING")


def check_oif_line(line: str) -> None:
    """The last check before a line reaches NT8: 13 fields, an allowed command in exact case,
    and a Sim account (PLACE / CLOSEPOSITION) or no account and an order ID (CANCEL)."""
    fields = line.split(";")
    if len(fields) != OIF_FIELDS:
        raise ValueError(f"OIF line needs {OIF_FIELDS} fields: {line!r}")
    if fields[0] not in OIF_COMMANDS:
        raise ValueError(f"OIF command {fields[0]!r} is not allowed (only {OIF_COMMANDS})")
    if fields[0] == "CANCEL":
        if fields[1] or not fields[10]:
            raise ValueError(f"CANCEL takes only an order ID: {line!r}")
    else:
        check_sim(fields[1])


def write_oif(incoming: Path, name: str, lines: list[str], tmp_dir: Path | None = None) -> Path:
    """Write `lines` to a temp file outside `incoming`, then move it in as `name` in one rename.

    NT8 never sees a half-written file. `tmp_dir` (default <incoming>\\..\\quant_brain\\tmp)
    must be on the same volume. Refuses to replace an existing OIF (IDs are unique; a clash
    means a duplicate send). Every line passes check_oif_line first."""
    if not (name.startswith("oif") and name.endswith(".txt")):
        raise ValueError(f"OIF names must match {OIF_GLOB}: {name}")
    for line in lines:
        check_oif_line(line)
    incoming.mkdir(parents=True, exist_ok=True)
    final = incoming / name
    if final.exists():
        raise FileExistsError(f"{final} already exists: refusing a duplicate send")
    tmp_dir = Path(tmp_dir) if tmp_dir is not None else incoming.parent / STATE_FOLDER / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / f"{name}.part"
    try:
        with tmp.open("w", encoding="ascii", newline="") as handle:
            handle.write("".join(line + "\r\n" for line in lines))
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(tmp, final)  # on Windows rename refuses an existing target
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return final


# --- outgoing files ------------------------------------------------------------------------


def _number(text: str) -> float:
    text = text.strip()
    if "," in text and "." not in text:
        text = text.replace(",", ".")  # unconfirmed: a locale decimal comma
    return float(text) if text else 0.0


def state_name(text: str) -> str:
    name = re.sub(r"[^A-Z]", "", text.upper())
    return PART_FILLED if name in ("PARTIALLYFILLED", "PARTFILLED") else name


def parse_order_state(text: str) -> tuple[str, int, float] | None:
    """'Order State;Filled Amount;Average FillPrice' -> (state, filled, avg), None if unreadable."""
    fields = text.strip().split(";")
    if len(fields) < 3 or not fields[0].strip():
        return None
    try:
        return state_name(fields[0]), int(_number(fields[1])), _number(fields[2])
    except ValueError:
        return None


def parse_position(text: str) -> tuple[int, float] | None:
    """'Market Position; Quantity; Average Entry Price' -> (signed qty, avg), None if unreadable."""
    fields = [f.strip() for f in text.strip().split(";")]
    if len(fields) < 3:
        return None
    try:
        qty, avg = int(_number(fields[1])), _number(fields[2])
    except ValueError:
        return None
    side = fields[0].upper()
    if side == "FLAT":
        return 0, avg
    if side in ("LONG", "SHORT"):
        return (qty if side == "LONG" else -qty), avg
    return None


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, PermissionError):
        return None  # missing, or NT8 holds it mid-write


def order_id_for(trade_date: date, seq: int, prefix: str = "QB") -> str:
    return f"{prefix}{trade_date:%Y%m%d}N{seq:04d}"


# --- the broker ----------------------------------------------------------------------------


@dataclass
class _Lot:
    side: int
    price: float  # ticks
    at: datetime


@dataclass
class _Tracked:
    order: OrderRecord
    sent_wall: datetime
    state: str = "SENT"
    filled: int = 0  # unsigned, from the order file
    avg: float = 0.0
    booked: int = 0  # unsigned, already in the lots
    booked_ticks: float = 0.0  # sum of booked qty x price, for each fill's own price


class NinjaTraderBroker:
    """Broker (live/broker.py protocol) over NT8's file interface, for one Sim account,
    instrument and session date. See the module docstring for the safety model."""

    def __init__(
        self,
        account: str,
        instrument: str,
        trade_date: date,
        *,
        nt_dir: Path | None = None,
        incoming: Path | None = None,
        outgoing: Path | None = None,
        state_dir: Path | None = None,
        root: str = "MNQ",
        tick_size: float = 0.25,
        fee_cents_per_side: int = 0,
        exchange: str = EXCHANGE,
        id_prefix: str = "QB",
        ack_seconds: float = 5.0,
        mismatch_seconds: float = 5.0,
        clock: Callable[[], datetime] = datetime.now,
        allow_onedrive: bool = False,
    ):
        self.account = check_sim(account)
        if not instrument or ";" in instrument:
            raise ValueError(f"bad instrument {instrument!r} (want e.g. 'MNQ 12-26')")
        if not re.fullmatch(r"[A-Za-z0-9]+", id_prefix):
            raise ValueError("id_prefix must be alphanumeric")
        nt_dir = default_nt_dir() if nt_dir is None else Path(nt_dir)
        self.incoming = Path(incoming) if incoming is not None else nt_dir / INCOMING
        self.outgoing = Path(outgoing) if outgoing is not None else nt_dir / OUTGOING
        self.state_dir = Path(state_dir) if state_dir is not None else nt_dir / STATE_FOLDER
        if not allow_onedrive:
            for p in (self.incoming, self.outgoing):
                if under_onedrive(p):
                    raise OneDriveFolder(
                        f"{p} is inside OneDrive, where NT8's ATI file processing is reported "
                        "to break: move the NinjaTrader 8 folder to a local drive and pass it "
                        "as nt_dir (or allow_onedrive=True to accept the risk)"
                    )
        self.instrument, self.trade_date, self.root = instrument, trade_date, root
        self.tick_size, self.fee_cents_per_side = tick_size, fee_cents_per_side
        self.exchange, self.id_prefix = exchange, id_prefix
        self.ack_seconds, self.mismatch_seconds = ack_seconds, mismatch_seconds
        self.clock = clock
        self.ledger = self.state_dir / f"nt_{account}_{trade_date:%Y%m%d}.jsonl"
        self.orders: list[OrderRecord] = []
        self.round_trips: list[RoundTrip] = []
        self.realized_cents = 0
        self.fees_cents = 0
        self.pnl_exact = True
        self._lots: list[_Lot] = []
        self._live: dict[str, _Tracked] = {}  # orders whose fills move the position
        self._base = 0  # NT8 position at reconcile, before the live orders
        self._next_seq = 1
        self._mismatch_since: datetime | None = None
        self._rebase_until: datetime | None = None
        self._extra = 0
        self.reconciliation: dict = {}
        self.prior_halt: str | None = None
        self._last_pnl: int | None = None
        self._lock: ProcessLock | None = None
        self._acquire_lock()
        try:
            self.reconcile()
        except BaseException:
            self.close()
            raise

    def __repr__(self) -> str:
        return f"NinjaTraderBroker(account={self.account!r}, instrument={self.instrument!r})"

    # --- files -----------------------------------------------------------------------------

    def _id_re(self) -> re.Pattern:
        return re.compile(rf"{self.id_prefix}{self.trade_date:%Y%m%d}N(\d{{4}})")

    def _oif_name(self, order_id: str, suffix: str = "") -> str:
        return f"oif_{order_id}{suffix}.txt"

    def position_file(self) -> Path | None:
        exact = self.outgoing / f"{self.instrument} {self.exchange}_{self.account}_Position.txt"
        if exact.exists():
            return exact
        found = sorted(self.outgoing.glob(f"{self.instrument} *_{self.account}_Position.txt"))
        return found[0] if found else None

    def nt_position(self) -> tuple[int, float] | None:
        path = self.position_file()
        text = _read(path) if path else None
        return parse_position(text) if text else None

    def _order_state(self, order_id: str) -> tuple[str, int, float] | None:
        text = _read(self.outgoing / f"{order_id}.txt")
        return parse_order_state(text) if text else None

    def _log(self, **event) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _ledger(self) -> list[dict]:
        if not self.ledger.exists():
            return []
        out = []
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a torn last line from a crash
        return out

    # --- single instance -------------------------------------------------------------------

    def lock_file(self) -> Path:
        safe = re.sub(r"[^A-Za-z0-9-]", "_", self.instrument)
        return self.state_dir / f"nt_{self.account}_{safe}_{self.trade_date:%Y%m%d}.lock"

    def _acquire_lock(self) -> None:
        """Hold the OS lock for this account, instrument and day (ProcessLock) or refuse."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        lock = ProcessLock(self.lock_file())
        if not lock.acquire({"pid": os.getpid(), "started": str(self.clock())}):
            pid = lock.holder()
            raise InstanceLocked(
                f"process {pid} holds {lock.path}: only one live_nt per account, instrument and "
                "day (the OS releases the lock when that process ends)"
            )
        self._lock = lock

    def close(self) -> None:
        """Release the instance lock."""
        lock, self._lock = self._lock, None
        if lock is not None:
            lock.release()

    # --- disarm and halts ------------------------------------------------------------------

    def disarm(self, reason: str) -> dict:
        """Move every oif*.txt in `incoming` (any date, any name) to <state_dir>\\quarantine,
        one rename each, so nothing left there can fire later. A moved file whose order has no
        state never reached NT8: the order becomes QUARANTINED. A file that cannot be moved
        may be in NT8's hands. Journaled in the ledger; returns {moved, armed, failed}."""
        moved, armed, failed = [], [], []
        rx = re.compile(rf"{self.id_prefix}\d{{8}}N\d{{4}}")
        dest = self.state_dir / QUARANTINE
        for path in sorted(self.incoming.glob(OIF_GLOB)) if self.incoming.is_dir() else []:
            try:
                dest.mkdir(parents=True, exist_ok=True)
                os.rename(path, dest / f"{self.clock():%Y%m%d-%H%M%S%f}_{path.name}")
            except OSError as error:
                failed.append(f"{path.name}: {error}")
                continue
            moved.append(path.name)
            m = rx.search(path.name)
            if m is None or "_cancel" in path.name:
                armed.append(path.name)  # not one of our orders, or a close / cancel
                continue
            oid = m.group(0)
            if self._order_state(oid) is None:
                armed.append(path.name)
                tr = self._live.get(oid)
                if tr is not None and tr.state not in TERMINAL:
                    tr.state = QUARANTINED
        if moved or failed:
            try:
                self._log(event="quarantine", reason=reason, moved=moved, armed=armed,
                          failed=failed, at=self.clock())  # fmt: skip
            except OSError:
                pass
        return {"moved": moved, "armed": armed, "failed": failed}

    def persist_halt(self, reason: str, **info) -> None:
        """Record a halt in the ledger, so a restart the same day comes up halted."""
        self._log(event="halt", reason=reason, at=self.clock(), **info)

    def clear_halt(self, why: str) -> str:
        """Append a halt_cleared entry (scripts/live_nt.py --clear-halt). Nothing is deleted.
        A broker_state halt is cleared only when NT8's position file shows flat."""
        if not why.strip():
            raise ValueError("say why the halt is being cleared")
        if self.prior_halt is None:
            raise ValueError("no halt to clear today")
        if self.prior_halt == BROKER_HALT:
            nt = self.nt_position()
            if nt is None or nt[0] != 0:
                raise BrokerStateError(
                    "a broker_state halt is cleared only when NT8's position file shows FLAT "
                    f"(it shows {'no file' if nt is None else nt[0]}): flatten Sim by hand first"
                )
        cleared, self.prior_halt = self.prior_halt, None
        self._log(event="halt_cleared", cleared=cleared, reason=why, at=self.clock())
        return cleared

    # --- startup ---------------------------------------------------------------------------

    def reconcile(self) -> dict:
        """Read incoming, the ledger and outgoing before anything is sent (module docstring)."""
        leftovers = self.disarm("startup")
        if leftovers["armed"] or leftovers["failed"]:
            raise BrokerStateError(
                "incoming held OIFs NT8 never processed; moved to "
                f"{self.state_dir / QUARANTINE}: {leftovers['armed']}; could not move: "
                f"{leftovers['failed']}. None of the moved ones was executed. Check the account "
                "in NT8, then start again."
            )
        rx = self._id_re()
        events = self._ledger()
        sent = {e["order_id"]: e for e in events if e.get("event") == "sent"}
        dead = {e["order_id"] for e in events if e.get("event") == "send_failed"}
        for e in events:
            if e.get("event") == "quarantine":
                dead |= {m.group(0) for n in e.get("armed", []) if (m := rx.search(n))}
        self.prior_halt = None
        for e in events:  # the last halt of the day stands unless a later halt_cleared clears it
            if e.get("event") == "halt":
                self.prior_halt = e["reason"]
            elif e.get("event") == "halt_cleared":
                self.prior_halt = None
        seqs = [int(e["seq"]) for e in sent.values()]
        on_disk = set()
        for folder in (self.outgoing, self.incoming, self.state_dir / QUARANTINE):
            if folder.is_dir():
                for p in folder.iterdir():
                    m = rx.search(p.name)
                    if m:
                        seqs.append(int(m.group(1)))
                        on_disk.add(m.group(0))
        self._next_seq = max(seqs, default=0) + 1
        notes, unknown, states = [], [], {}
        for order_id in sorted(set(sent) | on_disk):
            state = states[order_id] = self._order_state(order_id)
            if state is None:
                if order_id not in dead:
                    unknown.append(
                        f"{order_id}: no order state in outgoing (NT8 restarted and cleared "
                        "it, or it never reached NT8)"
                    )
            elif state[0] not in TERMINAL:
                unknown.append(f"{order_id}: still {state[0]} at startup; retry shortly")
            elif order_id not in sent:
                notes.append(f"{order_id}: in outgoing but not in the ledger")
            elif state[0] == REJECTED:
                notes.append(f"{order_id}: rejected by NT8")
        if unknown:
            raise BrokerStateError("cannot reconcile: " + "; ".join(unknown))
        fills = [e for e in events if e.get("event") == "fill"]
        booked: dict[str, list[float]] = {}
        for e in fills:
            b = booked.setdefault(e.get("order_id", ""), [0, 0.0])
            b[0] += abs(int(e["quantity"]))
            b[1] += abs(int(e["quantity"])) * float(e["price"])
        at = self.clock().replace(second=0, microsecond=0)
        for order_id, e in sent.items():  # fills NT8 made that the ledger never booked
            state = states.get(order_id)
            done, value = booked.get(order_id, [0, 0.0])
            if state is None or state[1] <= done:
                continue
            new = state[1] - done
            price = (state[1] * state[2] / self.tick_size - value) / new
            price = round(price) if abs(price - round(price)) < 1e-6 else price
            step = 1 if int(e["quantity"]) > 0 else -1
            fill = {"event": "fill", "order_id": order_id, "quantity": step * new,
                    "price": price, "at": str(at), "booked_at": "reconcile"}  # fmt: skip
            self._log(**fill)
            fills.append(fill)
            notes.append(f"{order_id}: {new} filled before the restart, booked now")
        ledger_position = sum(int(e["quantity"]) for e in fills)
        nt = self.nt_position()
        if nt is None:
            if fills or self.position_file() is not None:
                raise BrokerStateError(
                    f"no readable position file for {self.instrument} on {self.account} "
                    f"({len(fills)} ledger fills today): check the account in NT8 by hand"
                )
            notes.append("no position file: assumed flat (NT8 writes it on position updates)")
            nt = (0, 0.0)
        self._base = nt[0]
        for e in fills:  # today's realized P&L survives any restart
            self._apply(int(e["quantity"]), float(e["price"]), datetime.fromisoformat(e["at"]))
        if ledger_position != nt[0]:
            notes.append(f"ledger position {ledger_position} != NT8 position {nt[0]}")
            self.pnl_exact = False
            step = 1 if nt[0] > 0 else -1
            start = datetime.combine(self.trade_date, time(0))
            self._lots = [_Lot(step, nt[1] / self.tick_size, start) for _ in range(abs(nt[0]))]
            marks = [e for e in events if e.get("event") == "pnl"]
            if marks:  # never start better than the last day P&L the runner saw
                last = int(marks[-1]["cents"])
                self.realized_cents += min(0, last - self.day_pnl_cents(marks[-1]["mark"], False))
        self.reconciliation = {
            "account": self.account,
            "instrument": self.instrument,
            "position": nt[0],
            "avg_price": nt[1],
            "ledger_orders": len(sent),
            "ledger_position": ledger_position,
            "realized_cents": self.realized_cents,
            "next_order_id": order_id_for(self.trade_date, self._next_seq, self.id_prefix),
            "pnl_exact": self.pnl_exact,
            "prior_halt": self.prior_halt,
            "quarantined": leftovers["moved"],
            "notes": notes,
        }
        return self.reconciliation

    # --- state refresh ---------------------------------------------------------------------

    def _refresh(self) -> None:
        now = self.clock()
        for oid, tr in self._live.items():
            if tr.state in TERMINAL:
                continue
            state = self._order_state(oid)
            if state is None:
                if (now - tr.sent_wall).total_seconds() > self.ack_seconds:
                    pending = (self.incoming / self._oif_name(oid)).exists()
                    raise BrokerStateError(
                        f"no order state for {oid} after {self.ack_seconds:.0f} s"
                        + (" (OIF not consumed: NT8 closed or ATI off?)" if pending else "")
                    )
                continue
            tr.state, tr.filled, tr.avg = state
            if tr.state == REJECTED:
                raise BrokerStateError(f"NT8 rejected {oid}")
        self._check_position(now)

    def _own_position(self) -> int:
        return (
            self._base
            + self._extra
            + sum(tr.filled * (1 if tr.order.quantity > 0 else -1) for tr in self._live.values())
        )

    def _check_position(self, now: datetime) -> None:
        nt = self.nt_position()
        if self._rebase_until is not None:
            if now <= self._rebase_until:
                if nt is not None:  # after CLOSEPOSITION NT8's file is the truth
                    self._extra += nt[0] - self._own_position()
                return
            self._rebase_until = None
        own = self._own_position()
        nt_qty = nt[0] if nt is not None else (None if own else 0)
        if nt_qty == own:
            self._mismatch_since = None
            return
        if self._mismatch_since is None:
            self._mismatch_since = now
        elif (now - self._mismatch_since).total_seconds() > self.mismatch_seconds:
            raise BrokerStateError(
                f"NT8 position {nt_qty if nt is not None else 'file missing'} != broker "
                f"position {own} for {self.mismatch_seconds:.0f} s"
            )

    # --- Broker protocol -------------------------------------------------------------------

    def position(self) -> int:
        self._refresh()
        return self._own_position()

    def working(self) -> int:
        self._refresh()
        out = 0
        for tr in self._live.values():
            if tr.state not in TERMINAL:
                step = 1 if tr.order.quantity > 0 else -1
                out += step * (abs(tr.order.quantity) - tr.filled)
        return out

    def place_market_order(self, quantity: int, sent_at: datetime, tag: str = "") -> str:
        if quantity == 0:
            raise ValueError("zero-quantity order")
        seq = self._next_seq
        self._next_seq += 1
        oid = order_id_for(self.trade_date, seq, self.id_prefix)
        line = place_market_line(self.account, self.instrument, quantity, oid)
        try:
            self._log(event="sent", order_id=oid, seq=seq, quantity=quantity, tag=tag,
                      sent_at=sent_at)  # fmt: skip
        except OSError as error:
            raise BrokerStateError(f"cannot write the ledger ({error}); {oid} not sent") from error
        order = OrderRecord(oid, quantity, sent_at, tag)
        tracked = _Tracked(order, self.clock())
        try:
            self._write([line], self._oif_name(oid))
        except OSError as error:
            if (self.incoming / self._oif_name(oid)).exists():  # it went out: track it
                self.orders.append(order)
                self._live[oid] = tracked
                raise BrokerStateError(f"error after sending {oid}: {error}") from error
            try:
                self._log(event="send_failed", order_id=oid, error=str(error))
            except OSError:
                pass
            raise BrokerStateError(f"could not send {oid}: {error} (it was NOT sent)") from error
        self.orders.append(order)
        self._live[oid] = tracked
        return oid

    def _write(self, lines: list[str], name: str) -> Path:
        return write_oif(self.incoming, name, lines, self.state_dir / "tmp")

    def cancel_order(self, order_id: str) -> None:
        stamp = f"_cancel{self.clock():%H%M%S%f}"
        try:
            self._write([cancel_line(order_id)], self._oif_name(order_id, stamp))
        except OSError as error:
            raise BrokerStateError(f"could not cancel {order_id}: {error}") from error

    def cancel_all(self) -> None:
        """CANCEL each of this broker's working orders (never CANCELALLORDERS: all accounts)."""
        for oid, tr in self._live.items():
            if tr.state not in TERMINAL:
                self.cancel_order(oid)

    def close_position(self) -> None:
        """CLOSEPOSITION for this account and instrument (NT8 also cancels its working orders).
        For ack_seconds afterwards NT8's position file is adopted as the position; lots
        closed this way are not priced, so day P&L is no longer exact."""
        # not an order ID (no N<seq>), so reconcile never mistakes it for an unknown order
        name = f"oif_{self.id_prefix}{self.trade_date:%Y%m%d}close{self.clock():%H%M%S%f}.txt"
        try:
            self._write([close_position_line(self.account, self.instrument)], name)
        except OSError as error:
            raise BrokerStateError(f"could not send CLOSEPOSITION: {error}") from error
        self._log(event="close_position", at=self.clock())
        self.pnl_exact = False
        self._lots.clear()
        self._rebase_until = self.clock() + timedelta(seconds=self.ack_seconds)

    def on_bar(self, bar, bar_start: datetime) -> list[OrderRecord]:
        """Book fills seen in the order files since the last bar (fill time = this bar's start,
        as the FakeBroker and the backtest assume; the price is NT8's average fill)."""
        self._refresh()
        done = []
        for tr in self._live.values():
            new = tr.filled - tr.booked
            if new > 0:
                step = 1 if tr.order.quantity > 0 else -1
                # NT8 reports the average of all fills so far: this fill's own price is the rest
                price = (tr.filled * tr.avg / self.tick_size - tr.booked_ticks) / new
                price = round(price) if abs(price - round(price)) < 1e-6 else price
                tr.booked_ticks += new * price
                self._apply(step * new, price, bar_start)
                self._log(event="fill", order_id=tr.order.order_id, quantity=step * new,
                          price=price, at=bar_start)  # fmt: skip
                tr.booked = tr.filled
                tr.order.fill_price, tr.order.filled_at = price, bar_start
            if tr.state in TERMINAL and tr.order.status == "working":
                tr.order.status = "filled" if tr.state == FILLED else "cancelled"
                if tr.state == FILLED:
                    done.append(tr.order)
        return done

    def _apply(self, quantity: int, price: float, at: datetime) -> None:
        step = 1 if quantity > 0 else -1
        tick = orb.TICK_CENTS[self.root]
        for _ in range(abs(quantity)):
            self.fees_cents += self.fee_cents_per_side
            if self._lots and self._lots[0].side != step:
                lot = self._lots.pop(0)  # FIFO close
                self.realized_cents += round(lot.side * (price - lot.price) * tick)
                self.round_trips.append(RoundTrip(lot.side, lot.at, lot.price, at, price))
            else:
                self._lots.append(_Lot(step, price, at))

    def day_pnl_cents(self, mark: int, log: bool = True) -> int:
        """Realized + open at `mark` - fees. Each new value goes to the ledger, so a restart
        whose fills cannot all be priced still starts no better than the last value seen."""
        tick = orb.TICK_CENTS[self.root]
        open_pnl = sum(round(lot.side * (mark - lot.price) * tick) for lot in self._lots)
        out = self.realized_cents + open_pnl - self.fees_cents
        if log and out != self._last_pnl:
            self._last_pnl = out
            try:
                self._log(event="pnl", cents=out, mark=mark)
            except OSError:
                pass
        return out


# --- the runner guard ----------------------------------------------------------------------

BROKER_HALT = "broker_state"
STALE_HALT = "stale_data"


class GuardedRunner(Runner):
    """Runner for the NT8 bridge, with extra halts and halts that survive a restart.

    broker_state: a BrokerStateError from the broker (missing, stale or inconsistent NT8
      state, or a failed write) halts the session and sends NOTHING more, not even a
      flatten: with an order's state unknown, any order could double it. Journaled; flatten
      the Sim account by hand.
    stale_data: `halt_after_bars` bars in a row arriving more than `halt_lag_seconds` after
      they closed, or no bar for 2 x `halt_lag_seconds` (heartbeat), halts and flattens.
      Only from 5 minutes before the session opens to the flatten: overnight quiet minutes
      never count, and one tradeless minute (bar written late on the next tick) is one late
      bar, not a halt. The base Runner still blocks entries on any stale bar. A delayed
      feed (NT8's free Simulation data after the trial) halts within a few minutes.
    Every halt first moves any OIF still waiting in `incoming` to quarantine (broker.disarm),
    then is written to the broker's ledger; a restart the same day comes up halted (and
    flattens, unless the halt was broker_state).
    """

    def __init__(self, *args, halt_lag_seconds: float = 60.0, halt_after_bars: int = 3, **kwargs):
        super().__init__(*args, **kwargs)
        self.halt_lag_seconds = halt_lag_seconds
        self.halt_after_bars = halt_after_bars
        self._late_bars = 0
        self._watch_from = self._at(_t(self.engine._open_n - 5))
        prior = getattr(self.broker, "prior_halt", None)
        if prior:
            now = kwargs.get("now") or datetime.now()
            self.halted = prior
            self._record(now, "halt_restored", reason=prior)
            if prior != BROKER_HALT:
                self._guard(now, self._move_to, 0, now, "halt_restored")

    def _watching(self, now: datetime) -> bool:
        return self._watch_from <= now < self._flat_at

    def _disarm(self, now: datetime, reason: str) -> None:
        disarm = getattr(self.broker, "disarm", None)
        if disarm is None:
            return
        try:
            out = disarm(reason)
        except Exception as error:  # never let the safety step crash the runner
            self._record(now, "quarantine_failed", error=repr(error))
            return
        if out["moved"] or out["failed"]:
            self._record(now, "quarantine", reason=reason, **out)

    def _persist(self, now: datetime, reason: str) -> None:
        persist = getattr(self.broker, "persist_halt", None)
        if persist is None:
            return
        try:
            persist(reason)
        except Exception as error:
            self._record(now, "halt_not_persisted", reason=reason, error=repr(error))

    def _halt(self, now: datetime, reason: str, **fields) -> None:
        self._disarm(now, reason)
        self._persist(now, reason)
        super()._halt(now, reason, **fields)

    def _broker_halt(self, now: datetime, error: Exception) -> None:
        self.halted = BROKER_HALT
        self._record(now, "halt", reason=BROKER_HALT, error=str(error), orders_sent="none")
        self._disarm(now, BROKER_HALT)
        self._persist(now, BROKER_HALT)

    def _guard(self, now: datetime, fn, *args, **kwargs) -> None:
        if self.halted == BROKER_HALT:
            return
        try:
            fn(*args, **kwargs)
        except (BrokerStateError, OSError) as error:
            self._broker_halt(now, error)

    def _stale_halt(self, now: datetime, lag: float, source: str) -> None:
        if self.halted in (STALE_HALT, BROKER_HALT):
            return
        self._guard(now, self._halt, now, STALE_HALT, lag_seconds=lag, source=source)

    def on_bar(self, bar: Bar, now: datetime) -> None:
        self._guard(now, super().on_bar, bar, now)
        lag = (now - (self._at(bar.minute) + timedelta(minutes=1))).total_seconds()
        late = self._watching(now) and lag > self.halt_lag_seconds
        self._late_bars = self._late_bars + 1 if late else 0
        if self._late_bars >= self.halt_after_bars:
            self._stale_halt(now, lag, "bar")

    def on_clock(self, now: datetime) -> None:
        self._guard(now, super().on_clock, now)
        if self._last_bar_end is not None and self._watching(now):
            behind = (now - self._last_bar_end).total_seconds() - 60
            if behind > 2 * self.halt_lag_seconds:
                self._stale_halt(now, behind, "heartbeat")

    def end_session(self, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        try:
            return super().end_session(now)
        except (BrokerStateError, OSError) as error:
            if self.halted != BROKER_HALT:
                self._broker_halt(now, error)
            return self._record(
                now,
                "session_end",
                engine_status=self.engine.end_session(),
                model_legs=self.engine.legs,
                broker_position=None,
                broker_working=None,
                halted=self.halted,
            )

    def close(self) -> None:
        super().close()
        close = getattr(self.broker, "close", None)
        if close is not None:
            close()


def warm_up(runner: Runner, bars: list[Bar], now: datetime, contracts: int = 1) -> None:
    """Restart catch-up: feed bars that are already past to the engine only (no orders), then
    move the broker toward the engine's target with stale=True, so it can only be reduced.

    The target is what the engine has decided, not only what it holds: when the last bar is
    a check bar the engine has queued the change (its fill bar has not come yet), so the
    queued target counts (a reversal sends its exit; a reversal NT8 already filled sends
    nothing). A Void or ModelFill resets it to the engine's side."""
    if not bars:
        return
    target = runner.engine.side
    for b in bars:
        for ev in runner.engine.on_bar(b):
            if isinstance(ev, Signal) and ev.order is not None:
                target = ev.order.target
            elif isinstance(ev, (ModelFill, Void)):
                target = runner.engine.side
    runner._last_bar_end = runner._at(bars[-1].minute) + timedelta(minutes=1)
    runner._record(
        now,
        "catch_up",
        bars=len(bars),
        last=bars[-1].minute,
        model_side=runner.engine.side,
        model_target=target,
    )
    if isinstance(runner, GuardedRunner):
        if runner.halted == BROKER_HALT:
            return
        runner._guard(now, runner._move_to, target * contracts, now, "restart_reconcile", True)
    else:
        runner._move_to(target * contracts, now, "restart_reconcile", stale=True)


# --- bars ----------------------------------------------------------------------------------


def bar_file(bars_dir: Path, instrument: str, trade_date: date) -> Path:
    return Path(bars_dir) / f"{instrument}_{trade_date.isoformat()}.csv"


def parse_bar_line(line: str, tick_size: float = 0.25) -> tuple[date, Bar] | None:
    """'2026-10-29,08:30,21000.25,21001,20999.5,21000,812' -> (date, Bar in ticks)."""
    fields = line.strip().split(",")
    if len(fields) != 7:
        return None
    try:
        d = date.fromisoformat(fields[0])
        minute = time.fromisoformat(fields[1]).replace(second=0, microsecond=0)
        o, h, lo, c = (round(float(x) / tick_size) for x in fields[2:6])
        volume = float(fields[6])
    except ValueError:
        return None
    if not lo <= min(o, c) <= max(o, c) <= h:
        return None
    return d, Bar(minute, o, h, lo, c, int(volume) if volume.is_integer() else volume)


class BarFileTail:
    """Tail one exporter CSV: each poll returns the new complete bars for `trade_date`.

    A line counts only once its newline is written (QuantBarExporter flushes whole lines).
    Malformed lines, other dates, and bars at or before the last minute returned (NT8 rewrites
    history when a chart reloads) are skipped and counted in `skipped`."""

    def __init__(self, path: Path, trade_date: date, tick_size: float = 0.25):
        self.path, self.trade_date, self.tick_size = Path(path), trade_date, tick_size
        self.skipped: Counter = Counter()
        self._offset = 0
        self._buffer = b""
        self._last: time | None = None

    def poll(self) -> list[Bar]:
        try:
            with self.path.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
        except (FileNotFoundError, PermissionError):
            return []
        self._offset += len(chunk)
        data = self._buffer + chunk
        *lines, self._buffer = data.split(b"\n")
        out = []
        for raw in lines:
            text = raw.decode("utf-8", errors="replace").strip()
            if not text or text == BAR_HEADER:
                continue
            parsed = parse_bar_line(text, self.tick_size)
            if parsed is None:
                self.skipped["malformed"] += 1
            elif parsed[0] != self.trade_date:
                self.skipped["other_date"] += 1
            elif self._last is not None and parsed[1].minute <= self._last:
                self.skipped["duplicate"] += 1
            else:
                self._last = parsed[1].minute
                out.append(parsed[1])
        return out


def follow(
    tail: BarFileTail,
    stop: Callable[[], bool],
    sleep: Callable[[float], None],
    poll_seconds: float = 0.25,
) -> Iterator[Bar]:
    while not stop():
        yield from tail.poll()
        sleep(poll_seconds)


def read_session(
    path: Path, trade_date: date, tick_size: float = 0.25, start: time = time(8, 30),
    end: time = time(15, 7),
) -> tuple[dict[time, tuple[int, int, int, int]], dict[time, float]]:  # fmt: skip
    """A whole exporter file as (bars, volumes) for minutes in [start, end] (the DayInput view
    the sigma table and the previous close are built from)."""
    tail = BarFileTail(path, trade_date, tick_size)
    bars, vols = {}, {}
    for b in tail.poll():
        if start <= b.minute <= end:
            bars[b.minute] = (b.open, b.high, b.low, b.close)
            vols[b.minute] = b.volume
    return bars, vols


def regular_close(bars: Mapping[time, tuple[int, int, int, int]], close_at: time) -> int | None:
    """Close of the last bar before the regular close (futures/bars.py `_sessions`)."""
    before = [m for m in bars if m < close_at]
    return bars[max(before)][3] if before else None
