---
type: research_note
status: reviewed_by_claude_code
created: 2026-10-26
source: external research agent (pasted by Jason); citations spot-checked 2026-10-27
---

# Next MNQ/MES strategy candidates (2019–2024 practice data only)

Ranked by the research agent. Claude Code's review notes are in *italics*.

## 1. Late-day hedging-flow momentum (recommended first)
- **Rule (bare):** at 14:30 CT, sign of the return from the previous regular close (15:00 CT) to 14:30 → same-direction position at the next bar's open → flat at the 15:00 CT close. One trade per day. No filters. *(The agent wrote this in ET: 15:30/16:00 ET = 14:30/15:00 CT. Early-close days need a predeclared variant.)*
- **Why it might work:** options dealers who are short gamma, and leveraged ETFs, must trade in the direction of the day's move near the close. The other side is a forced hedger, not a "dumb" trader.
- **Evidence (high):** Baltussen, Da, Lammers & Martens (2021), *Hedging demand and market intraday momentum*, JFE 142(1):377–403. 60+ futures, 1974–2020; the rest-of-day return predicts the last 30 minutes; linked to gamma and leveraged-ETF hedging. Also Gao, Han, Li & Zhou (2018), *Market intraday momentum*, JFE (SPY 1993–2013; stronger on volatile, high-volume and news days). *Verified.*
- **Cost hurdle:** $15/day net needs about 4.24 MES points (or 9.11 MNQ points) of average captured move per trading day. *That is a demanding bar for a 30-minute hold; the paper's significance does not imply it.*
- *Extra lead the agent missed:* "NASDAQ-100 Index Futures: Intraday Momentum or Reversal?" (Journal of Investment Management) bears directly on MNQ.
- *Risks:* widely published since 2018 (possible decay), and 0DTE options since 2022 changed dealer gamma. 2019–2024 straddles both, which makes it a good falsification sample.

## 2. Large opening-gap fade
- **Rule:** fade an unusually large open vs the prior close (one predeclared, volatility-scaled threshold) and exit on a fixed morning clock.
- **Evidence (medium–low):** Fung, Mok & Lam (2000), J. Banking & Finance (S&P 500 and Hang Seng futures); Grant, Wolf & Yu (2005), *Intraday price reversals in the US stock index futures market: A 15-year study*, JBF 29(5):1311–1327 (1987–2002). *Verified. Caveat the agent under-stated: Grant et al. report that significance falls sharply after a bid-ask cost proxy, and that profitability is unresolved. The samples are old.*

## 3. Extreme intraday negative-jump reversal
- **Rule:** after a volatility-scaled 15-minute negative jump outside scheduled-news windows, go long next bar and exit after a fixed ~60 minutes.
- **Evidence (low–medium):** *The cited "Xiao, Yin & Zhao" paper could not be confirmed as given. The closest match is Xiao Yuewen (2025), J. Univ. Shanghai Sci. & Tech. 47(5):603–612 (ETF-based; no-news jumps reverse, negative jumps more strongly).* Evans (2011, JBF) documents jumps in E-mini futures around macro news. This is a transfer hypothesis, not a futures replication.

## Method points worth adopting
- Add a **matched random benchmark** per strategy (same window or event, random direction) next to the usual random-entry comparison. It answers "does the signal add money, or did we just pick a good time of day?"
- Predeclare one threshold per idea; every extra threshold counts as a trial. MES and MNQ are not independent confirmations.
- Screened out: another ORB variant; FOMC trading (too few events, fills unverifiable with 1-minute data); sub-second lead/lag arbitrage.

## Sources
- Baltussen et al. (2021): https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum/ · working paper https://www3.nd.edu/~zda/intramom.pdf
- Grant, Wolf & Yu (2005): https://ideas.repec.org/a/eee/jbfina/v29y2005i5p1311-1327.html
- NASDAQ-100 futures intraday momentum or reversal (JOIM): https://www.joim.com/nasdaq-100-index-futures-intraday-momentum-reversal
- Xiao (2025) jump/news lecture summary: https://bs.usst.edu.cn/Eng/2021/1012/c11213a256155/page.htm
