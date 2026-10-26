---
title: Manual fetch list (sources blocked to scripts, login-only, paywalled, or not yet legitimately retrievable)
status: unreviewed
promoted: false
created: 2026-10-22
---
# Manual fetch list

**Where to save:** print each item to PDF (browser "Print → Save as PDF") into `C:\Users\jason\OneDrive\Desktop\Quant\manual_sources\`. The folder has been created.

**How to name files:** `<row-id>_<short-name>_<YYYY-MM-DD>.pdf`. If a page offers an official download (CSV, XLSX or PDF), save that file as-is next to the PDF.

**What happens next:** the agent will take the PDFs from there, record a sha256, string-match quotes, and file them under the matching package.

**Rules:** I did not try to get around any block. URLs marked *(unverified)* are best guesses from search results. If one is wrong, use the site's own navigation to find the named item.

| ID | URL | Exact item / data needed | Package / claim it supports | Why blocked | Save format |
|---|---|---|---|---|---|
| M1 | https://www.cmegroup.com/trading/price-limits.html | Equity index rows for **MES, MNQ, ES and NQ**: dynamic circuit breaker %, daily limits, the "Special Price Fluctuations and Limits" guide link, and the page date | execution_costs (C24–C27: Velocity Logic and price-band values unknown); fill_models (halt/no-fill rows, B7–B8) | cmegroup.com returns 403 to scripts and an HTTP2 error to the automated browser | PDF of the page; save the linked guide as-is |
| M2 | Special Price Fluctuations and Limits guide / Rule 589 table, linked from M1 or the CME rulebook (https://www.cmegroup.com/rulebook/, unverified) | **Velocity Logic thresholds** (ticks and time window) for MES/MNQ, plus the related ES/NQ rows | execution_costs (VL values unknown; the I1 ES 6/18-tick figure is academic only); fill_models (L5 no-fill scenario) | Same CME block | Official PDF/XLSX as-is |
| M3 | CME "GCC Price Banding" list (referenced on the CME wiki Limits and Banding page; link on cmegroupclientsite.atlassian.net, or https://www.cmegroup.com/trading/price-banding.html, unverified) | **Price band values** for MES/MNQ (VL Narrow equals the band and VL Wide is 3× the band, per C24–C25) | execution_costs; fill_models | The link goes to cmegroup.com, which is blocked | PDF or official download |
| M4 | CME protection points page (search "protection points" on cmegroup.com; https://www.cmegroup.com/globex/trade-on-cme-globex/..., unverified) | **Protection point values** for market and stop orders on MES/MNQ | fill_models (B4: a protected stop can rest unfilled; option rows 1 and 3); execution_costs L3/L4 (D-COST-01 revisit trigger) | Same CME block | PDF |
| M5 | https://www.cmegroup.com/trading-hours.html, plus CME holiday calendar pages and archives for **2019–2025** (https://www.cmegroup.com/tools-information/holiday-calendar.html, unverified) | Holiday and early-close times for equity index futures, per date, for each year 2019–2025, and the 2026/2027 downloadable files | contracts (historical holiday/early-close archive is an unknown); economic_events (option h, CME early-close gap); synthesis T5 and the calendar artifact | 2026 notes were captured, but the downloadable per-product tables and past years are behind JS and downloads on the blocked site; Wayback domain search timed out | Official XLSX/PDF downloads as-is, plus a PDF of the index page |
| M6 | CME notices / Special Executive Reports on the equity index **daily settlement time change** (2020, 15:15 → 15:00 CT); search "SER settlement procedure E-mini 2020" on cmegroup.com/notices (unverified) | Effective date and wording of the change; the current equity settlement procedure document for ES/NQ/MES/MNQ | contracts (C2: settlement window change only from a lead source; history not homogeneous) | CME block | PDF |
| M7 | CME Liquidity Tool (https://www.cmegroup.com/tools-information/quikstrike/liquidity-tool.html, unverified) | MES and MNQ **bid-ask spread and top-of-book depth by hour**, with focus on 8:30–10:30 ET; export or screenshot for at least 1 month | execution_costs H3 / T4; the D-COST-01 revisit trigger | Requires Jason's CME login | CSV export if offered, plus a PDF print of the chart |
| M8 | https://www.cmegroup.com/terms-of-use.html and https://www.cmegroup.com/market-data/license-data.html (unverified) | Wording on (a) automated access and scraping, and (b) licensing of historical and derived CME market data (whether derived bars and metrics may sit in a repo) | providers (raw-data storage rule P7); every CME-sourced item | CME block | PDF |
| M9 | Databento licensing and terms (https://databento.com/terms, plus any licensing/redistribution page linked from it, unverified) | Redistribution, derived-data and storage terms for GLBX.MDP3 historical data | providers (unknown: Databento license and redistribution terms); P7 | Not yet retrieved; a no-Databento-API rule applies (public web pages are fine, but Jason can print them to avoid ambiguity) | PDF |
| M10 | US Treasury quarterly refunding (https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding) | Release **times (ET)** and dates of refunding statements and financing estimates, 2025–2026, as originally scheduled | economic_events (option g, expanded event set) | Not yet attempted; may be scriptable, so try a script first and print only if it's blocked | PDF |
| M11 | SSRN 7428398 (Fetna 2026) and IEEE Access doi 10.1109/access.2019.2899177 (TORB) | Full text: ES per-cell results, long/short split, $10 cost cells (Fetna); cost model (TORB) | orb_evidence (unknowns listed in orb_evidence.md and the Fetna addendum) | SSRN needs a login; the IEEE page has a consent wall | Publisher PDF as downloaded |
| M12 | López de Prado, *Advances in Financial Machine Learning*, chapters 7 and 12 (Jason's own copy) | Purged/embargoed CV and CPCV text, to quote | validation (AFML ch. 7/12 text not retrieved) | Paywalled book | PDF of the pages (personal copy) |
| M13 | MultiCharts wiki live pages (https://www.multicharts.com/trading-software/index.php/Intra-bar_Price_Movement_Assumptions, …/Limit_Order_Execution_Assumptions, …/Bar_Magnifier) | Current versions, to confirm the Wayback copies (2015–2024) still hold | fill_models B28–B32 | Cloudflare captcha for scripts (not evaded). Optional, because Wayback copies are held | PDF |

**Not listed because already retrieved legitimately:** Romano-Wolf 2005 (UZH author PDF, V16–V18); NinjaTrader IsFillLimitOnTouch (B33–B35); BLS and Fed point-in-time schedules (Wayback, E23–E29).
