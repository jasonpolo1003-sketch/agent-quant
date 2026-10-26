---
type: paper_note
status: unreviewed
promoted: false
citation: "Pandey, A., Joshi, K. (2023). Using Internal Bar Strength as a Key Indicator for Trading Country ETFs. arXiv:2306.12434 [q-fin.ST]."
source_url: "https://arxiv.org/pdf/2306.12434"
canonical: "https://arxiv.org/abs/2306.12434"
pdf: "2023_Pandey-Joshi_IBS-Country-ETFs_arXiv.pdf"
version_note: "arXiv v1, 14 Jun 2023 (student report, not peer reviewed)"
topics: ["strategies"]
rx0001_flag: "Exit/filter lead: IBS-based exit or IBS<0.2 filter on RSI(2) entries; low evidence quality (student report, Yahoo data, no cost/overfitting controls)."
retrieved: "2026-10-21"
quote_check: "each quote string-matched against pdftotext of the cited PDF page (whitespace normalized; PDF page index)"
---
# Using Internal Bar Strength as a Key Indicator for Trading Country ETFs (Pandey & Joshi, arXiv)

**Citation:** Pandey, A., Joshi, K. (2023). Using Internal Bar Strength as a Key Indicator for Trading Country ETFs. arXiv:2306.12434 [q-fin.ST].  
**Free copy:** https://arxiv.org/pdf/2306.12434  
**Version:** arXiv v1, 14 Jun 2023 (student report, not peer reviewed)

## Key points (verbatim quotes)

1. **IBS rule**  
   > "stocks that close with an IBS below 0.2, will rise in price the next day" (PDF p.1)

2. **Data**  
   > "Our analysis uses ETF data from 2009/1/1 to 2019/12/31." (PDF p.2)

## Relevance to Quant Agent Brain
Candidate alternative **entry/exit** indicator: IBS = (close-low)/(high-low). Popular practitioner companion to RSI(2).

## RX-0001 flag
Exit/filter lead: IBS-based exit or IBS<0.2 filter on RSI(2) entries; low evidence quality (student report, Yahoo data, no cost/overfitting controls).

## Caveats
Weak evidence: not peer reviewed.
