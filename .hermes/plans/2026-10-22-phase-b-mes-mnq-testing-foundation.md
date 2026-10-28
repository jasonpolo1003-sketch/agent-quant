# Phase B Plan — MES/MNQ Testing Foundation

> **Historical approved foundation plan.** Preserve this for provenance. Later scoped plans, frozen strategy cards, and `SESSION_HANDOFF.md` govern the current implementation; this document is not authorization to rerun tests, spend data credits, or trade.

**Status:** Approved for implementation after independent quant and engineering review
**Review outcome:** Quant PASS; Engineering PASS; no unresolved material findings
**Scope:** Research/backtest/simulation only. No live-money routing, sizing, authorization, or order transmission.
**Primary market:** MES
**Controlled comparison:** MNQ
**Strategy question:** Can a frozen opening-range-breakout (ORB) rule survive realistic execution and beat a preregistered random-anchor control?

## 1. What success means

Phase B succeeds only if we produce a deterministic and reproducible futures replay system that:

1. knows which MES/MNQ contract and trading session applied at every historical timestamp;
2. handles America/New_York and America/Chicago time, DST, holidays, early closes, expiry, and roll rules without guessing;
3. models versioned funded-account flatten rules, including the relevant 4:08–4:10 PM ET window where supported by dated evidence;
4. accounts for commissions, exchange/regulatory fees, bid/ask spread, slippage, fill uncertainty, and adverse execution;
5. rejects incomplete, ambiguous, stale, duplicate, out-of-order, or unsupported data;
6. passes synthetic and invariant tests before any paid market data is acquired;
7. freezes one MES-primary ORB falsification experiment before results are viewed;
8. treats MNQ as one controlled comparison, not another parameter-search space;
9. records enough provenance to reproduce every result from code commit, experiment hash, data hash, calendar/rule version, and cost model;
10. can honestly return **reject / inconclusive / survives this test**, never “proven profitable.”

## 2. Architecture: extend, do not corrupt the existing daily engine

The current `backtest/engine.py` is a daily, adjusted-equity engine. Phase B should not force intraday futures semantics into it. Build a separate futures replay path while reusing existing immutable manifests, frozen-card concepts, ledgers, and reporting patterns.

Proposed boundaries:

```text
src/quant_brain/futures/
  models.py            typed Bar, Contract, Session, Order, Fill, Position, RuleVersion
  reference_data.py    effective-dated contracts, expiries, holidays, early closes, rule provenance
  session_clock.py     UTC/local conversion, trading-date assignment, session boundaries, DST
  data.py              minute-bar normalization, validation, hashing, manifests, quarantine
  execution.py         deterministic order/fill simulation and scenario models
  account.py           position/P&L state, limits, forced-flatten rules
  replay.py            deterministic event loop and event ordering
  costs.py             commissions, fees, spread/slippage scenarios, L3 cost gate
  validation.py        fail-closed preflight and run invariants

src/quant_brain/experiments/
  orb.py               frozen ORB signal logic and random-anchor control
  futures_runner.py    preregistered run, append-only ledger, artifacts, verdict

config/reference/futures/
  contracts.*          MES/MNQ multiplier, tick, expiry, first/last trade, source
  sessions.*           regular/overnight sessions, holidays, early closes, source
  account_rules.*      effective-dated forced-flatten and account restrictions

config/experiments/
  ORB-0001.*           frozen experiment specification
```

All reference records use bitemporal provenance: timezone-aware half-open valid-time intervals, `published_at`/`observed_at`, `retrieved_at`, immutable version ID, source URL/document, page/section where available, and content hash. One fail-closed resolver applies explicit source precedence and the experiment's frozen as-of cutoff. Unknown, overlapping, not-yet-known, retroactively corrected, or conflicting records are not silently resolved; the affected run is blocked or quarantined.

## 3. Build sequence and gates

### Work package B0 — Freeze replay, temporal, numeric, and persistence contracts

Define these contracts before the domain model is fixed:

- immutable event envelope with UTC event time, UTC availability time, stable source sequence/event ID, event type, and payload hash;
- exact bar timestamp convention (interval-open or interval-close) and the time at which a completed bar becomes observable;
- total ordering for equal-time events, including bar publication, session transition, signal, order activation, cancellation, fill, risk action, and forced flatten;
- idempotency and duplicate-event policy independent of provider row order or container iteration order;
- integer ticks and integer minor-currency units (or one explicitly approved fixed-point alternative), including multiplier use, fee rounding, mark-to-market rounding, and aggregation order;
- byte-specified canonical serialization for scientific hashes;
- deterministic run identity and crash-safe states: `CREATED`, `RUNNING`, `FAILED`, `COMPLETED`;
- run-scoped staging, hash/referential-integrity validation, and atomic publication of one final manifest; only that manifest can mark a run complete;
- retry and concurrent-start behavior that cannot duplicate fills or produce two completed versions of the same run.

**Gate B0:** permutation tests for equal-time inputs, duplicate-event tests, exact numeric reconciliation, canonical cross-process serialization, and failure injection around persistence all pass.

### Work package B1 — Typed domain model and reference-data format

Build immutable typed records for contracts, sessions, rule versions, bars, orders, fills, positions, and cost scenarios.

Required behavior:
- represent timestamps internally as timezone-aware UTC;
- preserve exchange/local timestamps for audit output;
- prohibit naive datetimes;
- distinguish calendar date, trading date, contract, and continuous symbol;
- version external rules by effective date;
- include multiplier, tick size/value, currency, and contract identity;
- use the exact numeric and serialization contract frozen in B0;
- resolve all effective-dated inputs through the single bitemporal resolver;
- validate non-overlapping half-open intervals, boundary inclusivity, timezone, source precedence, as-of availability, and complete provenance.

**Gate B1:** malformed, overlapping, missing, provenance-free, not-yet-known, or ambiguously revised rules fail validation. Boundary, gap, conflict, and retroactive-correction fixtures pass.

### Work package B2 — Contract calendar and continuous-series policy

Build the historical MES/MNQ contract calendar from official or otherwise explicitly ranked sources.

Required behavior:
- store actual contract identities; never backtest a provider continuous symbol as if it were executable;
- represent expiry and exceptional dates explicitly rather than assuming “third Friday”;
- define a roll-selection rule using information available at the time;
- preserve raw contract prices; no equity-style dividend adjustment;
- map provider symbols to actual contracts with effective dates;
- record why a contract was selected on every trading date.

Use individually delivered contracts and freeze the exact non-hindsight MES/MNQ roll rule before ORB-0001 is hashed. Specify the prior-session observable-data cutoff, first eligible roll date, tie/missing-data behavior, treatment of roll sessions, and source-data hashes. One actual contract must supply the range, signal, quote, order, and fill for an entire strategy trading date; no same-day completed information may choose that day's contract.

**Gate B2:** every replayed bar maps to exactly one known tradable contract; gaps/ambiguity block the run.

### Work package B3 — Session clock

Implement deterministic conversion among UTC, America/Chicago, and America/New_York and assign every event to the proper futures trading date.

Cover:
- overnight session boundaries;
- RTH/opening range definition;
- spring/fall DST transitions;
- holidays and early closes;
- session maintenance breaks;
- missing expected minutes and extra unexpected minutes;
- session-specific flatten deadlines.

**Gate B3:** synthetic DST, holiday, early-close, and session-boundary cases all pass; no naive timestamp enters replay.

### Work package B4 — Intraday data intake and validation

Add a minute-futures dataset type separate from daily Yahoo data.

Validate:
- schema, units, timestamp timezone, and bar interval;
- OHLC consistency, positive prices, nonnegative volume;
- duplicates, out-of-order rows, contract mixing, missing minutes, bars outside known sessions;
- requested versus delivered date/symbol/schema range;
- immutable file hash and canonical content hash;
- provider metadata and exact request parameters.

Classify expected exchange closures separately from provider/data gaps. Quarantine questionable sessions instead of imputing them silently.

Before requesting a quote, map every permitted order, trigger, spread, and fill claim to the required provider fields and timestamp semantics. Quote-aware claims require quote-aware data. If the purchased schema cannot observe spread, queue, or intrabar chronology, use preregistered conservative modeled bounds, label them as modeled, and classify unsupported cases as non-evaluable rather than inventing precision.

**Gate B4:** invalid or ambiguous data cannot be loaded into the experiment runner.

### Work package B5 — Deterministic replay, execution, and account state

Create one event-ordering policy, document it, and test it. At minimum it must define when bars become observable, when signals may be formed, when orders become eligible, how intrabar ambiguity is treated, and when flatten events override strategy events.

Execution scenarios:
1. **baseline conservative** — explicit spread, fees, commission, and slippage;
2. **adverse** — worse spread/slippage and unfavorable ambiguous-bar ordering;
3. **stress** — elevated costs/fill degradation used by the L3 gate.

Required behavior:
- no fill at information unavailable at order time;
- market/stop/limit rules match minute-data limits;
- gap-through stops fill adversely, not at an impossible stop price;
- ambiguous same-bar target/stop paths resolve conservatively or mark unknown;
- no unmodeled partial fills; either implement an evidence-backed model or conservatively define all-or-none behavior and disclose it;
- mark-to-market P&L uses futures multiplier and tick rules;
- flatten events cancel pending orders and close positions by the configured deadline;
- no position survives an applicable forced-flatten deadline.
- define the last order-submission and eligible-fill instant so flattening is completed before, never at or after, the applicable deadline;
- distinguish observed execution inputs from conservative modeled assumptions in every fill artifact.

**Gate B5:** an independent hand-worked reference implementation matches golden fixtures exactly.

### Work package B6 — Costs and L3 cost gate

Represent costs as components rather than one opaque bps number:
- broker commission;
- exchange, clearing, and regulatory fees;
- half-spread on entry/exit;
- slippage in ticks;
- fill degradation/adverse selection;
- any account/platform charges reported separately from per-trade economics.

Every value needs units, direction, effective dates, provenance, and a conservative fallback. Missing required cost data blocks the run.

L3 report must show gross and net results under baseline, adverse, and stress scenarios and attribute the difference by cost component.

**Gate B6:** if the result only works under unrealistically favorable or zero-cost execution, it fails L3.

### Work package B7 — Synthetic verification

Before paid data, create compact synthetic fixtures covering:
- normal MES and MNQ sessions;
- both DST changes;
- holiday closure and early close;
- expiry exception and contract roll;
- missing, duplicate, and out-of-order minutes;
- incorrect provider symbol mapping;
- entry on range break, false break, no-trade day;
- spread/slippage and tick rounding;
- stop/target collision in one bar;
- gap-through stop;
- flatten deadline with open position and pending order;
- fee change by effective date;
- long and short P&L;
- rejected naive timestamps and unknown rules.
- equal-timestamp event permutations and duplicated source events;
- effective-date boundaries, source conflicts, and not-yet-published corrections;
- numeric threshold boundaries, large notionals, and repeated fee rounding;
- crash/failure injection after every persistence step, truncated artifacts, duplicate starts, retries, and concurrent starts;
- migration from a populated pre-Phase-B database plus unsupported-version and rollback/recovery cases.

Test layers:
- unit tests per module;
- property/invariant tests for clocks, P&L, and order state;
- golden end-to-end sessions with hand-computed outputs;
- second-implementation cross-check for the frozen primary rule;
- full regression suite and lint/type/static checks already used by the repository.
- Linux and Windows CI with pinned timezone data and identical clock/hash fixtures;
- a generated-data benchmark at expected multi-contract minute/event scale, including roll periods, quarantines, and artifact generation, with frozen runtime and peak-memory ceilings before B9.

Core invariants:
- no look-ahead;
- cash/P&L reconciliation after every event;
- fills align to tick size and known contract;
- exactly-once event processing;
- deterministic result for identical inputs;
- no open position past mandatory flatten;
- no accepted run with unknown calendar/cost/data state.

Persistence/integration requirement: futures datasets, runs, and artifacts use an isolated, versioned namespace and typed repository interfaces. Legacy daily schemas/readers remain unchanged. Forward migration, unsupported-version refusal, and rollback/recovery behavior must be documented and tested; daily and futures loaders must reject each other's data.

**Gate B7:** all synthetic tests, cross-platform checks, migration/daily golden regressions, determinism replays, and the representative-scale benchmark pass before pricing/download approval.

### Work package B8 — Freeze ORB-0001 before viewing outcomes

The quant reviewer must approve the exact specification before real results are exposed.

Freeze:
- MES primary and MNQ controlled comparison roles;
- exact opening-range window and timezone/session definition;
- entry, stop, target, timeout, flatten, and no-reentry rules;
- permitted direction(s) and maximum trades/day;
- position normalization used only for comparable research reporting, not live sizing;
- in-sample/held-out/walk-forward boundaries;
- excluded/quarantined-session policy;
- baseline/adverse/stress cost scenarios;
- economic-event treatment (include, exclude, or label) chosen in advance;
- random-anchor control generation, seeds, eligible windows, and equal trade opportunity;
- trial/multiple-testing budget;
- minimum sample/effective-day requirements;
- exactly one MES primary endpoint net of baseline costs, its sampling unit, and an economically meaningful minimum effect;
- the exact confidence/randomization procedure and dependence handling (date-level paired analysis and block resampling or another pre-approved dependence-aware method);
- rejection, inconclusive, and survives-this-test thresholds tied to that primary endpoint;
- negative-result policy: accept it without retuning ORB-0001.

The random-anchor control must freeze range length, eligible anchors, decision/fill timing, remaining holding opportunity, event-day treatment, and a paired-by-trading-date construction. Use a preregistered randomization distribution or fixed multi-seed ensemble summarized at the trading-date level; anchors are not independent trials. It tests whether opening anchoring adds net economic value relative to this declared control. It does **not** by itself prove that the open contains unique information.

All explored directions, windows, seeds/ensembles, cost scenarios, walk-forward slices, and MNQ comparison are entered in one explicit multiple-testing ledger; correlated outputs cannot be presented as independent confirmation. Adverse/stress scenarios diagnose robustness but cannot replace the primary endpoint.

The same frozen rule algebra applies to MES and MNQ, with only preregistered ex-ante instrument scaling and no MNQ-specific retuning. Report per-contract and preregistered risk-normalized economics separately, including integer-contract implications. The primary verdict is determined by MES alone. MNQ is a comparison, counts in the trial ledger, and cannot rescue or redefine a failed MES result.

Keep two conclusions separate:

1. **instrument-level strategy evidence** under explicitly labeled execution and flatten scenarios;
2. **venue/account feasibility**, which may be claimed only if an exact venue/product and effective-dated rule version are selected and every material path-dependent rule (drawdown, daily loss, consistency, position limits, restricted periods, liquidation, quantity/sizing) is modeled.

If no exact venue/account is selected, Phase B makes no funded-evaluation-readiness claim; the 4:08–4:10 PM ET behavior remains a versioned hypothetical/account-rule scenario, not a universal fact.

**Gate B8:** hash and commit the frozen spec and review sign-off before real outcome execution.

### Work package B9 — Databento quote and approval gate

Only after B1–B8 infrastructure is ready:
1. define exact dataset, schema, symbols/symbology, contracts, date range, and fields;
2. price the request using Databento’s current estimator/API;
3. show expected size, cost, credit use, and known coverage limitations to Jason;
4. obtain explicit approval;
5. download exactly the approved request—no broader pull.

**Gate B9:** no paid download or billing action without explicit user approval.

### Work package B10 — Execute once, report honestly

Run frozen ORB-0001 through the approved data:
- preflight and hash all inputs;
- append `started` before computation;
- run MES primary first under the frozen design;
- run MNQ only as the preregistered comparison;
- run the random-anchor control and cost scenarios;
- write machine-readable trades/events, cost attribution, exclusions, and decision report;
- preserve negative evidence and unknowns;
- do not retune after seeing the held-out result.

Possible conclusions:
- **reject** — fails economic/statistical/cost robustness criteria;
- **inconclusive** — insufficient or ambiguous evidence;
- **survives this test** — merits another separately preregistered phase, but is not proven and not authorized for live trading.

## 4. Reproducibility artifacts

Every completed run must record:
- Git commit and dirty-tree check;
- frozen experiment file and SHA-256;
- raw file and canonical data hashes;
- provider request/response metadata;
- calendar, contract-map, account-rule, and cost-rule versions/hashes;
- timezone database/runtime versions;
- deterministic seeds;
- validation/quarantine report;
- event/fill/trade ledger;
- gross/net metrics and cost attribution;
- MES and MNQ results kept visibly separate;
- random-anchor results;
- final decision and failed criteria.
- declared dependency closure and proof that relevant tracked/untracked files were clean;
- lockfile hash, Python implementation/version, packages, platform, pinned timezone-data hash/version, schema versions, and serializer version;
- final atomic run manifest linking all artifacts and hashes.

The dependency closure includes code, strategy specification, reference/config data, migrations, schemas, runner, lockfile, and serializer. Preflight rejects dirty or untracked inputs in that closure. Two fresh-process runs from the same immutable bundle must produce byte-identical canonical event, fill, trade, and metric artifacts; volatile operational metadata is kept outside those scientific hashes.

## 5. Two independent review tracks

### Quant-trader reviewer

Review before coding and again before ORB-0001 is frozen. The reviewer must answer:
- Does the design model an actually tradable MES/MNQ contract at each point in time?
- Is every signal based only on information then available?
- Are session, roll, expiry, holiday, and flatten assumptions historically valid?
- Are minute-bar fills limited to what minute data can support?
- Are costs/fills conservative enough to avoid a fake edge?
- Is the random-anchor control economically comparable and does it test whether the open is special?
- Is MES truly primary and MNQ only one controlled comparison?
- Are trial counts, sample-size rules, and decision thresholds honest?
- Can we accept a negative result without parameter hunting?
- Do the outputs answer the project goal: reliable evidence for research/simulation, not permission for live trading?

Material quant objections block experiment execution.

### Software-engineering reviewer

Review the architecture before coding and the actual implementation before merge. The reviewer must answer:
- Are reference data, data validation, clocks, execution, accounting, strategy, and reporting separated cleanly?
- Are interfaces typed and invalid states difficult to represent?
- Are calendars and rule sets deterministic, effective-dated, and provenance-backed?
- Does the system fail closed on unknown inputs?
- Is replay event ordering explicit and testable?
- Can every result be reproduced from committed code/config plus immutable inputs?
- Are tests sufficient for DST, holidays, early closes, expiry, rolls, gaps, duplicates, ambiguous bars, partial-fill policy, and forced flatten?
- Does the new futures path avoid breaking or silently changing the existing daily engine?
- Are migrations/integration reversible and CI-safe?
- Are performance choices adequate without premature complexity?

Material engineering objections block merge.

## 6. Review and delivery checkpoints

1. **Plan review now:** independent quant and engineering agents review this document.
2. **Reconcile:** update the plan only for material findings; retain disagreements and decisions.
3. **Architecture slice:** B0–B3 implemented test-first; engineering review.
4. **Replay slice:** B4–B7 implemented test-first; quant and engineering review.
5. **Experiment freeze:** quant approval of B8; spec hashed and committed.
6. **Data quote:** B9 price presented to Jason; stop for approval.
7. **Outcome run:** B10 only after approval and successful ingestion.
8. **Final independent review:** reviewers inspect implementation, artifacts, and interpretation before any phase-completion claim.

## 7. Non-goals and safety boundaries

- no live-money trading;
- no brokerage order transmission or credential handling;
- no LLM improvising, authorizing, or sizing a live trade;
- no evaluation purchase or paid subscription without approval;
- no performance claim from synthetic data;
- no continuous-contract shortcut presented as executable reality;
- no silent data imputation, calendar guessing, or zero-cost default;
- no post-result ORB parameter hunt;
- no destructive cleanup of the existing Grok research corpus or unrelated uncommitted work.
