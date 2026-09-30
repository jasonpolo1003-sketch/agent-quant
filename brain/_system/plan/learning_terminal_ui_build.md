---
id: PLAN-LEARNING-TERMINAL-UI
type: build_plan
status: draft
owner: jason
created: 2026-09-29
depends_on: PROP-010 (accepted; plan in learning_terminal_plan.md on branch testing)
lane: UI pages on branch ui-terminal (PROP-010 D6). Backend data lanes stay on testing.
---

# Learning Terminal: UI build plan (the "workspace" slice)

This is the **UI half** of PROP-010. It does not replace
`learning_terminal_plan.md`; it says how the pages get built, and it fixes
the complaint Jason raised on 2026-09-29:

> "it looks very confusing … you can't manipulate data on your own … make it
> feel like TradingView mixed with QuantConnect, sophisticated but simpler."

## 1. Why the current terminal feels confusing

1. **The pages are reports, not tools.** Every screen shows something the
   agents made; almost nothing lets you ask your own question.
2. **The chart is locked:**
   - 3 symbols and 3 fixed views;
   - no indicators to add, no settings to change;
   - no drawing, no range selection, no comparing arbitrary symbols.
3. **Nothing connects.** The backtest, the chart and the tutor live on
   different pages. On TradingView, the strategy's trades sit *on* the chart
   you are looking at.
4. **Six equal-weight pages.** There is no "home screen where you work",
   which on TradingView is the chart.

## 2. The idea in one line

**One main workspace, the Chart, where you can do everything yourself.**
Every other page is either a panel of that workspace or a door into it.

- **Simple:** open it and you see one clean chart with a watchlist.
- **Sophisticated:** every control is one click away and hidden until wanted
  (Beginner / Detail switch, PROP-010 principle 2).
- **You don't have to understand everything:** every number has a **?**,
  and every panel has **Explain this**, which sends the exact on-screen data
  to the tutor.

## 3. Layout (PROP-010 D7: TradingView layout, calmer terminal style)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [SPY ▾ search]  D W M  [+ Indicators] [Compare] [Replay] [Beginner|Detail]│  top bar
├──┬───────────────────────────────────────────────────┬──────────────────┤
│✚ │                                                   │ Watchlist        │
│╱ │            main chart (candles / line)            │  SPY  +0.4%  EOD │
│— │                                                   │  QQQ  ...        │
│📏│───────────────── RSI pane ─────────────────────────│──────────────────│
│⌫ │───────────────── MACD pane ────────────────────────│ Details / Learn  │
├──┴───────────────────────────────────────────────────┴──────────────────┤
│ Trades │ Selection stats │ Data table │ Strategy (lab)                    │  bottom drawer
└──────────────────────────────────────────────────────────────────────────┘
```

- **Left tool rail:** cursor, trend line, horizontal level, measure (from A
  to B: % change, days, drawdown inside the span), eraser. Drawings are saved
  per symbol in `db/terminal.sqlite`.
- **Right panel tabs:**
  - Watchlist: the starter universe, each row with a provenance badge;
  - Details: a "data window" with OHLC and every indicator value under the
    crosshair;
  - Learn: the tutor, preloaded with what you are looking at.
- **Bottom drawer tabs** (collapsible):
  - **Trades:** a backtest's trade list. Clicking one jumps the chart there.
  - **Selection stats:** drag a range to get return, max drawdown,
    volatility and best/worst day, beside buy-and-hold.
  - **Data table:** the exact numbers behind the chart, sortable, with CSV
    export.
  - **Strategy:** the Lab entry point (Phase 4 rule builder).
- The existing pages stay for their jobs: Today, Activity, Learn and Setup.
  **Markets becomes Chart** and moves first in the nav. **Strategies becomes
  Lab** and opens its backtests *inside* the Chart.

## 4. "Manipulate the data yourself": the interaction list

| # | You can… | How it works | Honesty guard |
|---|---|---|---|
| 1 | Pick any accepted symbol | Search box over the starter universe (`market/universe.py`) | Only Gate F-accepted datasets; the badge shows the source and age |
| 2 | Change the timeframe | Daily, weekly, monthly resampled server-side | Weekly/monthly bars built from the same daily file |
| 3 | Add, remove and configure indicators | SMA, EMA, Bollinger, RSI (Wilder), MACD, ATR, volume average; a settings dialog per indicator | SMA and RSI use **the engine's own functions** (`backtest/indicators.py`), so what you see equals what gets tested |
| 4 | Compare symbols | Overlay up to 4 symbols rebased to 100 | Shows total return with dividends |
| 5 | Chart a formula | `SPY/TLT`, `QQQ-SPY`, `XLK/XLU` (TradingView's "spread" charts) | Parsed by a tiny safe grammar (symbols, numbers, + − × ÷, parentheses); never `eval` |
| 6 | Measure and select | Drag across the chart for selection stats | The benchmark always sits beside the number |
| 7 | Replay history | Step or play bar by bar from any date; **blind mode** hides dates and ticker | Replay never reveals future bars |
| 8 | Replay a backtest's trades | Markers on the chart; click a trade to see the indicator values and the rule that fired it | Reads the exported replay JSON (`*.replay.json`) as-is |
| 9 | Look at the numbers | Data table plus CSV export of exactly what is on screen | Export includes a provenance header |
| 10 | Ask "what am I seeing?" | **Explain this** on every panel | The tutor gets the on-screen data and cites it |

Phase 4 (the rule builder) adds: build a rule from blocks, run an exploratory
backtest, and see the **trial counter**. That is its own slice (§8).

## 5. Architecture

- **Charts:** upgrade the bundled Lightweight Charts v4 to **v5**.
  - v5 has native multi-pane support for RSI/MACD panes, and the same
    Apache 2.0 licence.
  - Keep the **TradingView attribution** the licence requires (the chart's
    built-in attribution logo, plus a credit line in Setup).
  - Still vendored locally, so it works offline.
- **Frontend:** split the single `app.js` into small ES modules with no
  build step: `chart/`, `panels/`, `drawer/`, `api.js`, `state.js`.
  Workspace state (symbol, timeframe, indicators, drawings) sits in the URL
  hash plus `db/terminal.sqlite`, so a view can be reopened exactly.
- **New read-only endpoints** (`src/quant_brain/ui/`):
  - `GET /api/chart/bars?symbol&tf` returns adjusted/unadjusted OHLCV and
    provenance.
  - `POST /api/chart/indicators` takes a list of `{type, params}` and returns
    series.
  - `GET /api/chart/expr?f=SPY/TLT&tf` evaluates the safe formula.
  - `GET /api/chart/stats?symbol&from&to` returns selection stats beside
    buy-and-hold.
  - `GET /api/replays`, `GET /api/replays/{id}` return the trade-replay
    exports.
  - `GET/POST/DELETE /api/drawings` store drawings in `terminal.sqlite`.
  - `GET /api/watchlist` returns the universe with last close, change and
    badge.
- **Uses the other lane read-only:** `market/universe.py`,
  `market/replay.py` output, `market/risk.py`, `backtest/indicators.py`.
  The UI never edits `src/quant_brain/{market,backtest,data}`.

## 6. Decisions already made

- **vectorbt: not used.**
  - Its licence is Apache 2.0 **with the Commons Clause**, rejected by name
    in PROP-007.
  - Its strength is running thousands of parameter combinations in seconds.
    Without a trial ledger, that is exactly how beginners fool themselves.
    PROP-010 keeps the in-repo engine (D5) and puts a trial counter in front
    of every exploratory run.
  - Revisit only if a frozen card needs a grid too large for the in-repo
    engine, and then as a PROP.
- **OpenBB:** stays a separate exploration tool (user-level install), not a
  dependency.
- **TradingView Advanced Charts:** ruled out by PROP-010 §6 (its licence
  requires public use).

## 7. Coordination (no cross-over)

1. **Before building,** merge `testing` into `ui-terminal` inside the
   worktree. This brings in PROP-009/010, `market/` and the replay exports.
   The main checkout is never switched.
2. **UI-owned paths:** `src/quant_brain/ui/`, `ui/static/`,
   `tests/test_ui_*.py`, `scripts/serve_terminal.py`.
3. **Backend requests go to the testing lane as notes,** not edits. For
   example: "export replays for rules B and D too", or "a weekly-bar helper
   in market/".
4. **Merge timing:** `ui-terminal` merges into `testing` at the end of each
   slice, when that checkout is idle (a clean tree).

## 8. Build slices (each ends with something usable)

| Slice | Delivers | Exit test (observable) |
|---|---|---|
| W0 | Merge testing; Lightweight Charts v5; module split; Chart page shell with symbol search, timeframe, watchlist and badges | Open any starter symbol in D/W/M; the badge shows source and age; no console errors |
| W1 | Indicators with settings, extra panes, data window, compare, formula charts | RSI(2) on SPY equals the engine's value on 2021-06-17 to 1e-9; `SPY/TLT` matches a hand calculation on 3 dates |
| W2 | Drawings, measure, selection stats, data table, CSV export | A 2020-02-19 → 2020-03-23 selection shows SPY about −34% and matches a hand SQL query |
| W3 | Trade Replay (PROP-010 Phase 1 exit) and Replay with blind mode | SC-0002 held-out trade #41 opens; its fills and indicator values match the report; blind mode never shows a future bar |
| W4 | Explain-this on every panel; Beginner/Detail switch; the old pages folded in (Markets becomes Chart, Strategies becomes Lab) | A first-time user can say what the screen shows within 10 seconds (Jason's check) |
| W5 | Rule-builder UI on the backend's exploratory engine, with the trial counter | Rebuilding SC-0002 rule A reproduces its 91 held-out trades, labelled Exploratory |

## 9. Verification (every slice)

- Hermetic pytest for every endpoint, with fixture datasets and no network.
  The `brain.sqlite` hash must be unchanged by reads.
- A Playwright script drives the real page in Chrome and fails on any
  console error.
- Screenshots of each slice go in the slice summary for Jason.
- Taste-skill pre-flight rules for copy:
  - one accent colour;
  - no em-dashes in UI text;
  - plain labels;
  - sentence-case headings.

## 10. Not in this plan

- Live feeds (PROP-010 Phase 5) and the practice account (Phase 6).
- Paid data.
- Pine Script.
- Mobile.
- Anything that places an order.
