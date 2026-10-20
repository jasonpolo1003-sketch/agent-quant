---
id: GATE-D-SEED-DOSSIER-2026-09-26
type: research_lead_dossier
status: proposed
evidence_status: unverified
created: 2026-09-26
related_plan: PLAN.md Phase 6
research_ids: [RQ-6d9c12f4, RQ-c920baeb, RQ-80be8cf7]
related_proposals: [PROP-004, PROP-005]
---

# Gate D pre-run seed dossier (checkpoint E1)

> **Leads, not evidence.** Nothing in this file is verified, reviewed, promoted or counted toward
> Phase 6. It is the pre-run relevance check for each child question. Every candidate listed here
> would still have to be re-fetched and snapshotted by the Scout, extracted by Qwen and pass the
> unchanged validators, then clear the separately dispatched curator. A keyword hit or a report's
> citation is a screening aid, not support.

## How the dossier was built

- **Scope:** checkpoint E1 only. No code change, no Scout or curator dispatch, no model call through
  the harness, and no write to `db/brain.sqlite` or the intake catalog.
- **RQ-6d9c12f4:** built offline from pinned snapshots in
  `C:/Users/jason/quant-agent-brain-intake/exit-rules-final`. Every snapshot's `content_sha256` was
  re-checked, and 16/16 fetched or rejected snapshots match. Tiers were re-derived with the unmodified
  `source_quality.classify_source`. The script is read-only (session scratchpad, `dossier_scan.py`).
- **RQ-c920baeb and RQ-80be8cf7:** bounded lead discovery with a web search tool used as a lead
  finder, **5 queries per question** (cap 6). Leads were screened with one page fetch each, using
  prompts that asked for exact sentences. Those extractions came from a small model and are
  **screening only**. Two PDFs were extracted locally with `pypdf`.
- **Anchor terms (screening only):**
  - exit: `RSI`, `exit|sell|sold`, `ETF|SPY|QQQ|IWM|S&P 500`
  - max hold: `time stop`, `after N days`, `maximum … days`, `holding period`
  - cost: `commission|slippage|transaction cost|bid-ask|spread`

### Baseline at the start of E1

| Check | Result |
|---|---|
| `uv run pytest -q` | 425 passed, 1 skipped |
| `uv run ruff check .` | clean |
| `git diff --check` | clean |
| `db/brain.sqlite` SHA-256 | `6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29` |
| `exit-rules-final/external.sqlite` SHA-256 | `4b20094c6c6d4f97ba6bfdd410ef8745fae37bfe683e100ef36f6ae664047c00` |
| `agent-reach doctor` | `exa_search` **off**, `github` warn, `web` ok, `rss` ok |
| `gate_readiness.py` (all three) | **exit 4, 0 unique URLs** |

## New findings from E1 (not fixed; each needs its own decision)

1. **The arXiv lane is currently non-operational from Python.** For every question, `gate_readiness`
   reports `arXiv request failed: HTTPError: HTTP Error 406: Not Acceptable`.
   - Plain `urllib` receives the 406 from `export.arxiv.org` with the project's headers, and also
     with a curl-like User-Agent.
   - `curl` gets **200** for the same URL.
   - Cause not established. It is not a header issue.
   - Before 2026-09-20, RQ-6d9c12f4 was probe-ready at 3 URLs. It is now 0.
   - **Consequence:** every approved search lane now returns 0 candidates for all three questions.
2. **The DOI alias double-counts.** `distinct_upstream_keys` returns **2** keys for
   `https://doi.org/10.15405/epms.2022.10.4` and its publisher landing page
   `https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4`, which are one work. This is
   the same inflation class PROP-003 closed for arXiv versions. A seed rule must exclude such aliases,
   and a code fix would be a tightening.
3. **sec.gov comment letters classify as `primary` on host alone.** This applies to whoever wrote the
   letter, whether the exchange itself or a third-party commenter. It is not changed here, but a
   reviewer must record the actual author and whether the figure is measured.
4. **Plan correction.** The E1 plan said all three catalog DOI primaries were blocked. In fact
   `doi.org/10.15405/epms.2022.10.4` was **fetched** (4,522 words). Only `ssrn.4708400` (access
   blocked) and `0022-1082.00163` (content rejected) are unavailable.

---

## RQ-6d9c12f4 — exit rules for daily ETF RSI-oversold entries

**Seed rule, as declared in the approved plan:** every catalog target with a located verbatim
exit-rule span. That gives 5 targets.

| # | URL | Tier (re-derived) | Originator group | Access | Screening hits (RSI / exit / ETF) | Verbatim span (from pinned snapshot) | Relevance note |
|---|---|---|---|---|---|---|---|
| 1 | chartschool.stockcharts.com/…/rsi-2 | practitioner | **Connors** | fetched, hash ok | 87 / 22 / 2 | "In his example using the S&P 500, Connors advocates exiting long positions on a move above the 5-day SMA and short positions on a move below the 5-day SMA." | RSI(2) entry. The exit is price-based, not an RSI level. |
| 2 | articles.stockcharts.com/…arthurhill-2016-12…spy-qqq-and-ijr | practitioner | **Hill** | fetched, hash ok | 26 / 21 / 21 | "The original system bought when RSI(5) moved below 30 and sold when RSI(5) moved above 70." | SPY/QQQ/IJR, daily. RSI(5), not a locked entry. |
| 3 | connorsresearch.com/…does-mean-reversion-still-work | discovery-only | **Connors** | fetched, hash ok | 8 / 3 / 11 | "\*\*Sell\*\* when the 4-period RSI closes above 55." | Uses RSI(4). Not independent of #1. |
| 4 | naaim.org/…Pagonidis_The-IBS-Effect…pdf | discovery-only | **Pagonidis** | fetched, hash ok | 17 / 0 / 79 | "Maintain the position while RSI(3) ≤ 40" | Equity ETFs. The exit is implied. |
| 5 | thepatternsite.com/Double7sSetup.html | discovery-only | **Connors** (quoted from Connors & Alvarez) | fetched, hash ok | 0 / 59 / 18 | "Exit when the ETF closes at a seven-day high." | Not RSI-based, so low relevance. |

**Additional candidate found by the full-catalog scan, outside the declared rule and listed for
Jason's decision (not auto-added):**

| # | URL | Tier | Originator group | Access | Hits | Verbatim span | Relevance note |
|---|---|---|---|---|---|---|---|
| 6 | doi.org/10.15405/epms.2022.10.4 | **primary** | Malaysian proceedings authors applying the conventional RSI(14) 30/70 rule | fetched, hash ok | 89 / 29 / 0 | "If the RSI is below 30, it is oversold, and a buy signal is issued; if it is above 70, it is overbought, and a sell signal is generated." | Matches the **locked Wilder RSI(14)<30** entry. But the instruments are **Malaysian equities**, not SPY/QQQ/IWM. It is a low-profile proceedings chapter, and its publisher landing page is an alias (finding 2). |

**Counts:**

| Measure | Declared rule (#1–5) | With #6 |
|---|---|---|
| Distinct URLs, which is what the Scout's `MIN_UPSTREAM_SOURCES` counts | 5 | 6 (7 if the alias were counted, which it must not be) |
| Relevant (an RSI-conditioned exit rule) | 4 (#1–4) | 5 |
| Promotable tier | 2 (#1, #2) | 3 (#1, #2, #6) |
| Distinct originators among the promotable ones | 2 (Connors, Hill) | 3 (Connors, Hill, epms authors) |

**Pre-run finding:**
- Under the declared rule, a seeded Scout run could clear the ≥3 distinct-URL bar, but the curator
  could promote **at most 2 sources from 2 originators**.
- Including #6 raises the ceiling to 3 promotable sources from 3 originators, at the cost of a clear
  instrument-scope mismatch. That trade-off is a scope judgement for Jason, not something the
  pipeline should decide.
- **Before any run, Jason decides whether #6 enters the seed list.** The list must not be edited
  after a run.

---

## RQ-c920baeb — hard maximum holding periods

Five queries were logged, with the time-stop and max-hold phrasing aimed at practitioner-allowlist
and academic hosts first.

| # | URL | Tier | Access | Hard-cap statement (screening quote) | In scope? |
|---|---|---|---|---|---|
| 1 | chartschool …/rsi-2 (pinned) | practitioner | ok | none found (0 time-stop hits) | — |
| 2 | connorsresearch.com … (pinned) | discovery-only | ok | "the sweet spot for mean reversion equity trading tends to be 3-7 days", plus an "Average Hold in Trading Days" figure | **No.** These are averages and a preference, which the question explicitly excludes. |
| 3 | articles.stockcharts.com …arthurhill-2016-07… | practitioner | ok | none. The article specifies no time exit. | — |
| 4 | arxiv.org/abs/2506.06356 | primary | ok | "maintaining 50-100 daily positions with a 9-day maximum holding period" | **Partial:** Chinese A-shares with a deep-learning signal. Not an ETF or RSI swing rule. |
| 5 | swingfolio.com …/rsi-2-strategy | discovery-only | ok | "If no exit condition after 10 trading days, exit at market close on day 10" | **No as sole evidence.** It gives no citation and is an SEO-education site, which the question puts out of scope. |
| 6 | ssrn.com/abstract=4339128 (Micaletti) | primary | **HTTP 403** | not assessed | unknown |

**Counts:** 2 relevant and accessible hard-cap statements (#4 with a scope mismatch, #5
out-of-scope tier). In-scope promotable: **0**.

**Pre-run finding: source-insufficient.** There are fewer than 3 relevant, accessible, distinct
candidates. No weaker leads were added to reach 3.

---

## RQ-80be8cf7 — fixed commission and slippage for liquid US ETFs

Five queries were logged, aimed at regulator, exchange, academic and practitioner hosts.

| # | URL | Tier | Access | Screening quote | Measured or assumed | In scope? |
|---|---|---|---|---|---|---|
| 1 | sec.gov/comments/sr-nasdaq-2012-043/nasdaq2012043-28.pdf | primary (host) | ok (pypdf) | "The average daily spreads of the QQQ ETF are in the 1 … 1 to 2 basis point range" (pypdf line breaks) | **Measured.** This is Nasdaq's own data response to the SEC, covering Jan 2011 – Aug 2012. | QQQ only, and the data is from 2011–12, so it is dated. |
| 2 | arxiv.org/abs/2603.20319 | primary | ok (HTML) | "The baseline regime of 18 bps decomposes into 15 bps for commission and 3 bps for price impact (slippage), calibrated to the all-in cost of a retail brokerage that executes US large-cap equities in 2024." | **Assumed**, as a calibrated regime. | US large-cap equities, not ETFs specifically. |
| 3 | quantstart.com …Part-II | practitioner | ok | no numbers | — | no |
| 4 | robotwealth.com …backtesting… | practitioner | ok | no numbers | — | no |
| 5 | sec.gov/comments/s7-11-15/s71115-29.pdf (Angel, 2015) | primary (host) | ok (pypdf) | no SPY/QQQ/IWM spread figure found | — | no |
| 6 | alphaarchitect.com/trading-costs-destroy-factor-investing | practitioner | **HTTP 403** | not assessed | — | unknown |

**Counts:** 2 relevant and accessible candidates (#1 measured, #2 assumed), from 2 originators
(Nasdaq and the paper's authors). Both are promotable tier.

**Pre-run finding: source-insufficient.** There are fewer than 3 candidates. SEC Rule 605 or 606
execution-quality statistics would be the natural primary source for measured ETF effective spreads,
but no page giving SPY/QQQ/IWM figures was located within the query budget.

---

## Summary

| RQ | Relevant, accessible, distinct candidates | Promotable | Distinct originators (promotable) | Pre-run finding |
|---|---|---|---|---|
| 6d9c12f4 | 4 (5 with #6) | 2 (3 with #6) | 2 (3 with #6) | Scout bar clearable with a seed lane. Research ceiling 2 or 3, pending Jason's scope call on #6. |
| c920baeb | 2 (both out of scope) | 1 (off-scope) | — | **source-insufficient** |
| 80be8cf7 | 2 | 2 | 2 | **source-insufficient** |

**Not done in E1:** no seed files, no code change, no Scout or curator run, no tier or validator
change, and no intake-catalog or production-DB write.
