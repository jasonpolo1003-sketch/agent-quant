# Bot plumbing plan: NinjaTrader 8 simulator bridge (2026-10-29)

Approved by Jason on 2026-10-29: "Bot plumbing (Recommended)". Part one, late-half-hour momentum, was dropped because it was already tested as SC-FUT-0002 and failed.

## Goal

Have the frozen SC-FUT-0005 live engine place practice trades on a NinjaTrader 8 Sim account every day, for $0. This tests the real machinery: order timing, fills, restarts and disconnects. The same bridge later reaches firms that connect through NT8, such as Lucid and Tradeify (Rithmic/Tradovate). Topstep keeps its existing ProjectX broker (`live/projectx.py`).

## Hard rules

- Sim accounts only. The broker refuses any account whose name does not start with "Sim" (for example Sim101). There is no override flag in this plan; a funded account would need a new, separately approved change.
- The bot sends no orders outside the frozen SC-FUT-0005 engine's signals. It keeps the existing runner risk checks (kill switch, flatten at the session close).
- No credentials go in code, chat or the vault. NT8 handles its own logins.
- The strategy logic is unchanged. `live/engine.py` is frozen and has been proven identical to the backtest.

## Design (file-based, no DLLs)

1. **Orders.** NT8's Automated Trading Interface (ATI) Order Instruction Files: Python writes `oif*.txt` into `Documents\NinjaTrader 8\incoming`.
2. **State.** NT8 writes order and position status into `Documents\NinjaTrader 8\outgoing`, and the broker polls it.
3. **Bars.** A small NinjaScript indicator, `QuantBarExporter`, appends each completed 1-minute MNQ bar to a CSV file, which the runner reads.
4. **`NinjaTraderBroker`.** Implements the `live/broker.py` Broker protocol, alongside the existing FakeBroker and ProjectXBroker.
5. **`scripts/live_nt.py`.** Runs one session. Dry-run (FakeBroker) is the default; `--sim` sends orders to the NT8 Sim account. Every event is logged to a JSONL journal.

## Work split (sub-agents)

- **A, engineering:** broker, bar reader, NinjaScript exporter, runner script, and tests against a fake NT8 folder. It must check the ATI/OIF formats against NinjaTrader's official help.
- **B, research:** how to get free simulated or real-time MNQ data into NT8; how Lucid and Tradeify connect through NT8 and what they allow; and the exact setup steps for Jason.
- **C, QA:** an adversarial review of A's work, covering the Sim-only guard, duplicate or missing orders, restarts mid-session, stale bars and clock skew.

## Done when

- The tests pass, and a replay of practice days through the NT broker against the fake folder matches the backtest legs one for one.
- QA has no open High findings.
- Jason has a one-page setup guide: install NT8, enable ATI, add the indicator, run the command.
- A live Sim session waits for Jason to install NT8. I will not install software on his PC.
