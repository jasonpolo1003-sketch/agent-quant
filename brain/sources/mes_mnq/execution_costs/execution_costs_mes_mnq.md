---
title: Execution & transaction-cost evidence, one MES/MNQ micro contract (Package 4)
package: 04_execution_costs
status: unreviewed
promoted: false
created: 2026-10-22
retrieved: 2026-10-22
author: Grok Bot (research only; free sources; Databento API NOT used; no cost levels chosen)
---

# Execution & transaction costs: 1 MES / 1 MNQ (Package 4)

Labels: **[OFFICIAL]** = CME · **[VENUE]** = Topstep/ProjectX · **[VENDOR]** = a broker or data vendor's own statement · **[PEER/ACADEMIC]** = research paper · **[CONVENTION]** · **[QAB-OPTION]** = candidate, not chosen · **[ESTIMATE]** = my arithmetic.
Snapshots are in `../source_files/costs/`, plus earlier packages' `venue/` and `providers/`. 23/23 quotes (C1–C23) were string-matched after collapsing whitespace. Retrieved 2026-10-22, roughly 11:00–11:25 UTC-5. **No Databento calls** (Jason's instruction).

## 1. Tick size and value [OFFICIAL, Package 1 Q1/Q3]
MES 0.25 pt = $1.25; MNQ 0.25 pt = $0.50. Both trade in the same 0.25-point increments, but the dollar values differ by 2.5×. MNQ's tick is also a much smaller fraction of its price than MES's tick, so it is a smaller fraction of a typical move (inferred; index levels are not saved in the snapshots).

## 2. Fee stack per round turn (1 contract)
| Venue | Commission | Exchange/clearing | NFA/regulatory | **Total RT** | Label |
|---|---|---|---|---|---|
| Topstep (TC/XFA/LFA) | $0.50 | $0.70 | $0.02 | **$1.22** MES and MNQ (C4, C5) | VENUE |
| Interactive Brokers (retail comparison, fixed or ≤1,000/mo tier) | $0.25/side (C1) → $0.50 | $0.35/side "exchange fee recovery" (C2) → $0.70 | $0.01/side (C3) → $0.02 | **$1.22** | VENDOR |
- The two fee stacks agree to the cent. IBKR's $0.35/side "exchange fee recovery" matches Topstep's $0.70 round-turn exchange line, which cross-checks the exchange fee level.
- The **CME fee schedule itself was not captured**. The clearing-fees page links to PDFs that weren't saved, and it notes fee changes effective October 1, 2026. So CME's own micro fee is **Unknown/indirect**, inferred only from two intermediaries.
- Platform and data costs are fixed monthly costs, not per-trade costs (API $14.50–$29/mo, L2 $38/mo, from Package 2). Keep them out of per-trade cost assumptions.

## 3. Bid-ask spread and depth
- [PEER/ACADEMIC, ES, 2008–2011, CME DataMine BBO] Andersen, Bondarenko, Kyle & Obizhaeva, *Intraday Trading Invariance in the E-mini S&P 500 Futures Market* (draft dated March 26, 2018): "Hence, the spread is binding and equals a single tick almost always, implying that the tick size is “large” for this liquid market." (C6). Sample: "January 4, 2008, to September 30, 2011." (C7). Average best-bid-plus-ask depth was 56 (Asia), 274 (Europe) and 999 (America) contracts (C8). **Applicability: ES only, 2008–11, so this is a close proxy for MES.** MES trades in the same increments and settles to ES, but its own book depth isn't in this evidence. Treat it as indirect.
- [LEAD] Wang (2007, IMFI) reports an ES average spread of 0.25 points and NQ 0.51 points (2000s, CFTC estimator). Kovacevic (AUT conference paper) reports flat relative spread intraday, with depth lowest at the open and about 40% higher in the last 30 minutes. That PDF returned 403, so neither is saved. Both are leads only.
- [OFFICIAL tool, not accessible] CME's Liquidity Tool shows MES/MNQ spread, depth and cost-to-trade by time zone, but it requires a CME login. The methodology page is saved (C9). **No MES/MNQ spread number was obtained from a free official source.**
- [OFFICIAL] Activity level: MNQ 2025 ADV hit "a record 1.8M contracts" (C10).
- **MNQ spread is unknown.** Its tick is small relative to price, so it may not be "one tick almost always" the way ES was. This is a **hypothesis requiring a test** (§8).

## 4. Time-of-day and volatility regime
- [PEER] ES depth is about 18× higher in the American session than in Asia (C8). The intraday depth pattern from Kovacevic (lowest at the open) is a lead only.
- The 9:30 ET (8:30 CT) open has no free MES/MNQ-specific spread figure. Package 2 showed Topstep blocks or caps new entries around Tier-1 news. CME's Liquidity Tool and a quote sample are the only routes to measuring the open → §8.

## 5. Order behavior in fast markets [OFFICIAL]
- **Velocity Logic:** "designed to detect market movement of a predefined number of ticks either up or down within a predefined time." (C11). For equities "the entire group will transition into the Pre-Open state" (C12). A **Market order** that would trigger it "is eliminated… and the market will remain open." (C13).
  - ES thresholds as reported by an academic paper (not by CME directly): ±6 ticks in 1 ms or ±18 ticks in 1 s, each causing a 5-second pause (C17). The paper says these limits are updated monthly.
  - **Consequence:** in a spike, a market or stop order can be cancelled or paused rather than filled, so "fill at stop + N ticks" is not guaranteed.
- **Stop orders with protection:** "CME Globex matches the order at all price levels between the trigger price and the protection price limits. If the order is not completely executed, the remaining quantity is then placed in the order book at the protection price limit." (C14).
  - Slippage on a protected stop is therefore bounded by the protection range. The unfilled part rests as a limit, which creates a risk of no fill.
  - Whether TopstepX stop orders map to CME stops-with-protection or are simulated by the platform is **Unknown** (TopstepX is a simulator; Package 2).
- **Price limits and dynamic circuit breakers:** for non-S&P US equity index futures (including NQ/MNQ), "If a contract market moves beyond +/- 3.5% within an hour, trading will be paused for two minutes." (C15). This covers 3:00–4:00 PM CT and overnight. S&P products, including MES, follow a separate FAQ (C16); that FAQ was **not saved**, so the MES specifics are unknown. Market-wide 7%/13%/20% halts are per the paper's table (indirect).

## 6. Partial fills for one contract
- 1 lot is the minimum order size, so a market order fills fully or not at all; there's no partial fill at the order level. A protected stop can fill or rest at the protection limit (C14). A limit order of 1 lot fills fully once reached through the queue. **Queue position is the real uncertainty**, not partial fills [CONVENTION]. Topstep explicitly flags SIM "preferential queue position" as exploitable (C19), so simulated limit fills may be optimistic.

## 7. Latency for a home workstation
- No Topstep/ProjectX latency figure exists in the official docs captured.
- The ProjectX trailing-stop distance uses "The last traded price… read on the server at the moment the order is received." (C21). Round-trip time matters.
- Databento's internet delivery is "590 microseconds" at the 90th percentile (C22), but that is a data-vendor figure, not order-routing to TopstepX.
- [QAB-OPTION] Latency candidates: 250 ms / 1 s / 2 s from signal to the order reaching the server. All are unmeasured; measure them from Practice timestamps (§8).

## 8. Bar-based backtest vs SIM/paper fills
- [VENUE] Topstep warns against "exploiting the relative lack of slippage in SIM to achieve impossible stop-loss execution" (C18) and against SIM queue advantages (C19). So **Practice/SIM fills are likely optimistic** compared with live markets, and they can't validate a stress level.
- Risk liquidations use market orders with slippage (C20).
- Vendors omit no-trade minutes (C23). A bar backtest can't see the spread at all, because OHLC bars are trade prints.
- Implication: **neither bars nor SIM fills measure true slippage.** Only quote/trade data does: a bounded TBBO/MBP-1 sample, or the CME Liquidity Tool.

## 9. Cost-assumption table: candidates only, NOT chosen [QAB-OPTION / ESTIMATE]
Per round turn for 1 contract, including the $1.22 fees. Slippage ticks are measured relative to the modeled reference price, such as the bar price or the stop trigger.
| Level | Slippage (ticks RT) | MES $ RT | MNQ $ RT | Rationale / evidence | Label |
|---|---|---|---|---|---|
| L0 fees only | 0 | $1.22 | $1.22 | Valid only for limit fills assumed at the price; contradicted for market and stop orders (§5, §8) | QAB-OPTION (reject candidate) |
| L1 half-spread each side | 1 | $2.47 | $1.72 | Crossing a 1-tick spread costs ½ tick per side from mid (C6, for ES) | QAB-OPTION, base candidate A |
| L2 one tick per side | 2 | $3.72 | $2.22 | Conservative against a trade-print reference; covers a 1-tick spread plus small adverse moves | QAB-OPTION, base candidate B |
| L3 stress | 4 (e.g. 1 tick entry + 3 ticks stop exit) | $6.22 | $3.22 | Fast-market stop exits; protection range and Velocity Logic (C14, C11) | QAB-OPTION, stress |
| L4 severe / news / open | 8 | $11.22 | $5.22 | Spike conditions; ES Velocity Logic thresholds of 6–18 ticks (C17, indirect) | QAB-OPTION, severe stress |
| L5 no-fill | — | — | — | Market or stop order eliminated or paused (C13): model as a delayed fill at the first price after the pause | QAB-OPTION, scenario |
Notes:
- MNQ in ticks may need **higher** tick counts than MES for the same dollar risk, because its tick is relatively smaller (hypothesis).
- Dollars = ticks × $1.25 (MES) or $0.50 (MNQ), plus $1.22.

## 10. What only a quote sample or Practice fills can measure
- **From a bounded quote sample** (Databento `tbbo` or `mbp-1`; NOT run). Suggested request when Jason approves spending credit: `GLBX.MDP3`, `stype_in=raw_symbol`, symbols `MESZ6`,`MNQZ6`, `schema=tbbo` (and `mbp-1`), 10–20 RTH sessions including 2–3 CPI/FOMC days, windows 08:25–09:30 CT and 14:50–15:10 CT, `encoding=dbn`, `compression=zstd`. Run `metadata.get_cost` first.
  - It would measure:
    - the MES/MNQ spread distribution by minute;
    - top-of-book depth;
    - spread at the open and at news;
    - trade-through distance after stop-like triggers;
    - how often the stop and target are both hit within the same minute.
- **Free alternative:** Jason's CME Group login could give Liquidity Tool views of MES/MNQ spread and depth by time zone. That needs his action; I didn't log in.
- **From Practice fills (ProjectX, once allowed):**
  - order-to-ack latency from home;
  - SIM fill price versus contemporaneous BBO;
  - stop-fill slippage in SIM;
  - limit-fill rate at touch;
  - reject or elimination behavior;
  - bracket/OCO timing.
  - These show how SIM behaves, but they don't validate live slippage (C18).

## Source records
| Snapshot | Title / org | URL | Date | Type |
|---|---|---|---|---|
| ibkr_futures_commissions | Commissions Futures / Interactive Brokers | https://www.interactivebrokers.com/en/pricing/commissions-futures.php | live | broker schedule |
| ibkr_cme_fees | CME Exchange & Regulatory Fees / IBKR | https://www.interactivebrokers.com/en/accounts/fees/CME.php | live | broker schedule |
| cme_fee_schedule_equity | Exchange Fees for Clearing & Trading / CME | https://www.cmegroup.com/company/clearing-fees.html | live; notes Oct 1, 2026 changes | exchange (index page only) |
| cme_liquidity_methodology | Understanding the CME Liquidity Tool Methodology / CME | https://www.cmegroup.com/education/articles-and-reports/understanding-the-cme-liquidity-tool-methodology | n.d. | exchange education |
| cme_equity_insights_2025_07 | Equity Insights July 2025 / CME | https://www.cmegroup.com/newsletters/quarterly-equity-index-recap/2025-july-equity-index-recap.html | Jul 2025 | exchange newsletter |
| cme_velocity_logic | Velocity Logic / CME Client Systems Wiki | https://www.cmegroup.com/confluence/display/EPICSANDBOX/Velocity+Logic | Updated Feb 11, 2025 | exchange |
| cme_wiki_order_types | Order Types for Futures and Options / CME Wiki | https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457087412/Order+Types+for+Futures+and+Options | n.d. | exchange |
| cme_us_equity_price_limits_faq | US-Based Equity Index Futures Price Limits FAQ / CME | https://www.cmegroup.com/trading/equity-index/us-based-equity-index-futures-price-limits-faq.html | n.d. | exchange |
| arxiv_breaking_news_es | Winkelmann & Yao, "Breaking news", arXiv:2603.22835v1 | https://arxiv.org/html/2603.22835v1 | Mar 24, 2026 | working paper |
| abko_intraday_invariance_es.pdf | Andersen, Bondarenko, Kyle, Obizhaeva | https://pages.nes.ru/aobizhaeva/ABKO-intradayinv.pdf | draft Mar 26, 2018 | academic (published version in Econometrica, lead) |
Plus Package 2/3 snapshots (ts_commissions_fees, ts_prohibited_strategies, ts_mll, px_order_place, db_glbx_dataset, firstrate_faq). Checksums are in `../_sha256.txt`.

## Verified facts
- Fees are $1.22 per round turn for MES and MNQ at Topstep, and the same at IBKR's base tier.
- Velocity Logic can pause the entire equity group (pre-open) and eliminate market orders. CME stops-with-protection bound slippage and rest any remainder.
- NQ/MNQ have a ±3.5%-per-hour dynamic circuit breaker with a 2-minute pause.
- Topstep says SIM has less slippage than real markets.
## Indirect but credible evidence
- ES spread is one tick almost always (2008–11) and depth is far higher in US hours. ES Velocity Logic thresholds of 6 ticks / 1 ms and 18 ticks / 1 s come from an academic paper.
## Conflicting evidence
- None captured directly. Note the tension: SIM fills are "optimistic", yet Practice is the only fill venue we can test.
## Unknowns
- MES/MNQ actual spread and depth by minute; MNQ spread width.
- CME's own micro fee schedule (current, after Oct 1, 2026).
- MES-specific (S&P) price-limit FAQ.
- Whether TopstepX stops behave like CME protected stops.
- Home → TopstepX latency.
- Velocity Logic thresholds for MES/MNQ specifically.
## Engineering assumptions still required
- [QAB-OPTION] Which of L1/L2 is base and which of L3/L4 is stress; the reference price for slippage (bar open, trade, mid); the no-fill/pause scenario; separate MES and MNQ tick multipliers; the latency level.
## What was genuinely new
- Topstep's and IBKR's fee stacks are identical at $1.22.
- Velocity Logic can eliminate market orders and pause the whole equity group.
- Protected stops can leave the order resting unfilled.
- Free, official MES/MNQ spread data isn't publicly available without a login.
## What confirmed an existing decision
- No daily-OHLC spread estimators. Costs must include stress levels. SIM fills can't serve as cost proof.
## What should change in the roadmap
- Add a "no-fill / paused market" scenario to the fill-model package (7).
- Make the bounded quote sample (or a Liquidity Tool read via Jason's CME login) a prerequisite before freezing cost levels.
- Calibrate MES and MNQ tick counts separately.
## What should not change
- Package order. Fill-model rules are still decided in Package 7, not here.
## Next bounded action
- Jason chooses one of these:
  - (a) log in to the free CME Liquidity Tool and export MES/MNQ spread and depth by hour; or
  - (b) approve a Databento `get_cost` check only, for the §10 sample.
- Otherwise proceed to Package 5 (ORB evidence).

## Decision note 2026-10-22 (D-COST-01)
QAB ENGINEERING POLICY, decided by Jason via delegation; reversible. The L1–L5 ladder is carried as stress columns in all MES/MNQ backtests, and the gate level is **L3** (MES $6.22, MNQ $3.22 round turn). Rationale: ORB stop entries slip more than the one-tick ES spread proxy, so the gate fails closed. Revisit if CME Liquidity Tool or tick-sample spread data contradicts it. See `../synthesis/decisions_log.md`.


## Addendum 2026-10-22: Velocity Logic structure (unreviewed)
- [INDIRECT, FIA via CFTC] VLN triggers on a move greater than the price-band range within 1 ms; VLW on 3× the band range within 1 s; either gives a 5-second pre-open halt (C24–C25).
- [OFFICIAL] The CME wiki states VL is a predefined number of ticks within a predefined time. Product band values are in "GCC Price Banding" (C26–C27), which was **not retrieved** (403 / HTTP2 errors).
- MES/MNQ numeric values remain unknown. D-COST-01 is unchanged.
