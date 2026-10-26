---
type: paper_note
status: unreviewed
promoted: false
citation: "Bailey, D.H., Borwein, J.M., L\u00f3pez de Prado, M., Zhu, Q.J. (2017). The Probability of Backtest Overfitting. Journal of Computational Finance 20(4). Revised version Feb 2015."
source_url: "https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf"
canonical: "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253"
pdf: "2017_Bailey-Borwein-LopezdePrado-Zhu_Probability-of-Backtest-Overfitting.pdf"
version_note: "Author-hosted revised version, February 2015 (34 pp.)"
topics: ["backtesting", "risk"]
retrieved: "2026-10-21"
quote_check: "each quote string-matched against pdftotext output of the cited PDF page (whitespace normalized; page = PDF page index, not journal page)"
---
# The Probability of Backtest Overfitting (Bailey, Borwein, López de Prado, Zhu)

**Citation:** Bailey, D.H., Borwein, J.M., López de Prado, M., Zhu, Q.J. (2017). The Probability of Backtest Overfitting. Journal of Computational Finance 20(4). Revised version Feb 2015.  
**Free copy:** https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf  
**Version:** Author-hosted revised version, February 2015 (34 pp.)

## Key points (each backed by verbatim quote)

1. **Simple hold-out is unreliable for strategy selection**  
   > "Standard statistical techniques designed to prevent regression overfitting, such as hold- out, tend to be unreliable and inaccurate in the context of investment backtests." (PDF p.2)

2. **PBO definition**  
   > "the probability of backtest overfitting (PBO) is then eval- uated as the conditional probability that this strategy underperforms the median OOS while remaining optimal IS." (PDF p.5)

3. **CSCV avoids a single fixed hold-out by swapping IS/OOS splits**  
   > "We avoid the credibility issue of pre- serving a truly out-of-sample test-set by not requiring a fixed “hold-out,” and swapping all in-sample (IS) and out-of-sample (OOS) datasets." (PDF p.6)

4. **Only needs the backtest return series, model-free**  
   > "One advantage of our solution is that it only requires time series of backtested performance." (PDF p.6)

5. **Four diagnostics beyond PBO**  
   > "Performance degradation: This determines to what extent greater per- formance IS leads to lower performance OOS" (PDF p.13)

## Relevance to Quant Agent Brain
Direct input to a **backtest gate**. For the RSI exit/max-hold RQs, every grid of exit thresholds x hold caps x cost assumptions is a set of N configurations; save the per-config return series and run CSCV to report PBO alongside the chosen config. Fail closed if PBO is high (threshold to be set by reviewer; paper does not prescribe one for us). Also supports reporting performance degradation (IS vs OOS rank) per RQ.

## Caveats
Abstract/intro-level points only; body not yet reviewed. Reviewer should confirm before any promotion.
