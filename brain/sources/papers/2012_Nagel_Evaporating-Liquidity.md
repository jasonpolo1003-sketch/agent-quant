---
type: paper_note
status: unreviewed
promoted: false
citation: "Nagel, S. (2012). Evaporating Liquidity. Review of Financial Studies 25(7), 2005\u20132039."
source_url: "https://www.nber.org/system/files/working_papers/w17653/w17653.pdf"
canonical: "https://doi.org/10.1093/rfs/hhs066"
pdf: "2012_Nagel_Evaporating-Liquidity.pdf"
version_note: "NBER Working Paper 17653, Dec 2011"
topics: ["strategies", "risk"]
rx0001_flag: "Candidate explanation for the fade: 2015-2026 OOS is dominated by low-VIX years apart from 2020/2022; reversal returns should be small then. Test: split RX-0001 trades by VIX tercile at entry (VIX data from FRED VIXCLS, free)."
retrieved: "2026-10-21"
quote_check: "each quote string-matched against pdftotext of the cited PDF page (whitespace normalized; PDF page index)"
---
# Evaporating Liquidity (Nagel)

**Citation:** Nagel, S. (2012). Evaporating Liquidity. Review of Financial Studies 25(7), 2005–2039.  
**Free copy:** https://www.nber.org/system/files/working_papers/w17653/w17653.pdf  
**Version:** NBER Working Paper 17653, Dec 2011

## Key points (verbatim quotes)

1. **Reversal = paid liquidity provision**  
   > "The returns of short-term reversal strategies in equity markets can be interpreted as a proxy for the returns from liquidity provision." (PDF p.2)

2. **Predictable with VIX**  
   > "the expected return from liquidity provision is strongly time-varying and highly predictable with the VIX index." (PDF p.2)

3. **Even industry-level reversal pays in high VIX**  
   > "Even reversal strategies formed from industry portfolios (which do not yield high returns unconditionally) produce high rates of return and high Sharpe Ratios during times of high VIX." (PDF p.2)

## Relevance to Quant Agent Brain
Best candidate **filter**: condition RSI entries on VIX level/regime. Theory for why oversold buys pay most in stress.

## RX-0001 flag
Candidate explanation for the fade: 2015-2026 OOS is dominated by low-VIX years apart from 2020/2022; reversal returns should be small then. Test: split RX-0001 trades by VIX tercile at entry (VIX data from FRED VIXCLS, free).

## Caveats
Abstract/intro-level reading only; body not reviewed.
