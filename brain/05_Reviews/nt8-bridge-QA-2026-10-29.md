# NT8 Sim bridge: adversarial QA, 2026-10-29

This is reviewer C under `brain/_system/plan/bot_plumbing_plan.md`. It covers the uncommitted bridge:

- `src/quant_brain/live/ninjatrader.py`
- `ninjatrader/QuantBarExporter.cs`
- `scripts/live_nt.py`
- `tests/test_live_ninjatrader.py`

It also read `live/broker.py`, `live/engine.py` and `live/runner.py` for context. The reviewed files were not changed.

Reproductions are in `tests/test_live_ninjatrader_qa.py`. Each test marked `xfail(strict=True)` names its finding ID and fails today for the reason given. When a bug is fixed, its test will XPASS and fail the suite, so remove the mark at that point. The plain tests in that file confirm behaviour that was checked and found safe.

**Verdict:** not done. The plan's bar is "QA has no open High findings", and four are open: H1 to H4. The Sim-only guard itself holds.

## Summary

| ID | Sev | Finding | Repro |
|---|---|---|---|
| H1 | High | An OIF that NT8 never consumed stays armed in `incoming` after the halt. Reconcile also ignores OIFs from other dates. When ATI or NT8 comes back, the order runs with nothing managing it. | `test_H1_*` (2, xfail) |
| H2 | High | A restart between a check bar and its fill bar sends the wrong reconcile. `warm_up` uses `engine.side`, which is still the pre-check side. The result is a missed exit, or an extra order that undoes a filled reversal. | `test_H2_*` (2 xfail, plus 1 recording the damage) |
| H3 | High | There is no single-instance lock. Two processes on one account reuse the same order ID and double every order. | `test_H3_*` (xfail) |
| H4 | High | The session calendar ends 2026-10-21. `live_nt` treats holidays and early closes as normal full days, and CME-only holiday files feed the previous close and sigma. Both break backtest parity. | `test_H4_*` (2, xfail) |
| M1 | Med | Day P&L, and with it the daily loss stop, resets to 0 on a restart whenever the ledger and NT8 disagree. Halts are not persisted. | `test_M1_*` (xfail) |
| M2 | Med | One minute with no trades makes a bar arrive more than 60 s late. That is a permanent `stale_data` halt, including overnight before the open. | `test_M2_*` (xfail) |
| M3 | Med | `write_oif`, the "checked again" choke point, lets through FLATTENEVERYTHING, CANCELALLORDERS, and lowercase or space-prefixed PLACE lines for non-Sim accounts. | `test_M3_*` (4, xfail) |
| M4 | Med | An OS error while writing the OIF (PermissionError, FileExistsError) escapes the runner. `live_nt` crashes with no halt in the journal, and the day cannot be restarted. | `test_M4_*` (xfail) |
| L1 | Low | The second partial fill is booked at NT8's cumulative average, not at its own price. | `test_L1_*` (xfail) |
| L2 | Low | A REJECTED halt is not sticky: REJECTED counts as terminal, so a restart reconciles cleanly and trades on. | code read |
| L3 | Low | The temp OIF is written inside `incoming`, not "elsewhere" as the module's own docstring says. | code read |
| L4 | Low | No check of PC clock against bar clock. A PC clock about 11 s fast silently refuses every entry; about 61 s fast halts the day. | code read |
| L5 | Low | C# exporter: compiles plausibly, but unverified. One API path is unconfirmed, and an exception other than IOException kills the indicator. | code read |
| L6 | Low | If the chart is first loaded after `live_nt` starts, the historical burst halts the day as stale. | code read |
| L7 | Low | Tests are too forgiving: an instant, atomic FakeNT8, a frozen broker clock in the practice replay, and no tests for `live_nt.py`. | code read |
| L8 | Low | A crash between the ledger write and the OIF rename, or an NT8 restart, blocks restarts for the rest of the day. Safe, but there is no recovery path and the error message misleads. | `test_crash_between_ledger_write_and_oif_rename_never_sends` (pass) |

Checked and found safe:

- **Sim guard.** It is checked in the constructor, in `place_market_line`, in `close_position_line` and in `write_oif` for PLACE, CLOSEPOSITION and REVERSEPOSITION. It cannot be bypassed through `live_nt.py` arguments: `--sim Live1`, `sim101`, `""`, `" Sim101"` and `--sim … --replay` all exit before a broker is built (`test_live_nt_arguments_cannot_bypass_the_sim_guard`).
- **No environment variables.** None are read.
- **Account-wide commands.** The broker never calls `flatten_everything_line` or `cancel_all_orders_line`. `close_position` and `cancel_all` are never called by the runner.
- **Order IDs.** IDs are unique across days because the date is part of the ID. Sequence numbers continue across restarts (`test_restart_ids_continue_and_differ_across_days`).
- **Crash between ledger and rename.** Nothing is sent.

## High findings

### H1: an unconsumed OIF stays armed after the halt

- `ninjatrader.py:480-486` (`_refresh`) raises BrokerStateError when an order has no state after `ack_seconds`. It notices "OIF not consumed" but leaves the file in `incoming`.
- `_broker_halt` (`ninjatrader.py:634-636`) and `live_nt.py:287` then stop the session, and the file stays there.
- The existing test `test_stale_order_state_halts_the_runner_without_resending` asserts that the OIF is *still there* (`tests/test_live_ninjatrader.py:385`) and treats that as "never resent". In fact it is a market order waiting to fire.
- Separately, reconcile only matches today's IDs: `_id_re` at `ninjatrader.py:361-362` embeds `trade_date`, and the scan is at `ninjatrader.py:410-416`. Yesterday's leftover `oif_QB<yesterday>N….txt` therefore does not block startup.

**Failure scenario.** At 08:59 ATI is off, or NT8 is still loading, so the entry OIF is not consumed. At 09:00:05 the bot halts with `broker_state` and exits with code 2. Around 13:00 Jason enables ATI, or NT8 finishes connecting, and NT8 executes a market BUY. No runner is alive, so nothing flattens at 15:00 and the Sim position is held overnight.

The same happens one day later: a leftover OIF from the previous day passes reconcile, NT8 fills it mid-session, and the bot halts on a position mismatch without flattening. Both cases break the hard rule "no orders outside the engine's signals".

**Fix.**

- On any halt, and at reconcile, move every `oif*.txt` in `incoming` out to a quarantine folder with a single rename.
- A failed rename means NT8 has the file. Treat that as unknown state.
- Refuse to start while any `oif*.txt` from any date is present.

### H2: a restart inside a check window sends the wrong reconcile

- `warm_up` at `ninjatrader.py:692` moves the broker to `runner.engine.side * contracts`.
- When the last warm-up bar is a check bar (HH:59 or HH:29), `NoiseEngine._check` has only *queued* the change in `_pending` (`engine.py:230-238`). `side` changes when the next bar resolves it (`engine.py:241-254`).
- `live_nt.py:283-285` puts a bar into warm-up once it is more than `stale_seconds` (10 s) old.
- So a restart about 10 to 60 s after any of the 12 daily checks (09:00 to 14:30) reconciles to the pre-check side.

**Scenario a: crash just before the 10:29 bar, restart at 10:30:15.** The engine reversed long to short at 10:30. `warm_up` sees side +1 and the broker long, so it sends no order. When the 10:30 bar arrives the model is short, but no order follows a ModelFill. The broker stays long until the 15:00 flatten.

`test_H2_full_day_effect` records the result:

- Backtest legs: `[long 09:00→10:30, short 10:30→15:00]`.
- Live: `[long 09:00→15:00]`.

The required exit was never sent, even though exits are never meant to be refused.

**Scenario b: crash right after the reversal was sent and filled.** NT8 now holds −1. The ledger does not have the fill, so reconcile adopts NT8's −1. `warm_up` targets +1 and `stale=True` caps it at 0, so it sends BUY 1 `restart_reconcile` and flattens a correct short.

**Fix.** Reconcile toward the engine's pending target when `engine._pending` is set: the new side after the pending check. Alternatively, have the runner act on ModelFill and Void by reconciling to `engine.side`.

### H3: no single-instance lock

Nothing stops a second `live_nt.py --sim Sim101` from running at the same time. A second console, a scheduler run, or a hung first process is enough. Each process:

- reconciles the same ledger;
- picks the same `_next_seq` (`ninjatrader.py:417`);
- computes its own target from its own `_live` set.

The ledger write and `write_oif` at `ninjatrader.py:539-544` only refuse an existing OIF *file*. If NT8 has already consumed the first one, the second process writes the same ID again.

**Failure scenario.** Both processes see the 08:59 breakout and each sends `QB…N0001` BUY 1, so NT8 is long 2. That is already past `max_position=1` across the pair.

Each process then sees NT8 at 2 against its own 1 and halts on a mismatch after one bar, without flattening. The Sim account is left long 2 with nothing managing it. NT8's handling of a duplicate order ID is also unconfirmed.

The repro shows `fake.places() == ['…N0001', '…N0001']` and position 2.

**Fix.** Take an exclusive lock file per account, instrument and date in `state_dir`: `os.open(O_CREAT|O_EXCL)` plus the PID, or `msvcrt.locking`. Hold it for the whole session and refuse to start while it is held.

### H4: calendar staleness and holidays break parity

- `brain/_system/futures/session-calendar.v1.csv` ends at **2026-10-21**. Every live date since then is missing from it.
- `live_nt.py:233` sets `early = args.early_close or (day in calendar and …)`, so a missing date counts as a normal full day. Nothing warns about it.
- `history_context` (`live_nt.py:176-192`) takes every earlier exporter file (`d < day`), with no check that the date is an NYSE session. For a date missing from the calendar it assumes a 15:00 close.
- The backtest (`futures/bars.py:110-111` and `build_days`) only ever uses calendar sessions.

**Failure scenarios.**

1. **Thanksgiving, 2026-11-26.** CME equity futures trade to 12:00 CT; NYSE is closed. `live_nt` trades the holiday, which the backtest never does. Bars stop at 12:00, and the heartbeat halts and flattens at about 12:02 into a closed market. NT8 Sim holds that market order until the 17:00 reopen.
2. **Black Friday, 2026-11-27, an early close.** The engine runs its regular session: checks continue at 12:00 and later, with the flatten at 15:00 instead of 12:00. A position opened at the 11:30 or 12:00 check is not flattened at 12:00 as in the backtest. Bars stop at 12:15, and the heartbeat sends the flatten into the halted market, where it fills at 17:00.
3. **Parity after a CME-only holiday.** The holiday's half-day file becomes `prev_close` for the next session: 200 instead of 100 ticks in `test_H4_holiday_session_is_not_the_previous_close`. That moves both anchors. It also enters the 14-session sigma history for the next three weeks. Every check decision on those days can differ from the backtest.

**Fix.**

- Extend the calendar, for example from the CME and NYSE schedule through 2027.
- `live_nt` should refuse to run, or run dry only, on a date not in the calendar.
- `history_context` should keep only calendar sessions, matching `build_days`.

## Medium and Low details

- **M1** (`ninjatrader.py:447-458`, `runner.py:199`).
  - When the ledger position differs from NT8's, `realized_cents` starts at 0. Common causes: a crash within the minute after a fill and before `on_bar` books it, or Jason flattening by hand after a halt, as the halt message tells him to.
  - The repro shows a −$20.00 day reading $0.00 after a restart, so the daily loss stop starts over.
  - Even when the ledger matches, the `daily_loss_stop` halt is only re-derived after `_act` on the first bar (`runner.py:252-264`). A restart whose first live bar is a check bar can still send one entry before it halts again.
  - Fix: book terminal-but-unbooked fills from the order files at reconcile, and persist halts in the ledger.
- **M2** (`ninjatrader.py:651-659`, `QuantBarExporter.cs:47`).
  - With `Calculate.OnBarClose`, bar k is written on the first tick of a later bar. If minute k+1 has no trades, the bar lags by more than 60 s, and that is a permanent `stale_data` halt.
  - Repro: 03:01 bar delivered at 03:03:05 gives `stale_data` five hours before the open, and the day is lost.
  - Fix: apply the halt only from about 08:25 to the flatten, and distinguish an exchange gap (the bar's own minute is old but the PC and NT8 clocks agree) from a delayed feed. Or flatten only, without latching the halt, when flat.
- **M3** (`ninjatrader.py:197-202`).
  - `write_oif` only checks exact `PLACE`, `CLOSEPOSITION` and `REVERSEPOSITION`. All of these are written untouched: `FLATTENEVERYTHING;;;;;;;;;;;;`, `CANCELALLORDERS;;…`, `place;Live1;…` and `" PLACE;Live1;…"`.
  - The broker never builds these lines today. But the docstring promises "Every OIF line is checked again", and whether NT8 parses commands case-blind is unconfirmed.
  - Fix: an allow-list of `PLACE`, `CANCEL` and `CLOSEPOSITION` after `.strip().upper()`, and a refusal of everything else.
- **M4** (`ninjatrader.py:543-544`, `_guard` at `638-644`, `live_nt.py:287-292`).
  - An antivirus or indexer lock on the temp file is common on Windows. It makes `os.rename` raise PermissionError, which `_guard` does not catch.
  - The traceback ends `live_nt`: no halt record, no `end_session`, and the journal is left open.
  - Because "sent" was logged first, every restart that day then refuses with "no order state".
  - Fix: catch OSError in `place_market_order`, record a `send_failed` ledger event when the OIF is known not to exist, and raise BrokerStateError.
- **L1** (`ninjatrader.py:578-583`).
  - New fills are booked at `tr.avg`, NT8's average over all fills so far.
  - Example: 1 @ 100.00, then a second @ 101.00 with an average of 100.50. The second lot is booked at 100.50, not 101.00.
  - Fix: `(filled*avg - booked*prev_avg) / new`.
- **L2** (`ninjatrader.py:103, 429`).
  - A rejected order halts the session. A restart reconciles it as terminal and resumes trading without a note.
  - Recommend adding a reconcile note or a refusal on REJECTED.
- **L3** (`ninjatrader.py:207` against docstring `:15-16`).
  - `tmp-oif_….txt.part` is created in `incoming` itself. That is safe only if NT8 strictly filters on `oif*.txt`, which is not verified.
  - Write it in `state_dir`, which is on the same volume, and rename it across.
- **L4** (`live_nt.py:170-171`, `runner.py:246-247`). Wall clock and bar clock are compared directly. Log the median lag at startup and refuse to start if the PC clock is more than a few seconds off NTP or NT8's clock.
- **L5** (C#).
  - Plausible as NinjaScript:
    - namespace `NinjaTrader.NinjaScript.Indicators`;
    - `OnStateChange` with SetDefaults and DataLoaded;
    - `Calculate.OnBarClose` and `OnBarUpdate`;
    - `[NinjaScriptProperty]` and `Display`.
  - Bar labelling is right. NT8 stamps time-based bars with their **close** time, the exporter writes `Time[0] - 1 min` as the start, and the reader assumes a start. The two are consistent.
  - Time-zone conversion: `ConvertTime(Unspecified, GeneralOptions.TimeZoneInfo, "Central Standard Time")` handles CST and CDT. DST changes happen on Sunday at 02:00, while CME is closed.
  - Unverified: the `NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo` path, and whether the editor adds the generated-code region on compile. Compile it once in NT8.
  - `catch (IOException)` misses `UnauthorizedAccessException`. An uncaught exception stops the indicator, so bars stop and the heartbeat halts. That is safe, but the cause is silent.
  - `lastStart` resets on reload. The reader drops the duplicates.
  - File sharing works in both directions: `AppendAllText` uses FileShare.Read, and Python's `open('rb')` shares read and write.
- **L6** (`ninjatrader.py:653-654`, `live_nt.py:277-285`).
  - Warm-up only happens once, at startup. If the exporter's historical dump lands later, its first bar is very old, and the day halts and flattens.
  - Document "chart first", or treat a burst of more than one bar per poll as warm-up.
- **L7** (tests).
  - FakeNT8 (`tests/test_live_ninjatrader.py:49-113`):
    - consumes and fills in one step;
    - writes the order file and the position file together;
    - deletes OIFs;
    - never partially fills, never lags the position file, never writes "Accepted" or "Working" after a fill.
  - The practice-day replay passes `broker=make_broker(root, clock…)`, but `run_day` advances a *different* `Clock()` (`:150-157` against `:503-505`). The broker's clock is frozen at 2020-01-02 08:00, so the ack timeout and mismatch timer can never fire there.
  - No test covers:
    - `live_nt.py`: `history_context`, the warm-up split, or the loop;
    - a restart inside a check window (H2);
    - a concurrent process (H3);
    - a holiday or an uncalendared date (H4);
    - partial fills.
  - The reject test only checks that the error is raised.
- **L8.** After a crash between the ledger write and the rename, or after an NT8 restart that clears `outgoing`, every restart raises "no order state … NT8 restarted and cleared it" for the rest of the day. That is safe, and it is confirmed by a passing test. But there is no CLI to mark an ID "never sent" or "flattened by hand".

## Delayed feed, clocks and engine parity

- **Delayed feed.** A 10-minute delayed feed is handled. Every bar older than 10 s at startup only warms up the engine. The first live bar lags about 600 s, so the session halts and flattens. That is correct and safe.
- **Session times.** Session open and close, check minutes and the flatten minute all come from `noise._session`, so they are identical to the backtest.
- **Previous close and sigma.** The rule is the same as `bars._sessions`: the last bar before 15:00, or 12:15 on early days. `SigmaHistory` is the same. Both diverge only through H4.
- **Check-minute fill.** The order goes out when the check−1 bar arrives. NT8's market fill is booked at the check minute's start, at NT8's average price, which matches the backtest assumption.
- **Restarts.** A restart breaks parity through H2, and P&L through M1.

## Test counts (2026-10-29, `.venv/Scripts/python.exe -m pytest`, PYTHONPATH=src)

- Before QA: **1321 passed, 4 skipped** (243 s). `tests/test_live_ninjatrader.py`: 17 passed, including the practice-day replay; the dev partition is present.
- `tests/test_live_ninjatrader_qa.py`: **8 passed, 15 xfailed**. The 15 xfails cover H1×2, H2×2, H3, H4×2, M1, M2, M3×4, M4 and L1. Each fails today for the stated reason, checked with `--runxfail`.
- Full suite with the QA file: **1329 passed, 4 skipped, 15 xfailed, 1 warning** (242 s). The warning is a pre-existing Starlette/httpx deprecation.

## Re-review, 2026-10-29 (after the engineering fixes)

I re-read the bridge as revised and checked each fix against its finding. I also looked for bugs the fixes introduced. The revised files are `live/ninjatrader.py`, `live/calendar.py`, `session-calendar.live.v1.csv`, `scripts/live_nt.py`, `scripts/forward_log.py` and both test files. The implementation was not edited. New reproductions were added to `tests/test_live_ninjatrader_qa.py` under "re-review"; they are strict xfails tagged N1 to N4.

**Verdict: no High findings are open.** One new Medium (N3) is a parity bug introduced by the H4 fix.

### Status of the original findings

| ID | Status | Evidence |
|---|---|---|
| H1 | Closed | `disarm()` quarantines every `oif*.txt` in `incoming`, from any date and with any name. This runs on every halt, and before the flatten so the flatten itself is not quarantined, and again at startup. Startup refuses while anything unprocessed was found; the next start is clean, because the IDs are logged as dead. Both H1 tests pass unchanged. |
| H2 | Closed | `warm_up` now targets the queued `Signal.order.target`, and a ModelFill or Void resets it. Both H2 tests pass unchanged. `H2_full_day_effect` now asserts the fixed result: the long leg equals the backtest's, and the afternoon short is refused as stale. That is a fair restatement, not a weakening. |
| H3 | Closed, with N1 | There is an `O_CREAT`/`O_EXCL` PID lock. The adapted test only covers a second broker in the *same* process, where `pid == os.getpid()`. I added `test_lock_refuses_a_live_other_process_and_takes_over_after_a_hard_kill`, which uses a real child process and `TerminateProcess` and passes. With it, Windows `OpenProcess` / `GetExitCodeProcess` is checked against a live PID, a dead PID and a hard-killed one. |
| H4 | Closed, with N3 | The calendar now runs to 2027-12-31. I checked it against nyse.com/markets/hours-calendars, fetched 2026-10-29: there are exactly 12 full closes (2026-11-26, 2026-12-25; 2027-01-01, 01-18, 02-15, 03-26, 05-31, 06-18, 07-05, 09-06, 11-25, 12-24) and 3 early closes (2026-11-27, 2026-12-24, 2027-11-26). Every other weekday is present, there are no weekend rows, and none overlap the frozen file. NYSE lists no closure for 2027-12-31, because New Year 2028 falls on a Saturday and is not observed, and the file correctly keeps that day. `live_nt` refuses any date not in the calendar, and `history_context` uses only calendar sessions. The test adaptation, from the frozen file to `sessions()`, is correct. |
| M1 | Closed | Fills NT8 made that the ledger never booked are booked from the order files at reconcile. Realized P&L is always rebuilt. When the ledger and NT8 disagree, day P&L never starts better than the last value logged in the ledger. The adapted test calls `b.close()` instead of crashing, but crash takeover is covered by the lock test above. |
| M2 | Closed | Stale halts now only apply from 08:25 to the flatten, and a halt needs 3 late bars in a row or 180 s with no bar. One tradeless minute no longer halts. A 10-minute delayed feed halts after about 3 bars, and entries stay blocked by the base runner meanwhile. |
| M3 | Closed | `check_oif_line` allows only PLACE, CANCEL and CLOSEPOSITION, in exact case. PLACE and CLOSEPOSITION need a Sim account; CANCEL must have no account and an order ID. |
| M4 | Closed | OSError in the send path becomes `send_failed` plus BrokerStateError, and `_guard` catches OSError. A restart after a known-unsent order recovers. |
| L1 | Closed | Each fill is now booked at its own price: total value minus what was already booked, divided by the new quantity. |
| L2 | Closed | A REJECTED order halts, and the halt is persisted, so a restart comes up halted. |
| L3 | Closed | The temp file is now written in `state_dir/tmp`. If someone points `state_dir` at a different drive, the rename fails, and that becomes `send_failed` and a halt: safe. |
| L6 | Closed | Warm-up now happens on the first poll that returns bars, whenever that is, so loading the chart late no longer halts. |
| L4, L5, L7, L8 | Open, Low | Not in scope for this round. L8 is mostly addressed: a known-unsent order (`send_failed` or quarantined) no longer blocks restarts. |

### New findings

| ID | Sev | Finding | Repro |
|---|---|---|---|
| N3 | Med | **The live previous close after an early close is the 12:12 bar, but the backtest uses the 12:14 bar.** | `test_N3_*` (xfail) |
| N1 | Low | **Two starts racing to take over one dead lock can both run.** | `test_N1_*` (xfail) |
| N4 | Low | **`forward_log.py` takes the previous close after an early close from before 12:00, not before 12:15.** This existed before the change and is not caused by it. | `test_N4_*` (xfail) |
| N2 | Low | **A refused second start writes `halt broker_state` into the running session's journal.** | `test_N2_*` (xfail) |
| N5 | Low | **Every persisted halt is final for the day, with no supported way to clear it.** | code read |
| N6 | Low | **Quarantining on a halt can race NT8 for an order sent in the same bar.** | code read |

**N3 (Medium).** `live_nt.history_context` reads past files with `read_session(f, d, end=calendar[d].exit_minute)` (`live_nt.py:90`), which caps an early day at 12:12. It then takes `regular_close(bars, 12:15)` (`:92`).

The backtest's `futures/bars._sessions` (`bars.py:110-141`) takes the close from *all* of that day's bars before 12:15, without the exit cap: that is the 12:14 bar.

Real data confirms it: after the 2023-11-24 early close, the backtest's `prev_close` for 2023-11-27 is 64043, while the 12:12 close is 64056, 13 ticks apart.

Failure scenario: on 2026-11-30 and 2026-12-28, the sessions after the next two early closes, both anchors differ from the backtest, so any check decision near a band can differ.

Fix: read past files with `end=time(15, 7)` (or uncapped) for the previous close, and keep the `exit_minute` cap for the sigma moves only.

**N1 (Low).** `_acquire_lock` handles a dead PID by renaming the lock aside and retrying.

Failure scenario: process B reads the dead PID; process A renames the lock and creates its own; then B renames *A's live lock* aside and creates its own. Both now run, which is the H3 double order again. It needs two starts within milliseconds of each other after a crash, for example a double-clicked launcher or a scheduler run alongside a manual one. The repro forces that interleaving.

Fix: hold an OS lock that dies with the process (`msvcrt.locking` on an open handle) instead of comparing PIDs. Alternatively, after taking over, re-read the lock and confirm it holds our own PID.

**N4 (Low).** `forward_log.build_days` sets `prev_close` from the last bar before `exit_minute`, which is 12:00 on early days. The backtest uses the last bar before 12:15. The bars are also not capped at 12:12.

The first day affected is 2026-11-30.

**N2 (Low).** When `NinjaTraderBroker` raises InstanceLocked (a BrokerStateError), the constructor `except` in `live_nt.py` appends a `halt` record to the journal path. The default path is `<day>_sim-<acct>.jsonl`, the same file the running instance is writing.

Anyone reading that journal sees a broker_state halt in a session that is still trading.

Fix: on InstanceLocked, print only, or write to a separate `_refused` file.

**N5 (Low).** Every persisted halt is final for the day: `prior_halt` is restored at construction. That includes a stale-data halt from a brief feed glitch, a kill switch whose STOP file has since been deleted, and a broker_state halt Jason has fixed by hand. The only way to clear one is to edit the ledger.

This is safe, but it should be documented in the setup guide, or a `--clear-halt` flag should append an explicit `halt_cleared` event.

**N6 (Low, theoretical).** A non-broker halt in the same `on_bar` as a check order can run `disarm()` within milliseconds of writing that order's OIF. Kill switch and daily loss stop are examples.

Failure scenario: NT8 has read the OIF but not yet written its order file. The rename can then succeed, the order is marked QUARANTINED, NT8 still executes it, and the mismatch halt later leaves a position open with no flatten. The window depends on NT8's ATI latency, which is not verified here.

### `forward_log.py` calendar change: the 5 logged days are unchanged

I replayed the old version (git HEAD) and the new one offline over the local Yahoo cache (`../data/yahoo/NQ_F_1m`, 2026-09-28..10-28), with no network access. For 2026-10-22, 23, 26, 27 and 28, both give identical results:

- status;
- trade count;
- net;
- bar count (391);
- early-close flag;
- previous close;
- full sigma table.

They also match the logged CSV rows exactly: 424.78 / −68.22 / 173.28 / 168.06 / 0.00. The cache has no weekday that is not an NYSE session, so the warm-up window is unchanged too.

### Test counts (re-review)

- Engineering's run before my additions: 1349 passed, 4 skipped.
- `tests/test_live_ninjatrader_qa.py` now: **24 passed, 4 xfailed** (N1 to N4). Each xfail fails for its stated reason, checked with `--runxfail`.
- Full suite: **1350 passed, 4 skipped, 4 xfailed, 1 warning** (210 s). The warning is the same pre-existing deprecation.

## Close-out (coordinator, 2026-10-29)
- Round-3 fixes landed for N1-N5; N6 is documented. The strict xfails for N1-N4 now pass and their marks are removed.
- Full suite: 1356 passed, 4 skipped, 0 failed (re-run by the coordinator).
- Open: Lows only (L4 clock skew, L5 exporter compile in real NT8, L7 the fake NT8 fills instantly, L8 a crash between the ledger write and the OIF rename blocks restarts that day; N6 documented).
- No High or Medium findings are open. The bridge meets the plan bar, except that it has not run on a real NT8 yet.
