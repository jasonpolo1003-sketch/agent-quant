---
title: Free MES/MNQ (ES/NQ) intraday data check
status: unreviewed
promoted: false
retrieved: 2026-10-22
databento_calls: none
---
# Is there a FREE multi-year 1m/5m MES/MNQ source?

**Answer: No.** No free source tested gives several years of 1m/5m MES/MNQ or ES/NQ futures bars under a usable license. The free options are only a few days to a few months deep. Hourly bars go back about 2.4 years for free, but hourly is too coarse for an opening-range test.

Verification: V = checked on an official page or by a test pull on 2026-10-22. U = not re-verified this run (prior knowledge, treat as lead).

| Source | Free? | Depth | Resolution | Contracts | License / limits | Verified | URL |
|---|---|---|---|---|---|---|---|
| Yahoo Finance via yfinance (MES=F, MNQ=F) | Yes | **1m: about 8 days** (period=30d returned 0 rows). **5m: 60 days** (period=1y returned 0). 1h: 730 days (2024-05-31 onward) | 1m/5m/1h | Continuous front only (=F), unadjusted, no dated contracts | Yahoo ToS: personal use only, no redistribution, unofficial API | V (test pull 2026-10-22, about 9.5k 1m rows per symbol, 2026-10-14 to 2026-10-22 ET) | https://finance.yahoo.com/quote/MES=F |
| FirstRate Data free samples | Yes, no sign-up | **2 weeks** (21 Sep to 2 Oct 2026) | 1m/5m/30m/1h/1d | Sample contents not opened; paid set has continuous (unadj/abs/ratio) plus dated contracts from 2008 | Sample only; paid ES/NQ from 2008 | V (page) | https://firstratedata.com/free-intraday-data ; https://firstratedata.com/i/futures/ES |
| Kibot | **No for futures** | Free intraday covers stocks/ETFs only (IBM, OIH, IVE, WDC). Futures samples available on request via contact form | n/a | Paid continuous ES/NQ from 2009 | Paid | V (page) | https://www.kibot.com/free_historical_data.aspx |
| Portara / PortaraNinja samples | Yes | Snippet only | ES 1m continuous; NQ tick (one contract, 12-18) | ES continuous; NQ dated | Sample only | V (page, files not downloaded) | https://portaraninja.com/ninjatrader-sample-data/ |
| Databento free samples / $125 credit | Credit exists (account made) | n/a | n/a | n/a | **Excluded by Jason's rule, not checked** | – | – |
| CME DataMine samples | Small samples only | Days | Tick/MBO | Dated | Paid product, sample terms | U | https://www.cmegroup.com/market-data/datamine-historical-data.html |
| Massive (formerly Polygon) futures | **No minute data on free/Basic** | Futures Basic excludes minute aggregates; Starter and above (paid) include them | 1m in paid tiers | Dated contracts | Paid | V (docs) | https://massive.com/docs/flat-files/futures/overview |
| Barchart free tier / OnDemand free | Chart viewing only; downloads paid (Premier) | – | – | – | No bulk export free | U | https://www.barchart.com |
| Stooq | Daily futures only; intraday covers recent days only for some symbols | Not multi-year intraday | – | Continuous | Free, personal | U | https://stooq.com |
| Alpha Vantage | No CME futures intraday endpoint | – | – | – | – | U (search found no futures intraday endpoint) | https://www.alphavantage.co/documentation/ |
| Interactive Brokers | Needs a funded account plus a CME data subscription; expired futures history is limited | About 2 years for expired contracts | 1m | Dated | Not free / needs account | U | https://interactivebrokers.github.io/tws-api/historical_limitations.html |
| Topstep / ProjectX practice | Needs Topstep account plus ProjectX API subscription (paid) | Unknown | Bars via API | Dated | Not free; personal use | U (see package 2) | – |
| Kaggle | Yes | choweric/cme-es: **daily** individual contracts 2000-2022 (CC BY-SA 4.0). Finnhub SP tick (old, "Other" license). Other ES sets are single-day snapshots | Mostly daily | Dated (choweric) | Check each license | V (search result pages) | https://www.kaggle.com/datasets/choweric/cme-es |
| QuantConnect | Free to use inside its cloud (minute futures from about 2009) | Multi-year | 1m | Dated plus continuous | **Cannot export raw data** (license); research and backtests only on-platform | U | https://www.quantconnect.com/data |

## Implications (unreviewed, no choice made)
- **Smoke test only:** yfinance 5m covers 60 days, about 40 RTH sessions per symbol. Good enough for pipeline testing, far too small for falsification, and continuous only (no roll control).
- **Only free multi-year 1m path:** QuantConnect, run inside its cloud (data stays there). This would mean porting the engine to LEAN. Its license limits need verifying before relying on it.
- Otherwise a real test needs paid data: Databento (credit), FirstRate (paid ES/NQ from 2008), or Kibot.
