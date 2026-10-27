# Quant Agent Brain — Session Handoff

## SC-FUT-0005 independent rebuild + adversarial review (2026-10-27, late)

- `scripts/sc_fut_0005_independent_rebuild.py` (no `quant_brain` imports; `databento_dbn` decode; own volume roll) matches the workbench on all 1,424 MNQ practice days, to the cent; MES too. Run: `FILL=open|sigclose|plus2|delay1|worst .venv/Scripts/python.exe -I scripts/sc_fut_0005_independent_rebuild.py <dev 1m dbn> brain/_system/futures/session-calendar.v1.csv brain/sources/mes_mnq/contracts/roll_volume_check.csv <out.csv> MNQ`.
- Findings: `brain/05_Reviews/SC-FUT-0005-independent-review.md`.
  - Sign-flip p = 0.0001.
  - Break-even slippage 12.8 ticks/side.
  - One-minute delay: $7.94/day (-31%).
  - Best 20 days = 76% of profit.
  - Risk-only sizing points to 2 MNQ.
- Excluded from Ruff as a review receipt (like RX-0001). `needs_you.json`: `sc-fut-0005-prop-size` added.
- **Next:** Jason pre-registers the size; simulator Phase 2; one locked exam check.

## Prop-goal pivot and evaluation simulator Phase 1 (2026-10-27)

- **Ideas tried:**
  - SC-FUT-0002 (late-day momentum) was frozen and tested in the workbench: not demonstrated. MES lost $3.93/day; MNQ lost $0.45/day; the edge vs random was +$2-3/day, and costs swamped it. Closing awaits Jason.
  - SC-FUT-0003 (diversified TSMOM) was planned, reviewed by engineering and trader agents, and **shelved**. Prop firms (Topstep/Apex) require being flat by 3:10 pm CT. Reviews: `brain/05_Reviews/SC-FUT-0003-plan-reviews.md`.
  - Data was bought anyway: 28-market daily bars 2010-2024, $39.44 from Databento free credits. Stored in `Quant/data/databento/daily_.../`.
- **Jason's priority** is prop firm first, with same-day strategies only. Verified rules and the next idea (rare liquidity-shock reversal): `brain/sources/prop_firm_same_day_ideas_2026-10-27.md`. Topstep's API works in Combine and XFA, not Live; Apex bans bots.
- **Simulator plan:** `brain/_system/plan/prop_eval_simulator_plan.md`, revised after two reviews (`brain/05_Reviews/prop-eval-simulator-plan-reviews.md`).
- **Phase 1 built** (`src/quant_brain/prop/`; rules in `brain/_system/prop/topstep_50k.json`; CLI `scripts/prop_eval.py`):
  - intraday lows for the strategy and every control draw;
  - the EOD-trailing floor with lock;
  - consistency at 55%;
  - fees and resets;
  - a paired, non-wrapping bootstrap;
  - walk-forward with censoring.
- **Key finding:** with resets, even random trading passes about 99% of the time within 6 months at 5 micros. The gate is therefore the **first-account pass rate** versus luck at luck's best size, and Phase 2 (payouts, net cash) remains essential.
- **Security:** the Databento password had been committed to the public repo. It is removed from current files but still in history. Jason has been told to rotate it; history scrubbing is optional and needs a force-push.
- **Next:**
  - validation replay of SC-FUT-0001/0002 (running);
  - P7 UI panel;
  - Phase 2 (XFA payouts) after the rules are confirmed;
  - then draft SC-FUT-0004 (shock reversal).

## Backtest workbench core built (2026-10-26; plan approved: exam budget 3, MNQ/MES only)

- `src/quant_brain/workbench/`:
  - `strategies.py`: W1 plug-ins; ORB defaults = SC-FUT-0001, reproduces its dev results to the cent on sample days.
  - `engine.py`: W7 fingerprinted, cached runs; one ledger trial per distinct run, at `brain/04_Backtest_Reports/workbench/trials.jsonl`; practice data only.
  - `analysis.py`: W2/W5 year, backward-looking regime and L1-L4 slices with random-entry luck checks; W6 Sidak pass bar per family.
- Supporting pieces:
  - CLI: `scripts/workbench.py run|list`.
  - UI: **Workbench** tab (`ui/workbench_view.py`, `RENDER.workbench`). Saved verdicts are re-judged against the current bar when shown.
  - Engine hooks: `range_bars`, stop fraction via `atr_tr_sum`, control `first_fill`, volume roll. Frozen SC-FUT-0001 behaviour is unchanged (all fixtures, crosscheck and audit tests pass).
- First trials (baseline ORB, 2019-2024; orb family has 2 trials, so the bar is p < 0.0253):
  - MNQ: $2.91/day, p = 0.132.
  - MES: -$3.77/day.
  - Both not demonstrated.
- 2026-10-26: Researched next MNQ/MES intraday candidates (2019-2024 only): late-day hedging-flow momentum first; opening-gap fade and negative-jump reversal secondary. Reviewed and filed as `brain/sources/candidate_ideas_2026-10-26.md` (citations spot-checked; one paper could not be confirmed).
- Not built yet: W3 robustness nudges, W4 walk-forward, W8 exam proctor, run button in the UI, W10 paper feed.

## UI: PR #13 redesign restored as the main UI (2026-10-26)

- Jason prefers the PR #13 data-terminal UI. It was merged back onto `testing` (`1e5f46b`) from tag `archive/2026-10-26/cursor-interactive-base-ui-d89c`, keeping its app.js/app.css and re-adding the Study tab. 1,004 tests pass. Serve with `.venv/Scripts/python.exe scripts/serve_terminal.py --root . --port 8765`.
- Jason still found the UI hard to understand, so it now opens on **Home** with three plain answers (Where we are / Needs you / What we learned). The top bar is Home · Study · Chart · Learn; everything else is under **More**. Code: `src/quant_brain/ui/home.py`, `RENDER.home`.
- **Agents: keep `brain/_system/needs_you.json` current.** Add decisions waiting on Jason (title, why, recommendation, action) and mark them `"done": true` when settled. Ledger-derivable decisions (final exam vs close) appear automatically.
- UI code is under `src/quant_brain`, so any held-out read now needs a fresh development re-run first (code-unchanged gate).

## SC-FUT-0001 practice run: NOT DEMONSTRATED; study page built (2026-10-26)

- Jason confirmed interpretations A/B and authorized the development run (ledger). The run committed as `9b1fea3`.
- **MNQ 2019–2023** (1,157 evaluable days, 1,664 trades): **$3.11/day** absolute at L3 against the $15 floor; +$5.28/day vs random entries, **p = 0.114**. Joint power is 86% at +$20/day, so this is an adequately powered negative.
  - Missing-minute share 0.17%; same-bar share 1.7%; the verdict holds under the stress bound.
  - By year: 2019 −$1.45, 2020 +$0.48, 2021 +$1.95, 2022 +$9.87, 2023 +$2.93.
  - Cost ladder: L1 $5.27, L4 $0.24. DSR: N=1 0.74, N=25 0.11.
- **2024 diagnostic:** $1.99/day, p = 0.43. **MES:** −$5.28/day.
- The held-out read is **not** done. The gate would allow it after `held_out_authorized`, but whether to spend it is Jason's decision.
- **Study page** (`#study`; `src/quant_brain/ui/study.py`, `RENDER.study` in `ui/static/app.js`):
  - honesty trail, verdict meters and alarm chips;
  - strategy-vs-luck equity with the 5–95% band of the 500 draws, and the luck histogram;
  - by-year and cost-ladder tables;
  - 1-minute day replay, which refuses locked-period dates.
- The runner now saves `*.draws.npy`. The development run was re-executed at `6fcc129`; report and CSVs are byte-identical (`183f8fe`). The first replay takes ~15 s to load the minute file (cached after).
- Verification: 1,002 passed, 2 skipped; Ruff clean. The browser extension wasn't connected, so the page was checked via its API only, not visually.

## SC-FUT-0001 Step 2 built and reviewed (2026-10-26; no real P&L)

- Plan: `brain/_system/plan/phase_b_sc_fut_0001_engine.md` (approved). Fixtures were committed before the engine (`2bdbbbc`). Modules in `src/quant_brain/futures/`:
  - `orb.py`: engine;
  - `orb_reference.py`: independent reference;
  - `controls.py`: 500 seeded draws;
  - `bars.py`: loader;
  - `inference.py`: test, floor, alarms, power, DSR, Politis–White;
  - `runner.py` + `scripts/run_sc_fut_0001.py`: gates, ledger, reports.
- Verification:
  - the engine and the reference agree on all fixtures and on 12,000 random days;
  - the loader reproduces the audit's minute counts on all 1,428 MNQ sessions;
  - mutation check: 16/17 mutants caught, and the survivor (SIGNAL_START 08:44) is equivalent;
  - full suite **997 passed, 2 skipped**; Ruff clean.
- An independent review (fresh agent, read-only) found 5 should-fix defects, all fixed with regression tests in `55adc2d`:
  - a gap running to the flatten is now non-evaluable;
  - a day is non-pairable if any control draw is non-evaluable (the old behaviour biased results toward a pass);
  - no cash-window bars → ineligible;
  - the stress bound is never kinder than the primary;
  - DSR variance no longer silently 0;
  - the dev-bars hash is checked;
  - the loader sorts bars and rejects duplicate minutes.
- Accepted limitation: the gates are honor-system. The ledger is an editable file, `--by Jason` is a string, and there is no lock against concurrent runs.
- **Open for Jason before Step 3:** (A) a missing entry minute consumes that side (the engine's reading; the reviewer notes the spec could be read as re-arming); (B) the ATR close uses 15:00 CT, while the calendar's 16:00 is the Globex close.
- `status` shows development BLOCKED only by the missing `development_authorized`. Step 3 needs Jason's explicit OK; then run `authorize development_authorized --by Jason` and `run --phase development`.

## SC-FUT-0001 FROZEN (2026-10-26; Step 1 of the approved plan)

- Jason approved the 5-step plan, the three audit decisions (12:15 CT early close / 12:12 exit; void range = $0 no-trade day for ORB and control; ATR window uses NYSE sessions only), DSR at N=1/25 as a diagnostic, and keeping prop-eval deferred. Recorded in `brain/05_Reviews/SC-FUT-0001-session-audit.md`.
- Frozen spec: `brain/_system/futures/sc-fut-0001-spec.v1.json`, SHA-256 `e19f1907…30fb` after a same-day provenance-hash correction logged in `brain/04_Backtest_Reports/SC-FUT-0001.trials.jsonl` (freeze commit `bb71d2f`, correction `73d3571`; no rule changed). No nulls and no blockers; `execution_allowed: false`. Seeds: controls 20261026; bootstrap B=9999, seed 20261027.
- Pinned inputs: dev partition manifest, `session-calendar.v1.csv` (1,880 NYSE sessions 2019-05-01..2026-10-21, with the 12:15 override), roll calendar, cost levels, `sc-fut-0001-prior-looks.md`, decision records, `uv.lock`. `.gitattributes` marks them `-text` so the hashes survive checkout. `tests/test_futures_frozen_spec.py` fails on any edit.
- Not added to `brain/03_Strategy_Cards/freeze_ledger.json`: that ledger is the SC-0002 markdown-card schema, and its tests expect only SC-0001/0002.
- Verification: 907 passed, 2 skipped; Ruff clean. No P&L computed.
- **Next (Step 2):** build the minute-bar engine and the random-control generator to the frozen spec, gating on the spec hash. Test them on `simulator-handworked-fixtures.md` and synthetic bars, and write an independent reference implementation that must match trade-for-trade. Step 3 (dev replay) needs Jason's OK.

## Repo cleanup and SC-FUT-0001 session audit (2026-10-26, later)

- **Branches:** only `main` and `testing` remain (local and GitHub). Removed branches are kept as tags `archive/2026-10-26/*`; PR #13 (Cursor UI, unreviewed) was closed, tag `archive/2026-10-26/cursor-interactive-base-ui-d89c`. The `quant-agent-brain-ui` worktree was removed; its git-ignored `.hermes/` and `db/` are in `Desktop/Quant/_archive/`. The `quant-agent-brain-merge-fixes` worktree is now on `main`.
- **PR #14** (`testing` → `main`) carries the futures work, the cockpit chart-resize fix, and the research notes. Raw copyrighted copies (PDFs, saved HTML, `source_files/`, YouTube transcripts) are git-ignored because the repo is public. The RX-0001 script is excluded from Ruff to stay byte-identical. **Merge awaits Jason**: auto mode refused to merge an unreviewed PR.
- **Session audit** (outcome-blind; no prices or P&L): `brain/05_Reviews/SC-FUT-0001-session-audit.md`. MNQ has 1,154 dev and 252 diagnostic candidate days. Sessions with a live-window missing minute are 0.43% / 0.40%, below the 1% alarm. Gaps sit on fixed-roll days and the March 2020 halts. Calendars come from `pandas_market_calendars` 5.5.0 (cmegroup.com timed out); the library's 12:00 CT early close is overridden to **12:15 CT** (data plus CME's 2011 notice), pending Jason's confirmation.
- Verification: **904 passed, 2 skipped**; Ruff clean.
- Next: Jason confirms the 3 audit decisions (12:15 close; void range = $0 no-trade day; ATR window uses NYSE sessions) and merges PR #14. Then set seeds/hashes and freeze the spec.

## SC-FUT-0001 defaults approved; dev-only data partition built (2026-10-26; no freeze or ORB P&L)

- Jason approved all 13 pre-freeze defaults after a plain-language walkthrough; decisions are in `brain/05_Reviews/SC-FUT-0001-prefreeze-defaults.md` § "Jason's decisions (2026-10-26)". Key picks: 1% missing-stop alarm; matched random-entry control as primary; fixed mean-5 block bootstrap with Politis–White block length as sensitivity only; the lower-CI >$15 alternative rejected; 80% power at $20/day and the $15 floor is never lowered; opposite-side entry only after the exit bar; prop-eval deferred.
- New `src/quant_brain/futures/dev_partition.py` + `scripts/split_dev_partition.py` (+ `tests/test_futures_dev_partition.py`). Dependencies added: `databento-dbn`, `zstandard`. The run verified source hashes, wrote `C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31/` (1m: 5,727,350 records, last 2024-12-31 21:59 UTC; 1d: 14,994; 21 pre-lock definition chunks), and stopped at the first record ≥ cutoff 2024-12-31 23:00 UTC (Globex open of trade date 2025-01-01). No locked record was written or printed. Manifest: `brain/_system/futures/dev-partition-manifest.json`. An independent re-decode confirmed every output record precedes the cutoff, timestamps are monotonic and metadata `end` equals the cutoff.
- Verification: full suite **901 passed, 2 skipped**, Ruff clean.
- Next: obtain official CME holiday/early-close calendars for 2019-05-01..2024-12-31; run the eligibility / missing-minute / ATR warm-up audit on the dev partition only; set seeds and hashes; freeze the spec. Development replay and the held-out read each still need separate authorization.

## SC-FUT-0001 pre-freeze build (2026-10-25; no freeze or ORB P&L)

- Jason authorized a pre-freeze build only. Card/spec now retain $15 net/MNQ/eligible day, lower one-sided CI >$15 as **unselected** alternative, missing live-stop minutes as non-observed adverse-extreme stress bounds, 14 prior dated-contract sessions with required closes, impossible simultaneous close double-break invariant, and positive stop-distance half-tick rounding up. Proposed missing-stop-gap alarm is >1% of eligible sessions OR >1% of executed trades, plus conclusion sensitivity, **pending Jason approval**.
- One review list: `brain/05_Reviews/SC-FUT-0001-prefreeze-defaults.md`. Draft artifacts: `brain/_system/futures/{data-manifest-prefreeze,contract-map-manifest-prefreeze,session-calendar-audit-prefreeze,power-mde-prefreeze,trade-equity-record-draft,sc-fut-0001-spec.v0}.json`, `simulator-handworked-fixtures.md`, `PREFREEZE_SHA256SUMS`. Historical full-range OHLCV hashes are carried from a previously verified receipt, not rehashed; 21 pre-2025 definition chunks were rehashed. The calendar count is weekday-only upper bound; historical early closes/halts and chosen-contract missing-minute coverage are **not audited** because raw OHLCV mixes locked dates and no safe dev-only partition exists yet. No held-out data was decoded.
- `src/quant_brain/futures/prefreeze_stats.py` + `tests/test_futures_prefreeze_stats.py` implement synthetic-only stationary paired-bootstrap plumbing. A null returns nonrejection and a planted +$15 paired difference is detected; this is not real strategy evidence or a frozen inference method. Conditional power worksheet proposes 80% at true $20/day and shows assumed σ/dependence sensitivities, but **empirical dev variance, eligible count and joint two-gate power remain unavailable without authorized frozen-rule dev outcomes**.
- Verification: focused **43 passed, 1 skipped**, Ruff clean; full suite **896 passed, 2 skipped, 1 pre-existing Starlette deprecation warning**; diff checks clean. No ORB strategy P&L, empirical MDE, simulator probabilities, commit, held-out read, fee payment or trade. Next: Jason reviews remaining defaults and the >1% alarm; get a safe dev-only data isolation/official session and halt history; select statistical gate, exact eval rules, hashes and freeze separately before dev replay.

## Freeze-review draft and eval diagnostic scoped (2026-10-25)

- Jason supplied **$15/day net per MNQ per eligible session** (no-trade $0) and the pasted table of defaults; these are labeled engineering assumptions in `brain/03_Strategy_Cards/SC-FUT-0001-mnq-orb-falsification.md`. Source paper's after-cost result is negative; do not make an eval timeline depend on this rule.
- New canonical **draft, not executable/frozen** spec: `brain/_system/futures/sc-fut-0001-spec.v0.json`. Freeze-review blocker packet: `brain/05_Reviews/SC-FUT-0001-freeze-review.md`. The user asked that a prop-eval simulator be added to **development stage**; the Git-ignored revised plan Stage 3, card and packet now scope paired stationary-block daily resampling at 1/2/3/5 MNQ. Venue-specific target, trailing DD, daily limit, reset, horizon and intraday marked equity are absent, so no pass/blow-up estimate is possible. A daily total cannot identify intraday loss-rule breaches.
- No rule implementation, development or held-out strategy P&L, empirical MDE, eval simulation, fee payment, paper/live trading or freeze occurred. Source hashes and provenance, trial ledger, test algorithm/power and execution edge semantics still need review and approval. Held-out read remains separately gated.

## Lean futures ORB plan and single-rule card draft (2026-10-25)

- Jason approved revising the overbuilt futures plan to a spec-first, single-rule MNQ falsification path. The revised plan is `.hermes/plans/2026-10-25_175634-lean-orb-preregistration-revision.md` (Git-ignored); the older plan is superseded. A three-week preflight target is a scope checkpoint, never permission to waive causality or cost checks.
- Jason explicitly approved **PROP-011** for this single-rule track: PBO is `not applicable`, not a pass. A selectable family still requires CSCV/PBO. Recorded in `brain/_system/plan/plan_change_proposals.md` and PLAN.md §10. Other safeguards remain: L3 costs, one locked held-out read, power/MDE, paired random anchors, full trial accounting, no MES rescue, no live trading.
- Jason chose **draft for review, do not freeze or test** for Fetna's cash-open 15-minute R2 (10% prior 14-day ATR stop, no target). Draft: `brain/03_Strategy_Cards/SC-FUT-0001-mnq-orb-falsification.md`. It states sourced rules versus engineering assumptions and lists unresolved ATR, fill, sample, randomization, effect-size and statistical decisions. It is not a strategy approval or a machine-readable frozen spec.
- The five existing futures kernel files remain staged and uncommitted on `feature/phase-b-futures-foundation`. This checkpoint changed only governance/docs and the draft card; **no market-data strategy calculations, P&L, held-out read, commit, paid purchase, or broker action** occurred. Focused kernel suite rerun: **39 passed, 1 skipped**; `git diff --check` and cached diff check clean; original Fetna PDF SHA-256 matched the research note.
- Next: review the draft card and resolve its economic target, decision statistic, exact execution semantics, inherited-selection treatment and power method. Only then hash-commit the approved spec before expanding the engine. The real held-out run requires separate authorization.

## PROP-010 accepted; free-tier backend built (2026-09-29)

- **Decision:** Jason said "let's create the free one first" and relaxed the process gates for this direction. The safety rules stand: no live trading or broker routing, no paid data without a decision, provenance on data, and SC-0002 stays closed.
- **Built on `testing`** (`d5f111a..6a834c5`, new package `src/quant_brain/market/`):
  - **Trade replay:** `scripts/export_trade_replay.py`, cross-checked against the reference implementation. SC-0002 replays are committed for held-out (91 trades) and in-sample (101).
  - **Risk Center math** (`risk.py`): sizing, recovery, Kelly, seeded risk of ruin, heat, correlation.
  - **Starter universe:** `data/universe/starter.json`, 45 symbols with 45 accepted daily datasets.
    - `fetch_market_data.py --universe starter --no-cross-check`.
    - Screener with 5 presets (why + trap); `scripts/market_snapshot.py`.
  - **Calendar:** Fed FOMC page (official), 9 FRED releases (official; `FRED_API_KEY` in `.env`) and yfinance earnings; `scripts/fetch_calendar.py`.
  - **SEC EDGAR fundamentals:** `scripts/fetch_fundamentals.py`. It **needs `SEC_USER_AGENT="Name email"` in `.env`** and has not run live yet.
  - **Live crypto:** Coinbase public WebSocket, no key (`live_crypto.py`, `scripts/live_crypto_watch.py`). Checked live on BTC and ETH.
- **Checks:** 741 passed, 1 skipped; Ruff clean.
- **Incident:** a mistaken double run created 45 duplicate datasets. They were removed minutes later (Parquet, manifests and DB rows), and all 48 remaining datasets verify as accepted.
- **Next:**
  1. The UI agent builds the pages from `brain/_system/plan/learning_terminal_ui_prompt.md`, after merging `testing` into `ui-terminal`.
  2. Jason sets `SEC_USER_AGENT`.
  3. Academy lessons (plan §5.2) and the rule builder (phase 4) are the next backend-side work.

## PROP-010 proposed: Quant Learning Terminal plan (2026-09-29)

- **Plan:** `brain/_system/plan/learning_terminal_plan.md`, with PROP-010 in `plan_change_proposals.md`. Proposed, not accepted; nothing built.
- **What it is:** a local, beginner-first TradingView + QuantConnect inside the existing Brain Terminal.
  - Charts, replay, screener, calendars and news.
  - The universe → signal → sizing → risk → execution → evaluation spine.
  - An Academy and a Risk Center.
  - A rule builder with a trial counter.
  - Free data with provenance badges.
- **Research:** free sources checked against official docs where possible; paid options priced, with "reported" marked where only third-party figures exist. TradingView Advanced Charts is ruled out (its licence requires public use). Lightweight Charts (Apache 2.0) is already bundled.
- **Next:** Jason answers D1–D8 (plan §11) and accepts or trims PROP-010. Phase 1 ("See it": chart page and trade replay of SC-0002) is the smallest first build.

## SC-0002 held-out verdict: no edge shown; adversarial review upholds the reject (2026-09-29)

- **Approval:** Jason approved the in-sample report (ledger event committed at `f463db8`).
- **Held-out run:** 2016-01-04..2026-09-25, read once. Results were committed at `e14c13a`, in `brain/04_Backtest_Reports/SC-0002-held-out.md`.
- **Verdict for rule A, SPY at 5 bps: no edge shown.**
  - Average trade: +0.32% (pass).
  - Random-entry percentile: 94.9 against a threshold of 95 (fail, by 0.0001 pp; other seed blocks give 94.7–96.9).
  - Deflated Sharpe: 0.896 against 0.95 (fail). Even undeflated, the probabilistic Sharpe is 0.932.
  - Sharpe against buy-and-hold: 0.46 vs 0.89 (fail). It still fails with cash earning 2% or 5%.
- **Review:** `brain/05_Reviews/SC-0002-adversarial-review.md`. All four numbers were recomputed independently of the engine, and the held-out code equals the in-sample code (empty diff).
  - No lookahead was found.
  - A breaks even at about 21 bps per side.
  - The edge is concentrated in 2020–2022; 2016–2019 averaged 0.04% a trade.
  - B and D decayed out of sample, which vindicates not switching.
  - The review is **not independent**: the same session ran it.
- **State:** SC-0002 is closed, and PROP-007 step 7 (prop-firm fit) is not reached. A new idea means a new card, with these trials counted.
- **Next: Jason decides.** Options: an independent second review; a new card; the second door (Phase 9); or the model-backend decision.

## Backtest runner built; SC-0002 phase 1 (in-sample) done; waiting for Jason's review (2026-09-29)

**Runner** (`src/quant_brain/backtest/`, `scripts/run_backtest.py`; plan `brain/_system/plan/phase_08_backtest_runner.md`). It implements SC-0002's pinned definitions exactly:
- indicators and the bar-by-bar engine;
- buy-and-hold;
- seeded random entry;
- the deflated Sharpe ratio;
- an independent reference implementation of rule A.

**Gates:**
- the card must be frozen, unchanged and not superseded;
- datasets must be accepted and match their pinned hashes;
- the code must be committed. The code gate covers `src/quant_brain`, the runner script, `pyproject.toml` and `uv.lock`.

**Held-out read** requires:
- no code change since the approved in-sample commit (compared by `git diff`, not commit ID);
- an approval after the latest in-sample run;
- matching cross-checks from that run;
- a committed, clean trial ledger.

It is read once: a DB marker is written, and a ledger event appended, before any computation. A crash is recorded as `held_out_failed`.

**Ledger:** `brain/04_Backtest_Reports/SC-0002.trials.jsonl`, append-only, byte-exact, and mirrored to the `backtests` and `metrics` tables.

**Checks:** 704 passed, 1 skipped. Most mutations are caught; the three survivors are equivalent or redundant.

**Reviews:** the pre-run independent review found:
- 1 blocker (the held-out read not tied to the approved in-sample code). Its fix caused 2 more: the held-out gate could never pass, and held-out-once could be reset by a ledger restore.

All three are fixed and re-verified by walking the real workflow. No lookahead was found, and the engine matched the card.

**Phase 1** (in-sample 2000-01-03..2015-12-31, run at `cc0375b`, results committed at `1c52d27`): the reference matched the engine on all 9 symbol/cost combinations (SPY 101, QQQ 117, IWM 116 rule A trades).

| SPY at 5 bps | Trades | Avg trade | Win rate | Total | CAGR | Sharpe | Max DD | Days held |
|---|---|---|---|---|---|---|---|---|
| A (primary) | 101 | +0.35% | 71% | +40% | 2.1% | 0.41 | −15% | 9% |
| B | 80 | +0.72% | 91% | +76% | 3.6% | 0.74 | −14% | 10% |
| D | 285 | +0.32% | 65% | +135% | 5.5% | 0.51 | −19% | 21% |
| Buy-and-hold | 1 | — | — | +85% | 3.9% | 0.29 | −55% | 100% |

- The random-entry test and the DSR are computed on the held-out period only, as the card specifies.
- **B and D look better than A in-sample, but the card cannot switch.** Switching would be selection after seeing results; a different primary would be a new card, with this in-sample result counted.

**Next:** Jason reviews the in-sample report. Then: `run_backtest.py SC-0002 --approve-in-sample --by Jason`, commit the ledger, `--phase held-out` (once, ever), and the adversarial review of the verdict (step 6).

## Strategy card SC-0002 frozen; SC-0001 retired (2026-09-29)

PROP-007 step 4. No backtest has run, and no result has been seen.

- **SC-0001** was frozen *before* its independent review (a process mistake). The review found three problems:
  - two unsourced choices labelled as sourced: Wilder RSI for rules A and B, and A's close-based exit;
  - an ambiguous verdict;
  - open implementation details.

  No backtest had read it. It is kept on record and **superseded**: the ledger and DB mark it, and `verify_frozen_card` refuses it.
- **SC-0002** (`brain/03_Strategy_Cards/SC-0002-rsi2-connors-spy.md`, spec sha256 `4b838196…`) was reviewed **before** freezing. The review found two blockers (B's unlabelled "moving average"; a DSR not fully pinned) and four optional clarifications. All were fixed, and the re-check found no blockers. Jason approved the freeze.
  - **Rules:**
    - **A (primary):** ChartSchool/Connors RSI(2): buy when RSI(2) < 10 above the 200-day SMA; exit on a move above the 5-day SMA; no stops.
    - **B:** Connors Research "RSI 25".
    - **D:** NAAIM Cutler RSI(3).

    Every rule quote is verified against its snapshot. Every non-sourced choice is labelled `assumption` with a rationale: Wilder smoothing for A and B, close-based readings, SMA for B's moving average, next-open execution for all rules, adjusted prices, costs, and 0% on cash.
  - **Implementation fully pinned on the card:**
    - SMA and RSI definitions, and warm-up;
    - entry, re-entry and same-bar rules;
    - B's units and add timing;
    - compounding sizing;
    - period boundaries (last-bar signals dropped, forced closes);
    - multiplicative trade costs and daily-return conventions;
    - edge cases.
  - **Verdict:** rule A only, held-out 2016-01-04..2026-09-25 (read once), 5 bps. "Promising" only if **all** hold:
    1. the average trade is above 0;
    2. it is at or above the 95th percentile of 1,000 seeded random-entry runs (sampling rules pinned);
    3. the DSR probability is at least 0.95 with N = 3 trials (formula pinned);
    4. A's Sharpe is above buy-and-hold's.

    Otherwise the verdict is "no edge shown".
- **Schema** (`src/quant_brain/strategy/card.py`) now enforces:
  - an RSI basis (sourced needs a quote; assumption needs a reason);
  - labelled clause interpretations;
  - a required `implementation` block;
  - a structured verdict limited to the primary rule and a tested cost;
  - supersession through the ledger.
- **Cards are byte-exact** (`-text`), and the freeze verifies after a fresh checkout.
- **Checks:** 655 passed, 1 skipped; both Ruff checks clean.
- **Next:** PROP-007 step 5, the backtest runner. Plan it first. It must implement exactly the card's pinned definitions and refuse any card that isn't frozen, or is superseded or changed.

## Gate F complete: local market data with provenance (2026-09-28/29)

PROP-007 step 3, built per `brain/_system/plan/gate_f_market_data.md`, including Jason's three pre-build corrections. No strategy, signal or backtest work.

**Built**
- **`src/quant_brain/data/market_data.py`:** validation, immutable ordered ingest, manifest, DB registration, a read-only verifier, and a loader for accepted datasets only.
  - **Dataset IDs** are `<SYM>-1d-yfinance-<UTC second>-<random run id>`, so every download is a new dataset. The full content sha256 lets identical downloads be matched by hash.
  - **Price basis:** Yahoo's **split-adjusted** OHLC and volume (not the as-traded tape) plus `adj_close`; `adj_close / close` is Yahoo's dividend factor. The manifest records `price_basis: yahoo_split_adjusted`, and a backtest must state its execution basis.
  - **Write order:** `.partial` Parquet, read back and hashed; rename, never overwriting; the manifest via temp file and rename; re-verify; the DB row last. A dataset is *accepted* only when file, manifest and row agree, and only accepted datasets load. Otherwise the verifier reports `incomplete`, `unregistered` or `invalid`; nothing is auto-deleted.
  - **Validation rejects:**
    - duplicate, unsorted or weekend dates;
    - missing or non-positive prices;
    - a high below the body or a low above it;
    - negative volume;
    - NaN or negative dividends or splits;
    - a dividend factor outside (0, 1.0001];
    - a last bar on or after the download day (it may still be forming).

    Gaps of more than 4 weekdays, zero volume and moves above 25% become warnings.
- **Scripts:** `scripts/fetch_market_data.py` (the only network code) and `scripts/verify_market_data.py` (read-only; exit 1 on `invalid`).
- **Datasets** (Parquet gitignored; manifests committed in `data/manifests/`):

| Symbol | Dataset | Rows | Range | Warnings |
|---|---|---|---|---|
| SPY | `SPY-1d-yfinance-20260929T024440Z-472338d8` | 6,723 | 2000-01-03..2026-09-25 | 0 |
| QQQ | `QQQ-1d-yfinance-20260929T024440Z-d0bbceb5` | 6,723 | 2000-01-03..2026-09-25 | 0 |
| IWM | `IWM-1d-yfinance-20260929T024441Z-9857eca7` | 6,622 | 2000-05-26..2026-09-25 | 0 |

  All three verify `accepted` and pass the stricter post-review validation.

**Spot checks** (read-only)
- SPY closed 338.34 on 2020-02-19 and 222.95 on 2020-03-23, the known values.
- Splits: QQQ 2:1 on 2000-03-20 (already adjusted; no price jump) and IWM 2:1 on 2005-06-09.
- Dividend factors: SPY 0.63–1.0, QQQ 0.84–1.0, IWM 0.71–1.0.
- No weekend rows. The missing weekdays match NYSE holidays and closures.

**Second source: unavailable.** pandas-datareader 0.11.1 dropped Stooq, and Stooq's CSV endpoint now serves a browser challenge to scripts. The manifests honestly record `cross_check: unavailable`, and no workaround was attempted.

**Verification**
- 636 passed, 1 skipped. Both Ruff checks are clean. 11/11 targeted mutations are caught; three first survived, and isolating tests were added.
- An independent review found no blocker. Its gaps are fixed with tests:
  - NaN or negative corporate actions;
  - weekend dates;
  - incomplete same-day bars;
  - a corrupt manifest crashing the verifier;
  - the volume basis note.
- The receipt verifier is still OK.
- DB `6205b230…`: its only change is the 3 `price_datasets` rows.

**Limitations**
- Only one source (Yahoo, unofficial and able to restate history). There is no official exchange calendar, so gaps are flagged heuristically.
- The three existing manifests predate the "volume is split-adjusted too" wording. They are immutable and left as written.

**Next (PROP-007 step 4):** one frozen, hashed strategy card, written before any result is seen. Plan it first.

## Content-only grounding (2026-09-28)

Approved by Jason. The fix is model-agnostic: it changes what *any* extraction model is shown and what its output is checked against. Per Jason, testing stayed hermetic and on saved evidence, with **no live Qwen runs**. Qwen may be replaced later by a Claude or Codex CLI on his subscription; that would be a §9 model-policy change needing its own approval. No production rerun, curator run, push or merge.

**What changed**
- **Models and validators see only fetched content.** `live_discovery.snapshot_content()` strips the harness-written front matter (url, title, channel, backend, captured_at, hashes). The executor builds every evidence item from it: single prompts, windows, repairs and the whole-bundle validation.
  - Before this, a quote of `backend: jina` passed as exact evidence, and timestamp or hash digits made invented numbers look grounded.
  - Now, on the preserved Connors snapshot, "Uses a 28-day lookback" and "Tested over 16 years" are unsupported.
- **Snapshot bodies are stored verbatim** (they used to be `rstrip() + "\n"`), after one canonicalisation: `\r\n` and `\r` become `\n`, via `canonical_content()`, which is also used for the recorded content hash. So the content hash always re-verifies.
- **Front-matter values are single-line.** A title like `Evil\n---\nx` can no longer end the front matter early and leak metadata into the content.
- **Window manifests record a new derivation** ("front matter excluded"). `receipts.manifest_text()` chooses the whole file or the content by that string, so **E4 and E5 receipts still verify** (E3 5, E4 15, E5 34, ledger 2), and new receipts verify against content. `window_replay.py` uses the same rule.
- **One existing assertion changed on purpose.** `test_candidate_list_lane.py` required the model to see front matter; it now requires the reverse.

**Verification**
- 601 passed, 1 skipped. Both Ruff checks and `git diff --check` are clean.
- Mutations caught: model shown the whole file; content trimmed; verifier ignoring the derivation.
- A focused independent review found two material issues (`\r` round-trip, front-matter injection through the title or URL). Both are fixed with tests that reproduce the reviewer's demonstrations.
- The DB (`aa4d042f…`) and all receipts are unchanged.

**Remaining**
- A title containing a newline is now stored flattened to one line. Titles are metadata, not evidence.
- Everything else from E5 still applies. The next step, needing authorization, is one more rerun on the unchanged list, or first a decision on the model backend.

## Note writing and snapshot immutability fixed; historical evidence verifiable again (2026-09-28)

Fix and verification only. **No production rerun, no curator run, no push or merge.** Phase 6 / Gate D remain incomplete.

**1. Notes are written from the validated payload**

The E5 cause: the executor wrote the raw model output, and the model had legally omitted the optional `possible_strategy_rule`.
- Model output now takes `verdict.normalized`.
- **The independent review found more.** `build_raw_research_payload` still hard-coded the note's `open_questions` (RSI boilerplate) and `curator_recommendation: "promote_source"`. So a note could claim `promote_source` even though validation ran against `needs_more_work`, and the promotion check never saw the written value. This dates from before today.
- Fixed: `format_findings_markdown(validated_payload=…)` makes the JSON block exactly the validated payload, re-checked against the schema.
- The offline seeded path keeps its template.
- Tests (`tests/test_note_writing.py`):
  - omitted optional fields, on a normal source and on a windowed source;
  - note JSON == the whole-bundle validator's normalized output, including disagreement → `needs_more_work` and the model's own open question;
  - **E5's five recorded pages** run through validation to a schema-valid note. The body hashes are checked against E5's receipt, and the model is scripted.

**2. Snapshots are immutable** (`discovery/live_discovery.py`)
- Created with exclusive mode `"x"`. An existing name gets the next free `<name>.<n>.md`.
- Never reused, even when byte-identical: failed discovery deletes the snapshots it wrote.
- **The old writer could delete earlier evidence, not just overwrite it.** A failed discovery that re-fetched an unchanged page overwrote the earlier run's file, then deleted it as its own. A test demonstrated this on the old code.
- Tests (`tests/test_snapshot_immutability.py`):
  - same-day refetch;
  - byte-identical refetch;
  - failed discovery beside an earlier snapshot;
  - two same-day dispatches, with the first run's files unchanged byte-for-byte;
  - an existing snapshot is never opened for writing.

**3. Historical evidence reconciled** (no receipt edited)
- **Rule: the first writer keeps the recorded path.**
  - E4's bytes are restored from `c6d13d1` to `…/2026-09-28/c5f9673f32a4-97d0dbd7.md` (`cdc7a0e5…`) and `…/f57de4fc3101-1bb9664e.md` (`23410dfd…`).
  - E5's bytes moved to the `.2.md` names (`2af38021…`, `a8d295cb…`), identical to the `8265dca` blobs. Git history keeps both.
- **Ledger:** `brain/00_Inbox/Source_Snapshots/reconciliation.json`. It maps E5's recorded paths to the moved files, with their sha256 and the original owner's file hash.
- **Verifier:** `src/quant_brain/research/receipts.py` and `scripts/verify_receipts.py` (read-only). It checks:
  - each candidate content hash;
  - each window manifest's file-bytes, text and per-window hashes;
  - each kept diagnostic response hash;
  - the ledger's target hashes and original-owner hashes. The owner check was added after the review showed E4's content-only record of the Connors page could not tell E4's bytes from E5's.
- **Current result:**

| Record | Hashes verified |
|---|---|
| E3 | 5 |
| E4 | 15 |
| E5 | 34 |
| Ledger | 2 |

- `RUN-4e9d910742` records no hashes: it predates snapshot lineage.
- `scripts/window_replay.py` now follows the ledger.
- The E4 fixture test passes again **unchanged**, because the bytes are back where E4 recorded them.
- Tests (`tests/test_receipts.py`), each detected in isolation:
  - newline normalisation (file-bytes hash only);
  - an unwindowed body edit (content hash only);
  - an edited window offset (window hash only);
  - a ledger target with different bytes;
  - E5's bytes at E4's path.

**Verification**
- 590 passed, 1 skipped. Both Ruff checks and `git diff --check` are clean.
- **All 10 new mutations and the 21 earlier ones were caught.** Three verifier checks initially survived because a single tamper test tripped them all together; separate tests now pin each one.
- Evidence files are staged byte-exact with `-text` in effect.
- The DB (`aa4d042f…`), the list blob, and all receipts and diagnostics are unchanged.
- An independent review found three material points. Two are fixed and re-verified; the third is below.

**Open (material, pre-existing, not fixed here): front matter counts as source text**
- The model and validators see the full snapshot file, including the harness-written front matter (`url`, `title`, `channel`, `backend`, `captured_at`, hashes). So:
  - quotes of that metadata pass the exact-passage check;
  - more seriously, **digits from `captured_at` and the hashes make invented numbers look grounded.** The reviewer showed "Uses a 28-day lookback" and "Tested over 16 years" judged supported against the Connors snapshot, and unsupported against its body alone. This affects `main_claim`, `risks`, `data_required` and `open_questions`.
  - `possible_strategy_rule` is protected, because it must also be an exact passage.

**Next (needs approval):** give the model and validators only the fetched content, never the front matter. This changes window offsets for future runs only. Use TDD and an independent review. Then ask before another rerun.

## Gate D checkpoint E5: second windowed rerun of RQ-6d9c12f4 (2026-09-28 UTC). Extraction and validation passed, then the note write failed closed on a latent bug.

One authorized run, not retried. No code change. No curator run, push or merge. **Phase 6 / Gate D remain incomplete.**

**Readiness (all passed before dispatch)**
- `c9a3db1`; 567 passed, 1 skipped; both Ruff checks clean.
- The list is still `88ba2d3c…`, and `gate_readiness` exited 0.
- The dry-run routed to `research_scout`. Both Qwen models were present, and the `web` channel was `ok`.
- DB `4e80d281…`; the question was `queued`.

**Run `RUN-871299ea31`** (04:11:02–04:21:54 UTC, 652s of the 900s deadline, exit 1)
- 5 of 5 sources were fetched and accepted. **Every source's extraction validated** (first time on this question):

| Source | Extraction |
|---|---|
| S1 ChartSchool | 14B, after one repair |
| **S2 Hill** | **Windowed** (it is larger this fetch: 7 windows). W03 gave evidence after one repair; the other 6 returned `no_relevant_evidence`. |
| S3 Connors | 27B, after two 14B quote failures |
| **S4 NAAIM** | 8 windows. W03 gave evidence after one repair. W02 and W07 fell back to `no_relevant_evidence` after failed evidence attempts. The rest returned `no_relevant_evidence`. |
| S5 Double 7s | 27B after two 14B quote failures; 117s |

- The merged payload then passed the whole-bundle validator. **The run failed at `write_note`** with `KeyError: 'possible_strategy_rule'`.
- It failed closed: raw note removed, question back to `queued`, recovery complete, no secondary failures.
- **Diagnostics worked on their first real run:** `Failed_Runs/diagnostics/RUN-871299ea31.responses.json` holds 10 failed responses, labelled untrusted.
- No truncation warning.

**Cause (pre-existing, latent since `0b37d65`, and never reached because no live run had passed validation before)**
- `possible_strategy_rule` is optional in `RawResearchSource` (default `""`), so the constrained schema lets the model omit it.
- The validators accept that; their normalized copy fills in `""`.
- `executor.py:1321` writes the **raw** model output (`model_result.output["sources"]`), not the validated, normalized payload, and `format_findings_markdown` indexes the missing key.
- The windowed merge always sets the field, so the omission came from S1, S3 or S5. The run keeps hashes, not successful response text, so which one is not recorded.

**Second finding: snapshot overwrite (provenance defect)**
- Snapshot paths are `<UTC date>/<content hash>-<URL hash>`. Re-fetching unchanged content on the same UTC day reuses the path, and this run **rewrote two E4 snapshots in place**: `c5f9673f32a4-97d0dbd7.md` and `f57de4fc3101-1bb9664e.md`. Only `captured_at` changed.
- The E4 versions remain at `c6d13d1`. The E4 receipt's recorded file hashes no longer match the files on disk.
- **The test suite is now red:** `test_window_failure_e4.py::test_the_planned_windows_are_exactly_the_ones_the_run_recorded` fails, correctly, for this reason. It was left failing on purpose, not weakened.

**Preserved:** `8265dca` holds the receipt, the diagnostics, three new snapshots and the two rewritten ones, byte-for-byte, with exact-path `-text` rules and blob = working-file sha256.

**State**
- DB `aa4d042f…` (`agent_tasks` 6→7, `agent_events` 85→134).
- Protected tables are 0; `research_findings` 7, `notes` 23 and `sources` 7 are unchanged. All three questions are `queued`, and no raw note exists.

**What remains uncertain**
- Whether the next run passes: the model is not byte-stable, and this run used 652 of 900 seconds.
- The "none" fallback after failed evidence attempts happened again on S4-W02 and W07. The overlap still carried the rule through W03.
- Validation passing is not complete evidence coverage, and it is **not** evidence of a profitable strategy.

**Recommended next step (needs approval)**
1. Write the note from the validator's normalized payload, not the raw model output.
2. Make snapshots immutable: never overwrite an existing path (reuse it only when the bytes match, else fail or use a distinct name).
3. Pin the E4 fixture test to the `c6d13d1` blob so the suite is green again.

Use TDD and an independent review. Then ask before another rerun.

## PROP-006 amendment A: window-contract fix after E4 (2026-09-28)

Implementation and verification only. **No production rerun, no curator dispatch, no push or merge.** Phase 6 / Gate D remain incomplete.

**What changed**
- **`research/windowing.py`**
  - The window contract no longer asks the model for a `curator_recommendation`. A windowed source always carries `WINDOW_RECOMMENDATION = "needs_more_work"`, both while a window is validated and after the merge.
  - The new `WindowSource` makes `source_id` required (min length 1, whitespace stripped) in the schema sent to Ollama, where it had been legacy-optional. `RawResearchSource` and every validator are unchanged.
- **`llm/qwen_call.py`**
  - `QwenAttempt.response_text` keeps the raw model output.
  - It is never written to `agent_events`, and a test covers this.
- **`research/executor.py`**
  - Every failed attempt's raw response is collected across all ladders, including attempts that a later attempt repaired.
  - **Only when a run fails closed**, they are written to `brain/00_Inbox/Failed_Runs/diagnostics/<run>.responses.json`, labelled `untrusted_model_responses` / "not evidence".
  - The file is written through path enforcement and before the receipt, and the receipt records `diagnostic_responses_path`.
  - It is JSON, so the `*.md` indexer never picks it up. Nothing in curation, retrieval or indexing reads `Failed_Runs`.
  - A refused or failed diagnostics write becomes a secondary failure. The receipt is still written and the original error is still raised (tested).
- **`scripts/window_replay.py` (new):** replays a preserved run's windows through live Qwen under the current contract.
  - It first checks the snapshot hash and the recorded offsets and hashes.
  - It writes nothing: no DB, events or files.

**Verification: saved responses versus fresh inference, kept separate**
- **Saved-response validation** (`tests/test_window_failure_e4.py`, no model call). It uses the committed E4 receipt and snapshot plus `tests/fixtures/e4_window_failure/w03_replay_response.json`, a real qwen3:14b response to the exact W03 prompt, obtained by diagnostic replay. It is *not* in-run text, because the run kept hashes only.
  - The planned windows equal the run's recorded windows.
  - The exit rule lies in W02 and W03.
  - The saved response is refused for carrying the dropped field.
  - Without that field, its quotes pass both checks and only the two genuine defects remain (high confidence on a discovery-only source; `mvp_testable` with an ungrounded claim).
  - The same quotes are refused in W02, because the third quote starts exactly at W02's end.
  - A source without `source_id` is refused. This case is reconstructed from the recorded reasons.
  - A repaired copy merges into one conservative record that passes the whole-bundle validator.
- **Fresh inference** (`uv run python scripts/window_replay.py RUN-d67b1d121b`, one sample, no writes): **all 8 NAAIM windows validated.**
  - **W03 returned evidence** after one repair. It quoted "• Go long at the close if RSI(3) < 10", "• Maintain the position while RSI(3) ≤ 40" and "• Enter or maintain long position only if IBS ≤ 0.5", with confidence medium and `mvp_testable` false.
  - The other seven windows returned `no_relevant_evidence`.
  - No truncation warning, and the DB was unchanged.
- **Synthetic live smoke** (`scripts/window_smoke.py`): passed 12/12 under the amended contract.
- **Checks:** 567 passed, 1 skipped (+19 tests). Both Ruff checks and `git diff --check` are clean. **All 21 mutations were caught**, including 6 new ones: source identity optional again, response text dropped, diagnostics not written, window or repaired failures not collected, and the merge trusting a model recommendation.
- **Independent review:** no material defect. Its two untested-but-correct points are now tests: a refused diagnostics write, and no response text in events.
- **Integrity:** DB `4e80d281…`, the list `88ba2d3c…`, and the E3 and E4 receipts and snapshots are unchanged. Protected tables are 0, and all three questions are `queued` with NULL paths.

**What remains uncertain**
- **The fix is verified on saved data, plus a single fresh sample.** Ollama is not byte-stable at temperature 0, so one clean replay is not a guarantee that a production run passes.
- **Evidence can escape to "none".** On W02 and W07, the 14B first claimed evidence with quotes absent from the text. The validators caught those, and a repair or the 27B then settled on `no_relevant_evidence`, which cannot be verified. Nothing was lost here because the overlap delivered the rule through W03, but in general this route can hide evidence.
- **Failed attempts of successful runs keep only hashes.** Diagnostics are written for failed runs only.
- A response containing a lone surrogate would fail the diagnostics write. It is recorded as a secondary failure and nothing else is affected.
- The pipeline being able to quote an RSI(3) exit rule is **not** evidence of a profitable strategy. NAAIM is tier discovery-only.

**Next (needs Jason's authorization):** one more production rerun of RQ-6d9c12f4 on the unchanged list.

## Gate D checkpoint E4: windowed rerun of RQ-6d9c12f4 (2026-09-28 UTC). It failed closed at NAAIM window 2 because of a window-contract trap.

One authorized run, not retried. No code change. No curator dispatch, push or merge. **Phase 6 / Gate D remain incomplete.**

**Readiness (all passed before dispatch)**
- `5f3b7fc`; 548 passed, 1 skipped; both Ruff checks clean.
- The list is still `88ba2d3c…` (working file and committed blob), and `gate_readiness` exited 0 (5 listed, 5 distinct works).
- The dispatch dry-run routed to `research_scout`. Both Qwen models were present, and the `web` channel was `ok`.
- DB `a6ab24f8…`. The `server.log` truncation count was 0.

**Run `RUN-d67b1d121b`** (02:15:53–02:20:54 UTC, 301s, exit 1)
- **Sources:** 5 of 5 fetched and accepted; S4 = NAAIM/Pagonidis (windowed into 8 windows).
- **S1–S3 extracted and validated:**

| Source | Result |
|---|---|
| S1 | 14B, after one repair |
| S2 | 14B, first attempt |
| S3 | 27B, after two 14B failures on absent quotes and high confidence |

- **S4:** W01 returned a validated `no_relevant_evidence`. **W02 failed all three attempts**, so the run failed closed. W03–W08 were recorded `not_run`, and S5 was never reached.
- **Receipt:** `Failed_Runs/RUN-d67b1d121b.md` holds the full window manifest (offsets, hashes, attempts), the recovery is complete, and the retry command keeps `--candidate-list`.
- There was no truncation warning, and the most prompt tokens any call used was about 5k.

**Why W02 failed (investigated with diagnostic model calls on the saved snapshot; no dispatch, no writes)**
- The NAAIM exit rule sits at characters 15,648–15,760: "• Go long at the close if RSI(3) < 10 • Maintain the position while RSI(3) ≤ 40". That is inside **both** W02 [7,755, 15,836) and W03 [14,690, 23,608), so the overlap worked.
- **In-run attempt 1:** the model chose `evidence` but left `curator_recommendation` null. The rejection message is "an evidence outcome needs a source and a curator_recommendation".
  - A replay of the exact prompt matched the run's prompt hash and response hash, so this was reproduced exactly.
  - **The trap:** the window contract requires a recommendation for evidence, but the JSON schema allows null.
- **Attempts 2–3:** the repair prompt then pushed the model to "fix" the output. Both 14B-repair and 27B produced a source record **without `source_id`**, which is optional in the nested schema. One of them also quoted text that is absent from the full snapshot. The validators caught all of it.
- **The same trap on W03**, replayed once under the current contract: the model quoted all three rule lines verbatim, but again left the recommendation null and was rejected. With the recommendation set to the most conservative value, **every quote passed both the window and full-snapshot checks**. The remaining rejections were ordinary ones that the ladder can repair: high confidence on discovery-only, and `mvp_testable` with an ungrounded `main_claim`.
- **A stricter either/or schema made things worse:** the model chose `no_relevant_evidence` for both W02 and W03, which is a false negative. Schema shape steers this model.
- **Ollama is not byte-stable at temperature 0.** The first replay reproduced the run's response hash; two later identical calls returned a valid `no_relevant_evidence` for W02 instead.
- **Provenance gap:** failed attempts store only response hashes, so the raw failing output was only recoverable by chance of an exact replay.

**Integrity**
- DB `4e80d281…`. The change from `a6ab24f8…` is expected: `agent_tasks` 5→6 and `agent_events` 67→85.
- Protected tables are 0; `research_findings` 7, `notes` 23 and `sources` 7 are unchanged. All three questions are `queued` with NULL paths, and no raw note exists.
- The list blob, the E3 receipt and snapshots, and `RUN-4e9d910742.md` are unchanged.
- Evidence is preserved byte-for-byte in `c6d13d1`: the receipt plus five `2026-09-28` snapshots, with exact-path `-text` rules and blob = working-file sha256.

**What this is and is not**
- The pipeline read an oversize PDF without truncation and located a source-stated RSI(3) exit rule (NAAIM/Pagonidis, tier discovery-only).
- That is evidence that the harness can find and verify exact quotations. It is **not** evidence of a profitable strategy, and nothing was promoted.

**Recommended next step (needs approval: an amendment to PROP-006's window contract; validators unchanged)**
1. Remove `curator_recommendation` from the window outcome. The windowed source's merged recommendation becomes `needs_more_work`, which is the most conservative value. The curator does not read the field anyway.
2. Require the nested `source_id` in the window's model-facing schema.
3. Optionally store the raw response text of failed attempts in the receipt.

Test with TDD and an independent review, then replay the saved W02/W03 prompts diagnostically, with no dispatch. Only then ask for one more rerun. Watch the false-negative risk that the either/or experiment showed.

## Oversize-source windowing, PROP-006 (2026-09-27)

Implementation and verification only. No RQ-6d9c12f4 rerun, no curator run, no push and no merge. **Phase 6 / Gate D remain incomplete.**

**Schema finding (why a contract was needed):**
- One-source payloads *can* carry a window that has evidence (validated against the window text).
- They *cannot* say "nothing relevant here" honestly. `evidence` must be non-empty, `main_claim` needs `min_length=1`, and the validator rejects an omitted supplied source. The model could only pass by quoting an arbitrary sentence and writing a filler claim.
- Jason approved a **window-only** `WindowOutcome` contract (PROP-006). It is internal to extraction, and the curator contract is unchanged.

**What changed**
- `src/quant_brain/research/windowing.py` (new):
  - `plan_windows`: UTF-8-byte-bounded at 9,000 bytes (≈6k tokens at a pessimistic 1.5 B/token), 1,200-byte overlap, snapped back to a line or word break within the last 10%. Offsets are code points, each window has a sha256, and IDs look like `S4-W03`. Any passage of at most the overlap lies wholly inside some window (brute-force tested).
  - `WindowOutcome`: all fields required; `no_relevant_evidence` must carry no source, no questions and no recommendation.
  - `validate_window_outcome`: runs the unchanged `validate_research_output` on the window text, then checks every quote against the full snapshot and checks the window hash.
  - `merge_window_outcomes`: verbatim unions; `main_claim` and rules joined with `"; "`; minimum confidence; AND for `mvp_testable`; most restrictive `data_access`; a `source_type` disagreement fails; no evidence anywhere fails; exact window accounting.
  - Manifest and markdown helpers.
- `research/executor.py`:
  - Windowing applies only where the existing pre-flight refuses the single prompt. More than `MAX_WINDOWS_PER_SOURCE` (10) is refused before any model call.
  - Every window prompt is screened before the first call.
  - `_extract_windows` runs windows in order under the shared deadline and stops on the first failure.
  - Records an `extraction_window` event per window, plus the manifest in `discovered_provenance["extraction_windows"]` (so Failed_Runs receipts carry it) and an "Extraction Windows" note section outside the JSON block.
- `llm/qwen_call.py`: optional `validator`, `output_schema` and `attempt_context` parameters, all defaulting to the old behaviour.
- `tests/test_windowing.py` (37 hermetic tests), `scripts/window_smoke.py` (live, writes nothing), PROP-006 in `plan_change_proposals.md`.

**Verification**
- 548 passed, 1 skipped. Both Ruff checks and `git diff --check` are clean. **All 15 mutations were caught.** M14 (window-prompt pre-flight) first survived, and a test was added for it.
- The existing `test_one_source_too_large_…` passes unmodified. Its 80 KB source now fails through the window cap (it would need 11 windows), still before any model call.
- **Real snapshots, measured read-only with no model:** NAAIM (55,481 decoded bytes) → 8 windows of at most about 5.7k tokens at 1.77 B/token. The other four fit and take the unchanged path.
- **Independent review:** no material defect. Two low-severity findings were fixed with TDD:
  - the merge now compares window IDs as the validator normalised them;
  - the manifest records that offsets index the universal-newline-decoded text.
- **Live smoke** (`uv run python scripts/window_smoke.py`, qwen3:14b/27b): passed 12/12, with no new truncation warning.
  - Filler windows returned explicit `no_relevant_evidence`.
  - The needle window validated only after the 14B failed twice and the ladder escalated to the 27B (about 51s).
  - A first fixture's needle ("the synthetic position …", with no ETF or oversold entry) was judged irrelevant under every contract tried, including a flat passage list. It was replaced with a needle that directly answers the question. **This is a real behaviour:** the model applies relevance strictly.
- **Integrity:** DB `a6ab24f8…`, list blob `88ba2d3c…`, the E3 receipt and five snapshots, and `RUN-4e9d910742.md` are sha256-identical. Protected tables are 0, and all three questions are `queued` with NULL paths.

**Limitations**
- `no_relevant_evidence` is the model's unverifiable negative judgment. The 14B applies relevance strictly, so evidence may be under-reported. If every window says none, the run fails closed.
- A quote longer than 1,200 bytes that straddles a boundary cannot be extracted whole.
- Up to 8 × 3 calls for NAAIM, and the 27B took about 51s per window. A slow ladder can exhaust the 15-minute deadline and fail closed.
- The optimistic bytes/4 screen still decides what gets windowed. A dense source of about 25–46 KB can pass it and then overflow at the server; it fails closed, unchanged by design.

**Next, needing authorization:** re-run RQ-6d9c12f4 on the unchanged committed list.

## Independent review closeout and Phase 6 budget completion (2026-09-27)

Reviewed all six incoming commits from `94b82be` through `1088084`, plus the unstaged E3 receipt and five snapshots. The context-window/extraction fix passed independent review without a material finding. The candidate-list implementation was also sound in its main path, but review found two material reliability gaps before another production run:

1. A `Failed_Runs` retry command dropped `--candidate-list`, so following it silently switched from the frozen list to search. A prepare-stage failure also lost the lane provenance before the receipt was written.
2. Per-source Qwen calls had 600-second timeouts but no shared run deadline. With up to five sources and three attempts each, the Phase 6 15-minute whole-run guardrail was not enforced.

**Fixed and independently re-reviewed:** commit `c6ab150` (`[verified] fix(scout): preserve lane retries and enforce run deadline`). Candidate-list provenance is captured before note preparation, retry commands reproduce the same list, and one monotonic 15-minute deadline now covers discovery plus every Qwen ladder. Agent Reach subprocess/HTTP operations and Ollama generation each receive only the remaining shared time; expiry fails closed.

**Deliberately unchanged:** candidate-list freezing remains procedural, as PROP-004 explicitly specifies. The committed list hash is recorded in every run, and the current RQ list still matches committed blob `88ba2d3c…`. Adding a runtime Git dependency solely to enforce the already-recorded limitation was not justified.

**Evidence preserved:** `e064955` commits `RUN-9b0d5a6e12.md` and all five `2026-09-27` snapshots byte-for-byte, with exact-path `-text` rules. Every committed blob was SHA-256-identical to its working file, and all five snapshot `content_hash` values recompute from their bodies.

**Verification:** 511 passed, 1 skipped; both Ruff checks and `git diff --check` clean; live context smoke 7/7 PASS with no truncation warning. Independent final review found no material or blocking defect. `db/brain.sqlite`, the historical receipt and the committed candidate-list blob are unchanged. Protected tables remain zero and all three child questions remain `queued` with NULL raw-note paths.

**Next bounded step:** design deterministic, evidence-preserving windowing for a single oversize source before any re-run. Do not knowingly re-run the unchanged list yet: the 31,330-token NAAIM snapshot will correctly fail the current 11,571-token per-call budget before the first model call. Phase 6 / Gate D remain incomplete; no curator was dispatched and nothing was pushed or merged.

## Context-safe extraction fix (2026-09-26): prompts can no longer be silently truncated

Fix and verification only. No Scout or curator dispatch, no research, and no push. The E3 receipt and snapshots are still unstaged. **Phase 6 / Gate D remain incomplete.**

**Commit:** `9f963f1` `fix(llm): bound extraction prompts and fail closed on context overflow`.

**Calibration** (Ollama 0.34.3, RTX 5070 12 GB). All probes used synthetic text, except the read-only token counts of the five E3 snapshots, which wrote no DB rows, events or files.

| Question | Measured |
|---|---|
| Silent prompt limit | `num_ctx // 2 + 2`: 1,026 at 2,048 and 2,050 at 4,096. Independent of `num_predict`. `prompt_eval_count` reports the cut length. |
| `truncate:false` | Honoured. HTTP 400 `exceed_context_size_error` ("request (3192 tokens) exceeds the available context size (2048 tokens)"). |
| qwen3:14b speed | At 16k: 16%/84% CPU/GPU, about 18 tok/s. At 40k: 37%/63%, about 2.25 tok/s (a 31k-token prompt took 117s for 179 output tokens). |
| qwen3.8:27b speed | At 16k: 57%/43% CPU/GPU, about 6 tok/s. |
| E3 snapshot tokens | ChartSchool 4,711; Hill 3,647; Double 7s 9,728; **NAAIM 31,330** (1.77 bytes/token, PDF mojibake); Connors Research 2,065. |

**What changed**
- `research/executor.py` (`qwen_extract` only):
  - One `qwen_call` per source, with the snapshot as raw text between delimiters. It used to be one JSON-escaped bundle; `ensure_ascii` roughly doubled the tokens.
  - All prompts are screened before the first model call.
  - The deterministic merge keeps S-order and an order-preserving union of open questions. The recommendation survives only if unanimous; otherwise it becomes `needs_more_work`.
  - The merged payload must pass the old whole-bundle `validate_research_output`. If it fails, the run fails with a `merge:` reason.
  - Still all-or-nothing.
- `llm/ollama_client.py`:
  - `generate()` **requires** `num_ctx` and `num_predict`, and sends `truncate:false` and `shift:false`.
  - `ContextOverflowError` is raised on: the server's 400; a missing `prompt_eval_count`; a count equal to the truncation signature; a count over the budget; or `done_reason=length`.
- `llm/qwen_call.py`:
  - Constants: `EXTRACTION_NUM_CTX` 16384, `EXTRACTION_NUM_PREDICT` 1536, `PROMPT_TOKEN_BUDGET` 11,571 (80% of the window minus the output reserve), and `EXTRACTION_TIMEOUT` 600s (the 27B measured near 300s).
  - There is an optimistic pre-flight estimate (bytes / 4).
  - `ContextBudgetError(QwenValidationError)` stops the ladder immediately, since repair and escalation prompts are longer.
  - `qwen_attempt` events gain `source_ids`, `num_ctx`, `estimated_prompt_tokens` and `prompt_eval_count`.
- **Tests:**
  - New `tests/test_context_guard.py` (17 tests).
  - Three existing fakes now record every per-source call. No assertion was loosened; two became stricter: each call carries exactly one source, and a failed first source stops the run.
- `scripts/context_smoke.py` plus the fixed fixture `tests/fixtures/context_smoke_snapshot.md` (synthetic, needle sentence first).

**Verification**
- 505 passed, 1 skipped. Both Ruff checks and `git diff --check` are clean.
- DB `a6ab24f8…`, list blob `88ba2d3c…`, the E3 receipt and snapshots, `RUN-4e9d910742.md`, the `2026-09-21` snapshots, `.gitattributes` and `external.sqlite`: all sha256-identical.
- The dispatcher, registry, paths and discovery code are unchanged.

**Mutations** (each applied to a backed-up file, then restored byte-for-byte with its sha256 verified). All 13 were caught:

| Mutation | Tests failed |
|---|---|
| M1 drop `num_ctx` | 2 |
| M2a no truncation-signature check | 1 |
| M2b accept missing `prompt_eval_count` | 1 |
| M2c no post-hoc budget check | 1 |
| M3a no pre-flight in `qwen_call` | 2 |
| M3b no executor sweep | 1 |
| M4 ladder continues after a context error | 3 |
| M5 whole bundle in each call | 12 |
| M6 skip merged validation | 1 |
| M7 `truncate:true` | 1 |
| M7b `shift:true` | 1 |
| M8 accept `done_reason=length` | 1 |
| M9 server 400 not mapped | 1 |

**Live smoke** (`uv run python scripts/context_smoke.py`, exit 0, 7/7 PASS):
- Prompt of 30,791 bytes, estimate 7,698, **`prompt_eval_count` 5,914**, `done_reason` stop, 12.6s. The model returned the needle verbatim.
- The ladder validated via qwen3:14b after one repair (13.8s + 11.7s), with evidence = the needle.
- The pre-flight refused an oversize prompt (~22,772 estimated) without calling the model.
- The server refused a 5,887-token prompt at `num_ctx` 2048 with HTTP 400.
- The `truncating input prompt` count in server.log was 6 before and 6 after (3 from E3, 3 from the calibration probes).

**Limitations**
- The pre-flight estimate is a screen, not a tokenizer. Real snapshots run 1.8–3.9 bytes per token, so it can under-estimate. The exact guards are the server's refusal and the post-hoc `prompt_eval_count` checks.
- **An oversize single source fails closed; there is no windowing.** The NAAIM snapshot exceeds the budget, so a re-run on the committed RQ-6d9c12f4 list will fail closed before any model call.
- Up to 5 × 3 model calls per run (the ladder is per extraction), and there is no run-level wall-clock cap.
- The 27B is 57% on CPU, and a worst-case call is about 5 minutes.
- Server-side refusal depends on Ollama honouring `truncate:false` (verified on 0.34.3). The client checks still apply if it stops doing so.
- The constants are calibrated for this machine.

**Next, needing approval:** decide how to handle the E3 re-run (run and record the fail-closed outcome, or first approve a design for oversize sources). See PLAN.md §10 "What to do next".


## Gate D checkpoint E3: first candidate-list run for RQ-6d9c12f4 (2026-09-26 local, 2026-09-27 UTC). It failed closed, and the cause was prompt truncation.

One approved run and no retry. No code change, push or merge. PROP-005 is still **undecided** and was not applied. **Phase 6 / Gate D remain incomplete.**

**Commits** (local `testing`)

| Commit | Content |
|---|---|
| `94b82be` | E2 code and tests (10 files). Committed blobs equal the LF-normalised working files. |
| `eb91355` | PLAN.md, SESSION_HANDOFF.md, plan_change_proposals.md and the E1 dossier, as they stood before the run. |
| `7093f92` | `brain/00_Inbox/Scout_Candidates/RQ-6d9c12f4.md`. |
| next | This docs entry and PLAN.md §10. |

**The list**
- sha256: `88ba2d3ce98b69623d050197c15c8e5d7adf82e107b3a6bb8ea5e045022faeae`.
- The working file (LF), `git cat-file blob HEAD:<path>`, `gate_readiness` and the `discovery_started` event all give this same value. The list was not edited after the run.
- Contents: the dossier's declared rule only, 5 URLs. The Malaysian DOI chapter is excluded (Jason).
- `gate_readiness --candidate-list` exited 0: 5 listed, 5 distinct works.
- Originators: Connors (#1, #3, #5), Hill (#2), Pagonidis (#4).

**Pre-flight** matched the baseline:
- 488 passed, 1 skipped. Both Ruff checks and `git diff --check` are clean.
- DB `6db65981…f530f9e29`.
- `qwen3:14b` and `qwen3.8:27b` are present, and the `web` channel is `ok`.

**Run `RUN-9b0d5a6e12`** (task `TASK-378a8d93cd`, 02:47:13 to 02:50:21 UTC, 188s, exit 1)

- **Events (9):** `dispatch_started → discovery_started` (carries `discovery_lane` with the list sha) `→ qwen_attempt ×3 → discovery_failed (qwen_extract) → failed_run_written → handler_failed → dispatch_failed`. There is no `discovery_completed`, as expected on this path.
- **Sources:** all 5 were accepted and 0 rejected. There were 5 distinct upstream works against the 3 required.

| Label | Source | Tier | Snapshot `content_hash` prefix |
|---|---|---|---|
| S1 | ChartSchool | practitioner | `061e9f29` |
| S2 | Hill | practitioner | `13a68c8f` |
| S3 | Connors Research | discovery-only | `f57de4fc` |
| S4 | NAAIM/Pagonidis | discovery-only | `c5f9673f` |
| S5 | Double 7s | discovery-only | `576c861a` |

  All five hashes recompute from the snapshot bodies (after CRLF normalisation). Each dossier exit-rule span is present in its snapshot.
- **Model attempts** (all failed validation):

| Attempt | Duration | Result |
|---|---|---|
| `qwen3:14b` | 28.2s | invented `research_id: Double7sSetup`, omitted S1–S5, and cited unknown `Double7sSetup_*` IDs |
| repair | 18.0s | still omitted S4/S5; relabelled S1/S2 with Double 7s titles and URLs; quotes absent; ungrounded promotion |
| `qwen3.8:27b` | 118.9s | schema failure: S4/S5 evidence empty |

- **Receipt:** `brain/00_Inbox/Failed_Runs/RUN-9b0d5a6e12.md`. It holds full provenance (the lane block, the 5 accepted candidates with tier, snapshot path and sha256, and the counts 5/3), and records recovery as complete: raw note removed, question `queued`.

**Finding: the decisive cause is prompt truncation in the model runtime.**
- The Ollama `server.log` records `msg="truncating input prompt" limit=2050` at 21:47:46, 21:48:06 and 21:48:42 local time. The prompts were 53,917, 54,985 and 55,586 tokens, and each was cut to 2,050 (`keep=4`).
- `llm/ollama_client.py` sends only `temperature`, with no `num_ctx`. Nothing in the harness notices. **Correction (2026-09-26):** the server ran with `-c 4096`, but the effective prompt limit is `num_ctx // 2 + 2` (measured), which is **2,050** tokens, not 4,096.
- The models therefore saw about 4% of each prompt: the tail of the evidence bundle, which is the end of the S5 Double 7s snapshot, without the instruction, the question or S1–S4. This explains the `Double7sSetup` research ID.
- **The same happened to RUN-4e9d910742** on 2026-09-20 (`server-5.log`, 19:58–19:59: 11,962, 12,847 and 12,760 tokens → 2,050). **Correction (2026-09-26):** that run's source-relevance finding **stands**. Its snapshots were checked directly and have zero RSI or ETF mentions. The truncation confounds only the account of why the models misbehaved.
- The validators and fail-closed path behaved correctly. Per the task constraints this was **not fixed** (no code changes).
- The log lines are quoted here because Ollama rotates its logs.

**Curator:** not dispatched, because no raw note exists. There is no curator verdict, and nothing was promoted. Originator independence was not tested by the pipeline. The ceiling is still about 2 promotable from 2 originators (Connors via ChartSchool, Hill). #3 and #5 are not independent of #1.

**Post-run state**
- Protected tables (`strategy_cards`, `backtests`, `price_datasets`, `reviews`) are 0.
- `research_findings` 7, `notes` 23 and `sources` 7 are unchanged. `agent_tasks` went 4→5 and `agent_events` 58→67.
- All three questions are `queued` with a NULL path.
- DB sha256 is now `a6ab24f8a101599cd87f8e4bf9631db860fdf5263b16dd529186ce1e09a24e1a` (expected: run and audit rows only).
- `external.sqlite`, `.gitattributes`, `RUN-4e9d910742.md` and the five `2026-09-21` snapshots are sha256-identical.
- 488 passed, 1 skipped. Ruff and `git diff --check` are clean.
- Unstaged: `RUN-9b0d5a6e12.md` (sha256 `5ffa7a507016253a80ff71dba9b733ce1baa70861d7025f4e929fe534dd5ee5a`) and `Source_Snapshots/2026-09-27/` (5 files).

**Limitations**
- "Frozen" is procedural: the list sha is recorded, but the code does not check git.
- The receipt's suggested re-run command omits `--candidate-list`, so it would run the search lane. Its `retryable: true` is advisory.
- The 27B's output failed schema first, so it is unknown whether it would have passed the other validators.
- Unlisted publisher aliases are not collapsed. The arXiv 406 is untouched. PROP-005 is undecided.

**Next, each needing approval:** fix the context window and add truncation detection; re-run on the same committed list; re-read the RUN-4e9d910742 attribution. See PLAN.md §10 "What to do next".


## Gate D checkpoint E2: pre-registered candidate-list lane (2026-09-26). Ready for Drew's review; committed in E3 as `94b82be`.

This implements the scope PROP-004 authorized for E2. Nothing is committed, and there was no Scout or curator dispatch, network research, list registration, arXiv repair or later-phase work. PROP-005 remains **proposed**. **Phase 6 / Gate D remain incomplete.** `HEAD` is still `7277a76`.

**Change set**

New files:
- `src/quant_brain/discovery/work_identity.py`
- `src/quant_brain/discovery/candidate_list.py`
- `tests/test_work_identity.py`
- `tests/test_candidate_list_lane.py`

Modified files:
- `discovery/live_discovery.py`
- `research/executor.py`
- `harness/handlers.py` (the Scout handler only)
- `scripts/dispatch_task.py`
- `scripts/gate_readiness.py`
- `tests/test_gate_readiness.py`

`dispatcher.py`, `registry.py`, `paths.py` and `acquisition.py` are unchanged.

**How the lane behaves**

- **List file:** `brain/00_Inbox/Scout_Candidates/<RQ>.md`, holding exactly one ```json block with these fields:
  - `research_id`, `selection_rule`, `screening_reference`, `registered_by`, `registered_on`
  - `candidates[]`: 1 to 10 entries, each with `url`, `found_via`, `added_by`, `added_on`

  pydantic `extra="forbid"` applies at both levels, so an entry cannot carry a tier, title, claim or evidence. One work listed twice (for example a DOI and its landing page) is refused at load.
- **Run:**
  - `scripts/dispatch_task.py --type discovery --research-id <RQ> --candidate-list brain/00_Inbox/Scout_Candidates/<RQ>.md`
  - This requires the live backend and an explicit research ID matching the list's own `research_id`. Both are checked before any fetch.
  - The backend keeps `name = "live"`, so the Qwen ladder and validators always run.
  - **Search is not called.** Hits are built from URLs alone, and tiers come from `classify_source`.
- **Offline pre-registration check:**
  - `scripts/gate_readiness.py --research-id <RQ> --candidate-list <path>`
  - It checks that the list loads, matches the question, and names at least 3 distinct works.
  - It says nothing about relevance, access or support. Exit codes: 0 ready, 4 short, 5 invalid.
- **Budget, precisely:** at most 5 **accepted** sources. A thin or boilerplate page is backfilled from the next listed candidate, so fetch attempts can reach the list length (≤10). Pre-fetch `reject` URLs are never fetched.
- **Provenance:** a `discovery_lane` block (path, sha256, count, URLs) is recorded in:
  - the `discovery_started` and `discovery_completed` events
  - the handler detail
  - a `## Discovery Lane` note section, outside the JSON block
  - `InsufficientUpstreamSources.detail`
  - every Failed_Runs receipt, including failures inside `discover()`. It is captured before discovery as an input, not as candidate evidence.

**DOI identity** (`upstream_work_key`)

It uses only a host-anchored table:
- doi.org / dx.doi.org resolver paths
- the arXiv DataCite DOI, mapped to the abs URL
- European Proceedings `/article/10.15405/…`
- Wiley `/doi/(abs|full|pdf|epdf)/10.1111/…`
- SSRN `abstract_id` / `abstract=`, on SSRN hosts only

Publisher rows match the full path with a slash-free suffix. `…/figures`, unlisted publishers, query-string DOIs and `abstract_id` on other hosts stay separate.

The key is used by `distinct_upstream_keys` (the source minimum, which counts fetched sources) and by list validation. **Plan deviation:** search-lane candidate dedupe was left on the normalized URL. Changing it broke `test_duplicates_cannot_buy_a_passing_run`, which pins the existing layering, and the minimum was already protected at the counting layer.

**Verification**

| Check | Result |
|---|---|
| `uv run pytest -q` | **488 passed, 1 skipped** (425 plus 63 new) |
| `tests/test_dispatcher.py` | 13 passed, file unchanged |
| `ruff check .` | clean |
| `ruff check src tests scripts` | clean |
| `git diff --check` | clean |
| `db/brain.sqlite` | `6db65981…f530f9e29`, unchanged |
| `exit-rules-final/external.sqlite` | `4b20094c…7c00`, unchanged |
| `.gitattributes`, `RUN-4e9d910742.md`, five `2026-09-21` snapshots | sha256 OK |
| Questions | all three `queued` with a NULL path; agent_tasks 4, agent_events 58; protected tables 0 |

**Mutation checks** (each applied to a backed-up file and restored byte-for-byte, verified by sha256). All seven were caught:

| # | Mutation | Tests failed |
|---|---|---|
| M1a | drop the European Proceedings row | 5 |
| M1b | drop the SSRN host anchor | 1: `abstract_id` on another host |
| M2 | run search in list mode | 12 |
| M3 | loader ignores extra fields | 6 |
| M4 | lane not captured before discovery | 2 |
| M5 | count listed URLs, not acquisitions | 1 |
| M6 | pass list entries through as hits | 1 |

**Limitations**

- **"Frozen" is procedural.** The sha256 is recorded, but the code does not check git. Before any E3 run, compare the recorded sha256 with the committed blob.
- **Unlisted publisher aliases are not collapsed**, so work identity must be checked by hand before a run.
- Relevance screening and originator independence remain human steps.
- The arXiv 406 is untouched.

**Next, needing separate approval**
- Jason's scope decision on the Malaysian DOI chapter.
- Registering and committing the RQ-6d9c12f4 list.
- E3, the single run.


## Gate D checkpoint E1: seed dossier and proposals (2026-09-26). Stopped for Jason.

This was an approved plan checkpoint. It involved no code change, no Scout or curator run, and no write to the production DB or the intake catalog. **Phase 6 / Gate D remain incomplete.**

**Outputs:**
- `brain/00_Inbox/Gate_D_Seed_Dossier_2026-09-26.md`, holding leads only.
- PROP-004 (pre-registered seed lane plus DOI-alias collapse) and PROP-005 (narrow "source-insufficient" pipeline-acceptance clarification), both **proposed**, in `brain/_system/plan/plan_change_proposals.md`.

**Verified before and after:**
- **425 passed, 1 skipped.** Ruff and `git diff --check` clean.
- `db/brain.sqlite` `6db65981…f530f9e29` is unchanged.
- `exit-rules-final/external.sqlite` `4b20094c…7c00` is unchanged.
- All three questions are `queued` with a NULL raw-note path. agent_tasks is 4 and agent_events is 58. The protected tables are 0.

**New findings:**
1. **The arXiv lane now fails.** Python `urllib` gets **HTTP 406** from `export.arxiv.org` while curl gets 200; the cause is not established. `gate_readiness` now exits 4 with **0 URLs for all three** questions (RQ-6d9c12f4 was at 3).
2. **DOI aliases double-count.** `distinct_upstream_keys` counts a `doi.org` URL and its publisher landing page as 2 works.
3. **sec.gov comment letters classify as `primary` on host alone.**
4. **One catalog DOI primary was fetched, not blocked.** `doi.org/10.15405/epms.2022.10.4` states the RSI(14) 30/70 exit, but on Malaysian equities.

**Pre-run findings:**

| Question | Relevant, accessible | Promotable | Originators | Finding |
|---|---|---|---|---|
| RQ-6d9c12f4 | 4 (5 with the epms DOI) | 2 (3 with the DOI) | 2 (3 with the DOI) | The Scout bar is clearable via a seed lane. Whether the DOI enters is Jason's scope call. |
| RQ-c920baeb | 2, both out of scope | — | — | **source-insufficient.** One is an uncited SEO 10-day time stop; the other is a 9-day cap on A-shares. |
| RQ-80be8cf7 | 2 | 2 | 2 | **source-insufficient.** Nasdaq-measured QQQ spreads of about 1–2 bps (2011–12), and an arXiv paper assuming 18 bps for retail US large-cap equities (2024). |

**Decisions for Jason:**
- Accept or reject PROP-004, or configure Exa instead.
- Include or exclude the epms DOI from the RQ-6d9c12f4 seeds.
- Accept or reject PROP-005.
- Whether to diagnose the arXiv 406 as its own task.
- Next step after those decisions: E2, implementing the seed lane with tests. That needs approval, and no run happens in E2.


## YouTube methodology scout (2026-09-26) — video leads only

Cataloged the first 30 `@itsjjsimon` uploads and all 14 visible `@deltatrendtrading/videos` uploads via yt-dlp; fetched and reviewed English transcripts from 4 JJ Simon and 6 Delta Trend Trading videos. Timestamped transcripts retained outside the repo at `C:/Users/jason/quant-agent-brain-intake/channel-review-2026-09-26/` (video IDs are file names). These are creator claims/teaching, not independent strategy evidence.

- JJ Simon: the sample emphasizes prop-firm evaluation economics and payouts, with useful warnings about selection among many tests, uncounted trials, and small samples (`PMGhHCjYG5c` 03:39–05:40). This supports the existing immutable-trial and benchmark policy; it does **not** substantiate payout figures or a transferable market edge. The break-even/zero-edge account example (`2BtwoTCxcbc`) is a simulation premise, not proof of positive strategy expectancy. Do not copy risk sizing into this no-live-trading project.
- Delta Trend Trading: stronger fit for learning a research workflow. `M3-0LfZMsz4` distinguishes building/falsifying an idea from copying a guru setup; `Zu4sL5u-WyU` defines event sampling as a research start, not a strategy; `ZQUmXK_xapM` shows null results and context-feature experiments; `MCnFrUxZARU` explains net expectation and path dependence. Treat on-video p-values/results as unverified until data, code, split, cost assumptions, and trial family are available. `jGhk-uSrtII` initially describes IID trade bootstrap and later warns of regime dependence; resampling the same trade history does not increase independent information or establish edge.
- No reviewed video supplies three distinct promotable upstream sources documenting the daily ETF RSI exit rule. These videos belong in a methodology/learning lead pool, not the Phase 6 source count or trusted research index. No phase, gate, code, production database, or strategy state was changed.


## Methodology reports reviewed (2026-09-26) — leads, not trusted research

Jason supplied two PDFs, retained byte-for-byte in the vault's `Projects/Quant Agent Brain/Research/External Reports/`:
- `Quant Mind End-to-End - external synthesis.pdf` (11 pages; SHA-256 `0ee8b4878c08eb4089944b1ef7315c613127aa4f0f5d072167064b6f4db3ac6e`): useful hypothesis-first, point-in-time and anti-overfitting orientation; mostly familiar to PLAN.md. Its proposed immediate Alpaca/Tiingo, MLflow, six-station agents, Qlib and external competitions are **not adopted**; they expand scope or jump gates. Precise pricing, subscriber, platform and performance claims are unverified leads, not sources of truth.
- `Closing Three Missing Validation Gaps in the Evidence-First Quant Agent.pdf` (45 pages; SHA-256 `5a3e9ed7d3c3748449501b3350ac43baf16a60358f61e5d2b79c`): stronger candidate methodology for later validation: separate within-family instrument replication from independent economic environments; count signal episodes before exits and evaluate net-outcome power after a strategy freeze; compare feed semantic contracts and signal/trade parity before paper. Its source list provides leads, not independently verified proof; gate cutoffs and formulas need primary-source and data checks before implementation. Neither PDF supplies a third qualifying independent source for `RQ-6d9c12f4` or changes Phase 6 / Gate D.

Retained only as **external methodology leads** in the vault, not imported into the exit-rule claims catalog, RAG/trusted notes, or production database. Do not treat report prose as multiple independent sources. Any added phase/exit gate needs a proposal and Jason's approval; prioritize the current research-source blocker first.


## Resume verification (2026-09-26)

**Completed after Jason selected the original catalog:** appended five exact-quotation claims using the existing Intake API and verified all five offline against pinned snapshots. All five have `quote_match=true`, `full_rule_match=true`, and state `partially_supported` / `review_required`; this is exact passage matching, not validation of a complete strategy. No attributed human scope review was performed. Handoff remains empty. Added 5 claims, 5 evaluations and 10 history rows; no new targets, reports or fetches. All pre-existing catalog rows and non-database intake files (including acceptance.json) were preserved; production DB unchanged. Backup and machine-readable verification are in `C:/Users/jason/quant-agent-brain-intake/exit-rules-review/` as `external-before-remap-2026-09-26.sqlite` and `remap-recorded-verification.json`. The workspace decision is resolved; the next boundary is human scope review and acquiring additional relevant independent evidence through an approved route. Gate D remains incomplete.


- Live local `testing` and remote `refs/heads/testing` both resolve to `7277a76`; the checkpoint is pushed. Earlier "not pushed" statements below are historical.
- Fresh verification: `uv run pytest -q` = **425 passed, 1 skipped**; `uv run ruff check .` and `git diff --check` pass. Production DB SHA-256 before/after: `6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29`.
- All three Gate D child questions remain queued with no raw-note path. Strategy cards, backtests, price datasets and reviews are all zero. Phase 6 / Gate D remain incomplete.
- Existing uncommitted changes were documentation only (PLAN.md and SESSION_HANDOFF.md); preserved during this review.
- Next bounded step recommended: append exact-quotation claims and offline verification to the original isolated `exit-rules-final` catalog, preserving existing records. This resolves the copied-workspace path guard without bypassing it. Await Jason's workspace choice before catalog writes; do not attribute a scope review to him without his actual review.
- This step alone cannot satisfy Gate D: the existing packet identifies only two promotable targets (Connors via ChartSchool and Hill). More independent, relevant evidence and an approved ingestion route are still needed. No Scout/curator dispatch, model calls, production research writes, commits or pushes performed in this session.


## Verbatim re-mapping pre-check for RQ-6d9c12f4 (2026-09-22) — stopped at a guard, awaiting decision

The reliability checkpoint is committed as **`7277a76`** (entry below). This is the separate part B:
read-only, offline, no model, no network, no Scout, no curator. **Phase 6 / Gate D remain incomplete.**

- **Pre-check:** the intake verifier's own `normalized`/`source_span` were run on the integrity-checked
  pinned snapshots in `C:\Users\jason\quant-agent-brain-intake\exit-rules-final`. All **5 of 5**
  verbatim exit-rule spans were located, across 5 distinct targets:
  - ChartSchool (Connors, 5-day SMA exit);
  - Arthur Hill (RSI(5) above 70);
  - Connors Research (4-period RSI above 55);
  - NAAIM/Pagonidis (hold while RSI(3) ≤ 40);
  - Bulkowski (relaying Connors & Alvarez, seven-day high).
- **Only 2 are promotable tier (both StockCharts), and only 1 is independent of Connors.** Under the
  unchanged tier policy this material cannot meet the ≥3-source bar.
- **Not recorded, by design.** Recording was to happen in a byte-identical copy
  (`…\exit-rules-review`). But the catalog stores absolute snapshot paths inside `exit-rules-final`, and
  `safe_target` refuses paths outside the workspace root. The guard was not bypassed, and the recorded
  workspace was verified unchanged (24 files, sha256).
- **Packet:** `…\exit-rules-review\REVIEW-PACKET.md`; raw results in `remap-precheck.json`.
- **Jason's decision:**
  1. append the claims to `exit-rules-final` and verify offline;
  2. use a fresh workspace and one refetch; or
  3. stop here.

  Then comes his attributed `review --state supported_in_scope`. A third promotable, independent source
  is needed before any `RQ-6d9c12f4` Scout run could pass. A "reviewed-leads" Scout lane remains a
  possible governance proposal, not authorized.

## Reliability checkpoint committed (2026-09-22) — local on `testing`, not pushed

The discovery-recovery hardening and the reliability closeout (both described below) were independently
reviewed and are now **one local commit on `testing`**, directly after `df63698`. **Not pushed**
(`origin/testing` is still `3c02397`). No Scout run, retry, curator or research. **Phase 6 / Gate D remain
incomplete.**

- **Two wording fixes at commit time, no behaviour change:**
  - the held-question receipt now gives **two literal, runnable** release commands
    (`clear_raw_note_path=True` if the note was removed, `False` if it was kept) instead of a template;
  - a failed dispatcher finalization is reported as `task_row=unconfirmed (finalization update failed;
    state not verified)` instead of assuming the row is still `running`.

  The tests assert both.
- **Verified before committing:**
  - the related files (recovery, dispatcher-failure, dispatcher, discovery handler, provenance,
    upstream minimum): **76 passed**;
  - full suite **425 passed, 1 skipped**;
  - `ruff check .` and `ruff check src tests scripts` clean; `git diff --check` clean;
  - `db/brain.sqlite`, `.gitattributes`, and every `Failed_Runs/` and `2026-09-21` snapshot file
    sha256-identical.
- **Committed paths (7):** `research/executor.py`, `research/intake.py`, `harness/dispatcher.py`,
  `tests/test_fail_closed_recovery.py`, `tests/test_dispatch_failure_recording.py`, `PLAN.md`,
  `SESSION_HANDOFF.md`.
- **Limitations are unchanged:** see the closeout entry below.

**Research blocker, re-diagnosed (read-only; details in `PLAN.md`):** for `RQ-6d9c12f4` the bottleneck is
**claim-to-source mapping**, not discovery.
- The retained external reports paraphrased their claims.
- The intake verifier (by design) accepts only a claim that *equals* its verbatim quotation.
- So 4 located quotations, plus 2 exit rules present verbatim in pinned snapshots, never reached
  review.
- Tier policy (unchanged) makes only the 2 StockCharts targets promotable, fewer than the ≥3 bar.

**Next (approved):** an offline re-mapping of those verbatim spans in a *copy* of the intake workspace,
producing a review packet for Jason's attributed scope review. It creates no raw note, no Gate D
progress, and no promotion.

## Reliability closeout (2026-09-22) — historical: the pre-commit description

**425 passed, 1 skipped** (413 + 12 new); `ruff check .` and `ruff check src tests scripts` clean;
`git diff --check` clean. `db/brain.sqlite` (`6db65981…f530f9e29`), `.gitattributes` and every
historical `Failed_Runs/` and `Source_Snapshots/2026-09-21/` file are sha256-identical before and after.
On top of `df63698` together with the recovery hardening below; nothing staged, committed or pushed. No
Scout run, retry, curator or research. **Phase 6 / Gate D remain incomplete; source relevance is
unchanged.**

**1. Incomplete recovery no longer looks retryable, and a real control backs that up.**
- Inspection showed that **nothing reads a receipt's `retryable:` line**. The retry signal actually used
  is `research_questions.status`:
  - executor queue selection takes `researching`, then `queued`;
  - `claim_next_research_task` takes `queued`, then overwrites the note at its fixed path;
  - explicit `--research-id` dispatch took any status.
- So when raw-note recovery **fails**, the question is now held at a new status **`needs_review`**
  (added to `intake.VALID_STATUSES`), using the existing `update_research_status`, whose `COALESCE`
  keeps `raw_note_path` pointing at the leftover file.
- No selector picks `needs_review` up, and `execute_discovery_task` refuses it on explicit dispatch
  **before the task binds**, so fail-closed can't undo the hold.
- The receipt says `retryable: false` and **"Manual inspection required"**, naming the leftover path,
  what to check, and the exact release one-liner (`reset_research_for_retry(...)`).
- A preserved (`untouched-preexisting`) or `restored` pre-existing note counts as **successful**
  recovery: `queued`, `retryable: true`.
- The `recovery` block is now `raw_note` / `question` (`queued` | `needs_review` | `update-failed`) /
  `complete` / `secondary_failures`. If the hold or reset update itself fails, the receipt says
  "Recovery incomplete" and claims neither state.

**2. The dispatcher preserves the original error**
(`harness/dispatcher.py`, failure branches only).
- Both `except` branches now call `_record_dispatch_failure`, which independently attempts:
  1. the first event (`handler_failed` or `path_violation`);
  2. `dispatch_failed`;
  3. `_finish_task_row(..., "failed")`.
- Each goes through a local `_secondary` helper (the same contract as the executor's `_attempt`; kept
  local so the harness doesn't import a research module).
- Secondary failures are added as notes on the handler's exception, stating `task_row=failed` or
  `task_row=NOT finalized (still 'running')`, never a finalization that didn't happen.
- The bare `raise` re-raises the same object with its traceback; the notes appear in the CLI's traceback.
- `Exception` only is caught, so `KeyboardInterrupt`/`SystemExit` propagate. The success path, the
  pre-handler writes and the handler contracts are unchanged.

**Tests (12 new; mutation-checked).**
- `tests/test_dispatch_failure_recording.py` (8):
  - each event failing; finalization failing (the row really stays `running`, and the note says so);
  - everything failing together; a handler `PathViolation` whose own event fails;
  - `KeyboardInterrupt` during finalization; a clean failure with no notes;
  - a successful dispatch unchanged.
- `tests/test_fail_closed_recovery.py` (+4):
  - explicit dispatch of a held question refused with nothing mutated;
  - queue selection skips a held question;
  - a failed hold reported, not claimed;
  - end to end, the same Qwen exception carrying both executor and dispatcher notes.
- The two cleanup-failure tests now expect the hold, and the pre-existing-note tests assert
  `complete: true` / `retryable: true`.
- Mutation checks:
  - un-guarding finalization fails 2 dispatcher tests;
  - resetting after a failed cleanup fails 3 hold tests.
- The committed tests, including `tests/test_dispatcher.py`, pass unchanged.

**Limitations (precise).**
- The hold blocks automatic selection and Scout dispatch. It does **not** stop direct DB edits, or a
  manual `research_scout_runner.py prepare`, which claims only `queued` but would overwrite the fixed
  note path if the question were released without inspection.
- Release is a documented manual one-liner, not a CLI command.
- Recovery and finalization are attempted, not guaranteed. The success-path dispatcher writes and the
  pre-handler task-row and `dispatch_started` writes are still unguarded, but there's no original error
  to mask at those points.
- A scaffold whose creation failed mid-way is left in place and not held, because ownership can't be
  proven.
- Snapshot frontmatter still has no `run_id`.

**Recommended next step toward research acceptance (not authorized):** relevance, not reliability, is the
blocker (zero `RSI`/`ETF` mentions in the five retrieved works). The smallest step is read-only: add a
deterministic topical-relevance count to `scripts/gate_readiness.py` and use it to evaluate one
alternative lane or query for `RQ-6d9c12f4`, with no model and no Scout dispatch. Propose a single,
separately authorized Scout run only if a candidate set clears both the ≥3-source bar and the relevance
check.

## Fail-closed recovery hardened (2026-09-22, later) — historical; its dispatcher limitation is resolved above

**413 passed, 1 skipped** (397 + 16 new); `ruff check .` and `ruff check src tests scripts` clean; `git diff
--check` clean. `db/brain.sqlite` (`6db65981…f530f9e29`), `.gitattributes`, and every file under
`Failed_Runs/` and `Source_Snapshots/2026-09-21/` are sha256-identical before and after. On top of
`df63698`; nothing staged, committed or pushed. No Scout run, retry, curator or research. **Phase 6 /
Gate D remain incomplete; the source-relevance blocker is untouched.**

**Defects fixed, all in `src/quant_brain/research/executor.py`.** Each one could skip recovery and
replace the original research error with a diagnostic one:
1. The `discovery_failed` event ran *before* `_fail_closed_discovery`, unguarded, so a DB error there
   skipped *all* recovery. (Found during planning; not in the brief.)
2. The receipt write caught only `OSError`, so a `PathViolation` escaped.
3. The `failed_run_written` event shared the receipt's `try`: a DB error escaped, and an `OSError` nulled
   the path of a receipt that *had* been written.
4. Scaffold cleanup caught only `OSError`, its fallback event was unguarded, and the unlink/restore
   bypassed `resolve_write`.
5. `reset_research_for_retry` was unguarded.
6. The receipt always claimed the question "was returned to `queued`".

**Fix.**
- A private `_attempt()` runs each step and returns `(ok, value)`. Outcomes are read from the flag, so a
  successful `None` return can't read as failure. It absorbs `Exception` only, so
  `KeyboardInterrupt`/`SystemExit` propagate.
- `_fail_closed_discovery` now attempts, independently and in order:
  1. the `discovery_failed` event;
  2. raw-note recovery;
  3. the reset;
  4. the receipt, *after* recovery so it states the outcome, with a `recovery` block. `retryable: false`
     and "Recovery incomplete" appear when the reset failed;
  5. the `failed_run_written` event.
- Each failed step is added as a note on the original exception (`add_note`). That channel depends on
  neither the DB nor the filesystem. The executor's bare `raise` re-raises the same object with its
  original traceback.

**Ownership corrected (behaviour change).**
- Before: a pre-existing note at `Raw_Research/{research_id}.md` that the run never modified was
  **deleted** on an early failure. A pre-existing note that *was* restored lost its pointer, so a retry
  would recreate, and overwrite, it at the same path.
- Now the run mutates only what it provably owns or changed. A run-created scaffold is removed; a
  modified pre-existing note is restored byte for byte; an untouched pre-existing note is left alone.
- Every mutation passes `resolve_write` first: a `PathViolation` **refuses** recovery and is reported,
  never bypassed.
- `reset_research_for_retry` gained a keyword-only `clear_raw_note_path` (default `True`, so other callers
  are unchanged). The pointer is cleared only when no note remains at it. The curator only accepts
  `raw_saved`/`curated`, so a `queued` question that keeps its pointer can't be curated.

**Tests: `tests/test_fail_closed_recovery.py` (16).**
- Coverage:
  - receipt `PathViolation` (real enforcement) and receipt `OSError` (real `FileExistsError`);
  - each event failing with `PathViolation`/`OSError`/`sqlite3.OperationalError`, and all of them together;
  - cleanup refused by the real resolver after a normal scaffold and Qwen failure;
  - cleanup `PermissionError`; a reset DB failure;
  - `KeyboardInterrupt` propagation; a clean failure;
  - both pre-existing-note cases.
- Every case spies on the real handler and asserts the **same exception object** and the original
  traceback frame. Cases also assert task, question and scaffold state.
- Mutation-checked: all 16 fail against `HEAD` code (some only via the new `recovery` field), and
  un-guarding just the receipt step fails the 3 receipt tests.
- Existing tests pass unchanged.

**Remaining limitations.**
- Recovery is *attempted*, not guaranteed: a failed filesystem or DB step is reported, not overcome.
- The dispatcher (`harness/dispatcher.py`) still emits `handler_failed`/`dispatch_failed` and finalizes
  `agent_tasks` unguarded, so a broken DB there can still mask the original *after* discovery
  re-raises. That is harness-wide and a candidate follow-up.
- If `create_raw_research_note` fails mid-way, its scaffold is left in place, because ownership can't be
  proven.
- The manual `prepare_next_research_run` still overwrites `Raw_Research/{research_id}.md` whatever the
  pointer says. That behaviour predates this change and this change doesn't cause it.
- Snapshot frontmatter still has no `run_id`.

**Next decision is Jason's:** review this unstaged change set. A dispatcher-level guard is a
recommended small follow-up; it matters only when the DB is already failing, and in that case the
receipt still records the original error. The source-relevance blocker still decides whether a Scout
retry can succeed.

## Checkpoint committed (2026-09-22) — provenance repair and historical evidence (historical)

Two local commits on `testing`, **not pushed** (`origin/testing` is still `3c02397`). No Scout run, retry,
curator or research was executed. **Phase 6 / Gate D remain incomplete.**

- **`54df8cf`, evidence:** `RUN-4e9d910742.md` plus the five `Source_Snapshots/2026-09-21/` files, committed
  unchanged, and a new `.gitattributes` marking exactly those six paths `-text` so `core.autocrlf=true`
  cannot normalise them. Original, staged and committed sha256 were verified identical for all six (CRLF
  and trailing whitespace preserved). The link to `RUN-4e9d910742` stays **probable, not established**.
- **The commit containing this entry:** the provenance repair (`live_discovery.py`, `executor.py`), its
  tests (`test_failed_run_provenance.py`, `test_upstream_minimum.py`), and this file plus `PLAN.md`. Code
  and test bytes are sha256-identical to the state verified below (397 passed, 1 skipped, Ruff clean), so
  that verification was reused rather than re-run.
- **Next build task, required before any further production Scout attempt:** harden
  `_fail_closed_discovery`:
  - treat receipt-write and event failures (`PathViolation`, `OSError`, any `Exception`) as secondary;
  - always run raw-note cleanup and `reset_research_for_retry`;
  - re-raise the **original** exception, recording the handler failure without masking it;
  - add regression tests injecting `PathViolation`/`OSError` into the receipt and event writes. Each asserts
    the original exception propagates, the question is back in `queued`, no scaffold remains, and the
    evidence gates are unchanged.

  Optional and separate: stamp `run_id`/`task_id` into new snapshot frontmatter.

## Finalization verification of the provenance repair (2026-09-22) — historical: the pre-commit state

**Verdict: no blocker to committing the provenance repair.** Verification and status updates only; nothing
staged, committed or pushed; no Scout run, retry, curator or research. Phase 6 / Gate D remain
**incomplete**. Branch `testing` at `3c02397` (= `origin/testing`).

- **397 passed, 1 skipped**; `ruff check .` and `ruff check src tests scripts` both clean; `git diff --check`
  clean; untracked `tests/test_failed_run_provenance.py` and `RUN-4e9d910742.md` whitespace-clean.
- **Change-set integrity, checked by hashes rather than `git status`:** the DB, all 12 files under
  `Failed_Runs/` and `Source_Snapshots/2026-09-21/`, the tracked `git diff`, and every modified or untracked
  change-set file were sha256-hashed before verification and matched afterwards. `db/brain.sqlite` =
  `6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29`.
- **Scope review:** the code diff touches only `live_discovery.py` and `executor.py`; no change to source
  minimums, the 5-source cap, validators, tiers, prompts or the model ladder. The receipt and all 5 snapshots
  were read in full: public arXiv abstract pages only.
- **Snapshot integrity (intact, not authorship):** for all 5, `content_hash` recomputes exactly from the
  LF-normalised body *including* its final newline (on disk the files are CRLF because `write_text` runs on
  Windows); filename prefixes and `url_hash` also match. This proves integrity, not which run wrote them;
  the link to `RUN-4e9d910742` stays **probable**.
- **Separate follow-up, required before the next production Scout run** (new build task, needs approval):
  make `_fail_closed_discovery` catch non-`OSError` failures from the receipt write and its event, always run
  cleanup and the reset to `queued`, and re-raise the *original* exception, with `PathViolation` and
  `OSError` injection tests. Optional: stamp `run_id`/`task_id` into new snapshot frontmatter.
- **Proposed commit scope (later, separately approved):**
  - **A, the fix:** both source files, both test files, `PLAN.md`, `SESSION_HANDOFF.md`.
  - **B, historical evidence as-is:** `RUN-4e9d910742.md` and the 5 snapshots. No backfill; the commit
    message calls the lineage "probable". Precedent: `46728a7`.
- **Commit-stage cautions:**
  - There is no `.gitattributes` and `core.autocrlf=true`, so stored blobs will be LF. After staging, compare
    the sha256 of the `git cat-file blob :<path>` output with the on-disk sha256 and decide explicitly on
    normalisation. `content_hash` is defined over the LF body, so it stays verifiable either way.
  - The snapshots contain trailing whitespace that is part of the captured content and covered by the hash:
    never whitespace-fix them. There are no pre-commit hooks.

## Failure-receipt provenance defect fixed (2026-09-20, later)

**397 passed, 1 skipped (re-verified 2026-09-22 after the review follow-up; 396 at the
original fix); Ruff clean on `.` and on `src tests scripts`; `git diff --check` clean.**
The failed-run receipt and five `2026-09-21` snapshots were hash-checked before and after
the follow-up and are unchanged. Production
`db/brain.sqlite` byte-identical across the whole session at sha256
`6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29` (this is the
**post-run** hash; the older `43fa24b0…` is the pre-run baseline and is now historical —
the database legitimately changed when `RUN-4e9d910742` wrote its audit rows, which must
not be discarded). Everything is **unstaged**; nothing committed, pushed or merged.
**No Scout child run, no curator, no other research question was executed.** Phase 6
remains **incomplete**.

**Root cause — two defects sharing one gap.**

1. **Candidate evidence was attached to an exception class, not to the run.**
   `_fail_closed_discovery` built the receipt's `Detail` from
   `{"task_id", "created_scaffold", **getattr(error, "detail", {})}`. Only
   `InsufficientUpstreamSources` defines `.detail`; `QwenValidationError` carries
   `.attempts` and no `.detail`, so the spread contributed nothing and, whenever a receipt
   *was* written for a post-fetch failure (Qwen validation, write_note, a path violation
   raised by the run's own writes), it named no source and no snapshot.
2. **`snapshot_path` / `snapshot_sha256` were read but never written.** `executor.py`
   read both off each source dict, but `_source_from_fetch` only ever interpolated the
   path into an `evidence` string — it never set the keys. So **even the sparse-source
   path** recorded `null` for both. `tests/test_upstream_minimum.py` asserted only that
   the key was *present*, which `None` satisfies; that is why a green suite carried this.

**The fix (smallest robust change, 2 source files).**

- `src/quant_brain/discovery/live_discovery.py` — `_source_from_fetch` takes
  `snapshot_sha256` and sets both `snapshot_path` and `snapshot_sha256` as real keys. The
  hash is computed at the call site from the same `content` `save_source_snapshot` hashes,
  so it is identical by construction and the filename's 12-char prefix stays a cross-check.
- `src/quant_brain/research/executor.py` — new shared `candidate_evidence()` helper (one
  definition, used by both failure paths, so they cannot describe candidates differently);
  provenance captured **once at the discover stage** into `discovered_provenance` and
  passed to `_fail_closed_discovery` as `run_provenance`, merged **beneath**
  `error.detail` so `InsufficientUpstreamSources` keeps precedence.

**Why capture at the discover stage:** a *successful* model call rebinds
`sources = list(model_result.output["sources"])`, so reading `sources` at failure time
would describe a later `write_note` failure with model-shaped values instead of what
discovery actually fetched. Capturing early pins the classifier tier and the canonical
fetched URL regardless of which later stage fails. This is covered by its own test.

**`QwenValidationError` was deliberately left untouched.** Giving it a `detail` would
require `qwen_call` — which knows nothing about snapshots — to carry per-source
provenance, inverting a boundary the codebase maintains. The executor-side keyword covers
the *contents* of every receipt the fail-closed path writes, whatever the exception type.

**How future failures retain lineage — receipt contents, not receipt creation.** This fix
improves what a receipt says **when the receipt is successfully written**; it does not
change whether one is written. For a discovery failure after the discover stage, a written
receipt now contains `run_id`, `task_id`, `research_id`, `stage`, `error_type`,
`accepted_candidates` (url / title / tier / snapshot_path / snapshot_sha256),
`snapshot_paths`, `distinct_upstream_count`, `required_upstream_count`,
`rejected_candidates` and `search_query_expression` — enough to reconstruct the run without
directory dates or manual inference (verified by building the receipt the real run
*should* have written, in an isolated scratch project). For a failure inside discovery,
before a `DiscoverResult` exists, the receipt carries `run_id`/`task_id`/`research_id`/
`stage`/`error_type` and the error text, and **no** candidate or snapshot fields (absent,
not empty) — covered by its own test.

**Receipt creation is still not guaranteed (unchanged, pre-existing).**
`_fail_closed_discovery` catches only `OSError` around the receipt write, and the receipt
is written only once a task has loaded. So: (i) an `OSError` writing the receipt leaves no
receipt (cleanup and reset still run); (ii) a `PathViolation` from `resolve_write` on the
`Failed_Runs` path — or any other non-`OSError` from the write or its event — escapes the
handler, skipping raw-note cleanup and the `queued` reset, and replaces the original
exception (which survives only as `__context__`); (iii) a failure before the task loads
(e.g. an unknown `research_id`) writes no receipt by design. None of this was fixed here.

**Regression coverage — `tests/test_failed_run_provenance.py` (6 new tests):** the reported
Qwen-validation defect; the recorded hash verified against the filename prefix and the
snapshot's own frontmatter; fail-closed containment unchanged; a later-stage failure
keeping discovery-side values rather than model-shaped ones; an early discovery failure
(valid task, real live backend raising `LiveDiscoveryError` before any `DiscoverResult`)
that spies on the real `_fail_closed_discovery` to prove it runs once at stage `discover`,
propagates the original exception object, and writes a receipt with run/task/research/
stage/error but no candidate or snapshot fields; and an unknown `research_id`, which
writes no receipt because no task ever loads.
`tests/test_upstream_minimum.py` was strengthened from key-presence to non-null values.
**Mutation-checked:** temporarily removing the two keys fails 4 of these tests, so they
genuinely detect the defect rather than merely passing alongside it.

**Review follow-up (2026-09-22).** An independent review found two issues, both now
resolved: (1) the original early-failure test used an unknown `research_id`, so it failed
before a task loaded and never reached `_fail_closed_discovery` or the provenance
carrier — it was renamed to say what it actually pins, and the valid-task test above was
added (mutation-checked: seeding `discovered_provenance` with an empty
`accepted_candidates` fails it); (2) this file and `PLAN.md` implied every failure now
writes a complete receipt — corrected above to distinguish receipt *contents* from
receipt *creation*. No production code changed in the follow-up.

**Nothing weakened.** No change to prompts, the model ladder, validators, source tiers,
`MIN_UPSTREAM_SOURCES`, the 5-source cap, curator controls, snapshot-before-model ordering,
or the cleanup sequence. The sparse path's **contract** is preserved (same keys, same
semantics, same behavior); its **contents** necessarily change, because two fields that
were always `null` now hold real values — it is not byte-identical, and claiming so would
be wrong.

**The existing receipt was NOT backfilled, and that is deliberate.** An earlier assessment
called the attribution "deterministically provable". That was an overclaim. The evidence is
strong but circumstantial: `TASK-a679b61436` is the only `discovery` task ever recorded;
all five `captured_at` values (00:57:54–00:58:03 UTC) fall strictly inside the run's event
span (00:57:30–01:00:18 UTC); and every `content_hash` recomputes exactly from its snapshot
body. **None of that proves authorship** — content hashes prove *integrity*, not which
process wrote the file. An identical snapshot could come from a standalone script or an
unrecorded invocation; the files carry no `run_id` and no event references a path. The
brief permits backfill only when deterministically proven, so
`brain/00_Inbox/Failed_Runs/RUN-4e9d910742.md` is **unchanged**. The association is
recorded here as **probable**, with that limitation stated. The tiers reported for those
five URLs are **re-derived** by running the current `classify_source` now — not recovered
runtime records.

**Remaining limitations.** (a) The five existing snapshots stay without machine-readable
lineage; only *future* runs get it. (b) The fix records provenance in the receipt, not in
`agent_events` — a reader still needs the receipt file. (c) Snapshot frontmatter still
carries no `run_id`; linking a loose snapshot back to a run remains inferential. (d) The
unsuitable-relevance blocker for `RQ-6d9c12f4` is untouched and unresolved. (e) Receipt
*creation* is not guaranteed — see "Receipt creation is still not guaranteed" above.

**Next decision is Jason's:** review this unstaged change set; then choose whether to widen
the lane set toward sources that document RSI exit rules, stamp `run_id` into snapshot
frontmatter as a follow-up, or accept the relevance gap as the finding. Do **not** lower
`MIN_UPSTREAM_SOURCES` or relax extractive support.

## First Scout child run executed — research acceptance FAILED, fail-closed safeguards verified (2026-09-20)

**Verdict: Scout research acceptance failed; fail-closed safeguards verified.** The first
Research Scout child run ever executed under PROP-003 ran end to end for `RQ-6d9c12f4`
only, and stopped at the Qwen validation gate. **This is not Gate D or Phase 6 progress on
the research question** — it is the first evidence that the production path's safety
machinery works on live material.

**Precisely what was and was not written.** Nothing was promoted. No validated raw
research note and no curator recommendation were produced. But the run was not
write-free: it wrote durable task and event audit rows (`agent_tasks` +1,
`agent_events` +9), a failed-run receipt, and five source snapshots. An earlier draft of
this section said "nothing durable was written", which was wrong.

> **Correction (2026-09-20, later).** This section originally stated that the five
> snapshots' provenance "survives in `agent_events`". **It does not.** All nine event
> payloads were re-inspected: they carry `S1`–`S5` opaque labels, model/prompt/response
> hashes and validator reasons, and **no source URL, no snapshot path and no content
> hash**. The snapshot files likewise carry no `run_id` or `task_id`. The original failure
> path preserved **no explicit run-to-snapshot lineage**; the snapshot *content* remains on
> disk, but nothing machine-readable ties those files to this run. That defect has since
> been fixed in code — see the 2026-09-20 provenance-fix section above this one.

**Run:** `RUN-4e9d910742` / `TASK-a679b61436`, branch `testing` at `3c02397`, 2026-09-20
19:57:30–20:00:18 local (168s). Exit 1 with traceback, by design.

```bash
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4
```

**Pre-run baseline (all verified):** 391 passed / 1 skipped; Ruff clean on `.` and on
`src tests scripts`; tree clean; `origin/testing` == local. `agent_reach_check.py` exit 0
(`exa_search` off, `github` warn/usable, `arxiv` usable, `web`/Jina ok).
`gate_readiness.py --research-id RQ-6d9c12f4` exit **0** with **3** candidate URLs. The
dry run was verified genuinely inert: sha256, schema hash, all 40 schema objects and every
row count byte-identical before and after.

**What the Scout actually found.** The live path retrieved **5 distinct arXiv works** —
more than the probe's 3, because the probe passes `limit=min_sources=3` while the live run
uses the agent's `max_sources: 5`. All five classify `primary` via the unmodified
structural `arxiv-abs` signal. All five were fetched through Jina and snapshotted before
any model call:

| Work | Title |
|---|---|
| `arxiv.org/abs/1411.5062` | Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit |
| `arxiv.org/abs/2309.16008` | Optimal Entry and Exit with Signature in Statistical Arbitrage |
| `arxiv.org/abs/1601.04210` | Speculative Futures Trading under Mean Reversion |
| `arxiv.org/abs/1707.03498` | Mean Reversion Trading with Sequential Deadlines and Transaction Costs |
| `arxiv.org/abs/0911.1921` | Diagnostics of Rational Expectation Financial Bubbles… |

The ≥3-source bar was **cleared** (5 distinct works, re-derived independently with
`distinct_upstream_keys`, not trusted from the printed count). The run failed later, at
extraction.

**Why it failed — the validators were right.** The full bounded ladder ran and all three
attempts failed deterministic validation:

| Attempt | Model | Duration | Validator reasons |
|---|---|---|---|
| 1 | `qwen3:14b` | 51.8s | invented `research_id: R1`; omitted all 5 supplied sources; cited `<missing>` sources |
| 2 (repair) | `qwen3:14b` | 14.3s | still omitted all 5; still `<missing>` citations |
| 3 (escalation) | `qwen3.8:27b` | 69.4s | used S5, but `quote:S5: exact evidence is absent from snapshot`; `ungrounded-promotion:S5: main_claim asserts a strategy/performance claim that is not an exact passage of the snapshot` |

**This was verified as a true positive, not validator over-strictness.** The snapshots
contain **zero** standalone occurrences of `RSI` and **zero** of `ETF`. `RQ-6d9c12f4` asks
for source-supported exit rules pairing with daily ETF RSI-oversold entries; arXiv returned
continuous-time optimal-stopping theory on Ornstein-Uhlenbeck processes. The 27B's
ungrounded main_claim was papering over exactly that gap, and the Gate B extractive-support
rule blocked it.

**Attributing the failure precisely** (an earlier draft said "not a model defect and not a
lane fault", which was too generous on both counts):

- **The decisive research blocker was unsuitable source relevance.** Even a perfect
  extraction could not have produced ETF RSI exit rules from these five papers.
- **The models also produced genuinely invalid outputs** — an invented `research_id`
  (`R1`), all five supplied sources omitted, citations to `<missing>` sources, and finally
  an evidence quotation absent from the snapshot. Those are real model failures, separate
  from the relevance gap.
- **The validators and the fail-closed runtime handled those outputs correctly.** Every
  invalid output was caught and none reached a durable note.
- **The arXiv lane operated as designed.** It searched, returned real `primary`-tier
  works, and fetched them. Its *topical coverage* was unsuitable for this particular
  question — a property of what arXiv indexes, not a malfunction.

**Fail-closed behavior verified against evidence, not assumed:**
- Event trail complete and correct for the model-validation path: `dispatch_started →
  discovery_started → qwen_attempt ×3 → discovery_failed → failed_run_written →
  handler_failed → dispatch_failed` (9 events). No `discovery_candidates_rejected` —
  nothing was rejected pre-fetch.
- Per-attempt audit intact: model, duration, prompt hash, response hash, validator verdict
  and reasons recorded for all three attempts.
- `agent_tasks` row finalized `failed` with the error text; `output_path` NULL.
- Raw-note scaffold **removed** — no `Raw_Research/RQ-6d9c12f4.md` exists.
- `RQ-6d9c12f4` reset to `queued` with `raw_note_path` NULL. `RQ-c920baeb` and
  `RQ-80be8cf7` untouched and still `queued`.
- **No curator recommendation was produced or acted on.** No curator was dispatched.

**Protected tables unchanged** (before → after): `strategy_cards` 0→0, `backtests` 0→0,
`price_datasets` 0→0, `reviews` 0→0, `research_findings` 7→7, `notes` 23→23, `sources` 7→7,
`chunks` 260→260, `embeddings` 260→260, `research_questions` 7→7. No `external_*` tables.
Only `agent_tasks` 3→4 and `agent_events` 49→58 changed, as a dispatch must.

**Post-run verification:** 391 passed / 1 skipped; Ruff clean on both invocations.

**Defect found — the Failed_Runs receipt is thin on this path.** The receipt
`brain/00_Inbox/Failed_Runs/RUN-4e9d910742.md` records id, research_id, `stage:
qwen_extract`, the error string and a retry command — but its `Detail` JSON contains only
`task_id` and `created_scaffold`. It records **no source URLs, tiers, snapshot paths or
snapshot hashes**, because `_fail_closed_discovery` populated that block from
`getattr(error, "detail", {})` and `QwenValidationError` carries no `detail` attribute —
only `InsufficientUpstreamSources` does. Consequence: the five snapshots on disk are
**not referenced by the receipt or by any event**, so a reader cannot machine-verify what
was fetched. **This has since been fixed in code — see the provenance-fix section above.**

**Unstaged artifacts left for review (nothing staged, committed or pushed):**
- `brain/00_Inbox/Failed_Runs/RUN-4e9d910742.md`
- `brain/00_Inbox/Source_Snapshots/2026-09-21/` — 5 files whose **content** remains on
  disk, each self-describing with url/title/captured_at/content_hash. Their association
  with `RUN-4e9d910742` is **probable, not established**: no artifact records the linkage
  (see the attribution limitation in the provenance-fix section).

**Date skew, not an inconsistency:** the run executed on **2026-09-20 local time**
(19:57–20:00), while the snapshot directory is named **`2026-09-21`** because snapshot
paths are derived from UTC (`snapshot_relative_path` uses `datetime.now(UTC)`). The
`agent_events` timestamps are UTC too, which is why they read `00:57–01:00`.

**Limitations.** (a) One run of one question; Phase 6's exit gate requires all three child
runs and remains **incomplete**. (b) A passing extraction was never demonstrated, so the
success path of the production Scout is still unproven end to end. (c) The question-to-
literature relevance gap is unresolved and is not fixable by retrying the same lane.

**Next decision is Jason's.** The options, none of which were taken here: (1) accept the
relevance gap as the finding and widen the lane set toward documentation/practitioner
sources that actually discuss RSI exit rules; (2) authorize a receipt-completeness fix so
`QwenValidationError` carries candidate evidence into `Failed_Runs`; (3) retain sources
manually through the external intake and verify their upstream works; (4) re-run the same
question unchanged, which on this evidence would be expected to fail the same way. Do
**not** lower `MIN_UPSTREAM_SOURCES` or relax the extractive-support rule — the bar was
cleared; the grounding was not.

## Gate D partially unblocked — arXiv lane added, no child run (2026-09-19)

**Gate D remains NOT executed.** One of three child questions is now probe-ready; the other two are honestly still blocked. PROP-003 was committed at `cddd3d84d3849e445c2d227f824bb5b9206c5c85` and pushed to `origin/testing`, followed by the documentation commit `30630a0cb8d4559372ca6430812ceb78cd20fd91`. `origin/testing` was fetched and verified at `30630a0`, matching local `HEAD`. `main` remains untouched at `51979f6`; nothing was merged and no branch was created. Post-change verification on the committed tree: **391 passed, 1 skipped**, Ruff clean on `.` and on `src tests scripts`, working tree clean, and `db/brain.sqlite` unchanged at sha256 `43fa24b0c7c7e92d08760404774cb872d5b4530080d8a7ac6a677bafed3069bb`; the production invariants below remain unchanged.

**Starting state, verified live at `51979f6`:** `gate_readiness.py` exited **4** with **0 candidate URLs** for all three children. Only `search_exa` and `search_github` could turn a question into URLs (`agent_reach.py`, `SEARCH_CHANNELS = ("exa_search",)`). Exa is `off` by Jason's decision; GitHub is authenticated and working but searches *code repositories* — `gh search repos "RSI exit rules backtest"` returns `[]`. The plan's "web search" was never implemented as search: `fetch_web(self, url)` takes one already-known URL and has no query parameter. RSS/YouTube have no search code at all. `SEARCH_LANES` was decorative — `operational_lanes()` was never called from `src/`.

**What changed (PROP-003, approved before implementation).**
1. **`src/quant_brain/discovery/arxiv_search.py`** — an independent zero-account lane over arXiv's free Atom API, with its own hardened transport: fixed HTTPS host, explicit timeout and User-Agent, bounded read, DOCTYPE/entity rejection, redirects refused outright, strict arXiv-host validation on every identifier, and canonical `https://arxiv.org/abs/<id>` output. A valid empty feed returns `[]`; malformed or oversized responses raise. It is **not** gated on the Agent Reach `web`/Jina channel — conflating the two would misreport *why* discovery failed.
2. **One deterministic query transformation** (`build_arxiv_query`) applied identically to every question, recorded in the run and in any receipt. **No per-question tuning.** A three-phrase conjunction returned 0 for all three questions; two phrases is the measured rule.
3. **The ≥3-source bar is now enforced in the pipeline.** It previously lived only in `gate_readiness.py` (a read-only probe) and Phase 6 prose — `executor.py` checked only `if not sources`, i.e. ≥1. It is now counted over **distinct normalized upstream works**, not `len(sources)`, with one shared `MIN_UPSTREAM_SOURCES` constant imported by the probe so the two cannot drift.
4. **Sparse results are quarantined, never promoted.** Below the minimum the run fails closed **before** any raw note is written, and the existing `_write_failed_run_note` path records canonical URLs, tiers, snapshot paths/hashes, actual/required counts, the generated query and follow-up guidance — with **no `raw_saved` note and no curator recommendation**.

**Verified results.** **391 passed, 1 skipped**; Ruff clean on `.` and on `src tests scripts`.

| Question | unique URLs | `gate_readiness` exit |
|---|---|---|
| RQ-6d9c12f4 exit rules | 3 | **0 — ready** |
| RQ-c920baeb max holding period | 1 | 4 — still blocked |
| RQ-80be8cf7 costs/slippage | 1 | 4 — still blocked |

RQ-6d9c12f4's three candidates are distinct `primary`-tier works (`arxiv.org/abs/1411.5062`, `/2309.16008`, `/1601.04210`) from the generated expression `all:"mean reversion" AND all:"exit"`. **No query was tuned to produce this.** The two blocked questions are a finding about reachable literature, not a lane fault — arXiv indexes academic preprints, and "maximum holding-period caps" and practitioner cost conventions are largely documented elsewhere.

**Independent review: APPROVED**, after finding two real defects in the first implementation, both fixed and regression-tested:
- **P2 — `/pdf/` and `/abs/` of one paper counted as separate works**, so three links to a single paper satisfied the floor of 3. `canonical_abs_url` now reduces both renderings (and a `.pdf` extension) to one identity.
- **P2 — a bare trailing `v` split one work in two** (`v\d+$` required a digit). Now `v\d*$`.
- P3s also fixed: an arXiv transport failure no longer reads as "the literature is empty" (the reason is retained and reported), and the generated query is now recorded even when a caller injects its own `search_fn`. Redirects are refused outright rather than checked at the final hop, since `geturl()` cannot see a chain that leaves the host and returns.

**Production invariants unchanged:** `strategy_cards`/`backtests`/`price_datasets`/`reviews` all **0**; no `external_*` tables; all three RQs still `queued` with `raw_note_path NULL`; `db/brain.sqlite` byte-identical after every readiness probe.

**Known limitations.** (a) arXiv is academic-only, so documentation and practitioner questions may still find nothing — that is the honest reason two questions remain blocked. (b) The lane is a *search* addition only; caps, tiers, validators, the curator threshold and snapshot-before-model are untouched. (c) A run reaching exactly 3 sources still has to pass every downstream gate; probe-ready is not evidence.

**Next decision is Jason's:** whether to authorize a single Research Scout child run for `RQ-6d9c12f4` only. That is a separate authorization and was deliberately not taken here.

## External intake merged to `main` (2026-09-19)

The independently approved external-research intake and its documentation correction were fast-forwarded to `main` at `75b51c9` and pushed. `main` and `testing` are being kept synchronized; Gate D remains blocked and was not executed. The next authorized activity requires a new bounded Gate D brief and prerequisite check, not a strategy or backtest.

## P1 quotation defect corrected and re-reviewed — committed to `testing` (2026-09-19)

The substring-matching blocker is fixed, independently re-reviewed and **APPROVED**, and the intake feature is committed on `testing`. **350 passed, 1 skipped**; Ruff clean on `.` and on `src tests scripts`.

**What the bug was.** `normalized()` collapsed whitespace but applied no token boundaries, so `quote in normalized(body)` was a raw substring test. `Exit when RSI > 5` matched source text `Exit when RSI > 50 or after 10 trading days.` Reproduced end-to-end: `quote_match`/`full_rule_match` true, `approve_scope` accepted, and the curator handoff carried `evidence: "Exit when RSI > 5"` — a threshold the source never states. Not automatic promotion (an attributed reviewer must approve scope), but it defeated the exact-quotation safeguard, whose whole promise is that evidence is the verbatim source span. Truncation at *either* edge did it, not only the reported prefix case.

**Why it mattered in plain terms.** Exiting at RSI > 50 is an ordinary mean-reversion exit; exiting at RSI > 5 would exit on nearly every bar — a different strategy. The one number defining the rule could be silently wrong in material handed to the curator while still passing an "exact quotation" check.

**The correction.** A boundary-safe `source_span()` helper in `external_verification.py`, used by all three matching sites: verification, `approve_scope` and `handoff`. A span must begin and end on a token boundary; a severed word or number is refused. Clean partial quotation stays legitimate (`Exit when RSI > 50` ends on a boundary and still matches). Text matching stays separate from full-rule and contextual assessment — `full_rule_match` remains its own `claim == quote` check, and reviewer scope judgement is unchanged.

**Stale cache closed.** `verify_claim` returns a cached `evaluations` row *before* matching runs, and `UNIQUE(claim_id,fetch_id)` prevents a corrected row replacing it, so a catalog verified under the old rule keeps `quote_match: true` permanently. Fixing the matcher alone was therefore insufficient: `approve_scope` and `handoff` now **re-derive** the check from the pinned snapshot instead of trusting the stored flag. Cached rows stay immutable (append-only history preserved, no schema change). A stale flag can still *display* as matched; it cannot approve or promote. `verify --force --allow-network` refreshes recorded values.

**Two further defects were found in the fix itself by re-review, and corrected.** (1) The first boundary rule was asymmetric — it guarded a quote ending in `.`/`,` before a digit but left the mirror case open, so `Threshold is 1` matched `1,250` (a 1250× misstatement) and `Win rate 0` matched `0.55`. Tellingly, `Threshold is 1,` was rejected while the *more* misleading `Threshold is 1` passed. Now symmetric over `.,:/%-` plus typographic separators, severing only when digits sit on both sides. (2) The character class was ASCII-only, letting the original defect back in via fullwidth (`５０`→`５`) or Arabic-Indic digits; now `str.isalnum()`, so the alnum test and `str.isdigit()` agree across scripts. The em dash is deliberately **not** a joiner: a dash census over the 18 real snapshots found en dash binding numeric ranges 25 times and em dash 0 times, while including it falsely rejected `It rose 20` from `It rose 20— then fell.`

**Verification.** 350 passed/1 skipped; Ruff clean. Recomputing all 18 evaluations in the real demo catalog under the corrected matcher gives **identical verdicts** — 4 quote matches, 0 full-rule matches, zero changed — so `acceptance.json` counts are unchanged and no legitimate quotation was penalized. Handoff on an isolated copy returns `[]`. All mutation-capable work used a scratchpad copy; `C:/Users/jason/quant-agent-brain-intake/exit-rules-final/external.sqlite` is byte-identical (sha256 `20ebc695…`). Production untouched: `strategy_cards`/`backtests`/`price_datasets`/`reviews` all 0, no `external_*` tables in `db/brain.sqlite`, `RQ-6d9c12f4` still `queued` with `raw_note_path NULL`, `gate_readiness.py --research-id RQ-6d9c12f4` still exits **4** with `brain.sqlite` byte-identical after the run.

**Known limitations.** (a) An em-dash-bound numeric range truncates undetected — a documented trade-off with 0 observed instances in the corpus. (b) `source_span` is a boundary check only: clipping a complete, meaning-bearing token (`Exit when RSI > 50` out of `...50 unless volume is below average`) matches by design; the safeguard there is `full_rule_match` plus the attributed reviewer's scope judgement, not the matcher. (c) Review attribution is a name, not authentication. **Gate D is not advanced and was not executed.**

## Verified closeout / limits

- Only `main` and `testing` exist. The intake feature and documentation correction were **merged to `main` and pushed** at `75b51c9` after independent re-review and approval.
- Final verification: **350 passed, 1 skipped**, Ruff clean. (The 321/1 figure below predates the P1 correction and its regression tests.)
- Canonical demo: `C:/Users/jason/quant-agent-brain-intake/exit-rules-final/acceptance.json`. All three PDFs extracted; 18 claims/citation leads, 17 distinct targets (not independent works). Counts of fetch outcomes below are per claim, not network calls. Final catalog reuses hash-checked snapshots from the earlier live run with original timestamps and reuse provenance. Both reimport and offline replay verified idempotent.
- 47 protected production files, question rows and tracked entity counts unchanged. No trusted promotion, Gate D, strategy or backtest executed.
- Automatic parsing is conservative: ChatGPT's unstructured sections remain citation leads requiring manual claim-to-source mapping. Four quote matches do not constitute four supported full exit rules. Handoff is empty; no evidence threshold was relaxed.
- Review role is attributed, not authenticated: this local CLI cannot establish that a reviewer is human. Source matching preserves operators but does not prove context or profitability. Do not call this production-ready before an independent review.
- Workflow and small learning note: `brain/_system/external_intake_workflow.md`.


> **External research intake implemented locally 2026-09-18 (branch `testing`, not merged).** A bounded retention lane for manually-collected external reports. **321 passed, 1 skipped**; Ruff clean. **Gate D was NOT executed and is NOT advanced.** `RQ-6d9c12f4` remains `queued` with `raw_note_path NULL`; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0; `db/brain.sqlite` has no `external_*` tables; `scripts/gate_readiness.py --research-id RQ-6d9c12f4` still exits **4**.
>
> **What it does.** `scripts/external_intake.py` retains original PDFs, native `pypdf` text, per-report citations, deduplicated source targets and an append-only per-claim review history in an **isolated workspace database outside the repository and vault** (the workspace guard refuses any path inside either). Retention is not trust: a claim enters as `unreviewed_lead`, a deterministic verifier can only move it to `partially_supported`/`unresolved`/`blocked`, and **only an attributed reviewer scope review can set `supported_in_scope`** — which is the sole state the curator handoff will offer. The handoff builds its payload from the exact verified source span, not the report's transcription, and still has to pass the existing unmodified `promotion_block_reason`.
>
> **Real run over Jason's three reports:** 3 reports, 18 claims, **17 distinct targets** (ChartSchool is cited by 2 reports and counted once — repeated citation is not corroboration). Live verification: 13 fetched, 1 access-blocked, 3 content-rejected, 1 no-URL. **4 quotations located, 0 full-rule matches, so the curator handoff is correctly empty.** Two DOI/SSRN sources sit behind access walls and are parked with reasons, never circumvented. Re-importing all three is a no-op; re-verifying without `--allow-network` replays from cached snapshots in <1s.
>
> **Reproduce:**
> ```
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo import "<pdf>" --provider <name> --research-id RQ-6d9c12f4
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo verify --allow-network --limit 20
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo leads
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo handoff
> ```
>
> Governance: **PROP-002** in `brain/_system/plan/plan_change_proposals.md` (accepted, authorized before implementation) plus the §5 amendment in `PLAN.md`. Still needing separate approval: OCR/further extraction deps, relaxing the ≥3-source bar, and any production promotion.
>
> **Gate D attempted 2026-09-17 — BLOCKED, no child question executed.** Prerequisites were checked before any run. `RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7` remain `queued` with no raw note; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0. **284 passed, 1 skipped**; Ruff clean. Work is on `testing`, **not merged to `main`**.
>
> **Three code defects found and fixed.** (1) `default_runner` decoded subprocess output with the locale codec (`cp1252`) while `agent-reach doctor --json` emits UTF-8 — the `UnicodeDecodeError` fired on subprocess's reader thread, nulled `stdout`, and surfaced as a misleading `TypeError`. Every live discovery call was broken on this machine. (2) The adapter looked for channels `"search"`/`"exa"`; the real doctor key is `exa_search`, so the Exa lane could never be selected. The recorded fixture repeated the same invented names — which is why a green suite carried this through a whole gate. (3) `plan_queries` sent the full 440-character question to `gh search`, which rejects long queries as malformed, misreporting a query error as an empty result.
>
> **The blocker is not a defect and was not fixed:** `exa_search` reports `status: "off"` — mcporter installed, Exa not configured, no config and no `EXA_*` env vars. That is Jason's decision; project code must never call `agent-reach`/`mcporter configure`.
>
> **Say the blocker precisely.** It is *not* "no usable lane". `github` is `warn`, which the code correctly treats as usable, so discovery would run **GitHub-only** — the sweep Gate C exists to prevent. The blocker is that the only lane able to answer these questions is `off`, GitHub returns **0 results for all three children**, and Phase 6 requires **≥3 upstream sources per raw note**.
>
> **Reproduce:** `uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4` → exit **4**. Read-only: no fetch, no snapshot, no model, and `db/brain.sqlite` is byte-identical afterwards. The general `agent_reach_check.py` exits **0**, correctly — GitHub genuinely is usable, and a lane is not unhealthy merely because it suits a question poorly. **Do not mistake that 0 for Gate D readiness.**
>
> **Gate C verified 2026-09-16.** Bounded source acquisition now discriminates by credibility before spending a fetch or a model call. `discovery/source_quality.py` makes the written Tier A/B/C/D policy executable (structural host/path signals + allowlists + a commercial-intent reject detector that runs first); `discovery/acquisition.py` adds normalize → dedupe → classify → rank → budget plus a 600-char/120-word content floor. The central unlock: live discovery previously hardcoded `source_quality="discovery-only"` while the curator only promotes `primary`/`practitioner`, so the live path could never promote anything it found. Tiers are now assigned discovery-side, the only correct placement given the validators' protected-field guard. **269 passed, 1 skipped**; Ruff clean on both invocations. PR #3 was merged first (`2a876f7`). The three child questions remain **queued** — Gate C ran none of them.
>
> Acceptance demonstration: `uv run python scripts/acquisition_report.py` — zero network, finds 3 primary + 1 practitioner, rejects promotional material pre-fetch and a cookie banner post-fetch/pre-model, collapses a cross-channel duplicate, exits non-zero on any failed check.
>
> **Gate D is next and requires Jason's explicit authorization.**
>
> **Gate B verified 2026-09-11.** The production live Research Scout passes fetched snapshots through `quant_brain.llm.qwen_call`: qwen3:14b at temperature 0/schema mode, deterministic validation, exactly one 14B repair, qwen3.8:27b escalation, then structured fail closed. Every attempt records model, duration, prompt/response SHA-256 hashes, and validator verdict/reasons in `agent_events`. Durable promotion requires fully extractive main claims and strategy rules; late write failures restore/delete notes consistently; dispatcher validation failures finalize tasks as failed. Hermetic and adversarial tests pass (**201 passed, 1 skipped**), with full-tree/scoped Ruff clean. Phase 6 remains pending; Gate C is next.
>
> **Gate A verified 2026-09-07.** Desktop `main` was safely fast-forwarded from `f053341` to merged PR #1 commit `feaa84e86db5b435cf12a21d65e7e924cd116bbb`, then the pre-existing tracked and untracked work was reapplied. The exact backup directory is `C:\Users\jason\quant-agent-brain-gate-a-backup-20260907-171959`; it contains `tracked-worktree.patch`, `tracked-index.patch`, `untracked.tar.gz`, `untracked-list.txt`, `head-before.txt`, `status-before.z`, and related inventory files. The backup branch and retained stash also preserve the pre-integration state.
>
> The reviewed PR implementation is the production Scout path: registry/dispatcher → `quant_brain.discovery` → recommendation only. Pre-existing untracked `src/quant_brain/research/live_*.py` and dashboard files remain preserved as experimental local work; they are not a competing accepted architecture.
>
> `RQ-66078766` remains an **experimental audit receipt**, including raw research, rejected curator review, source snapshots, failed-run material, and decision log. The real child queue remains untouched: `RQ-6d9c12f4`, `RQ-c920baeb`, and `RQ-80be8cf7`. Do not execute them until the later roadmap gate is explicitly approved.
>
> Gate A verification: `uv sync --extra dev` succeeded; full pytest passed (`149 passed, 1 skipped`); Ruff passed with immutable failed-run audit artifacts explicitly excluded in `pyproject.toml` (maintained `src`, `tests`, and `scripts` remain lint-clean); discovery registry and child dry-run resolved to `research_scout`; Agent Reach health was inspectable, with web/RSS/Bilibili healthy and optional-channel warnings/off states. No research, strategy card, backtest, paper trade, remote push, or remote merge was performed.
>
> **Read `PLAN.md` first.** It remains the master architecture source of truth. Use `.hermes/plans/2026-09-07_171423-research-to-paper-trading-roadmap.md` for the gated execution sequence, and do not silently rewrite master phases.

Use this file to resume work in a new Hermes session without reloading the full conversation.

## Project Path

`C:\Users\jason\OneDrive\Desktop\quant-agent-brain`

## Current Goal

Build a budget-first, local-first agentic quant research/backtesting second-brain system that showcases AI/ML skills without overengineering or creating an agent for every tiny task.

Core idea:

```text
research structure + RAG structure + controlled work packets
```

## User Preferences For This Project

- Move slowly, one verified step at a time.
- Avoid overengineering.
- Do not delegate an agent for every small thing.
- Prefer local/free tools first.
- Use paid/cloud models only for escalation/review later.
- Build like a serious quant research workflow: evidence first, backtests second, review before any paper trading.
- No live trading.

## What Has Been Built

### 1. Project foundation

- `pyproject.toml`
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `.env.example`
- `src/quant_brain/`
- `tests/`

Python uses `uv`.

Latest verified test count:

```text
396 passed
1 skipped
```

(Was 391/1 before the 2026-09-20 provenance fix added 5 regression tests.)

### 2. SQLite database

Database path:

```text
db/brain.sqlite
```

Schema/init code:

```text
src/quant_brain/db/schema.sql
src/quant_brain/db/init_db.py
```

Important tables:

```text
notes
sources
chunks
embeddings
research_questions
research_findings
strategy_cards
price_datasets
backtests
metrics
reviews
agent_tasks
retrieval_log
```

### 3. Market data foundation — historical claim, not current capability

Earlier handoffs claimed market-data downloader/registry modules and downloaded SPY/QQQ/IWM data. Those modules are not present in the reconciled source tree, and the current database has **`price_datasets = 0`**. Do not infer that usable price files or registrations exist. Roadmap **Gate F** owns restoring reproducible files, provider/date/calendar/adjustment metadata, checksums, and SQLite registrations before any backtest.

### 4. Research intake system

Files:

```text
src/quant_brain/research/intake.py
scripts/research_intake.py
brain/_system/research_intake_workflow.md
```

Creates research questions and briefs.

Existing research task:

```text
RQ-4ddd4ef4
Question: Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data
Status: curated
```

### 5. Research Scout runner/executor

Files:

```text
src/quant_brain/research/scout_runner.py
scripts/research_scout_runner.py
src/quant_brain/research/executor.py
scripts/research_executor.py
agents/research_scout.md
```

Output raw research note:

```text
brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
```

The first executor is intentionally conservative and deterministic, not a web crawler yet.

### 6. Curator promotion/executor

Files:

```text
src/quant_brain/curation/promotion.py
scripts/curator_promotion.py
src/quant_brain/curation/executor.py
scripts/curator_executor.py
agents/knowledge_curator.md
```

Curated `RQ-4ddd4ef4` and promoted 5 source notes:

```text
brain/01_Sources/web/SRC-df1769724d-relative-strength-index-rsi-investopedia-overview.md
brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md
brain/01_Sources/docs/SRC-7691c731ac-quantconnect-glossary-survivorship-bias.md
brain/01_Sources/docs/SRC-26d92ac325-backtesting-py-documentation.md
brain/01_Sources/docs/SRC-022c5bed68-vectorbt-documentation.md
```

Curator review:

```text
brain/00_Inbox/Curator_Reviews/RQ-4ddd4ef4-curated.md
```

### 7. Markdown indexer

Files:

```text
src/quant_brain/indexing/markdown_indexer.py
scripts/index_markdown.py
brain/_system/markdown_indexer_workflow.md
```

Indexes Markdown notes into:

```text
notes
chunks
```

Current indexed count at last run:

```text
23 Markdown files
260 chunks
```

### 8. Embedding indexer

Files:

```text
src/quant_brain/indexing/embeddings.py
scripts/embed_chunks.py
brain/_system/embedding_indexer_workflow.md
```

Uses real local semantic embeddings through Ollama:

```text
nomic-embed-text
768 dimensions
```

The deterministic `local-hash-embedding-v1` backend remains available only as an offline/test fallback.

Current embedding count at last run:

```text
260 embeddings
0 pending chunks
```

Later scaling options:

```text
Ollama mxbai-embed-large
sentence-transformers/all-MiniLM-L6-v2
LanceDB or Chroma
```

### 9. Retrieval context builder

Files:

```text
src/quant_brain/retrieval/context_builder.py
scripts/build_context.py
brain/_system/retrieval_context_builder_workflow.md
```

Builds an agent-ready evidence packet:

```text
query
source path
heading
chunk id
score
chunk text
rules to cite evidence and avoid guessing
```

### 10. Agent work packet builder

Files:

```text
src/quant_brain/agents/work_packet.py
scripts/build_work_packet.py
brain/_system/agent_work_packet_builder_workflow.md
```

Creates work packets with:

```text
agent role
specific task
retrieved context
allowed read paths
allowed write paths
output contract
guardrails
```

Latest sample packet:

```text
brain/00_Inbox/Work_Packets/WP-3818c6a760-knowledge_curator.md
```

It asked the Knowledge Curator to review whether lookahead bias should update the validation checklist.

### 11. Deterministic Work Packet Executor

Files:

```text
src/quant_brain/agents/executor.py
scripts/execute_work_packet.py
tests/test_work_packet_executor.py
brain/_system/work_packet_executor_workflow.md
```

The first executor is intentionally narrow and deterministic. It:

```text
parses one bounded packet
→ verifies retrieved evidence
→ enforces project-relative allowed write paths
→ writes a cited Markdown result
→ validates path + heading citations
→ updates agent_tasks running/completed/failed state
```

Unsupported tasks fail closed instead of receiving a fabricated generic answer. No local or cloud model is called yet.

Verified real execution:

```text
Packet: WP-3818c6a760
Status: completed
Output: brain/00_Inbox/Curator_Reviews/WP-3818c6a760-result.md
Citations validated: 1
```

The Markdown indexer was also hardened for repeated identical heading/text sections inside one note. Duplicate occurrences now receive distinct chunk IDs instead of raising a SQLite uniqueness error.

### 12. Canonical Pre-Backtest Validation Checklist

File:

```text
brain/_system/pre_backtest_validation_checklist.md
```

The completed work-packet recommendation was reviewed and promoted into a short system checklist. Version 1 contains one evidence-backed gate only:

```text
confirm all signal inputs were available at decision time
→ close-based signals execute no earlier than the next bar unless timing proves otherwise
→ failing configurations stop before performance is reported
```

The checklist cites the curated QuantConnect lookahead-bias source. It intentionally does not add speculative validation rules yet.

### 13. First Strategy Door

File:

```text
brain/02_Strategy_Doors/DOOR-etf-mean-reversion.md
```

The door maps the daily SPY/QQQ/IWM ETF mean-reversion family without creating a strategy card. It currently identifies RSI oversold rebound as the only candidate with enough support for another focused research pass.

### 14. Focused RSI Definition Research

Research task:

```text
RQ-17a4103d
Status: curated
```

New curated sources:

```text
brain/01_Sources/docs/SRC-1ea110cb46-stockcharts-chartschool-relative-strength-index-rsi.md
brain/01_Sources/docs/SRC-89c682a686-ta-lib-documentation-relative-strength-index-rsi.md
```

This pass captured Wilder's formula and bounded the entry-condition research space to:

```text
RSI(14) below 30 at the close
RSI(2) below 20 at the close
next-bar entry for either candidate
```

It did not find enough evidence to approve an exit rule or maximum holding period, so no strategy card or backtest was created.

A follow-up task was originally queued, then used only by the preserved experimental
live-research work described below. It is not a production acceptance receipt:

```text
RQ-dd7da469
Question: Find source-supported exit conditions, maximum holding periods, timing/regime risks, and fixed cost assumptions for the bounded RSI candidates.
Current artifact status: rejected (experimental history; not accepted)
```

### 15. Agent Reach Live-Research Connection

Canonical repository:

```text
https://github.com/Panniantong/Agent-Reach
```

Verified local connection:

```text
Version: 1.5.0
Clone: C:/Users/jason/Projects/Agent-Reach-review
Executable: C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe
Obsidian skill: C:/Users/jason/OneDrive/Desktop/memory_vault/Agents/skills/agent-reach/SKILL.md
```

Agent Reach is now named in `AGENTS.md`, the Research Scout role, and generated Research Scout prompts. It is used as a discovery router for web pages, YouTube transcripts, GitHub, RSS, and social leads. Durable notes cite upstream sources rather than Agent Reach itself.

### 16. Cross-Asset Quant Research Universe and Quality Gate

Files:

```text
brain/80_Summaries/quant-research-universe.md
brain/_system/research_source_quality_policy.md
brain/_system/citations/quant-universe-ledger.json
```

The grounded scan used official institutional research, trading-firm pages, practitioner interviews, and YouTube transcripts from AQR, Man Group/Man AHL, Two Sigma, HRT, Jane Street, Wintermute, BlackRock, Aspect Capital, and J.P. Morgan.

The project is explicitly open to:

```text
equities and ETFs
futures / rates / FX / commodities
options and volatility
crypto and digital assets
factor/style premia
systematic macro and trend following
statistical arbitrage / relative value / mean reversion
market making and liquidity
alternative data / machine learning
portfolio construction and risk allocation
```

This is a research universe, not an approval list. The curator now promotes only `primary` or `practitioner` source-quality items; `discovery-only` material can create leads but cannot independently enter durable source notes. The policy rejects untraceable returns, screenshots without rules/data/costs, copied summaries, hidden assumptions, and invented citations.

### 17. Local Qwen Research Evaluation

Files:

```text
src/quant_brain/research/model_eval.py
scripts/evaluate_research_model.py
tests/test_research_model_eval.py
brain/00_Inbox/Model_Evaluations/qwen-research-evaluation.md
brain/00_Inbox/Model_Evaluations/qwen3-14b-research-eval-v4.json
brain/00_Inbox/Model_Evaluations/qwen3.8-27b-research-eval-v2.json
brain/_system/local_qwen_research_policy.md
```

Models and hardware:

```text
qwen3:14b       9.3 GB
qwen3.8:27b    17 GB
GPU: NVIDIA GeForce RTX 5070, 12 GB VRAM
```

Final bounded evaluation results:

```text
qwen3:14b      3/3 passed, 17.740 seconds total, 2 cases repaired
qwen3.8:27b   3/3 passed, 123.972 seconds total, 0 cases repaired
```

The cases tested missing-evidence honesty, slop rejection, and cross-asset source-grounded mapping. A stronger validator caught a direct contradiction in an early 14B answer; one bounded repair corrected it. Therefore 14B is approved only as the default evidence-processing worker behind schema, source-ID, validator, and one-repair gates. The slower 27B model is the escalation/reviewer.

### 18. Experimental Local History — Not Production

The following files and run records are preserved because they are useful audit history.
They were pre-existing untracked local work when Gate A was reconciled. They do **not**
replace, extend, or prove acceptance of the registry/dispatcher architecture in `PLAN.md`.

#### Experimental live-research prototype

Files:

```text
src/quant_brain/research/live_discovery.py
src/quant_brain/research/live_worker.py
src/quant_brain/research/live_executor.py
scripts/live_research_executor.py
brain/_system/live_research_executor_workflow.md
```

The prototype attempted this bounded flow:

```text
Agent Reach health check
→ upstream web search
→ deterministic dedupe/ranking
→ Jina source snapshots + hashes
→ bounded Qwen 14B extraction
→ exact source/URL/quote validation
→ one repair
→ Qwen 27B escalation
→ raw research note
→ curator gate
→ ordered SQLite events
```

Experimental rejected run (not an acceptance run):

```text
Research: RQ-dd7da469
Run: RUN-rsi-exit-live-v5
Sources fetched: 3
Qwen 14B: two exact-quote validation failures
Qwen 27B: passed validation
Curator: rejected all 3 discovery-only sources
```

The rejection is retained as quality-gate evidence only. It did not accept the Scout,
promote sources, resolve the RSI evidence gaps, or authorize another stage.

#### Experimental operations dashboard

Files:

```text
src/quant_brain/ops/events.py
src/quant_brain/ops/dashboard.py
scripts/serve_agent_dashboard.py
ui/agent_dashboard.html
brain/_system/agent_operations_dashboard_workflow.md
brain/07_Decision_Log/DEC-agent-operations-dashboard.md
```

Historical prototype launch command:

```bash
uv run python scripts/serve_agent_dashboard.py
```

Local URL:

```text
http://127.0.0.1:8765
```

This dashboard is preserved experimental UI. It is not the production interface, not a
Gate A deliverable, and not part of the canonical execution path.

## Canonical Current Architecture

`PLAN.md` is authoritative. Gate A recognizes only this production Scout path:

```text
agent registry + typed capability
→ dispatcher selects research_scout
→ quant_brain.discovery performs the bounded discovery task
→ validated output
→ recommendation only
→ harness/human decides whether any later task is authorized
```

The `src/quant_brain/research/live_*.py` modules, experimental dashboard, and their
workflows are outside that path. Do not package, promote, or describe them as current
production. As of 2026-09-16 they live on `preserve/live-research-and-dashboard-20260916`
and are no longer in the working tree — being on a branch does not make them accepted.

## Merged Checkpoint (2026-09-15)

Gate B was merged to `main` as `fb3ecc3` (PR #2). Local `main` is synchronized with it by
fast-forward; the merge introduced no upstream edits, so the accepted Gate A/B code is
byte-identical to the reviewed checkpoint. Recovery tag: `pre-gatec-reconcile-20260915`.

Verified after reconciliation: 210 passed / 1 skipped, Ruff clean on both invocations,
child RQs queued, `RQ-66078766` rejected, and `strategy_cards` / `backtests` /
`price_datasets` / `reviews` all zero. (That 210 included 13 experimental tests — see
the test-baseline note below.)

### Deliberately uncommitted work — resolved 2026-09-16

The working tree is now clean. Everything previously held back has been classified and
routed. Decision note:
[brain/07_Decision_Log/DEC-2026-09-16-phase-3-indexing-checkpoint.md](brain/07_Decision_Log/DEC-2026-09-16-phase-3-indexing-checkpoint.md).

- **Phase 3 semantic-RAG edits** — reviewed on their own merits and **accepted** on
  `phase-3/indexing-and-retrieval-eval` (`b236175`), PR open and **awaiting Jason's approval;
  not merged**. Excludes `Source_Snapshots` from the index, removes a retrieval fixture that
  was *unreachable* (its target lives in the excluded `_system/`, so it could never be
  retrieved), and makes a dimension mismatch raise instead of returning an empty list.
  Re-verified: Recall@1 0.71, Recall@5 1.00, MRR 0.790 across 7 now-reachable fixtures.
- **Gate C-adjacent scaffolding** — `src/quant_brain/research/live_{discovery,executor,worker}.py`,
  `src/quant_brain/ops/dashboard.py`, `ui/`, `scripts/{live_research_executor,serve_agent_dashboard,gate_b_live_smoke}.py`
  and their 4 test files. **Preserved** on `preserve/live-research-and-dashboard-20260916`
  (`7a7209e`), pushed. Audit history only — never reviewed in PR #2, not the accepted
  architecture, not to be merged.
- `.hermes/` and `src/quant_agent_brain.egg-info/` are now gitignored; the egg-info was
  untracked with `git rm --cached` (files remain on disk). It is regenerated by every
  editable install and produced diff noise unrelated to any real change.

Promoting any preserved work into production requires its own reviewed change, not a
carry-over from this reconciliation.

### Test baseline — read this before comparing numbers

The **210 passed** figure recorded for the Gate B merge included 13 tests from the
then-untracked experimental files. The tracked-only baseline at that commit was
**197 passed, 1 skipped**. With the Phase 3 branch's `tests/test_retrieval_eval.py` (2 tests)
the current tracked baseline is **199 passed, 1 skipped**. The experimental tests now live on
the preserve branch and no longer inflate a run on `main`.

### Known issue — `retrieval_eval.py --compare` is broken

It compares the semantic backend against the `local-hash-embedding-v1` baseline, but the hash
vectors are absent from `db/brain.sqlite` (only `nomic-embed-text@768`), despite the Phase 3
design note saying to keep them for this purpose — most likely lost to the documented
re-index-drops-embeddings behavior. **Pre-existing, not caused by the Phase 3 branch**; it
previously failed *silently* as recall 0.00 and now raises. Fixing it requires re-embedding
every chunk under the hash model, which writes to the database — deliberately not done. The
single-model run that gates Phase 3 is unaffected.

## Gate Status and Resume Rule

Gate A reconciliation, Gate B / master-plan Phase 5, and Gate C are complete. **Gate D was
authorized and attempted on 2026-09-17, and is blocked on an unconfigured search lane — not
on authorization.** No child question was executed; all three remain `queued`.

**Re-attempting Gate D requires a usable search lane that can answer documentation and
academic questions.** That is Jason's decision: Exa is a third-party service, and he has
said to enable it only if it is genuinely free with no API key. Project code must never run
`agent-reach`/`mcporter configure`. Before assuming the blocker still stands, run
`uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4` — exit 4 means still
blocked, exit 0 means the lanes can now reach the minimum.

When a lane is available, Gate D runs the three child research questions one at a time, in
order: `RQ-6d9c12f4` (exit rules), `RQ-c920baeb` (maximum holding periods), `RQ-80be8cf7`
(commission/slippage). Each needs its own dispatch, snapshot set, validated raw note, event
trail, and a **separately dispatched** curator verdict, with tests run before the next child
starts. Zero promotions is an acceptable outcome.

Nothing here authorizes a strategy card, market-data download, backtest, or paper trading.
Follow the explicit gated roadmap and do not infer a production step from the experimental
run history. Until Gate D is authorized, preserve `RQ-6d9c12f4`, `RQ-c920baeb`, and
`RQ-80be8cf7` in `queued` without executing them.

### Acquisition lane status (Gate C)

| Lane | Status | Notes |
|---|---|---|
| Exa via mcporter | declared operational, **currently off** | Primary search channel. `exa_search` reports `status: off` (Exa not configured) as of 2026-09-17 — this is the Gate D blocker |
| GitHub via `gh` | operational | Top-up only when search is short of the cap |
| arXiv `/abs/` | **operational since 2026-09-19** (PROP-003) | Now a real search lane over the free public Atom API — zero account, no key, own hardened transport, not routed through Agent Reach. Academic preprints only. Still no PDF parser; `/pdf/` links are canonicalized to `/abs/`. (Was: fixture-only rewrite of hits already found.) |
| YouTube, RSS | deferred | Declared so doctor output maps cleanly; never dispatched |
| Reddit, X, Facebook, Instagram, XiaoHongShu, LinkedIn | never | Login-backed; appear in no lane |

## Commands To Verify State

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q
uv run ruff check . --no-cache
uv run ruff check src tests scripts
uv run python -m quant_brain.harness.registry --task-type discovery --json
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4 --dry-run

# Gate C acceptance demonstration (offline, no database writes)
uv run python scripts/acquisition_report.py

# Which lanes are usable right now? (exit 0 = at least one; 3 = none)
uv run python scripts/agent_reach_check.py

# Can those lanes answer a specific question? (exit 0 = ready; 4 = not)
uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4
```

## Important Design Rule

Do not overengineer. This is not yet a fully autonomous AI quant firm. Build reliable primitives first:

```text
queue → evidence → curation → retrieval → bounded work packets → review
```

Only add more automation after the loop is verified.
