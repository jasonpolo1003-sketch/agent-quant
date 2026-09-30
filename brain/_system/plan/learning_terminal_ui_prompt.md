# Builder prompt: Learning Terminal pages (PROP-010, free tier)

You are working in: `C:\Users\jason\OneDrive\Desktop\quant-agent-brain-ui` (branch `ui-terminal`). Never `git switch` in the main checkout.

**Goal**
Turn the Brain Terminal into a beginner-first, TradingView-style learning workspace on top of the free-data backend that now exists on `testing`.

**Context**
- Jason accepted PROP-010 on 2026-09-29, free tier first, with lighter process gates. Plan: `brain/_system/plan/learning_terminal_plan.md` on `testing` (read §2 principles, §4 feature map, §5 teaching core).
- First merge `testing` into `ui-terminal`. This branch predates the backtest runner and the new `quant_brain.market` package.
- **Backend you can use** (read-only; `testing` commits `d5f111a..6a834c5`):
  - `market/replay.py`, with files `brain/04_Backtest_Reports/SC-0002-*.replay.json`: bars, indicators, signal flags, and trades with `why_entry`/`why_exit`.
  - `scripts/market_snapshot.py` (`build()`), producing `data/processed/market_snapshot.json`: 45-symbol screener rows, each with a `provenance` badge; presets with why/trap; a 1-year correlation matrix.
  - `scripts/fetch_calendar.py`, producing `data/processed/calendar.json`: FOMC, FRED releases and earnings, each with a source and a "why it matters" note.
  - `market/risk.py`: position size, drawdown table, Kelly, risk-of-ruin simulation, portfolio heat. Each result has an `explain` line.
  - `market/live_crypto.stream()`: an async generator of ticker/trade/book/candle/status events from Coinbase, with no key. Bridge it to SSE.
  - `data/processed/fundamentals/<SYM>.json` (SEC EDGAR) is empty until Jason sets `SEC_USER_AGENT`. Show an empty state that says so.

**Success criteria**
- The chart page follows the TradingView layout: centre chart, watchlist on the left, a Learn panel on the right, and bottom tabs for Replay/Screener/Calendar/Risk. It has a Beginner/Detail toggle.
- Trade Replay of SC-0002 held-out: clicking trade #41 zooms to 2021-06-18..06-22 and shows RSI(2) 1.8, SMA200 351.00, SMA5 391.61, and +0.87%, matching the file.
- The screener's rows and presets equal the snapshot, and each preset shows its "why" and "trap".
- The calendar lists the FOMC decision on 2026-10-28 with its source.
- In the Risk Center, every calculator shows its `explain` line.
- Live crypto shows a price, a 10-level order book with spread, and 1-minute candles. Dropping the network shows "Feed paused" within about 10 s.
- Every number carries its source and freshness badge (LIVE / END OF DAY). The Lightweight Charts attribution to TradingView is visible.
- Hermetic tests pass: no network in pytest.

**Constraints**
- The server binds to `127.0.0.1` only. Yahoo data is personal-use only.
- No buy/sell buttons or order forms, and no broker calls (the practice account is a later, separate decision).
- `brain.sqlite` stays read-only. Don't edit `quant_brain/market` or `backtest`; if the backend needs changes, list them for Claude on `testing`.
- Keep the calmer terminal style and plain-language copy.

**Deliverables**
Pages, API routes, tests, and a short handoff note with screenshots of each page.

Plan first: send the plan (pages, routes, data flow, test list) and do not implement until Jason approves. Stop after the pages above are built and verified.
