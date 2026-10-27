# Backtest workbench plan (proposed 2026-10-26, for Jason's approval)

## Why
Jason wants to test strategies as often as he likes, under many conditions, with each run starting from a clean slate, rather than feeling limited to one test. The trading logic stays **pure code**: no AI decides trades. The only limited resource is a final yes/no on data nobody has looked at, and this plan makes even that reusable a few times, honestly.

## The three kinds of data
| Data | Use | Limit |
|---|---|---|
| Practice: 2019–2024 MNQ/MES minute bars (dev partition) | Explore, compare, stress-test | **Unlimited.** Every run is logged and counted. |
| Exam: 2025-01-01..2026-10-21 (still unread) | Final yes/no for a finalist | **Pass/fail proctor with a small budget** (W8) |
| Forward: from today on | Paper-trading check of real fills | Continuous; no real money |

## What gets built
| # | Piece | Plain English | Done when |
|---|---|---|---|
| W1 | **Strategy plug-in format** | A strategy is a small, fixed code module: entry rule, exit rule, settings. SC-FUT-0001's ORB becomes the first plug-in. | ORB plug-in reproduces the SC-FUT-0001 development results to the cent |
| W2 | **Conditions grid** | One click runs a strategy across markets (MNQ, MES), each year, calm vs volatile periods (classified using only past data), cost levels L1–L4 plus missed fills, and fixed vs volume roll. | Grid results match single runs; volatility regimes use no future information |
| W3 | **Robustness neighbours** | Small nudges to a setting (e.g. stop 8/10/12% of ATR, range 10/15/20 min) show whether a result is a fragile peak or a broad plateau. Every nudge counts as a trial. | Neighbour runs are logged as trials |
| W4 | **Walk-forward** | For strategies with tunable settings: choose settings on earlier years, test on the next months, roll forward. Only the out-of-sample pieces are scored. | No window ever sees its own test months |
| W5 | **Luck checks on every run** | Random entries (same stop, costs, timing rules) and resampling are shown next to every result, as on the Study page. | Reused from SC-FUT-0001 code |
| W6 | **Honesty counter** | Every run is logged with a fingerprint of its code and settings. The workbench counts how many variations of a strategy family were tried and **raises the pass bar automatically** (deflated Sharpe / multiple-testing haircut). The page says, e.g., "14 variations tried; the bar is now p < 0.004". | Counter can't be reset by deleting results; identical re-runs are recognised, not double-counted |
| W7 | **Clean-slate runs + cache** | Each run starts fresh from committed code plus a settings file. Re-running the same thing gives the identical answer instantly from cache. | Same fingerprint → same result |
| W8 | **Exam proctor (reusable holdout)** | Holds the 2025–26 data. Accepts only frozen strategies, answers **only pass/fail** (no numbers or charts), with a little noise, and a **budget of 3 checks**, each with a stricter bar (Dwork et al., *Science* 2015, "the reusable holdout"). Each use needs Jason's OK. | Proctor never reveals more than one bit per check; budget enforced and logged |
| W9 | **Workbench page in the UI** | Pick a strategy and conditions → a year × cost heat-map, the luck band, robustness chart, honesty counter and day replay, with a plain-English summary on top. | Jason can run and read a grid without a terminal |
| W10 | *(later)* **Paper-trading feed** | Records live MNQ data and what the frozen code would have done, with no orders sent, for a forward check of fills. | Separate plan; needs data-feed choice |

**Order:** W1 → W7 → W2 → W5 → W6 → W9 (the usable core), then W3/W4 as strategies need them, W8 before the next exam, and W10 later. Estimate 3–4 sessions for the core.

## Safety rules (unchanged)
- No live trading and no broker connection. Purchases (more markets' data, data feeds) only with Jason's decision.
- The exam data is only reachable through the proctor; the workbench refuses exam dates.
- The engine stays deterministic code; agents build, test and explain, but never trade.

## Decisions for Jason
1. **Proctor budget:** recommend **3** pass/fail checks for the 2025–26 exam, each stricter than the last.
2. **Markets:** start with MNQ and MES (data already owned). More markets (ES, NQ, CL, GC…) need a separate data purchase decision.
3. **Approve this plan** to start with W1.
