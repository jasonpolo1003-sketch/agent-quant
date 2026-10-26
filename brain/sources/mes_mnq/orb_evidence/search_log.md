---
title: Package 5 search log (ORB evidence)
status: unreviewed
promoted: false
created: 2026-10-22 (UTC-5)
---
# Search log

The tool was WebSearch, a general web index. It returns hits from SSRN, arXiv, IDEAS/RePEc, IEEE, ScienceDirect and others. Google Scholar and NBER were **not queried directly**: the WebSearch index stood in for them. That is a limitation (see Unknowns in orb_evidence.md).

| Pass | # | Query (abridged) | Databases surfaced | New DIRECT works |
|---|---|---|---|---|
| 1 | 1–8 | opening range breakout E-mini / ES / NQ / MES / MNQ; SSRN ORB futures; arXiv ORB; Crabel opening range; ORB QQQ Zarattini; intraday momentum index futures; ORB crude oil / S&P futures; ORB volatility | SSRN, arXiv, IEEE, diva-portal, umu.se, JFE, practitioner sites | Fetna 2026; Mesfin 2026; Tsai et al. 2019 (TORB); Lundström; Levine 2026 |
| 2 | 9 | arXiv q-fin ORB ES 2025/2026 out-of-sample replication Zarattini decay | arXiv/scirate, SSRN, paperswithbacktest, practitioners | none (Mesfin and Fetna again) |
| 2 | 10 | intraday time-series momentum equity index futures opening breakout NBER RePEc | IDEAS/RePEc, IEEE, ScienceDirect, SSRN | none direct-ORB. Found Grant, Wolf & Yu 2005 (S&P futures opening continuation then reversal, not ORB) and Li, Sakkas & Urquhart 2022 (distant) |
| 2 | 11 | "opening range" breakout Nasdaq/NQ futures 2024 SSRN micro e-mini MES | SSRN (Mesfin mirror 6709401), arXiv, practitioners | none (Mesfin SSRN mirror = same work) |
| 3 | 12 | Scholar-style "opening range breakout" S&P 500 futures E-mini peer-reviewed Lundström | IDEAS, diva-portal, umu.se, IEEE | none (all already known) |
| 3 | 13 | "opening range" index futures false-breakout statistics DAX Taiwan KOSPI | IEEE (CIFER 2019, ICASSP 2020 Taiwan ORB), NDLTD thesis, practitioners | none for ES/NQ/MES/MNQ |

**Stop rule:** passes 2 and 3 were consecutive and added no new direct ES/NQ/MES/MNQ work, so the search stopped.

## Retrieval status
| Work | Status | File |
|---|---|---|
| Mesfin 2026 arXiv 2605.04004 | retrieved (PDF) | source_files/orb/mesfin_2026_mnq_falsification.pdf |
| Zarattini & Aziz 2023 (SSRN 4416622) | retrieved (free PDF, concretumgroup.com) | zarattini_aziz_2023_orb_qqq.pdf |
| Tsai et al., "Comparing Profitability ... Taiwan, Hong-Kong, and USA" | retrieved (kdajdqs.org PDF). The IEEE Access 2019 TORB article (doi 10.1109/access.2019.2899177) was **identified-not-retrieved** (consent wall) | tsai_torb_index_futures.pdf |
| Lundström, Day trading returns across volatility states | retrieved (diva-portal PDF) | lundstrom_volatility_states.pdf |
| Holmberg, Lönnbark & Lundström, FRL 2013 | abstract via IDEAS; umu.se working-paper PDF timed out → full text **identified-not-retrieved** | holmberg_2013_ideas.html/.txt |
| Fetna 2026 SSRN 7428398 | RETRIEVED 2026-10-22 via Jason manual SSRN download | fetna_2026_orb_225cell.pdf/.txt |
| Levine 2026 SSRN 6833239; Howard 2026 SSRN 6350238; Zarattini SSRN 4824172 / 4729284; Gao et al. SSRN 2552752 (JFE 2018); Grant, Wolf & Yu SSRN 689282 (JBF 2005); Baltussen et al. JFE 2021; Li, Sakkas & Urquhart JFM 2022 | **identified-not-retrieved** (SSRN block / paywall) | — |
| CE Market Solutions NQ ORB 324 variations | retrieved (practitioner LEAD) | cemarketsolutions_nq_orb_lead.html/.txt |
| paperswithbacktest ORB replication page | retrieved (practitioner LEAD, no quotes verified) | paperswithbacktest_orb.html |
