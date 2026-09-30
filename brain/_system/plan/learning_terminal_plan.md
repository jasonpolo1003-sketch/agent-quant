---
id: PLAN-LEARNING-TERMINAL
type: phase_plan
status: proposed
owner: jason
created: 2026-09-29
depends_on: PROP-010 (proposed); builds on PROP-008 (Brain Terminal, branch ui-terminal) and PROP-009 (FRED, proposed)
---

# Quant Learning Terminal: a local, beginner-first TradingView + QuantConnect

Parent: [../../../PLAN.md](../../../PLAN.md) · Proposal: PROP-010 in [plan_change_proposals.md](plan_change_proposals.md)

> **Status: proposed, not accepted.** Nothing here is built until Jason accepts PROP-010 and answers the decisions in §11.
> It is a plan, not a promise. §9 says plainly where "1-to-1 with TradingView" cannot happen for free.

## 1. What it is

A **local app, running only on Jason's PC**, that looks and feels like TradingView and teaches like QuantConnect's Boot Camp.
- **From TradingView:** charts, watchlists, a screener, heatmaps, calendars, news and bar replay.
- **From QuantConnect:** a strategy lab and a structured way of thinking: universe → signal → sizing → risk → execution → evaluation.
- **What neither has:** a **teacher on every screen**. The teacher explains what you are looking at, why a quant cares, and what the common trap is.

The goal is not to make a beginner trade. It is to make a beginner **think like a quant**: form a hypothesis, write exact rules, test them honestly, size risk before hoping for returns, and accept "no edge" as a normal answer.

It extends the existing Brain Terminal (FastAPI + vanilla JS, six plain-language pages, Lightweight Charts already bundled). It is not a second app.

## 2. Principles (every feature is checked against these)

1. **Learn-first.** Every screen has a one-line "what this page is for", a **?** on every number, and an **Explain this** button. That button sends the exact on-screen data to the tutor (PROP-008's no-tools, cite-your-sources tutor).
2. **Simple by default, deep on request.** A **Beginner / Detail** switch. Beginner shows fewer numbers, plain words and guided steps; Detail shows everything.
3. **Honest.** Nothing shows a profit figure without its benchmark and a "not proof of future profit" note. The first case study is a strategy that **failed** (SC-0002).
4. **Every number shows where it came from.** Each price or statistic carries a badge: source, **LIVE / DELAYED 15m / END OF DAY**, and how old it is. The same idea as Gate F provenance, made visible.
5. **Free first; paid only by decision.** §8 lists what money would buy; nothing is bought by default.
6. **No real money, ever.** No broker order routing and no live trading (AGENTS.md). Any "practice" mode is a local simulation (decision D3).
7. **Local and private.** The server binds to `127.0.0.1` only. Several free sources, Yahoo included, are **personal-use only**, so nothing is published or shared publicly.

## 3. How a quant thinks: the spine of the app

QuantConnect's Algorithm Framework splits a strategy into stages ([QuantConnect Boot Camp](https://www.quantconnect.com/docs/v2/cloud-platform/learning-center/training)). We use the same stages as the **navigation of the Lab and the chapters of the Academy**. The beginner learns one mental model and sees it everywhere.

| Stage | Question a quant asks | Where the app teaches it |
|---|---|---|
| 1. Universe | What am I allowed to trade, and why? | Screener, universe builder, survivorship lesson |
| 2. Signal (alpha) | What exact, testable rule says "buy" or "sell"? | Chart indicators, rule builder |
| 3. Sizing | How much do I put in each trade? | Position-size calculator, risk-of-ruin simulator |
| 4. Risk | What is the most I can lose, and what stops me? | Risk Center: stops, drawdown, exposure, correlation |
| 5. Execution | What price do I really get, and at what cost? | Costs and slippage lesson, live order-book view (crypto) |
| 6. Evaluation | Is it better than doing nothing, and than luck? | Lab report: benchmark, random entry, deflated Sharpe, held-out data |

## 4. Feature map: TradingView / QuantConnect → ours

"Phase" refers to §7. "Free?" means free at the level described.

| Their feature | Our version | Data source (§6) | Free? | Phase |
|---|---|---|---|---|
| TV Supercharts | Candles, volume, overlays (SMA/EMA/Bollinger), lower panes (RSI, MACD), drawing basics (lines, horizontal levels), multi-timeframe (D/W/M) | Local EOD Parquet | Yes | 1 |
| TV Watchlist | Watchlist panel with last price, change and a provenance badge | EOD; live later | Yes | 1 |
| TV Bar Replay ([TV](https://www.tradingview.com/support/solutions/43000712747-bar-replay-how-and-why-to-test-a-strategy-in-the-past/)) | **Replay**, plus a **blind mode** that hides the date and ticker, so the learner decides without hindsight | Local EOD | Yes | 1 |
| QC backtest report | **Trade replay** of any backtest: markers on the chart, click a trade to see the indicator table that caused it | Backtest outputs | Yes | 1 |
| TV Screener | Screener over a starter universe: price, % change, RSI, distance from SMA200, volatility, sector | EOD + EDGAR SIC codes | Yes | 2 |
| TV Heatmap | Sector/stock heatmap sized by market cap, coloured by % change | EOD + EDGAR shares outstanding | Yes | 2 |
| TV Economic Calendar | Calendar of CPI, jobs, GDP, FOMC, with "why markets care" notes | FRED release dates, Fed FOMC calendar | Yes | 2 |
| TV Earnings Calendar | Upcoming earnings for the watchlist | Finnhub free (1 month ahead), yfinance | Yes (limited) | 2 |
| TV Symbol page | Company page: what it does, filings, key financials over time | SEC EDGAR companyfacts | Yes | 2 |
| TV News | Headlines per symbol and market-wide, each with a timestamp and source link | SEC filings RSS, GDELT, Finnhub company news | Yes | 3 |
| TV Strategy Tester / Pine | **Rule builder** (no-code blocks) → exploratory backtest → optional frozen card | Local engine | Yes | 4 |
| QC Boot Camp | **Academy**: short lessons, each with a real-data chart, an exercise and a quiz | Local | Yes | 3 |
| QC Risk Management model | **Risk Center**: position sizing, stop placement, drawdown math, risk of ruin, correlation | Local | Yes | 3 |
| TV live prices | Live crypto (full), live US stocks (IEX only on free plans) | Coinbase WS; Alpaca/Finnhub free | Yes, partial | 5 |
| TV Paper Trading | **Practice account**: a local simulation, no broker | Local + live/EOD | Yes | 6, **only if D3 = yes** |
| TV Alerts | Local alerts ("SPY closes below SMA200") shown in-app | Local | Yes | 5 |
| TV Ideas / community | Replaced by the **Journal**: your own ideas, predictions and graded outcomes | Local | Yes | 4 |
| QC LEAN engine ([Apache 2.0](https://github.com/QuantConnect/Lean/blob/master/LICENSE)) | Keep our small, readable engine for teaching; LEAN stays an optional later "graduate" path (D5) | n/a | Yes | Later |
| TV options chains, futures, global markets, Level 2 stocks | **Out of scope for free** (§9) | Paid only | No | §8 |

## 5. The Academy and the Risk Center (the teaching core)

### 5.1 Lesson format (every lesson, no exceptions)
1. **The idea in one sentence.**
2. **See it on a real chart:** the lesson opens a chart already set up (for example SPY in 2008 to show a drawdown).
3. **Try it:** one small interactive task, such as "move the stop and watch the risk change".
4. **The trap:** the mistake beginners make.
5. **Check:** 2–3 quiz questions, stored locally, with progress per module.
6. **Go deeper:** links to the primary sources, and to the tutor with this lesson preloaded.

### 5.2 Curriculum (order is deliberate: risk before signals)
| # | Module | Key ideas | Built on |
|---|---|---|---|
| 0 | Reading a market | Candles, volume, timeframes, bid/ask, what an ETF is | Chart, live crypto book |
| 1 | Returns | Simple vs log returns, compounding, why −50% needs +100% | Calculator on SPY history |
| 2 | Risk | Volatility, drawdown, Sharpe in plain words, why the average hides the worst day | SPY vs QQQ vs IWM |
| 3 | **Sizing and risk management** | Risk per trade (1–2% rule as a convention, not a law), stop distance → position size, risk of ruin, why Kelly is dangerous at full size | Risk Center simulators |
| 4 | Diversification | Correlation, why it rises in crashes (2020), portfolio vs single bet | Correlation matrix from EOD |
| 5 | Costs and execution | Spread, commission, slippage, how 10 bps kills a small edge | SC-0002 cost table |
| 6 | Thinking like a quant | Hypothesis → exact rules → test → validate; the six stages of §3 | Rule builder |
| 7 | Backtest traps | Lookahead, survivorship, overfitting, data snooping | Lab demos that deliberately cheat, then show the fix |
| 8 | Is it better than luck? | Benchmark, random entry, held-out data, multiple testing, deflated Sharpe | Lab report |
| 9 | Regimes and macro | Rates, recessions, VIX; why a strategy works in one decade and not the next | FRED (PROP-009) |
| 10 | **Case study: SC-0002** | A real, fully logged strategy that failed honestly, walked through trade by trade | This repo's reports and review |
| 11 | Portfolio thinking | Rebalancing, equal weight vs risk parity, one strategy vs many | Lab |

Lesson text is written by us and reviewed. Facts link to primary or official sources, for example [Investor.gov on position sizing](https://www.investor.gov/introduction-investing/investing-basics/glossary/position-sizing), FINRA, the Fed and SEC. The tutor may explain but never be the only source (PROP-008 rule).

### 5.3 Risk Center (interactive tools)
- **Position-size calculator:** account size, risk %, entry, stop → shares, and the dollar risk shown in words.
- **Risk-of-ruin simulator:** win rate, payoff and risk per trade → thousands of simulated paths, showing the chance of losing X%.
- **Drawdown recovery table:** the loss and the gain needed to get back to even.
- **Portfolio heat:** total risk if every stop is hit at once.
- **Correlation matrix** of the watchlist, with a "they all fell together in 2020" replay.

### 5.4 Built-in honesty features (the QuantConnect lesson TradingView does not teach)
- **Trial counter** in the rule builder: "You have tried 23 variations of this idea. The best-looking one is expected to look this good by luck alone." The multiple-testing lesson, live.
- **Sandbox vs frozen:** rule-builder runs are labelled **Exploratory**. Only a frozen card through the existing gated runner (PROP-007) earns a verdict. The Lab shows both side by side, so the difference is learned by doing.

## 6. Data: sources, labels and limits

Tiers follow `research_source_quality_policy.md` in spirit: **A** = official or first-party documentation; **B** = the vendor's own docs; **reported** = a third-party article, **to be verified before building**.

### 6.1 Free sources (the default stack)
| Need | Source | Access | Limits and terms | Tier |
|---|---|---|---|---|
| Daily prices, stocks/ETFs | Yahoo via `yfinance` (already Gate F) | No key | **Personal use only**; unofficial and can break ([yfinance](https://github.com/ranaroussi/yfinance)) | Existing |
| Macro, rates, VIX, recession flag | FRED API | Free key | ~2 requests/sec; release-dates endpoint for the calendar ([FRED API](https://fred.stlouisfed.org/docs/api/fred/), [releases/dates](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html)) | A |
| FOMC meeting dates | Federal Reserve | Page | Dates are tentative until confirmed ([Fed calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)) | A |
| Company financials, filings | SEC EDGAR `data.sec.gov` | No key; User-Agent with contact | Max ~10 requests/sec ([SEC developer](https://www.sec.gov/developer)) | A |
| Filing news | SEC RSS feeds | No key | Every 10 min on weekdays ([SEC RSS](https://www.sec.gov/structureddata/rss-feeds)) | A |
| Symbol universe | Nasdaq Trader symbol directory | No key | Daily text files of all listed symbols | A (verify URL) |
| Live crypto: trades, candles, order book | Coinbase Advanced Trade WebSocket | **No key** for public channels | level2, ticker, candles, market_trades ([Coinbase docs](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/guides/websocket)) | B |
| Live US stocks | Alpaca Basic (free) | Free account + key | **IEX only, ~2.5% of US volume**; 1 connection; 30 symbols for trades/quotes ([Alpaca data docs](https://docs.alpaca.markets/us/docs/about-market-data-api)) | B |
| Live US stocks, alternative | Finnhub free | Free key | 60 calls/min; WebSocket ~50 symbols; earnings calendar 1 month ([pricing](https://finnhub.io/pricing)) | Reported, verify |
| Company news | Finnhub free, GDELT DOC API | Key / none | GDELT covers a rolling 3 months ([GDELT](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)) | B / reported |
| Charts | TradingView **Lightweight Charts** | Bundled already | Apache 2.0; **attribution to TradingView required** ([license](https://github.com/tradingview/lightweight-charts/blob/master/LICENSE)) | A |

**Not usable:** TradingView **Advanced Charts**. Its free licence requires a *public* web project, not private use ([FAQ](https://www.tradingview.com/charting-library-docs/latest/getting_started/Frequently-Asked-Questions/)). Also **not usable**: any "TradingView data API" resellers, since provenance is unclear and they likely breach TradingView's terms.

### 6.2 Live-data rules
- Every live price shows **which feed** it is. "LIVE · IEX" is taught as a lesson: why an IEX price can differ from the consolidated price.
- Live data is **display and practice only**. Backtests and cards use stored, hashed EOD datasets (Gate F rules), never a live stream.
- Crypto is the **main live classroom**: free, 24/7, with a full order book. It suits lessons on spreads, order books and slippage.
- Reconnect, rate-limit and outage states are shown plainly ("Feed paused: reconnecting"), never hidden.

### 6.3 Storage
- EOD bars and fundamentals go to Parquet + DuckDB, with a manifest per dataset (sha256, source, time, limits), reusing the Gate F module.
- Live ticks stay **in memory** with a small rolling cache. They are not committed.
- Refresh jobs use the existing terminal scheduler allowlist (`data_refresh`), with an API-budget meter per source.
- Keys go in the git-ignored `.env`, as in PROP-009. They are never logged or shown in the UI.

## 7. Phases (each one ends with something Jason can use)

| Phase | Name | Delivers | Exit test (observable) |
|---|---|---|---|
| 0 | Accept | PROP-010 accepted, decisions D1–D8 answered | Answers recorded in PROP-010 |
| 1 | **See it** | TradingView-style chart page, watchlist, Replay + blind mode, **Trade Replay** of SC-0002 | Jason opens SC-0002 trade #41 (2021-06-18 → 06-22) and sees the signal, fills and indicator values matching the report |
| 2 | **Market data breadth** | Starter universe (D4), FRED lane (PROP-009), EDGAR fundamentals, economic/FOMC/earnings calendar, screener, heatmap, symbol page | Screener returns the same rows as a hand SQL query; every page shows a provenance badge; the calendar matches the Fed's page for FOMC dates |
| 3 | **Learn it** | Academy modules 0–5 and 10, Risk Center, glossary, Explain-this, news panel | A non-expert (Jason or Drew) completes modules 0–3 and passes the quizzes; every lesson fact has a source link |
| 4 | **Test it** | Rule builder, exploratory backtests with trial counter, honest report, Journal, bridge to frozen cards; Academy 6–8 | Rebuilding SC-0002 rule A in the builder reproduces its 91 held-out trades exactly (labelled Exploratory) |
| 5 | **Live** | Coinbase live crypto chart and order book, IEX live stocks (D2), in-app alerts, feed-status badges | A 1-hour live session with no silent gaps; unplugging the network shows "Feed paused" within 10 s |
| 6 | **Practice** (only if D3 = yes) | Local simulated account: market/limit/stop orders against live or replay data, **risk rules enforced** (max risk per trade, max portfolio heat), graded journal | An order breaking the risk rule is refused with a plain explanation; nothing ever contacts a broker |
| 7 | Upgrades (optional) | Any paid source Jason chooses from §8, behind the same provenance badges | Chosen per decision |

Phase 1 needs almost nothing new: the terminal, the charts and the data already exist, and the trade-replay export was already proposed to Jason. Phases 3 and 4 carry the most teaching value, so they take priority over live data (Phase 5), which costs the most to maintain.

## 8. What money would buy (researched; nothing bought by default)

Prices are what the sources state on 2026-09-29. **"Reported"** means a third-party article; confirm on the vendor's page before paying.

| Want | Option | Price | Why you might pay | Recommendation |
|---|---|---|---|---|
| Full real-time US stocks (all exchanges) | Alpaca Algo Trader Plus | Paid monthly (reported ~$9–$99; verify) | IEX-only shows ~2.5% of volume | Only if live stock lessons feel wrong on IEX |
| Delayed or real-time US stocks, long history | Massive (formerly Polygon.io) | Reported: $0 EOD / $29 delayed / $79 / $199 real-time | Clean API, trades and quotes | Not needed for daily research |
| Cheap broad EOD + news | Tiingo Power | Reported ~$10/mo | More symbols, higher limits, news API | Good first paid step if Yahoo breaks |
| Tick or order-book data | Databento | Usage-based; $125 free credits for new accounts ([Databento](https://databento.com/docs/faqs/usage-pricing-and-data-credits)) | Microstructure lessons on real stock order books | Later, with the free credit |
| **Survivorship-free history, including delisted stocks and index members** | Norgate Data | Reported ~$270–788/yr | The only honest way to backtest stock-picking strategies | **Best research value** if stock-selection cards happen |
| Options chains, Greeks, IV history | ORATS, Cboe DataShop, etc. | Varies; OPRA licensing applies | Options lessons with real data | Out of scope until an options module is wanted |
| Just use TradingView itself | TradingView Plus/Premium | $28.29/$56.49 a month billed annually; real-time exchange data is **extra** ([pricing](https://www.tradingview.com/pricing/)) | Its screener, alerts and deep backtests | Honest alternative for the parts §9 cannot copy |

**Recommendation:** $0 through Phase 5. The first paid item, if any, should be **Norgate** (research integrity), not live data (it looks exciting but teaches little more than crypto already does).

## 9. Honest limits: where "1-to-1" cannot happen

- **Data breadth.** TradingView licenses feeds from many exchanges worldwide. For free we get US daily bars, IEX-only live stocks, full live crypto, US macro and US filings. No free global markets, futures, options or Level 2 stocks.
- **Intraday history.** Free sources give little minute-level history for stocks. Replay and backtests are daily.
- **Survivorship.** The free universe is today's listed stocks. Stock-picking backtests on it are biased upward, which the Academy teaches (module 7) and the Lab warns about.
- **Pine Script.** We do not clone Pine. The rule builder covers beginner rules; Python is the "graduate" path.
- **Community and ideas.** Not copied. The Journal replaces them.
- **Maintenance.** Every free source can change or break (Yahoo especially). Each lane has a verifier and fails loudly, never silently.

## 10. Non-goals
Live trading; broker order routing (including broker paper-trading APIs, unless D3 says otherwise); public hosting or sharing data; mobile apps; social features; Pine compatibility; predicting prices; any "signals to trade" feature.

## 11. Decisions for Jason (recommended defaults in bold)
- **D1 Scope order:** **the §7 order (see → data → learn → test → live → practice)**, or live data first.
- **D2 Live stock feed:** **Alpaca Basic (IEX)**, which needs a free Alpaca account used for data only; or Finnhub free; or none (crypto only).
- **D3 Practice account:** **yes, local simulation only, Phase 6**, which amends PROP-007's "no paper trading" to allow it; or no.
- **D4 Starter universe:** **~40 symbols: SPY/QQQ/IWM, the 11 SPDR sector ETFs, bond/gold/dollar ETFs, and ~20 large caps**; or the current S&P 500 (heavier, and survivorship-biased).
- **D5 Engine:** **keep the in-repo engine** (readable, already verified); or adopt LEAN locally (more features, much bigger to learn).
- **D6 Who builds:** **the UI agent builds pages on `ui-terminal`; backend data lanes land on `testing` first, then merge** (this avoids two agents in one checkout); or one agent does both.
- **D7 Look:** **TradingView layout (left tools, centre chart, right watchlist/learn panel, bottom Lab/Screener/Calendar tabs) inside the calmer terminal style**; or a closer TradingView visual clone.
- **D8 Beginner audience:** **Jason first, written so Drew or any beginner can follow**; or also plan multi-user (not recommended: licensing, §2.7).

## 12. How each phase is built (process, unchanged from the project rules)
- Plan first, then build, then an independent review, per phase. Stop for Jason between phases.
- Tests are hermetic: small committed fixtures, with no network in pytest.
- Every new data lane gets the Gate F treatment: immutable file, manifest, verifier, accepted-only loader.
- The UI never writes to `brain.sqlite`. Academy progress and practice trades live in `db/terminal.sqlite`.

## 13. Sources (checked 2026-09-29)
- TradingView: [pricing](https://www.tradingview.com/pricing/), [Bar Replay](https://www.tradingview.com/support/solutions/43000712747-bar-replay-how-and-why-to-test-a-strategy-in-the-past/), [free charting libraries](https://www.tradingview.com/free-charting-libraries/), [Advanced Charts FAQ](https://www.tradingview.com/charting-library-docs/latest/getting_started/Frequently-Asked-Questions/), [Lightweight Charts licence](https://github.com/tradingview/lightweight-charts/blob/master/LICENSE)
- QuantConnect: [LEAN licence](https://github.com/QuantConnect/Lean/blob/master/LICENSE), [Learning Center training](https://www.quantconnect.com/docs/v2/cloud-platform/learning-center/training), [Boot Camp](https://www.quantconnect.com/learning/course/1/Boot-Camp-101-US-Equities)
- Data: [FRED API](https://fred.stlouisfed.org/docs/api/fred/), [FRED release dates](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html), [Fed FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), [SEC developer resources](https://www.sec.gov/developer), [SEC RSS](https://www.sec.gov/structureddata/rss-feeds), [Coinbase WebSocket](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/guides/websocket), [Alpaca market data](https://docs.alpaca.markets/us/docs/about-market-data-api), [Finnhub pricing](https://finnhub.io/pricing), [GDELT DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [Databento credits](https://databento.com/docs/faqs/usage-pricing-and-data-credits), [Norgate](https://norgatedata.com/), [yfinance](https://github.com/ranaroussi/yfinance)
- Reported (third party; verify before relying): Massive/Polygon plan prices, Tiingo limits, Finnhub free-tier limits, Alpaca paid plan price, Norgate annual range.
- Education: [Investor.gov position sizing](https://www.investor.gov/introduction-investing/investing-basics/glossary/position-sizing)
