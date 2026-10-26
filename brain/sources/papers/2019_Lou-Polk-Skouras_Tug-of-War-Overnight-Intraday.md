---
type: paper_note
status: unreviewed
promoted: false
citation: "Lou, D., Polk, C., Skouras, S. (2019). A tug of war: Overnight versus intraday expected returns. Journal of Financial Economics 134, 192\u2013213."
source_url: "https://personal.lse.ac.uk/POLK/research/TugOfWar.pdf"
canonical: "https://doi.org/10.1016/j.jfineco.2019.03.011"
pdf: "2019_Lou-Polk-Skouras_Tug-of-War-Overnight-Intraday.pdf"
version_note: "Author-hosted published JFE version"
topics: ["strategies", "microstructure"]
rx0001_flag: "Candidate explanation for the next-open vs same-close gap, and a design lead: MOC (market-on-close) entries. Cross-sectional stock result, not ETF timing; needs a test on SPY/QQQ/IWM close-to-open vs open-to-close after signals."
retrieved: "2026-10-21"
quote_check: "each quote string-matched against pdftotext of the cited PDF page (whitespace normalized; PDF page index)"
---
# A Tug of War: Overnight Versus Intraday Expected Returns (Lou, Polk, Skouras)

**Citation:** Lou, D., Polk, C., Skouras, S. (2019). A tug of war: Overnight versus intraday expected returns. Journal of Financial Economics 134, 192–213.  
**Free copy:** https://personal.lse.ac.uk/POLK/research/TugOfWar.pdf  
**Version:** Author-hosted published JFE version

## Key points (verbatim quotes)

1. **Reversal profits earned overnight**  
   > "profits are either earned entirely overnight (for reversal and a variety of momentum strategies) or entirely intraday" (PDF p.1)

2. **Same for short-term reversal**  
   > "essentially all of the abnormal returns on momentum and short-term reversal strategies occur overnight" (PDF p.21)

## Relevance to Quant Agent Brain
Directly relevant to **fill timing**: RX-0001 showed same-close fills beat next-open by about 0.1–0.2 Sharpe. If reversal profit accrues overnight, buying at the next open skips the profitable leg.

## RX-0001 flag
Candidate explanation for the next-open vs same-close gap, and a design lead: MOC (market-on-close) entries. Cross-sectional stock result, not ETF timing; needs a test on SPY/QQQ/IWM close-to-open vs open-to-close after signals.

## Caveats
Abstract/intro-level reading only; body not reviewed.
