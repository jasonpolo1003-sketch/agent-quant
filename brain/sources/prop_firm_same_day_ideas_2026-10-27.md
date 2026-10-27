---
type: research_note
status: reviewed_by_claude_code
created: 2026-10-27
source: external research agent (pasted by Jason); first-party prop-firm pages checked by the agent 2026-10-27
---

# Prop-firm rules and same-day candidates (reviewed)

## Verified rules (agent, first-party help pages, 2026-10-27)
| | Topstep 50K | MyFundedFutures Builder 50K | Tradeify Select 50K |
|---|---|---|---|
| Flat by | 3:10 pm CT | 4:10 pm ET | 4:45 pm ET |
| Target / drawdown | $3,000 / $2,000 EOD-trailing, enforced intraday incl. unrealized | $3,000 / $2,000 EOD trailing | $3,000 / $2,000 EOD, enforced real-time |
| Daily loss | no mandatory DLL in Combine/XFA | $1,000 soft pause (help center inconsistent) | none |
| Size | 5 minis / 50 micros | 4 / 40 | 4 / 40 |
| Cost | $49/mo, reset $49, XFA activation $149 | $153 one-time | $165 one-time, reset $109 |
| Automation | Documented API; bots allowed in Combine and XFA; **API unavailable in Live Funded** | personal automation allowed incl. live; no public API spec found | personal bots allowed; no public API spec found |
| Bans | HFT; max size into major news | HFT | HFT; correlated hedging |
Apex: first-party rules prohibit automation, so excluded.

**Firm for the next automated experiment: Topstep 50K.** XFA payouts are reachable by a bot. The live stage would need a different execution route.

## Candidates
1. **Rare intraday liquidity-shock reversal (test first).** After an extreme, volatility-normalised 15-minute move outside scheduled-news windows, wait for one reversal confirmation, fade it once with a stop and a time exit, flat well before 3:10 CT. Evidence: Christensen, Oomen & Renò, "The drift burst hypothesis", J. Econometrics. *Review: real paper, but it uses finer-than-1-minute data, so this is an adaptation. Needs a historical macro-release calendar for the exclusion. Many design choices (threshold, confirmation, stop, hold) must be frozen blind as one spec. Shock days are the riskiest days against a $2,000 trailing limit, so sizing is critical. Overlaps the "negative-jump reversal" lead from the 2026-10-26 research.*
2. **Extreme opening-dislocation reversal (second, low conviction).** Fade only extreme gaps after about 10 minutes. Evidence: Grant, Wolf & Yu (2005); Fung, Mok & Lam (2000); a newer ETF study reports decay after the 2010s. Needs about $97 net per trade at about 13 trades a year to reach $5/day. *Review: weak after costs and decaying; test only if #1 is informative.*
- **Excluded (agree):** more late-day momentum (Rosa, JFM, OOS failure plus our own SC-FUT-0002); pre-FOMC drift (gone after 2015, too few events); speed-based news trading.

## Method change adopted
The prop-evaluation simulator (bootstrap whole days; intraday equity against the trailing floor; pass/fail/time-to-pass; fees; XFA payout survival) becomes the **main gate** for prop-goal strategies, ahead of Sharpe and $/day.
