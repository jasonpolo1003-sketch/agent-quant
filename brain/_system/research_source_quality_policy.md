# Research Source and Quality Policy

## Purpose

Keep Quant Agent Brain open to useful ideas across markets without allowing polished but untraceable content to become strategy evidence.

The system uses a wide discovery funnel and narrower promotion gates:

```text
open discovery
→ cited raw research
→ quality-scored curation
→ method door
→ frozen strategy card
→ backtest and robustness review
```

## Live Discovery Connection — Agent Reach

Canonical repository:

```text
https://github.com/Panniantong/Agent-Reach
```

Verified local installation:

```text
Version: 1.5.0
Local review clone: C:/Users/jason/Projects/Agent-Reach-review
Executable: C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe
Obsidian skill: C:/Users/jason/OneDrive/Desktop/memory_vault/Agents/skills/agent-reach/SKILL.md
```

Agent Reach is the discovery router, not the source of truth. It points agents toward upstream web pages, transcripts, repositories, feeds, and discussions. Durable notes cite the upstream source rather than citing Agent Reach itself.

Before a broad live-research pass:

```bash
C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe doctor --json
```

Preferred read-only channels:

- Web pages: Agent Reach web channel via Jina Reader.
- YouTube: `yt-dlp` or transcript helper; verify non-empty transcript content.
- GitHub: authenticated `gh` CLI.
- RSS: feedparser channel.
- Reddit/X/social: discovery only unless the post contains checkable primary evidence.

Never store browser cookies, passwords, API keys, or private session data in the project.

## Open Research Universe

Research is not restricted to SPY/QQQ/IWM, equities, RSI, or traditional finance. It may cover:

- equities, indices, and ETFs;
- government bonds and interest rates;
- foreign exchange;
- commodities;
- futures and forwards;
- options and volatility;
- crypto and digital assets;
- factor and style premia;
- systematic macro and trend following;
- statistical arbitrage, relative value, and mean reversion;
- market making and liquidity;
- alternative data and machine learning;
- portfolio construction and risk allocation.

Being in the research universe does not mean the project can test it now.

## Source Quality Tiers

### Tier A — Primary evidence

Examples:

- peer-reviewed or credible working papers;
- official documentation and datasets;
- regulatory/exchange materials;
- source code and reproducible repositories;
- named institutional research with methods and limitations.

Use for durable claims and strategy-card support.

### Tier B — Identifiable practitioner evidence

Examples:

- named quant practitioner blogs;
- interviews or YouTube transcripts with identifiable professionals;
- books or legal previews with exact citations;
- research summaries that link to original work.

Useful when the mechanism, assumptions, and limitations are visible. Important claims should be corroborated before strategy-card promotion.

### Tier C — Discovery leads

Examples:

- Reddit, X, Discord, newsletters, unsourced YouTube explanations;
- search snippets;
- opinion posts and community discussions.

May create research questions. Cannot independently support durable claims or strategy cards.

### Tier D — Reject as slop

Reject or quarantine content with:

- guaranteed-return or effortless-profit claims;
- performance screenshots without rules, data, and costs;
- copied summaries with no original source;
- hidden or changing entry/exit rules;
- cherry-picked periods presented as general evidence;
- inaccessible datasets described as if they are available;
- invented citations, unverifiable quotes, or fake precision;
- affiliate/sales content pretending to be independent research.

## Stage-Appropriate Gates

### Raw research

Allow Tier A, B, and C material. Every item must record its URL/citation, source tier, claim, evidence, uncertainty, and why it might matter.

### Curated source note

Require Tier A or defensible Tier B support. Preserve conflicts and caveats. Tier C can remain only as an explicitly labeled lead.

### Method/Strategy Door

Require:

- plausible economic, behavioral, structural, or market-mechanics rationale;
- asset class and intended horizon;
- required data and realistic accessibility;
- implementation and market-specific risks;
- unresolved questions stated directly.

A door may remain open even when the idea is not currently feasible.

### Strategy Card

Require frozen, testable rules before seeing results:

- universe and data fields;
- signal calculation;
- entry, exit, and maximum holding period;
- execution timing;
- position sizing and portfolio rules;
- costs, spread, slippage, funding, and borrow assumptions as relevant;
- benchmark and validation plan;
- parameter-count and multiple-testing declaration.

### Backtest promotion

Require reproducible code/data, no lookahead, realistic instrument handling, costs, robustness checks, an untouched evaluation period, and a review that can reject the result.

## Asset-Specific Feasibility Checks

- **Equities/ETFs:** corporate actions, delistings, survivorship, borrow, spread, liquidity.
- **Futures:** contract rolls, continuous-series construction, margin, multipliers, session timing.
- **FX:** spot/forward definition, carry, rollover, trading calendar, institutional vs retail pricing.
- **Options:** complete chains, bid/ask, implied volatility, greeks, exercise/assignment, expiration, surface quality.
- **Crypto:** venue quality, fragmented liquidity, funding, fees, custody, token survivorship, 24/7 timing, manipulation risk.
- **Market making/HFT:** order-book and message data, latency, queue position, inventory risk, maker/taker fees; usually research-only for the current MVP.
- **Alternative data/ML:** timestamp lineage, revisions, licensing, missingness, leakage, feature stability, incremental value over existing signals.

## Decision Rule

Do not ask, “Is this idea conventional enough?”

Ask:

```text
Is the claim traceable?
Is the mechanism plausible?
Can the required data be obtained honestly?
Can the rule be frozen before testing?
Can costs and failure modes be represented?
Can the result survive an adversarial review?
```

Unusual ideas may pass. Popular ideas may fail.
