---
type: index
status: unreviewed
promoted: false
retrieved: "2026-10-21"
---
# Papers (free author/official copies) — Index

All notes unreviewed. Quotes string-matched against pdftotext of the cited PDF page (PDF page index).

| Paper | PDF | Note | Verified quotes | Tags |
|---|---|---|---|---|
| The Probability of Backtest Overfitting (Bailey, Borwein, López de Prado, Zhu) | [[2017_Bailey-Borwein-LopezdePrado-Zhu_Probability-of-Backtest-Overfitting.pdf]] | [[2017_Bailey-Borwein-LopezdePrado-Zhu_Probability-of-Backtest-Overfitting]] | 5 | backtesting, risk |
| The Deflated Sharpe Ratio (Bailey & López de Prado) | [[2014_Bailey-LopezdePrado_Deflated-Sharpe-Ratio.pdf]] | [[2014_Bailey-LopezdePrado_Deflated-Sharpe-Ratio]] | 5 | backtesting, risk |
| Does Academic Research Destroy Stock Return Predictability? (McLean & Pontiff, JF 2016, PRIMARY; licensed St. John's copy, personal use) | [[2016_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability_JF.pdf]] | [[2016_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability_JF]] | 8 | backtesting, strategies |
| ? 2012 working paper (superseded) | [[2012wp_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability.pdf]] | [[2012wp_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability]] | 5 | backtesting, strategies |
| Optimal Execution of Portfolio Transactions (Almgren & Chriss) | [[2000_Almgren-Chriss_Optimal-Execution.pdf]] | [[2000_Almgren-Chriss_Optimal-Execution]] | 3 | microstructure, risk |
| Time Series Momentum (Moskowitz, Ooi, Pedersen) | [[2012_Moskowitz-Ooi-Pedersen_Time-Series-Momentum.pdf]] | [[2012_Moskowitz-Ooi-Pedersen_Time-Series-Momentum]] | 3 | strategies |
| Value and Momentum Everywhere (Asness, Moskowitz, Pedersen) | [[2013_Asness-Moskowitz-Pedersen_Value-and-Momentum-Everywhere.pdf]] | [[2013_Asness-Moskowitz-Pedersen_Value-and-Momentum-Everywhere]] | 3 | strategies, portfolio |
| ...and the Cross-Section of Expected Returns (Harvey, Liu, Zhu) | [[2016_Harvey-Liu-Zhu_Cross-Section-of-Expected-Returns.pdf]] | [[2016_Harvey-Liu-Zhu_Cross-Section-of-Expected-Returns]] | 4 | backtesting |
| Empirical Asset Pricing via Machine Learning (Gu, Kelly, Xiu) | [[2020_Gu-Kelly-Xiu_Empirical-Asset-Pricing-via-ML.pdf]] | [[2020_Gu-Kelly-Xiu_Empirical-Asset-Pricing-via-ML]] | 3 | ai-ml |
| Volatility Managed Portfolios (Moreira & Muir) | [[2016wp_Moreira-Muir_Volatility-Managed-Portfolios.pdf]] | [[2016wp_Moreira-Muir_Volatility-Managed-Portfolios]] | 3 | risk |
| Pairs Trading: Performance of a Relative Value Arbitrage Rule (Gatev, Goetzmann, Rouwenhorst) | [[1999wp_Gatev-Goetzmann-Rouwenhorst_Pairs-Trading.pdf]] | [[1999wp_Gatev-Goetzmann-Rouwenhorst_Pairs-Trading]] | 0 | strategies |

## Not downloaded / failed
- **Elements of Statistical Learning (Hastie et al.)** — official PDF links on hastie.su.domains (`printings/ESLII_print12.pdf`, `Papers/ESLII.pdf`) returned an HTML 404 from the box on 2026-10-21. Free official copy is advertised at https://hastie.su.domains/ElemStatLearn/ — download manually in a browser.
- **Jansen, ML for Algorithmic Trading** — not a paper; code/notebooks are free at https://github.com/stefan-jansen/machine-learning-for-trading (book itself is paid). Link kept in reading list.
- **McLean & Pontiff published 2016 version**: RESOLVED 2026-10-21. Licensed copy obtained via St. John's library and saved as primary.
- **Gatev et al.** — scanned NBER PDF, no text layer; note has no quotes until OCR.
- Skipped non-author mirrors (counterpointfunds.com, gwern.net, elmwealth.com) to stay on author/official hosts.


## Batch 2 — Step 3 SSRN/NBER/arXiv mining (2026-10-21, unreviewed, promoted:false)

| File | Paper | Tags | RX-0001 flag |
|---|---|---|---|
| 2019_Baltussen-vanBekkum-Da_Indexing-and-Serial-Dependence.md | Indexing and Stock Market Serial Dependence Around the World (Baltussen, van Bekkum, Da) | strategies, microstructure | Does NOT by itself explain a post-2015 fade (it predicts negative dependence persisting as indexing grows). Test idea: measure SPY/QQQ/IWM daily AR(1) on Tiingo data by year; if it moved toward 0 after 2015 that is a candidate explanation for RX-0001's decay. |
| 2012_Nagel_Evaporating-Liquidity.md | Evaporating Liquidity (Nagel) | strategies, risk | Candidate explanation for the fade: 2015-2026 OOS is dominated by low-VIX years apart from 2020/2022; reversal returns should be small then. Test: split RX-0001 trades by VIX tercile at entry (VIX data from FRED VIXCLS, free). |
| 2014_Chordia-Subrahmanyam-Tong_Anomalies-Attenuated.md | Have Capital Market Anomalies Attenuated in the Recent Era of High Liquidity? (Chordia, Subrahmanyam, Tong) | strategies, backtesting | Supports an arbitrage-crowding explanation of RX-0001's decay (cross-sectional stock anomalies, not ETF timing; indirect). |
| 2019_Lou-Polk-Skouras_Tug-of-War-Overnight-Intraday.md | A Tug of War: Overnight Versus Intraday Expected Returns (Lou, Polk, Skouras) | strategies, microstructure | Candidate explanation for the next-open vs same-close gap, and a design lead: MOC (market-on-close) entries. Cross-sectional stock result, not ETF timing; needs a test on SPY/QQQ/IWM close-to-open vs open-to-close after signals. |
| 2018_Frazzini-Israel-Moskowitz_Trading-Costs.md | Trading Costs (Frazzini, Israel, Moskowitz) | microstructure, risk | — |
| 2024_Ardia-Guidotti-Kroencke_EDGE-Bid-Ask-Estimator.md | Efficient Estimation of Bid–Ask Spreads from OHLC Prices (Ardia, Guidotti, Kroencke) | microstructure, data | — |
| 2017_Abdi-Ranaldo_Bid-Ask-from-CHL.md | A Simple Estimation of Bid-Ask Spreads from Daily Close, High, and Low Prices (Abdi & Ranaldo) | microstructure, data | — |
| 2012_Corwin-Schultz_High-Low-Spread-Estimator.md | A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices (Corwin & Schultz) | microstructure, data | — |
| 2017_Petajisto_Inefficiencies-in-ETF-Pricing.md | Inefficiencies in the Pricing of Exchange-Traded Funds (Petajisto) | microstructure | — |
| 2018_Ben-David-Franzoni-Moussawi_ETFs-Increase-Volatility.md | Do ETFs Increase Volatility? (Ben-David, Franzoni, Moussawi) | microstructure | — |
| 1990_Lehmann_Fads-Martingales-Market-Efficiency.md | Fads, Martingales, and Market Efficiency (Lehmann) | strategies | — |
| 1990_Lo-MacKinlay_Contrarian-Profits.md | When Are Contrarian Profits Due to Stock Market Overreaction? (Lo & MacKinlay) | strategies | — |
| 2023_Pandey-Joshi_IBS-Country-ETFs_arXiv.md | Using Internal Bar Strength as a Key Indicator for Trading Country ETFs (Pandey & Joshi, arXiv) | strategies | Exit/filter lead: IBS-based exit or IBS<0.2 filter on RSI(2) entries; low evidence quality (student report, Yahoo data, no cost/overfitting controls). |
| 2005_Hsu-Kuan_Technical-Analysis-Reality-Check.md | Re-Examining the Profitability of Technical Analysis with White's Reality Check (Hsu & Kuan) | backtesting, strategies | Suggests per-ETF differences are real-ish: test whether IWM/QQQ carry most of any edge (beware: RX-0001 OOS IWM was weak). |
| 2000_Lo-Mamaysky-Wang_Foundations-of-Technical-Analysis.md | Foundations of Technical Analysis (Lo, Mamaysky, Wang) | strategies | — |

### Not obtained (login required or download failed; nothing bypassed)
- Kaminski & Lo, "When Do Stop-Loss Rules Stop Losses?": MIT DSpace returned HTTP 429. Retry later or use SSRN 968338 (login).
- Da, Liu & Schaumburg, "A Closer Look at the Short-Term Return Reversal" (Mgmt Sci 2014): nd.edu author copy timed out from the box and JPolo. Retry, or SSRN 1571326 (login).
- Cooper, Cliff & Gulen, "Return Differences between Trading and Non-trading Hours" (overnight): only a third-party copy found; SSRN 1004081 (login).
- Wijesinghe, "Do Simple Technical Trading Rules Survive Realistic Costs?": SSRN 6977700 (login).
- McLean & Pontiff JF 2016: RESOLVED (obtained via St. John's library).
