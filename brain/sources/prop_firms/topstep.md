# Topstep: official rules (checked 2026-10-28)

Grade: OFFICIAL (help.topstep.com). JSON drafts: `brain/_system/prop/firms/topstep_{50,100,150}k_{standard,no_activation_fee}.json`.

## Sources
| # | Page | Date on page |
|---|---|---|
| P1 | https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions | "Updated over a week ago" |
| P2 | https://help.topstep.com/en/articles/8284197-trading-combine-parameters | 2026-09-24 |
| P3 | https://help.topstep.com/en/articles/8284208-consistency-at-topstep | 2026-09-17 |
| P4 | https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit | 2026-09-18 |
| P5 | https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account | 2026-06-30 |
| P6 | https://help.topstep.com/en/articles/8284215-express-funded-account-parameters | 2026-08-05 |
| P7 | https://help.topstep.com/en/articles/8284217-express-funded-account-activation | 2026-09-24 |
| P8 | https://help.topstep.com/en/articles/8284233-topstep-payout-policy | "Updated over 2 weeks ago" |
| P9 | https://help.topstep.com/en/articles/11187768-topstepx-api-access | 2026-09-17 |
| P10 | https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan | 2026-07-16 (tiers only in an image) |

## Trading Combine
| Item | 50K | 100K | 150K | Src |
|---|---|---|---|---|
| Subscription, Standard path | $49/mo | $99/mo | $199/mo | P1 |
| Subscription, No Activation Fee path | $95/mo | $149/mo | $229/mo | P1 |
| Reset (Standard / NAF) | $49 / $95 | $99 / $149 | $199 / $229 | P1 |
| XFA activation | $149 one-time per XFA (Standard); $0 (NAF) | same | same | P1, P7 |
| Profit target | $3,000 | $6,000 | $9,000 | P3 |
| Max Loss Limit | $2,000 | $3,000 | $4,500 | P4 |
| MLL type | trails the end-of-day balance; enforced intraday incl. open P&L | | | P4 |
| MLL lock | "Once it reaches your starting balance, it locks permanently" | | | P4 |
| Daily loss limit (optional) | $1,000 | $2,000 | $3,000 | P5 |
| Consistency | best day ≤55% of target; if exceeded, target = best day / 0.55 (no fail, no rounding) | | | P3 |
| Min days | none stated; "pass in as few as two days" | | | P2 |
| Max position | 5 minis / 50 micros | 10 / 100 | 15 / 150 | P2 |
| Data | Level 1 included; Level 2 $38/mo optional | | | P1 |

DLL (P5): optional in Combine and XFA; set at checkout it is fixed and carries into the XFA. "Triggering it is not a rule violation — it's a forced break for the rest of that session"; positions flattened, trading resumes 5 PM CT next session.

## Express Funded Account (XFA)
| Item | 50K | 100K | 150K | Src |
|---|---|---|---|---|
| Start balance | $0 | $0 | $0 | P6 |
| MLL | -$2,000 | -$3,000 | -$4,500 | P4 |
| MLL lock | locks at $0 once balance reaches +$2,000 (50K example only) | not stated | not stated | P4 |
| After payout | "Your Maximum Loss Limit (MLL) resets to $0 permanently" | | | P8 |
| Standard path | 5 winning days of $150+ net P&L (not consecutive; day locks 4 PM CT) | | | P8 |
| Consistency path | ≥3 trading days, largest day ≤40% of total net profit | | | P3, P8 |
| Payout size | 50% of account balance, up to cap | | | P8 |
| Cap, Standard / Consistency | $2,000 / $3,000 | $3,000 / $4,000 | $5,000 / $6,000 | P8 |
| Cap with DLL set at Combine purchase | $4,000 / $6,000 | $6,000 / $8,000 | $10,000 / $12,000 | P8 |
| Min payout | $125 | | | P8 |
| Split | 90/10 | | | P8 |
| Max XFAs | 5 active | | | P6 |
| Back2Funded | $599 | $699 | $829 | P1 |
| Scaling | 50K starts on a 2-lot (20 micros); tiers only in image | ? | ? | P10 |

Breach: "Your account is liquidated and closed at the end of the day" (P6).

## Automation and order route
- XFA parameters (P6), automated strategies: "Yes, with conditions. Topstep won't help set them up or cover malfunctions."
- API (P9): "API Access is $29/month" (50% off with Topstep promo code, $14.50). "No, Live funded accounts are not allowed to trade through the ProjectX API."
- "All trading activity must originate from your personal device." "The use of VPS, VPNs, and remote servers is prohibited by Topstep's Terms of Use." Servers may store data, backtest, log, run read-only dashboards; nothing that places/modifies/cancels/routes orders.
- Custom bots allowed "subject to standard platform rules and our prohibition on highfrequency trading (HFT)". No sandbox; use a Practice account. Session tokens expire; back off on rate limits.
- Route for Python: TopstepX / ProjectX REST + websocket API, from Jason's own PC.

## Re-verification of existing 50K files
`brain/_system/prop/topstep_50k.json` and `topstep_50k_xfa.json`: **no value changed.** Target, MLL, lock, 55% consistency, 50 micros, $49/$95 fees and resets, $149/$0 activation, $1,000 DLL, $125 minimum, 90% split, 50% of balance, caps $2,000/$3,000 (doubled with DLL $4,000/$6,000), 5 XFAs, $599 Back2Funded all match.
Notes:
- New field to add: API fee $29/month ($14.50 with promo). The old files have no API cost.
- The Combine parameters page now carries a date (2026-09-24).
- The XFA parameters page still shows "up to $5,000 / $6,000" with no size given (150K figures). The size table in the Payout Policy is used.
- Payout policy: traders who joined the new dashboard before 2026-01-12 keep 100% of the first $10,000. That doesn't apply to a new account.

## Open questions
1. XFA lock level/trigger for 100K and 150K (assumed: locks at $0 once balance reaches +MLL).
2. XFA scaling tiers (image only), so max size for 100K/150K XFA isn't known.
3. The 15:10 CT flat time wasn't re-read today (carried over from the 2026-10-27 note).
4. Whether the DLL-doubled payout caps offer is still running (started June 2; no end date given).
