---
title: Topstep / ProjectX official rules and API behavior (Package 2)
package: 02_venue_rules
status: unreviewed
promoted: false
created: 2026-10-22
retrieved: 2026-10-22
author: Grok Bot (research only; not trading advice; no rules chosen for QAB)
---

# Topstep / ProjectX rules & API (Package 2)

Labels: **[VENUE RULE]** = official Topstep/ProjectX statement (venue policy, not an exchange rule) · **[OFFICIAL]** = CME · **[QAB-OPTION]** = engineering options, none chosen · **[LEAD]** = unverified.
Sources: help.topstep.com and gateway.docs.projectx.com only, rendered in Chrome on 2026-10-22 ~09:50–10:10 UTC-5. Snapshots are in `../source_files/venue/`. All 66 quotes (V1–V66) were string-matched against the snapshots after collapsing whitespace: 66/66 PASS (`quote_verification.tsv`).
"Updated" dates are as shown on the page on 2026-10-22. Relative dates ("Updated yesterday") are resolved to approximate calendar dates.
**Caution:** Topstep help pages are edited often (several were updated within the last week or two). Re-verify before any decision. Confidence: High = explicit official statement; Med = explicit but ambiguous or inconsistent; Low = inferred.

## Cross-stage API & automation facts [VENUE RULE]
| Rule | Quote | Source (updated) | Conf. |
|---|---|---|---|
| Bots allowed | "Custom automated strategies and bots are allowed via the TopstepX / ProjectX API, subject to standard platform rules and our prohibition on highfrequency trading (HFT)." (V5) | ts_api_access (Sep 17, 2026) | High |
| **Live: no API** | "No, Live funded accounts are not allowed to trade through the ProjectX API. The API Gateway is built for the simulated environment and isn't available on Live." (V4) | ts_api_access | High |
| No VPS/VPN for order flow | "The use of VPS, VPNs, and remote servers is prohibited by Topstep's Terms of Use. Running automation on a VPS can result in account suspension or removal from the program." (V1); "The line is order transmission: your server can watch and record, but it cannot trade." (V2); "Do not use a VPN…" (V35) | ts_api_access; ts_prohibited_conduct (~early Oct 2026) | High |
| No sandbox; use Practice | (V6) | ts_api_access | High |
| Cost | "API Access is $29/month. Topstep Traders get 50% off with code topstep — that's $14.50/month…" (V3). Billed as Sim2Funded Solutions. | ts_api_access | High |
| One key, all accounts | (V7) | ts_api_access | High |
| Same rules for automation | "A rule violation is treated the same whether it originates from manual trading or third-party automation." (V8) | ts_api_access | High |
| No help for bots or malfunctions | Combine: "Yes, with conditions… no exceptions are made for errant trades or malfunctions." (V13); XFA (V20) | combine/xfa params | High |

## Stage tables
### Practice
| Item | Finding | Ref | Conf. |
|---|---|---|---|
| What it is | "free 150K simulated account available to any Trader with an active Trading Combine subscription" (V9); max position 15 lots; 1 account at a time | ts_practice (Jul 28, 2026) | High |
| API | Explicitly recommended as the test venue (V6) | ts_api_access | High |
| Resets | Free; "up to 10 times per day" (V10) | ts_practice | High |
| Cost | Free, but requires an active paid Combine subscription | ts_practice | High |
| MLL/DLL/consistency for Practice | Not stated on the Practice page | — | Unknown |
| Flatten time / news restriction for Practice | Not stated specifically for Practice | — | Unknown |

### Trading Combine (TC)
| Item | Finding | Ref | Conf. |
|---|---|---|---|
| API automation | Allowed with conditions (V5, V13) | | High |
| Core rule | MLL (V11): $2,000 / $3,000 / $4,500 for 50K/100K/150K. Trails end-of-day balance, never moves down, locks at the starting balance (V22). Monitored intraday, including unrealized P&L (V23). Liquidation is by market orders (V24) | ts_mll (Sep 18, 2026) | High |
| Profit target | $3,000 / $6,000 / $9,000 | ts_consistency | High |
| Consistency | Best day must stay at or below 55% of the profit target; otherwise the target increases (V15). Best day locks at 3:10 PM CT | ts_consistency (Sep 17, 2026) | High |
| DLL | Optional; fixed if set at purchase ($1,000 / $2,000 / $3,000). A breach flattens positions and blocks trading until 5 PM CT; it is not a violation (V25, V26) | ts_dll (Jun 30, 2026) | High |
| Minimum days | "as few as two days" | ts_combine_params | High |
| Max size | 5/10/15 minis, or 50/100/150 micros, at a 10:1 ratio (V12) | ts_combine_params (~Sep 2026) | High |
| Concurrency | No limit on number of Combines; single profile required (V14) | ts_combine_params | High |
| Cost (monthly) | Standard path $49 / $99 / $199; No-Activation-Fee path $95 / $149 / $229 (V43). Rebills every 30 days. Resets cost the same amounts. L1 data included; L2 $38/mo (V46) | ts_pricing (~week of Oct 19, 2026) | High |
| What happens on passing | Combine closes and its subscription cancels | ts_subscriptions | High |

### Express Funded Account (XFA)
| Item | Finding | Ref | Conf. |
|---|---|---|---|
| API automation | Allowed with conditions (V20, V5) | ts_xfa_params (Aug 5, 2026) | High |
| Balance and MLL | Starts at $0; MLL starts at −$2,000 (50K) and trails up, locking at $0. After the first payout the MLL is set to $0 | ts_mll | High |
| Breach | Account permanently closed. Back2Funded reactivation costs $599 / $699 / $829 | ts_mll, ts_pricing | High |
| Payout paths | Standard: "Hit 5 winning days with at least $150 profit each" (V18). Consistency: "Trade at least 3 days…" (V19) and largest day ÷ total at or below 40% (V16) | | High |
| DLL | Optional | ts_dll | High |
| Scaling plan | Max contracts grow with balance (tables in ts_risk_adjust_hv) | | Med |
| Concurrency | Up to 5 XFAs (V17); trade copier allowed up to $750K buying power; cross-account hedging prohibited (V36) | | High |
| Inactivity | "XFAs with no trading activity for more than 30 days may be closed." (V21) | | High |
| Cost | Activation $149 (Standard path) or $0 (V44); no monthly fee | ts_pricing, ts_xfa_activation | High |
| Tax | Payouts reported on 1099-NEC if over $600 (US); traders are independent contractors (V47) | ts_tax (May 29, 2026) | High |

### Live Funded Account (LFA)
| Item | Finding | Ref | Conf. |
|---|---|---|---|
| **API automation** | **Not allowed** (V4) | ts_api_access | High |
| Transition | "When the call-up comes, all Express Funded Accounts (XFA) close." (V27). Traders cannot decline and stay in an XFA. **Moving to Live therefore removes API trading** | ts_lfa_params (~Oct 21, 2026) | High |
| DLL | Automatic: $2,000 / $3,000 / $4,500 (V28, V25). Drops to $2,000 at a $10K-or-lower balance and $1,000 at $5K-or-lower | ts_lfa_params | High |
| Capital | 20% tradable (minimum $10K) and 80% reserve released in 25% steps. Below a $1,000 balance the account is liquidated and closed | ts_lfa_params | High |
| Micro:mini ratio | Not available on Live (V29) | ts_combine_params | High |
| Data fees | "subject to Professional Data fees" (V45); amount not captured | ts_pricing | Med |
| Tier-1 news | Balances under $3,000 are limited to 1 contract | ts_risk_adjust_hv | High |

## Hours, flatten time and news (all stages unless noted) [VENUE RULE]
- "All positions must be closed by 3:10 PM CT every weekday." (V30). Auto-cancel and flatten begin at 3:10 PM, and Risk Managers start flattening at 3:08 PM CT (V31). Reopen is 5:00 PM CT. Note that QAB would be flat 50 minutes before CME's 4:00 PM CT close and about 10 minutes after the 3:00 PM CT settlement window.
- Tier-1 news (CPI, NFP, PPI at 7:30 AM CT; FOMC decision at 1:00 PM CT; FOMC press conference at 1:30 PM CT): opening positions are restricted from 5 minutes before to 5 minutes after the release. Minis are blocked. MES/MNQ opening size is capped at 1 / 3 / 6 / 9 / 15 contracts by account size (V38). "Pending orders… will not fill during the 10-minute window, and new pending orders intended to execute during this timeframe cannot be placed." (V39). "TP/SL brackets that are reducing/closing positions will be accepted during the window." (V40). Updated 2026-10-22 ("Updated today").
- Prohibited: "Purposefully trading your full Maximum Position Size directly into a scheduled major news event." (V32). Also prohibited: exploiting SIM fills, including "impossible stop-loss execution" (V33) and "tight brackets or auto-breakeven" (V34), "Using an external or slow data feed to trade" (V37), HFT, and account stacking.
- Roll/contract handling by Topstep: **no official statement found**. The ProjectX contract search returns dated contract IDs (e.g. `CON.F.US.MNQ.U25`, V61) with an `activeContract` flag. → Unknown.

## Costs summary (per round turn, TopstepX) [VENUE RULE]
MES $1.22 and MNQ $1.22 (V41, V42), made up of NFA $0.02 + exchange $0.70 + commission $0.50 (MES breakdown shown; MNQ total matches). These apply in TC, XFA and LFA. Other costs: subscription, activation and API fees as listed above. L2 data $38/mo.

## ProjectX Gateway API [VENUE RULE: ProjectX docs]
- **Auth:** "Logging in with an API key is the only supported way to obtain a token." (V48). `POST https://api.topstepx.com/api/Auth/loginKey` with userName and apiKey. The token is a JWT, sent as a bearer token. "It is valid for 24 hours from the time it is issued." (V49). Refresh via `POST /api/Auth/validate`. "One token works for every REST request and realtime hub connection you open." (V50). A failed login still returns HTTP 200 with an errorCode (3 = invalid credentials, 7 = agreements not signed, 9 = no API subscription, 10 = API key login disabled).
- **Realtime (SignalR):** user hub `https://rtc.topstepx.com/hubs/user` and market hub `.../hubs/market`. Token is passed as `?access_token=` / accessTokenFactory, using the WebSockets transport with skipNegotiation. The sample uses `.withAutomaticReconnect()` (V60) and **re-subscribes in onreconnected**. Implication: subscriptions are not restored automatically after a reconnect. This is shown in sample code only (Med).
- **Rate limits:** retrieveBars 50 requests per 30 s (V51); everything else 200 requests per 60 s (V52); exceeding returns HTTP 429 (V53). Login counts toward the limits.
- **Orders:** types 1 Limit, 2 Market, 4 Stop, 5 TrailingStop, 6 JoinBid, 7 JoinAsk. Brackets in ticks (stopLossBracket/takeProfitBracket) only when the account is set to "Auto OCO Brackets". The default mode is Position Brackets, which rejects bracket objects (V57). "The rejected order is still created and its ID is returned in orderId." (V58). TrailingStop distance is computed from the server's last price on arrival (V59). customTag must be unique per account.
- **History bars:** `POST /api/History/retrieveBars`, units second/minute/hour/day/week/month, up to 20,000 bars per request (V54), with a `live` flag for sim versus live data, partial-bar option and UTC timestamps. It takes a **dated contract ID** (example `CON.F.US.RTY.Z24`, V56), so per-contract minute bars are supported in principle. How far back expired contracts are kept is **not documented**.

## Conflicts (preserved)
1. retrieveBars documents `contractId` as "integer" (V55), but its example sends the string "CON.F.US.RTY.Z24" (V56). Order/place declares it a string.
2. Flatten time is written as "3:10 PM CT" (V30) and also "3:10 PM CST" (V31). CST is wrong during daylight time; CT is presumably intended. The 3:08 PM "Risk Managers begin flattening" note is a separate, earlier time.
3. Tier-1 news micro caps: the text lists 1/3/6/9/15 (V38) while the XFA scaling table shows lower values at low balances (e.g. a $50K XFA below $1,500 allows 1 micro). The caps depend on balance; the effective cap is the lower of the two (inferred, Med).
4. DLL breach is "not a rule violation" (V25), while MLL breach liquidates the account. Both are monitored on unrealized P&L. Not a contradiction, but the two risk mechanisms differ.
5. Practice vs evaluation: Practice is recommended for API testing, but its risk rules aren't documented, so Practice fills and rules may differ from TC/XFA.

## Side check → added to contracts note
- MNQ/NQ daily settlement [OFFICIAL]: NQ/MNQ settlements "are determined by CME Group staff based on trading and market activity on CME Globex." (V62). Lead month is the VWAP from 14:59:30 to 15:00:00 CT (V64). "Daily settlement of the Micro contracts are equal to the settlement price of their associated Mini contracts." (V63)
- Juneteenth 2026 [OFFICIAL]: "Note: Friday June 19, 2026 CME Group will not derive or disseminate settlement prices…" (V65). Products settled at normal times Thursday 6/18. The exact last-trade time of the June 2026 contract on 6/18 is **still not stated** in any captured notice (a search synthesis claims expiry was 6/18; lead only). Final settlement uses the SOQ "on expiration Friday" (V66). The wording assumes a Friday, which conflicts with the 6/18 table entry.

## Unknowns / unresolved questions
- Exact Practice-account rules (MLL, flatten time, news window).
- Whether the API key works on Practice with identical fill logic.
- Retention of history for expired dated contracts in retrieveBars, and whether `live=false` (sim) bars equal CME prints.
- Market hub event schema and its depth/trade feed (realtime page not fully parsed).
- How Topstep handles contract rolls and expiries (auto-flatten? which contract counts as active?).
- Amount of the LFA professional data fee.
- The ProjectX Terms of Use "fair-use limits" (not captured).
- Whether the HFT prohibition has a numeric threshold. The prohibited-strategies page says abuse is "usually hundreds or thousands of trades per day", which is not a hard number.
- Whether an XFA can be kept to avoid the Live call-up (no: the options are move or close).

## Source records
| Snapshot | URL | Page date | Type |
|---|---|---|---|
| ts_api_access | https://help.topstep.com/en/articles/11187768-topstepx-api-access | Sep 17, 2026 | venue help |
| ts_practice | https://help.topstep.com/en/articles/8284134-practice-account | Jul 28, 2026 | venue help |
| ts_combine_params | https://help.topstep.com/en/articles/8284197-trading-combine-parameters | "over a month ago" | venue help |
| ts_xfa_params | https://help.topstep.com/en/articles/8284215-express-funded-account-parameters | Aug 5, 2026 | venue help |
| ts_xfa_activation | https://help.topstep.com/en/articles/8284217-express-funded-account-activation | "over a month ago" | venue help |
| ts_lfa_params | https://help.topstep.com/en/articles/10657969-live-funded-account-parameters | "yesterday" (~Oct 21) | venue help |
| ts_consistency | https://help.topstep.com/en/articles/8284208-consistency-at-topstep | Sep 17, 2026 | venue help |
| ts_mll | https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit | Sep 18, 2026 | venue help |
| ts_dll | https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account | Jun 30, 2026 | venue help |
| ts_hours_products | https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade | Jul 13, 2026 | venue help |
| ts_prohibited_conduct | https://help.topstep.com/en/articles/10296582-prohibited-conduct | "over 3 weeks ago" | venue help |
| ts_prohibited_strategies | https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep | Jun 10, 2026 | venue help |
| ts_risk_adjust_hv | https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility | "today" (Oct 22) | venue help |
| ts_commissions_fees | https://help.topstep.com/en/articles/8284213-topstepx-commissions-and-fees | "over 3 weeks ago" | venue help |
| ts_pricing | https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions | "this week" | venue help |
| ts_subscriptions | https://help.topstep.com/en/articles/8284121-trading-combine-subscriptions | "over a week ago" | venue help |
| ts_market_data | https://help.topstep.com/en/articles/8284120-level-1-and-level-2-market-data | Jun 18, 2026 | venue help |
| ts_tax | https://help.topstep.com/en/articles/8284238-funded-trader-tax-questions | May 29, 2026 | venue help |
| ts_hedging, ts_payout, ts_program_overview, ts_topstepx | (saved for context; not quoted) | — | venue help |
| px_auth_apikey, px_validate_session, px_rate_limits, px_connection_urls, px_retrieve_bars, px_search_contracts, px_available_contracts, px_order_place, px_realtime | https://gateway.docs.projectx.com/docs/... (see the file names) | not dated | API docs |
| cme_wiki_nq_mnq_settlement | https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457222172/Nasdaq-100 | "Updated Aug 20" | exchange procedure |
| cme_juneteenth_2026_settlement.pdf | https://www.cmegroup.com/tools-information/holiday-calendar/files/2026/juneteenth-day-settlement-times-2026.pdf | 2026 | exchange notice |
| cme_final_settlement_soq | https://www.cmegroup.com/trading/equity-index/settlement.html | not dated | exchange page |
Checksums for every file are in `../_sha256.txt`. Applicability: all venue rules apply directly to MES/MNQ on TopstepX. Limitation: they are venue policy, can change without notice, and are not exchange rules.

## Verified facts
- API bots are allowed in Practice, Combine and XFA, but **not in Live**. A call-up to Live closes all XFAs. Order transmission must come from a personal device (no VPS/VPN).
- Everything must be flat by 3:10 PM CT (flattening starts at 3:08). Tier-1 news windows restrict opening orders on MES/MNQ from 5 minutes before to 5 minutes after.
- MLL trails end-of-day balance, is monitored intraday on unrealized P&L, and liquidates by market order. Combine consistency is 55%; XFA consistency path is 40%.
- MES/MNQ round turn costs $1.22. API costs $29/mo ($14.50 with the Topstep code). Combine costs $49–$229/mo; activation is $149 or $0.
- Token lasts 24 h. Rate limits are 50 per 30 s for bars and 200 per 60 s for everything else. Bars endpoint allows 20k bars per request on dated contract IDs.
## Indirect but credible evidence
- Reconnect/re-subscribe behavior is inferred from sample code. The Tier-1 effective cap is inferred from the interaction of two tables.
## Conflicting evidence
- See Conflicts 1–5. The June 2026 SOQ text says "expiration Friday" while the calendar says 6/18.
## Unknowns
- See the list above. The biggest: Practice rules, bar history depth for expired contracts, and Topstep's roll handling.
## Engineering assumptions still required
- [QAB-OPTION] Forced-flatten time on or before 3:08 PM CT; whether to blackout Tier-1 windows entirely; bracket mode (Auto OCO vs Position) to configure; token refresh cadence and re-subscribe logic; request budget within the rate limits; local-device-only execution architecture.
## What was genuinely new
- Live accounts have no API, and the call-up is mandatory, so **an automated system has no automated path into Live funding**. Topstep explicitly lists tight brackets and SIM stop-fill exploitation as prohibited. The flatten deadline is 3:10 PM CT, not the 4:00 PM CME close. Topstep enforces its own Tier-1 news windows. The bars endpoint takes dated contracts.
## What confirmed an existing decision
- No live trading. Practice is the API test venue. Execution stays on Jason's local PC.
## What should change in the roadmap
- Treat Practice/Combine/XFA as the only automatable stages and record "Live = manual only" as a hard constraint.
- Add the venue session (Sun 5:00 PM – weekday 3:10 PM CT, flatten from 3:08) and the Tier-1 windows to the contract-calendar artifact.
- Backtests should model forced liquidation at 3:08–3:10 PM CT and MLL checks on unrealized P&L.
- Add a ProjectX bar-history probe (Practice account, expired contract) to Package 3.
## What should not change
- Package order. MES/MNQ focus. Costs package still needed for spread and slippage (Topstep's round-turn fee is not the full cost).
## Next bounded action
- Package 3 (data providers). Include one bounded ProjectX probe once Jason has an API key: retrieveBars 1-minute for an expired MNQ contract, to test retention. That needs his approval and a subscription; no calls were made in this package.
