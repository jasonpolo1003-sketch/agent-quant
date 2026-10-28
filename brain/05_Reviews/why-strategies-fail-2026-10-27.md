---
type: investigation
date: 2026-10-27
question: Why did SC-FUT-0001/0002/0004 all fail? Backtest, coding, data, or market?
method: four independent read-only agents (code/data audit, outside replications, costs/fills, quant structure)
---

# Why the MES/MNQ strategies fail: combined verdict

**It is the market, not the machinery.** The gross edge over random is real but tiny: about $2–5 per trade (ORB about +$3.3/trade, late-day momentum about +$2.5, shock reversal negative). A micro round trip costs about the same. No coding, data or cost artifact changes any verdict.

## Evidence
1. **Code and data audit (independent rebuild from raw bars):**
   - ORB and late momentum matched to the cent on every day (0 mismatches).
   - The timestamp convention was confirmed by the 08:30 CT volume spike, with daylight-saving changes correct.
   - Buy-and-hold matches the S&P/Nasdaq excess returns within a few percent.
   - Random entries average about $0 gross, so there is no fill or drift bias.
   - Costs are subtracted exactly once.
2. **Costs:** every strategy also fails at zero cost on the dollar floors. Fees are verified at $1.22 per round trip. L3 is about fair for MNQ and somewhat harsh for MES (L2 is closer for regular trading hours). Even L1 passes nothing.
3. **Outside replications agree:**
   - An MQL5 rerun of Zarattini-Aziz reproduces the gross edge, with net about 0.
   - Mesfin (2026) finds 0 of 14 MNQ intraday families pass, with ORB t = 0.88.
   - Rosa (2022) finds S&P intraday momentum vanishes out of sample, and QuantConnect's ETF rerun gets a Sharpe of −0.63 for 2015–2020.
   - Baltussen's net claim assumes full-size ES at 1 tick.
   - The strong published numbers come from ETFs, no slippage, leverage or in-sample windows.
4. **Structure:**
   - McLean-Pontiff report post-publication decay of about 58%, and ES/NQ are among the most competed markets.
   - Micros cost about 10× more per notional than full-size contracts.
   - Passing and keeping a $3k / $2k-trailing account reliably needs a net Sharpe of about 1.5+. No single-market published rule shows that.
   - Industry figures (secondary): about 17% of Topstep Combines pass, about a third of funded traders get a payout, and about 0.7% reach Live.

## Minor issues found (fix going forward)
- **Fixed roll trades the thin new contract** on about 35 roll days (2–8% of volume). This flattered ORB by about $0.5/day. Use the `volume` roll by default for new cards.
- **Shock-reversal matched control:** if the flipped trade can't be scored, it falls back to the original trade. This is rare.
- **The 0.10×ATR ORB stop is tight:** one L3 round trip is about 22% of the risk per trade on MES.

## Structurally better directions (all long shots)
- **A. The same frozen same-day mechanism across several uncorrelated markets** (ZN, CL, GC, 6E micros plus MES/MNQ). Portfolio Sharpe grows with about the square root of the number of independent markets, and Baltussen found intraday momentum in every asset class. Check: daily-bar correlations first (data owned), then a quote for 1-minute data for 5–6 markets.
- **B. Volatility-conditioned and volatility-sized same-day trading** (Zarattini, Aziz & Barbon 2024 "noise area"; reported net Sharpe 1.33 on SPY). Our 2019–2024 data overlaps their sample, so it is a replication check, not fresh evidence.
- **C. Event-time windows in ZN/CL** (pre-announcement drift; EIA). Needs 1-minute ZN/CL data and release calendars.
- **Note:** the 2025–26 MES/MNQ data is our locked exam. Using it as fresh data spends the exam.
