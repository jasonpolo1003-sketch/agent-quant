---
title: Package 7 — Bar-fill ambiguity for MES/MNQ ORB backtests
status: unreviewed
promoted: false
package: 7
date: 2026-10-22
---
# Bar-fill ambiguity (options only; no policy chosen, no strategy code, no parameters)

Labels used here:
- **OFFICIAL FACT**: CME or Topstep's own documentation.
- **VENDOR METHOD**: how a platform says it simulates fills. These describe that vendor's software, not market truth.
- **CONVENTION**: research practice.
- **QAB ENGINEERING POLICY**: an option still open for decision.

Quote IDs (B#) refer to `quote_verification.tsv`; 27/27 string-matched after whitespace normalization. All retrievals are dated 2026-10-22.

## Claim-level provenance
| ID | Label | Source / URL | Instrument | Timeframe | Transferability to MES/MNQ ORB |
|---|---|---|---|---|---|
| B1–B5 | OFFICIAL FACT | CME Client Systems Wiki, Order Types for Futures and Options: https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457087412/Order+Types+for+Futures+and+Options (snapshot: costs/cme_wiki_order_types) | All CME Globex futures (example uses ES) | Live matching | Direct: matching-engine behaviour for MES/MNQ stops |
| B6 | OFFICIAL FACT | CME Velocity Logic: https://www.cmegroup.com/confluence/display/EPICSANDBOX/Velocity+Logic (costs/cme_velocity_logic) | All Globex futures; tick/time thresholds per product not retrieved | Live | Direct (mechanism); the thresholds are unknown |
| B7–B8 | OFFICIAL FACT | CME equity price limits FAQ: https://www.cmegroup.com/trading/equity-index/us-based-equity-index-futures-price-limits-faq.html (costs/cme_us_equity_price_limits_faq) | ES/NQ family incl. micros | Live | Direct |
| B9–B10 | OFFICIAL FACT (venue rule) | Topstep help, When and what products can I trade: https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade (venue/ts_hours_products) | Topstep accounts | Daily | Direct for Topstep accounts only |
| B11–B14 | VENDOR METHOD | TradingView Pine docs, Strategies: https://www.tradingview.com/pine-script-docs/concepts/strategies/ | Any | Bar backtests | Describes TradingView's software only |
| B15–B17 | VENDOR METHOD | NinjaTrader 8 help, Understanding Historical Fill Processing: https://ninjatrader.com/support/helpguides/nt8/understanding_historical_fill_.htm | Any | Bar backtests | Same |
| B18–B21 | VENDOR METHOD | QuantConnect LEAN docs, Future fill model and Trade Fills key concepts: https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/supported-models/future-model and .../trade-fills/key-concepts | Futures | Tick/quote/trade bars | Same |
| B22–B24 | VENDOR METHOD | backtrader docs, order creation/execution and slippage: https://www.backtrader.com/docu/order-creation-execution/order-creation-execution/ and https://www.backtrader.com/docu/slippage/slippage/ | Any | Bar | Same |
| B25–B26 | CONVENTION (published research) | Fetna 2026, SSRN 7428398 (orb/fetna_2026_orb_225cell.pdf) | ES/NQ + 7 other futures | 1-min | Close; the same class of strategy |
| B27 | CONVENTION (practitioner lead) | cemarketsolutions NQ ORB page (orb/) | NQ | 1-min | LEAD only |

Not retrieved:
- MultiCharts Bar Magnifier (HTTP 403).
- NinjaTrader's separate "fill limit orders on touch" page.
- CME per-product protection-point and Velocity Logic threshold tables for MES/MNQ.
- Any academic study of limit-order queue position specific to MES/MNQ.

## Key facts and vendor methods
**What CME's matching engine does (OFFICIAL FACT).**
- CME stop orders trigger on a *trade* at or through the trigger price.
- A stop with protection becomes a market order, but it fills only within a protection range. Any remaining quantity **rests on the book at the protection limit** (B1, B2, B4).
- A stop-limit becomes a limit order and can go unfilled (B2, B3). So in a fast move a live stop can fill partially or late. It does not have to fill at the trigger price or at the bar's open.
- Buy stops must be above the last trade (B5). A stop placed on the wrong side of the market during an entry bar is rejected, not filled.
- Velocity Logic puts the instrument into a reserved (paused) state (B6).
- Price-limit events halt trading for 2 minutes (B7), and a regulatory halt resumes after 10 minutes (B8). During these pauses no fill is possible at any price inside the paused interval.

**Topstep flatten rule (OFFICIAL FACT).**
- Positions must be closed by 3:10 PM CT (4:10 PM ET) (B9).
- Risk Managers begin flattening at 3:08 PM CT (4:08 PM ET) (B10).
- The forced-exit price is not specified by Topstep, so it is unknown. A backtest exit "at the close" (4:00 PM ET cash close, or the 4:15 ET futures daily close) is a different time from Topstep's 4:08–4:10 PM ET window.

**How backtest vendors fill orders (VENDOR METHOD).**
- **TradingView and NinjaTrader (standard mode):** assume the bar's path from the open's proximity to the high or low: open→high→low→close if the open is closer to the high (B11, B15).
- **TradingView:** treats any price inside the bar as fillable, with no intrabar gaps (B12). Orders crossed in a gap between bars fill at the next bar's open (B13). An optional lower-timeframe "bar magnifier" mode exists (B14).
- **NinjaTrader:** has an optional secondary series (B16) and caps slippage at the next bar's high/low (B17).
- **QuantConnect, TradeBar data:**
  - stops fill at the worse of the stop price and close ± slippage (B18), and only while the exchange is open (B20);
  - limits require a strict trade-through (low < limit; B19);
  - backtests assume complete fills (B21).
- **backtrader:**
  - a stop gapped through at the open fills at the open (B22);
  - a limit counts as filled if the bar's low touches it (B23);
  - slippage matching is optionally capped (B24).
- **Fetna (CONVENTION):** when stop and target are touched in the same bar, the stop fills first; a bar that gaps through a level fills at its open (B25); no trade when both sides break on the same bar (B26).

## Condition → response OPTIONS (no option chosen; all are QAB ENGINEERING POLICY candidates)

**1. Stop and target both touched in the same bar**
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. Stop first (worst case) | Conservative; simple; matches published ORB work | Biases expectancy down; can reject real edges built on targets | B25 |
| b. Infer the path from the open's proximity to the high/low | Used by major vendors; often more realistic | A heuristic that has not been validated for MES/MNQ 1-minute bars; a bar-close entry is itself the bar's open | B11, B15 |
| c. Resolve on finer data (seconds or ticks); fall back to (a) where unavailable | Closest to truth | Needs data that is not approved yet | B14, B16 |
| d. Report (a) and (b) as bounds, with the share of trades affected | Shows how sensitive the result is | Two numbers to interpret | CONVENTION (Package 6 sensitivity arms) |
| e. Drop ambiguous trades | No assumption needed | Selection bias, because ambiguous bars are the high-volatility ones | — |

**2. Entry and stop in the same bar** (e.g., a stop-entry breakout bar that also reaches the stop)
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. Signal on bar close, enter at the next bar's open (removes same-bar entry) | No look-ahead; the stop can be placed live after the fill | Worse entry price; a different strategy from a stop-entry | B26 (next-open entry), B27 |
| b. Stop-entry intrabar; if the stop is also inside the bar, count it as a loss | Conservative | Overstates losses when the true path went the favourable way first | CONVENTION |
| c. Path heuristic as in 1b | Vendor practice | Unverified | B11 |
| d. Finer-data resolution | Accurate | Data not approved | — |
| e. Flag a stop that is invalid relative to the last trade (rejected order) | Matches CME rules | Needs tick-level last-trade data | B5 |

**3. Gap through a stop** (overnight/RTH open, news, between bars)
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. Fill at the next bar's open | Common vendor practice; conservative versus the stop price | Bar open ≠ first tradable price in a halt or reopen | B13, B22, B25 |
| b. Fill at the stop price | Simple | Optimistic; contradicts CME trigger mechanics | (no support) |
| c. Fill at open plus extra slippage, capped by the protection range | Closer to stop-with-protection behaviour | MES/MNQ protection points not retrieved | B1, B4 |
| d. Stop-limit model: a no-fill is possible, so the position stays open | Matches stop-limit semantics | Needs an extra rule for when to exit | B2, B3 |

**4. Limit fills and queue position** (targets, limit entries)
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. Fill on touch (low ≤ limit) | Generous; vendor default in places | Overstates fills; ignores the queue | B23 |
| b. Require a trade-through by ≥1 tick | Common proxy for a queue | Understates fills at round levels | B19 (strict <) |
| c. Volume-at-price / queue model from depth data (MBP or MBO) | Most realistic | Needs L2 data; complex | VENDOR schema names (Databento MBP/MBO), not priced |
| d. Report both (a) and (b) as bounds | Gives sensitivity | — | CONVENTION |
| e. Partial fills | Realistic for size | Micro sizes are small; QC's defaults ignore partials | B21 |

**5. Velocity Logic pause, price-limit halt, no-fill**
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. No fills during the pause; fill at the first post-reopen price plus slippage | Matches the mechanism | Needs halt/status timestamps | B6–B8; Databento Status schema (VENDOR, not priced) |
| b. Exclude days with halts or limit events | Simple | Removes tail events from the risk record | — |
| c. Treat as a gap (option 3a) | Uniform | 1-minute bars hide pause timing | B13 |
| d. Treat missing bars as no trading (Fetna voids ranges with missing bars) | Avoids phantom fills | Can hide real losses | Fetna (orb/, range void rule) |

**6. Topstep forced flatten**
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. Exit no later than a time before 3:08 PM CT (user-set buffer), at that bar's close/open plus slippage | Stays within the rule | Differs from academic "exit at close" studies, which break comparability | B9, B10 |
| b. Model a forced exit at 3:08–3:10 PM CT at a worse-than-bar price | Captures the risk of forced liquidation | The liquidation price model is unknown | B10 |
| c. Run both "4:00 PM ET close" and "Topstep-flatten" variants as stress arms | Comparability plus realism | More columns (stress arms, not trials, per Package 6) | Package 6 table |
| d. Add a separate check for daily-loss-limit and maximum-loss-limit liquidations (intrabar, on unrealized P&L) | The MLL acts on unrealized balance | Needs an intrabar path, so it interacts with option 1 | Package 2 venue_rules (ts_mll) |

## Bounded minute-vs-second/tick test design (no Databento calls; to be priced only after Jason approves)
**Goal.** Measure how often 1-minute ORB bars are ambiguous, and the P&L gap between options 1a/1b/1c and 3a/3c, for MES and MNQ.

**Sample a future approval would need:**
- MES and MNQ front-month data. Either trades or L1 (the TBBO/Trades-type schemas a vendor such as Databento offers), plus 1-minute OHLCV and the instrument Status feed for halts.
- About 60 RTH sessions, stratified by volatility tercile (20 per tercile) and covering FOMC, CPI and roll weeks. The session list and session dates are to be fixed *before* looking at the data.
- Only the window from 9:30 ET to the flatten time.

**Data sources.**
- A free alternative is to check whether any already-owned or free sample exists first (e.g., a vendor's free sample files). Nothing will be bought or downloaded without approval.
- Cost: none estimated. A cost check is itself an API call, so it is deferred to Jason's approval.

**Procedure (pure local, on the box):**
1. Build 1-minute bars from the ticks and check they match vendor OHLCV.
2. Generate candidate ORB events mechanically from a fixed, illustrative rule family **taken from the literature**, not tuned.
3. For every bar where the stop and target, or the entry and stop, are both touched, record the true first-touch order from ticks.
4. Compute the path heuristic's hit rate.
5. Record gap fills: the real first trade after the level is crossed versus the bar open, plus the slippage distribution.
6. Record the flatten-window price versus the 4:00 PM close.
7. Record the share of ambiguous bars and the P&L difference per micro, with block-bootstrap CIs by session.

**Outputs.** Ambiguity rate per tercile; heuristic accuracy; gap slippage (median and p95); bounds for each table option. No parameters are selected.

**Bounded scope.** At most one sample request, a fixed sample size, and a single report.

## Verified facts
- CME stop/stop-limit/protection semantics (B1–B5).
- The Velocity Logic reserved state (B6).
- The 2-minute and 10-minute halts (B7–B8).
- The Topstep 3:08 and 3:10 PM CT rules (B9–B10).
- Five vendor/research fill conventions quoted verbatim (B11–B27).
## Indirect but credible evidence
- Vendors converge on two methods: an open-proximity path heuristic and next-open gap fills. That consensus shows shared practice, not accuracy.
## Conflicting evidence
- Vendors disagree on limit fills: touch (backtrader) versus strict trade-through (QuantConnect, B19).
- On stop fills, QuantConnect uses the close (B18) while backtrader and TradingView use the open (B13, B22).
- Fetna's "stop first" conflicts with the path heuristic.
## Unknowns
- MES/MNQ protection-point values and Velocity Logic thresholds.
- Topstep's liquidation price mechanics.
- The true frequency of ambiguous 1-minute MES/MNQ bars.
- Queue position at round levels.
- The MultiCharts method (403).
## Engineering assumptions still required
All option rows above, especially 1, 3, 4 and 6.
## What was genuinely new
- A CME protected stop can **rest unfilled** at the protection limit (B4).
- Topstep flattening starts at 3:08 PM CT.
- Vendors disagree on stop fill prices (open vs close).
## What it confirmed
- Fetna's conservative conventions are standard.
- Fill model choices act as sensitivity arms, not trials (Package 6).
## Roadmap changes
- The ORB backtest spec should log, per trade, which ambiguous condition occurred, so options can be compared as stress columns.
- Plan the tick-sample test before any ORB claim is promoted.
## What should not change
- The no-Databento rule.
- No policy chosen here.
- Micro cost levels from Package 4.
## Next bounded action
- Jason picks which options to carry as stress arms.
- Separately, approve (or not) a priced lookup for the 60-session tick sample.


## Addendum 2026-10-22: retry via Wayback and static NinjaTrader help (unreviewed)
- [VENDOR] MultiCharts (Wayback captures; B28–B32): uses an open-proximity path (O-H-L-C if the open is nearer the high, otherwise O-L-H-C). Limit option: "fill … when trade price goes beyond limit price by 3 points". Bar Magnifier assumes "no ticks between the detailed resolution ticks". Precise backtesting fills buys on the ask series.
- [VENDOR] NinjaTrader IsFillLimitOnTouch (B33–B35): the default fills only once price has *penetrated* the limit; touch is opt-in, and the default is false.
- Conflict C3 (touch vs trade-through) now spans four vendors. Options rows are unchanged; no policy chosen. Details: ../synthesis/scraper_retry_2026-10-22.md
