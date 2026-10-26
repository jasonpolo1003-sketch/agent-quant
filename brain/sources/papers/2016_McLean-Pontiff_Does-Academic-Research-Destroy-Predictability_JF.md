---
type: paper_note
status: unreviewed
promoted: false
citation: "McLean, R.D., Pontiff, J. (2016). Does Academic Research Destroy Stock Return Predictability? Journal of Finance 71(1), 5–32."
canonical: "https://doi.org/10.1111/jofi.12365"
pdf: "2016_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability_JF.pdf"
version_note: "Published JF version, licensed copy via St. John's University library, for Jason's personal research only. Do not redistribute or share."
supersedes_as_primary: "2012wp_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability.md"
topics: ["backtesting","strategies"]
retrieved: "2026-10-21"
quote_check: "string-matched against pdftotext of each page (whitespace normalized). p. = PDF page index; journal page = PDF page + 4."
---
# Does Academic Research Destroy Stock Return Predictability? (McLean & Pontiff, JF 2016) — PRIMARY VERSION

## Key numbers
- Sample: 97 cross-sectional predictors.
- Out-of-sample (after the original sample ends, before publication): returns are **26% lower**. This is the upper bound on data mining.
- Post-publication: returns are **58% lower**, implying about a **32%** publication or arbitrage effect.
- Arbitrage costs: decay is larger for predictors with higher in-sample returns. Returns stay higher where arbitrage is costly (high idiosyncratic risk, low liquidity).
- Trading signs: turnover, dollar volume, short interest and correlation with other published predictors all rise after publication.

## Verbatim quotes

1. **Headline decay**  
   > "Portfolio returns are 26% lower out-of-sample and 58% lower post-publication." (PDF p.1; JF p.5)

2. **Publication effect**  
   > "We estimate a 32% (58%–26%) lower return from publication-informed trading." (PDF p.1; JF p.5)

3. **Data-mining bound**  
   > "The out-of-sample decline is an upper bound estimate of data mining effects." (PDF p.1; JF p.5)

4. **Bigger in-sample = bigger decay; arbitrage costs preserve returns**  
   > "Post-publication declines are greater for predictors with higher in-sample returns, and returns are higher for portfolios concentrated in stocks with high idiosyncratic risk and low liquidity." (PDF p.1; JF p.5)

5. **Arbitrage-cost test logic**  
   > "If predictor returns are the outcome of rational asset pricing, then the post-publication decline should not be related to arbitrage costs." (PDF p.17; JF p.21)

6. **Pre-publication pressure tempered by costs**  
   > "The results largely support the notion that some sophisticated traders exert price pressure pre-publication, but the price pressure is tempered by arbitrage costs." (PDF p.19; JF p.23)

7. **Trading activity rises**  
   > "we find that turnover, dollar volume, and especially short interest increase significantly in predictor portfolios post-publication." (PDF p.24; JF p.28)

8. **Correlation with other predictors rises**  
   > "Predictor portfolios exhibit post-publication increases in correlations with other published-predictor portfolios." (PDF p.1; JF p.5)

## Relevance to RX-0001 fade
- RSI(2) and Connors ETF rules were popularized around 2008–2009 (Connors & Alvarez books) and were widely discussed afterward. Under McLean-Pontiff, expect about 26% decay from data mining and up to about 58% after a strategy becomes public. RX-0001's E1/A pooled Sharpe fell from 0.61 in-sample to 0.35 out-of-sample, a drop of about 43%. That is within this range.
- The arbitrage-cost interaction cuts against persistence here. SPY, QQQ and IWM are the cheapest instruments to arbitrage (spreads under 1 bp; see `brain/sources/costs/RQ-80be8cf7_cost_assumptions.md`). The paper's logic therefore predicts the *strongest* decay for this kind of edge.
- Caveat: the evidence is cross-sectional single-stock anomalies, not ETF timing rules, so it is analogy, not a direct test. Pair with Chordia-Subrahmanyam-Tong 2014 and Baltussen et al. 2019.
- Testable: date the "publication" of RSI(2) (about 2008) and compare RX-0001 performance before and after that date, alongside the 2015 split.
