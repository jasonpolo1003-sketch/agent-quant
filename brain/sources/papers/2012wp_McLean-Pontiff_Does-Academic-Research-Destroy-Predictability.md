---
superseded_by: "2016_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability_JF.md"
type: paper_note
status: unreviewed
promoted: false
citation: "McLean, R.D., Pontiff, J. (2016). Does Academic Research Destroy Stock Return Predictability? Journal of Finance 71(1), 5\u201332."
source_url: "https://abfer.org/media/abfer-events-2013/annual-conference/corporate-finance/track2-does-academic-research-destroy-stock-return-predictability.pdf"
canonical: "https://doi.org/10.1111/jofi.12365"
pdf: "2012wp_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability.pdf"
version_note: "WORKING PAPER dated January 23, 2012 (82 characteristics), posted by ABFER conference. NOT the published version: published JF 2016 abstract reports 97 predictors, 26% out-of-sample and 58% post-publication declines. SSRN full text (abstract 2156623) returned HTTP 403 without login."
topics: ["backtesting", "strategies"]
retrieved: "2026-10-21"
quote_check: "each quote string-matched against pdftotext output of the cited PDF page (whitespace normalized; page = PDF page index, not journal page)"
---
# Does Academic Research Destroy Stock Return Predictability? (McLean & Pontiff)

> **Superseded as primary** by the published JF 2016 version: [[2016_McLean-Pontiff_Does-Academic-Research-Destroy-Predictability_JF]]. Cite the published numbers (26% out-of-sample / 58% post-publication decline); keep this working paper for history only.

**Citation:** McLean, R.D., Pontiff, J. (2016). Does Academic Research Destroy Stock Return Predictability? Journal of Finance 71(1), 5–32.  
**Free copy:** https://abfer.org/media/abfer-events-2013/annual-conference/corporate-finance/track2-does-academic-research-destroy-stock-return-predictability.pdf  
**Version:** WORKING PAPER dated January 23, 2012 (82 characteristics), posted by ABFER conference. NOT the published version: published JF 2016 abstract reports 97 predictors, 26% out-of-sample and 58% post-publication declines. SSRN full text (abstract 2156623) returned HTTP 403 without login.

## Key points (each backed by verbatim quote)

1. **Out-of-sample decay (2012 draft estimate)**  
   > "The average out-of-sample decay due to statistical bias is about 10%, but not statistically different from zero." (PDF p.1)

2. **Post-publication decay (2012 draft estimate)**  
   > "The average post-publication decay, which we attribute to both statistical bias and price pressure from aware investors, is about 35%, and statistically different from both 0% and 100%." (PDF p.1)

3. **Interpretation: mispricing that gets traded away**  
   > "Our findings point to mispricing as the source of predictability." (PDF p.1)

4. **Decay is larger where arbitrage is cheap**  
   > "Consistent with costly (limited) arbitrage, post-publication return declines are greater for characteristic portfolios that consist of stocks with low idiosyncratic risk." (PDF p.1)

5. **Three-period design**  
   > "We compare each characteristic’s return-predictability over three distinct periods: (i) the original study’s sample period; (ii) after the original sample period but before" (PDF p.2)

## Relevance to Quant Agent Brain
Sets a **haircut prior** for published rules like Connors RSI(2): expect materially weaker results post-publication, and the haircut should be larger for very liquid instruments (SPY/QQQ/IWM are the cheapest-to-arbitrage case). Harness idea: split every literature-sourced rule test into in-sample / post-sample-pre-publication / post-publication windows using the source's publication date.

## Caveats
Numbers here are from the 2012 working paper and differ from the published 2016 paper (26% / 58% / 32%). Cite the published version once obtained via St. John's library (Wiley JF access) or SSRN login. Cross-sectional stock anomalies, not ETF timing rules.
