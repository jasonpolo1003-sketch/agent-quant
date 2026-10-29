---
type: research_note
status: scout_draft (citations searched 2026-10-29; effect sizes marked [verify] were not read from full text)
created: 2026-10-29
author: Claude Code research scout (read-only)
scope: prop-firm 50K eval (trailing DD $2,000, target $3,000, flat by 15:10 CT, Globex 17:00 to 15:10 CT allowed), CME micros, 1-min data 2019-2024
---

# Edge scout: published intraday/overnight candidates (2026-10-29)

**Excluded as already tried or close variants:** ORB, late-day momentum (Baltussen; Gao et al.), shock reversal (this also covers the VIX-spike next-day premium in Hu et al.), noise-area band fade/momentum (SC-FUT-0005), RTH gap fill, evening reversion, pyramiding, cushion sizing, DOW/vol tilts, news-day gap fill, weekly options, and the bold play. Overnight drift (Boyarchenko et al.) is being tested now, and candidate #3 has to be tested **as an increment over it**.

**Honesty note:** most of the effects below are calendar or event effects. That gives only 1-12 trades a month and about 70-700 events in 2019-2024, so statistical power is low. The structural story carries more weight than usual, and every candidate needs the matched random benchmark (same window, random dates or random sign).

## Ranked list (best chance of surviving an honest OOS test with costs first)

### 1. Month-end institutional rebalancing pressure (stocks vs bonds)
- **Sources:** Harvey, Mazzoleni & Melone, *The Unintended Consequences of Rebalancing*, NBER WP 33554 (2025, rev. Jan 2026) https://www.nber.org/papers/w33554 ; SSRN 5122748 ; summary https://cxoadvisory.com/calendar-effects/exploiting-predictable-institutional-portfolio-rebalancing ; press https://www.fuqua.duke.edu/duke-fuqua-insights/what-do-pensions-lose-from-rebalancing
- **Rule as published:** track a 60/40 ES/10y T-note portfolio. (a) *Calendar signal:* in the last week of the month, if stocks have outperformed bonds month to date (equity overweight), expect rebalancers to sell ES and buy ZN, and the reverse if stocks underperformed. (b) *Threshold signal:* when weights drift past bands of 0-2.5% (averaged across bands), expect next-day rebalancing in the restoring direction. The trade is short (long) ES plus long (short) ZN in front of the flow. The paper used daily nearest futures from Sep 1997 to Mar 2023.
- **Effect:** "when stocks are overweight ... equity returns decrease ~17 bps over the next day" (abstract). Reversal follows early in the next month. The Sharpe ratio and the exact day window are [verify]; the full text has them.
- **Post-publication:** the paper is too new for independent replication. The authors' own sample runs to 2023, so our 2019-2024 data mostly overlaps it in-sample. Practitioners widely watch month-end pension estimates from banks (GS, JPM, Nomura), which is a crowding risk, but the flow is forced and huge.
- **Why it should persist:** mandate-driven, calendar-scheduled rebalancing with cash-flow needs (pensions paying benefits). The paper presents the pattern to pension managers as a cost, and they have not stopped.
- **Prop-firm version:** MES (or MNQ) only, intraday. On the last 1-3 trading days of the month, take the side opposite to month-to-date ES minus ZN relative performance (one sign rule, one threshold, predeclared). Hold RTH open to 15:00 CT, or 14:00-15:00 CT if the pressure sits at the close [verify]. Optional: early-month reversal day in the opposite direction.
- **Frequency:** 1-3 trades a month (about 12-36 a year, so roughly 70-200 in the sample).
- **Risks:** crowding (sell-side flow notes front-run the trade), low trade count, and quarter-end being much bigger than plain month-ends (heterogeneity).
- **Extra data:** daily ZN (10y note) settlements, or TLT/IEF daily closes, for the month-to-date bond return. Futures roll calendar.

### 2. Turn-of-the-month (TOM) long equity index, driven by the cash cycle
- **Sources:** Etula, Rinne, Suominen & Vaittinen, *Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs*, RFS 33(1) 2020 https://www.aalto.fi/en/news/matti-suominens-paper-accepted-to-be-published-in-the-review-of-financial-studies ; McConnell & Xu (2008, FAJ), *Equity returns at the turn of the month* https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes ; Carchano & Pardo (2011), 188 calendar anomalies on index futures where only TOM survived costs https://cxoadvisory.com/calendar-effects/stock-index-futures-calendar-effects ; counter-evidence: Maberly & Waggoner (2000) https://www.atlantafed.org/research/publications/wp/2000/11.aspx
- **Rule as published:** McConnell & Xu define the window as the last trading day of the month (T-1) through the third trading day of the new month (T+3), long the index, flat otherwise. Etula et al. add that returns are depressed in the days *before* the TOM window, when institutions raise cash, and rebound during it [verify exact day offsets].
- **Effect:** McConnell & Xu (1926-2005) find essentially all of the excess return on US equities came in TOM days. Carchano & Pardo report a 27.5% cumulative net return on S&P futures from 1991 to 2008 after 5 bp round-trip costs. A spot update to Q3 2024 (Quantpedia-linked) says holding 4 days a month earned nearly the same annual return as the other ~17 days combined.
- **Post-publication:** mixed. Maberly & Waggoner found the effect gone in S&P futures in the 1990s, yet later samples show it back. Persistence is OK on average but unstable.
- **Why it should persist:** payroll, 401(k) contributions, pension benefit payments and coupon reinvestment are scheduled monthly. This is the same structural engine as #1.
- **Prop-firm version:** long MES or MNQ from 08:30 CT to 15:00 CT (or the Globex open 17:00 CT to 15:00 CT) on T-1..T+3. One position, no stop or a wide stop. **Better:** combine with #1 by skipping or halving TOM longs when the rebalancing signal says "sell equities".
- **Frequency:** 4-5 trading days a month (about 290 days in the sample).
- **Risks:** a large part of the TOM premium is overnight (close to open), which the flat-by-15:10 rule cuts off except from 17:00 CT onward. The intraday-only part may be thin against costs. It is also widely known.
- **Extra data:** none beyond the trading calendar.

### 3. Pre-scheduled-macro-announcement overnight premium (CPI / NFP / FOMC)
- **Sources:** Hu, Pan, Wang & Zhu, *Premium for Heightened Uncertainty: Explaining Pre-Announcement Market Returns*, JFE 2021 https://www.nber.org/papers/w25817 (PDF https://en.saif.sjtu.edu.cn/junpan/PreAnn_20210728.pdf) ; Savor & Wilson (2013, JFQA) ; Lucca & Moench (2015, JF) ; skeptics: Kurov, Wolfe & Gilbert, *The disappearing pre-FOMC announcement drift*, FRL 2021 https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html ; Ernst, Gilbert & Hrdlicka, *Is There a Macro-Announcement Premium?*, Management Science https://pubsonline.informs.org/doi/references/10.1287/mnsc.2024.06960
- **Rule as published:** S&P 500 futures return from the prior 16:00 ET close to 5 minutes before the scheduled announcement, compared with the near-zero overnight return on non-announcement days. The effect is attributed to uncertainty (VIX) build-up and its resolution.
- **Effect:** "economically large, comparable to the pre-FOMC drift" (abstract). Which releases are individually significant is [verify] in the tables.
- **Post-publication:** the pre-FOMC part **essentially vanished after 2015** (Kurov et al.). Ernst et al. argue the macro-announcement premium is small or absent. **Flagged as possibly decayed.**
- **Why it might persist:** a risk premium for holding through scheduled uncertainty. This is a weaker structural argument than flow-driven effects.
- **Prop-firm version:** long MES from the 17:00 CT Globex open the evening before CPI/NFP (7:30 CT release) and exit at 7:25 CT. This fits inside one session. For FOMC, 17:00 CT the prior evening to 12:55 CT (but that is the decayed leg).
- **Frequency:** about 2-3 a month.
- **Risks:** heavily overlaps the Boyarchenko overnight drift under test. It is only worth it if it beats the unconditional overnight drift on the same nights. Small N.
- **Extra data:** historical release calendar (BLS CPI/Employment Situation dates, FOMC dates) for 2019-2024.

### 4. Gold: long overnight / short day session (MGC)
- **Sources:** Blose, Gondhalekar & Kort, *Overnight versus day returns in gold and gold related assets*, J. Economics & Finance 42(3) 2018 https://ideas.repec.org/a/spr/jecfin/v42y2018i3d10.1007_s12197-017-9403-0.html ; earlier futures-only study 1985-2012 (same authors) https://scholarworks.gvsu.edu/fsdg/200 . Context on Chinese night sessions: https://ideas.repec.org/a/eee/glofin/v64y2025ics1044028325000110.html
- **Rule as published:** overnight return (prior COMEX close to next open) vs day return (open to close) on front-month COMEX gold. Overnight was significantly positive and day significantly negative, "economically important after transaction costs". The proposed reading is that gold is overpriced at the US open.
- **Post-publication:** the authors themselves say the asymmetry has **weakened substantially over time but is still present**. A 2011 conference version reported the opposite sign, so the sign is unresolved in the record. No independent replication was found. **Flagged as decaying.**
- **Why it might persist:** Asian/London physical demand and the LBMA auction (10:30/15:00 London) happen overnight in US terms; US-hours selling comes from futures and ETF flows. The structural story is plausible but loose.
- **Prop-firm version:** (a) long MGC 17:00 CT to 07:20 CT (COMEX day open); (b) optional short MGC 07:20 to 12:30 CT. Test each leg on its own.
- **Frequency:** about 20 a month per leg. That is the highest power on this list, which is good for an honest test.
- **Risks:** decay, unresolved sign, and costs vs the per-trade edge (MGC tick $1; the needed average move is small but the edge is likely a few bp). Gold's strong 2019-2024 bull trend inflates the long leg, so use a long-all-session benchmark.
- **Extra data:** MGC/GC 1-minute bars (assumed available, since MGC is listed), with continuous back-adjustment across rolls.

### 5. Crude oil intraday momentum on EIA inventory Wednesdays (MCL)
- **Sources:** Wen, Indriawan, Lien & Xu, *Intraday Return Predictability in the Crude Oil Market: The Role of EIA Inventory Announcements*, Energy Journal 44(5) 2023 https://ideas.repec.org/a/sae/enejou/v44y2023i5p149-172.html (accepted PDF https://digital.library.adelaide.edu.au/dspace/bitstream/2440/141224/2/hdl_141224.pdf) ; exec summary https://www.iaee.org/ej/ejexec/ej44-5-Xu-exsum.pdf ; release-window reversal context: Geman & Li, J. Energy Markets https://www.risk.net/journal-of-energy-markets/5728636/an-analysis-of-intraday-market-response-to-crude-oil-inventory-shocks
- **Rule as published:** on EIA days, the return of the half-hour containing the 10:30 ET release (the paper's "third half-hour") positively predicts the last half-hour return of the pit session (about 13:00-13:30 CT, into settlement). On non-EIA days the first half-hour's predictive power comes from the overnight gap. Exact bar boundaries are [verify].
- **Effect:** "substantial economic gains" (abstract). The magnitudes are [verify].
- **Post-publication:** published 2023, with no independent replication found.
- **Why it should persist:** informed trading and lower liquidity around the release; settlement-window hedging in crude (producers, swap dealers) concentrates at 13:28-13:30 CT.
- **Caution:** this belongs to the same family as late-day momentum, which already failed on equities. It is listed because the market, conditioning event and settlement mechanism are different, not as a free retry. Count it as a new trial.
- **Prop-firm version:** on Wednesdays (Thursdays in holiday weeks), sign of MCL return 9:30-10:00 CT → same-direction MCL 13:00 CT → exit 13:30 CT.
- **Frequency:** about 4 a month (about 300 in the sample).
- **Risks:** MCL liquidity and spreads in the last half-hour are fine but slippage around settlement is real. 2020 negative-price period. Small per-trade move.
- **Extra data:** MCL/CL 1-minute bars; EIA release-date calendar (holiday shifts).

### 6. Treasury auction cycle (dealer inventory)
- **Sources:** Lou, Yan & Zhang, *Anticipated and Repeated Shocks in Liquid Markets*, RFS 26(8) 2013 https://researchonline.lse.ac.uk/id/eprint/43120 (DP https://www.fmg.ac.uk/sites/default/files/publications/DP684.pdf)
- **Rule as published:** Treasury secondary-market prices fall over the few days before scheduled auctions and recover shortly after. Cost to the Treasury is 9-18 bp of auction size. Mechanism: limited primary-dealer risk capacity plus slow-moving end investors.
- **Post-publication:** no clean futures replication found [verify]. Auction sizes rose sharply in 2023-2024, which may strengthen the concession.
- **Why it should persist:** a fixed, publicly scheduled supply shock absorbed by balance-sheet-constrained dealers.
- **Prop-firm version:** short ZN (or 10Y micro yield futures, if the firm allows them) intraday on the 1-2 sessions before 10y/30y auctions, and long on the session after. Equity cross-asset version (MES weak into large auctions) is speculative.
- **Frequency:** about 3-6 a month across 2y/5y/7y/10y/30y.
- **Risks:** **instrument fit**, since the edge lives in rates, not the listed micros. ZN full-size at $15.625/tick is tradable within $2k DD but is not a micro. The edge per day is a few bp of a low-vol asset, so costs matter.
- **Extra data:** ZN 1-minute bars, Treasury auction calendar (TreasuryDirect).

### 7. Option-expiration-week long (dealer hedge rebalancing)
- **Sources:** Stivers & Sun, *Returns and option activity over the option-expiration week for S&P 100 stocks*, JBF 37(11) 2013 https://ideas.repec.org/a/eee/jbfina/v37y2013i11p4226-4240.html ; https://cxoadvisory.com/calendar-effects/option-expiration-week-stock-return-drill-down ; https://quantpedia.com/screener/details/102
- **Rule as published:** long large caps or the S&P 500 during the monthly OpEx week (week of the 3rd Friday). High average returns from 1983-2008; nothing unusual before 1983.
- **Post-publication:** practitioner backtests report **deterioration in recent years**. The 0DTE boom since 2022 changed the gamma calendar. **Flagged as decaying.**
- **Prop-firm version:** long MES 08:30-15:00 CT, Monday to Thursday of OpEx week.
- **Frequency:** about 4 days a month.
- **Risks:** decay, overlap with general bull drift (needs a random-week benchmark), close to the "weekly options" family already tried.
- **Extra data:** expiration calendar only.

### 8. FOMC-cycle even weeks
- **Sources:** Cieslak, Morse & Vissing-Jorgensen, *Stock Returns over the FOMC Cycle*, JF 2019 https://papers.ssrn.com/abstract=2687614
- **Rule as published:** week 0 starts the day before a scheduled FOMC announcement; the equity premium from 1994-2016 was earned in weeks 0, 2, 4 and 6. Long equities in even weeks, flat in odd weeks.
- **Post-publication:** the authors' own 2014-2016 holdout held up. **No independent post-2019 replication found**, and the related pre-FOMC drift decayed.
- **Why:** Fed-put / information-flow story (board meetings on an even-week cadence). Plausible but not a mechanical flow.
- **Prop-firm version:** long MES intraday on even-week days only.
- **Frequency:** about 10 days a month, so it is barely a filter. It is better used as an overlay on a working strategy than as a standalone strategy.
- **Risks:** data-mined cycle, decay, mostly beta.
- **Extra data:** FOMC meeting dates 2019-2024.

## Screened out (and why)
- **Closing-auction imbalance reversal** (Bogousslavsky & Muravyev, JFM): about 1/3-1/2 of the reversal occurs in the first 30 minutes after 15:00 CT and the rest overnight. That is mostly beyond the 15:10 CT flat rule, and it needs paid NYSE/Nasdaq imbalance feeds.
- **Pre-FOMC drift alone** (Lucca & Moench): decayed after 2015 (Kurov et al.). It survives only inside #3 as a test leg.
- **Goldman roll front-running** (Mou 2010): a calendar-spread trade across multiple days that does not map to intraday micros.
- **VIX-spike next-day premium** (Hu et al.): too close to the failed shock-reversal family.
- **Treasury → equity intraday lead-lag:** no strong peer-reviewed futures-level evidence found. Old work (Stoll & Whaley 1990) covers futures → cash, not bonds → equities.

## Suggested test order
1 + 2 together (same month-end flow; one predeclared combined rule), then 4 (highest N, cheap to falsify), then 3 as an increment over the overnight-drift result, then 5. Treat 6-8 as backlog.
