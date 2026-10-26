---
title: Scraper inventory and retry of missing items (2026-10-22)
status: unreviewed
promoted: false
date: 2026-10-22
---
# Scraper inventory and retry log

Rules followed: no logins, no paywall bypass, no captcha evasion, robots.txt checked (MultiCharts: `User-agent: * Allow: /`, content signal `use=reference, ai-train=no`; NinjaTrader: `Disallow:` empty), nothing paid, no Databento. All times are box-local UTC-5 unless marked.

## Step 1: scraper tools found
| Tool | Location | How to run | Status on 2026-10-22 |
|---|---|---|---|
| Research Scout runner | repo `scripts/research_scout_runner.py`, `agents/research_scout.md`, `brain/_system/research_scout_runner_workflow.md` | `uv run python scripts/research_scout_runner.py prepare` | Only prepares a work packet and raw-note scaffold from the research_questions table. Its own doc says it "does not yet automate web browsing". Not a fetcher |
| Scout live discovery (dispatcher + Agent Reach adapter) | `scripts/dispatch_task.py`, `src/quant_brain/discovery/{agent_reach,live_discovery,acquisition}.py`, `brain/_system/agent_reach_adapter_workflow.md` | `uv run python scripts/agent_reach_check.py`, then `research_intake.py add …`, then `dispatch_task.py --type discovery --research-id RQ-…` | `agent_reach_check` exit 0. **Exa search lane NOT usable** (mcporter/Exa off). Usable lanes: github, arXiv, youtube, rss. Fetch = Jina Reader |
| Agent Reach CLI | `C:\Users\jason\.agent-reach-venv\Scripts\agent-reach.exe`; vault skill `memory_vault\Skills\agent-reach\SKILL.md` | `agent-reach doctor --json`; web pages via `https://r.jina.ai/<url>` | Doctor runs. Social lanes are login-backed and stay off |
| pack-research skill | `memory_vault\Skills\pack-research\pack-research.md` | Wraps agent-reach (Jina, yt-dlp, feedparser) | Veyra-specific; same fetch lane |
| fetch_calendar.py | repo `scripts/fetch_calendar.py` | `uv run python scripts/fetch_calendar.py` | FOMC page plus FRED (needs FRED_API_KEY) plus yfinance. Not run: it writes `data/processed/calendar.json` and uses a key; it has no point-in-time history |
| Box tools (open source) | curl; Wayback CDX and availability APIs; CDP Chrome grabber `/tmp/grab.py`; poppler | — | Used as the fallback |
| Other vault skills (design, seo, website, job-apply) | memory_vault\Skills | — | Not scrapers |

**Research Scout verdict.** I did not run the full discovery pipeline. Its only general web-search lane, Exa, is off. GitHub and arXiv lanes can't find vendor docs or agency calendars. A run would also need a new RQ written into the repo's research_questions store, which is a repo state change. I did use its **fetch lane (Jina Reader)**:
- From the box: blocked with HTTP 401 "bad network reputation (AS54113)".
- From JPolo: HTTP 200, but MultiCharts served a Cloudflare "Performing security verification" challenge. Per the rules I did not try to get past it.
- NinjaTrader: the old URL returned 404, and the help-guide frame came back empty.

So the Scout's lane failed for every item.

## Step 2: results per item
| Item | Tool that worked | Retrieved | Saved to |
|---|---|---|---|
| MultiCharts intrabar fill | **Wayback Machine** (`id_` raw captures), fetched from JPolo because the box's TLS to web.archive.org failed | Intra-bar Price Movement Assumptions (capture 2022-05-12 UTC); Limit Order Execution Assumptions (2024-04-12); Precise Backtesting (2021-01-21); 4.6.7 Price Movement Emulation / Bar Magnifier (2015-05-09); Bar_Magnifier (2024-04-13, held in JPolo temp only) | source_files/fill_models/mc_*.{html,txt}; quotes B28–B32 |
| NinjaTrader fill limit on touch | **Direct curl on the box** to static.ninjatrader.com (the help guide moved there) | IsFillLimitOnTouch page | source_files/fill_models/ninjatrader_isfilllimitontouch.*; B33–B35 |
| CME protection points / Velocity Logic values for MES/MNQ | Partial. CME Client Systems Wiki via the box's CDP Chrome; CFTC-hosted FIA paper via curl | Velocity Logic and Limits & Banding pages (mechanism only). FIA Sept 2023 paper: VLN is a move greater than the price-band range in 1 ms; VLW is 3× the band in 1 s; either triggers a 5-second halt | source_files/costs/cme_wiki_{velocity_logic,limits_banding}.*, cftc_fia_vcm.*; C24–C27 |
| Romano-Wolf 2005 | **Direct curl** (UZH author-hosted Econometrica PDF) | Full paper, 46 pp (StepM) | source_files/validation/romano_wolf_2005_econometrica.*; V16–V18 |
| BLS/Fed original calendar dates | **Wayback Machine** (CDX listing plus `id_` captures from JPolo). FRASER was not needed | BLS CPI/Empsit/PPI schedules captured 2025-01-04, 2025-09-07/10, 2026-01-23/30 and 2026-02-13. Fed FOMC calendar captured 2025-01-03 and 2025-09-01 | source_files/economic_events/wayback/*; E23–E29; the CSV gained columns pit_original_date_wayback, pit_capture_utc, pit_snapshot, pit_check |

All 23 new quotes string-matched (B28–B35, C24–C27, V16–V18, E23–E29).

## What changed in the packages
- **economic_events:**
  - 47 BLS original dates were filled from pre-release Wayback captures. Nine shutdown rows agree with the BLS lapse table.
  - **September 2025 CPI original = Oct 15, 2025** (the gap is now closed), actual Oct 24.
  - The two PPI rows for Jan and Feb 2026 have a Wayback capture taken after the 2026 revision, so the lapse-table original stands.
  - The FOMC 2025 and 2026 meeting dates match the 2025-01-03 capture, when the 2026 dates were still tentative. No date changed.
  - GAP-labelled lines remaining: 63. Most are 2026 CPI originals and the FOMC time and minutes gaps.
- **fill_models:**
  - MultiCharts adds a third vendor with the open-proximity heuristic (O-H-L-C if the open is nearer the high, otherwise O-L-H-C), plus a "beyond limit by N" limit option and bid/ask precise fills.
  - NinjaTrader's default is trade-through (penetration), with touch available as an option.
  - The touch vs trade-through conflict now has four vendors: backtrader touch; QuantConnect, NinjaTrader default and MultiCharts optional trade-through.
- **execution_costs:** the Velocity Logic structure is now sourced (thresholds are tied to the price band). The actual MES/MNQ band and protection values are still not retrieved.
- **validation:** the Romano-Wolf 2005 text is now held. StepM is a stepwise FWE-controlling extension of White's reality check (V16–V18).

## Still missing
- **MES/MNQ numeric protection points, price-band values and VL thresholds.**
  - cmegroup.com returned 403 to curl and an HTTP2 error in the browser.
  - The CME wiki points to "GCC Price Banding", and I couldn't fetch it.
  - Wayback CDX domain searches on cmegroup.com timed out (504).
  - Possible routes: Jason opens the CME Globex price banding page or the Special Price Fluctuations and Limits guide in his normal browser and saves it, or a later Wayback retry.
- **2026 CPI original dates:** I didn't fetch a pre-release capture from 2026-02 onward.
- FOMC minutes original dates, the press-conference time from a Fed source, and CME MES/MNQ early-close times.
- AFML ch. 7/12 text (not attempted; it's a paywalled book).
