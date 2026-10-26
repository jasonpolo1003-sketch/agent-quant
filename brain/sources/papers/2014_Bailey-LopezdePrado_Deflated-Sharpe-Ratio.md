---
type: paper_note
status: unreviewed
promoted: false
citation: "Bailey, D.H., L\u00f3pez de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. Journal of Portfolio Management 40(5), 94\u2013107."
source_url: "https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf"
canonical: "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551"
pdf: "2014_Bailey-LopezdePrado_Deflated-Sharpe-Ratio.pdf"
version_note: "Author-hosted, version July 31, 2014 (JPM forthcoming)"
topics: ["backtesting", "risk"]
retrieved: "2026-10-21"
quote_check: "each quote string-matched against pdftotext output of the cited PDF page (whitespace normalized; page = PDF page index, not journal page)"
---
# The Deflated Sharpe Ratio (Bailey & López de Prado)

**Citation:** Bailey, D.H., López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. Journal of Portfolio Management 40(5), 94–107.  
**Free copy:** https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf  
**Version:** Author-hosted, version July 31, 2014 (JPM forthcoming)

## Key points (each backed by verbatim quote)

1. **DSR corrects two sources of inflation**  
   > "The Deflated Sharpe Ratio (DSR) corrects for two leading sources of performance inflation: Selection bias under multiple testing and non-Normally distributed returns." (PDF p.2)

2. **Number of trials is the missing disclosure**  
   > "the most important piece of information missing from virtually all backtests published in academic journals and investment offerings is the number of trials attempted." (PDF p.3)

3. **Enough search guarantees a false positive**  
   > "After a sufficient number of trials, it is guaranteed that a researcher will always find a misleadingly profitable strategy, a false positive." (PDF p.4)

4. **Expected max Sharpe rises with trials**  
   > "as the number of independent trials (N) grows, so will grow the expected maximum of" (PDF p.8)

5. **What to disclose**  
   > "disclose: i) The number of independent trials carried out (N); ii) the variance of the backtest results" (PDF p.9)

## Relevance to Quant Agent Brain
Make the harness **log every trial** (each RSI exit level, hold cap, cost scenario tested) and report N, variance of trial Sharpes, sample length T, skew and kurtosis with each backtest report, then compute DSR. A backtest report missing N should fail the gate. Pairs naturally with PBO.

## Caveats
Abstract/intro-level points only; body not yet reviewed. Reviewer should confirm before any promotion.
