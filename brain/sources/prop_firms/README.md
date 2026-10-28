# Prop firms for a fully automated Python MNQ bot: comparison (2026-10-28)

Workstream R of `brain/_system/plan/prop_firm_grid_plan.md`. Per-firm detail and sources: `topstep.md`, `tradeify.md`, `lucid.md`, `fundednext.md`, `myfundedfutures.md`. Simulator drafts: `brain/_system/prop/firms/*.json`. Numbers come from official help centres; Lucid prices are BLOG only.

## 50K at a glance
| Firm / plan | Cost | Target | Drawdown (all EOD trailing, intraday breach) | Lock | Eval DLL | Eval consistency | Funded payout | Split | Bots allowed (official) | Python route |
|---|---|---|---|---|---|---|---|---|---|---|
| Topstep Combine, Standard | $49/mo + $149 activation | $3,000 | $2,000 | at start | optional $1,000 soft | 55% (target rises) | 5×$150 days, 50% of balance, cap $2,000 (or 3 days at 40% consistency, cap $3,000); MLL → $0 after payout | 90% | Yes, Combine + XFA; **not Live** | **TopstepX API, $29/mo ($14.50 promo), own PC only (no VPS/VPN)** |
| Topstep Combine, No Activation Fee | $95/mo, $0 activation | same | same | same | same | same | same | 90% | same | same |
| Tradeify Growth | $145 one-time, reset $95 | $3,000 | $2,000 (eval never locks) | funded +$100 | $1,250 soft | none | 5×$150 days, balance ≥$53K, cap $1.5K→$3K, 35% consistency | 90% | Yes, with conditions: sole ownership, live video of the code starting on your own PC, not at other firms, no HFT | none documented |
| Tradeify Select → Flex / Daily | $165 one-time, reset $109 | $3,000 | $2,000 | funded +$100 | none | 40%, min 3 days | Flex: 5×$150 days, 50% of profit, cap $2.5K. Daily: 2× profit since last, cap $1,250, $2.1K buffer | 90% | same | none documented |
| Tradeify Lightning (no eval) | $492 one-time | goal $3K then $2K | $2,000 | +$100 | n/a | n/a | 20/25/30% consistency, cap $2K–$2.5K, min $1K | 90% | same | none documented |
| Lucid Flex | one-time (BLOG ~$146) | $3,000 | $2,000 | +$100 | optional | 40% | 5×$150 days, 50% of profit, cap $2K, 5 payouts then live | 90% | Yes ("Automated trading systems and trade copiers are permitted") | none documented |
| Lucid Pro | one-time (BLOG ~$130–192) | $3,000 | $2,000 | +$100 | $1,200 soft | none | buffer $52.1K, cap $2K/$2.5K, 40% consistency per cycle | 90% | Yes | none documented |
| Lucid Direct (no eval) | one-time (unknown) | goal $3K then $2.5K | $2,000 | +$100 | n/a | n/a | 20% consistency per cycle, cap $2K/$2.5K | 90% | Yes | none documented |
| FundedNext Rapid Pro | $169.99 one-time, reset $174.99 | $3,000 | $2,000 | +$100 | none (add-on $1K) | none | every 3 days, $250–$1,200, 40% consistency, 5 payouts then closed | 90% | Yes, EAs/bots in challenge + funded; no HFT | none documented |
| FundedNext Rapid Daily | $169.99, reset $189.99 | $3,000 | $2,000 | +$100 | $1,000 soft | none | daily above $52.1K buffer, max $1,200, 5 payouts | 90% | Yes | none documented |
| FundedNext Flex | $74.99 (coupon) / $141.99, reset $82.99 | $2,500 | **$1,500** | +$100 | none | 40% of target per day | 5×$200 days, 50% of profit, cap $1,500, 5 payouts | 95% | Yes | none documented |
| FundedNext Direct (no eval) | $169.99 | none | $2,000 | +$100 | n/a | n/a | $2.1K buffer, $800–$1,200, 20% perpetual consistency | 90% | Yes | none documented |
| MyFundedFutures | not collected | | | | | | | | Officially "may make use of automated trading strategies"; blogs say semi-auto only | none documented |

FundedNext Legacy (discontinued 2026-10-11) and Bolt (no longer in help centre) are left out.

## Recommendation
1. **Topstep is the only firm where a self-written Python bot is clearly allowed and technically documented.** The route is the TopstepX API for $29/month ($14.50 with promo), run from Jason's own PC, never a VPS or VPN. It works in the Combine and the XFA only; promotion to Live ends the bot run. Simulate the 50K first, then 100K/150K (costs scale; DLL and payout caps double when the DLL is set at purchase).
2. **Tradeify, Lucid and FundedNext allow bots by policy, but none documents a way for a Python program to send orders.** The only realistic own-PC route is NinjaTrader 8 (NinjaScript, or ATI fed by local Python). Direct Tradovate API access is reported as disabled for prop accounts, and Rithmic's API needs approval. Simulate these plans as "rules only" and gate any real use on a written support answer about the order route.
   - FundedNext Rapid/Flex has the clearest bot permission plus cheap one-time pricing. Note Flex's $1,500 drawdown and the 5-payout account end.
   - Tradeify adds ownership checks (live video on your own PC) and forbids running the same bot at other firms. That clashes with running it at Topstep too.
   - Lucid has the loosest automation wording, but official prices aren't readable.
3. MyFundedFutures: skip for now.

## Biggest uncertainties
- Python order route for every non-Topstep firm (no official API).
- Lucid prices and resets (BLOG only).
- Topstep 100K/150K XFA lock levels and scaling tiers (image only).
- Several in-firm conflicts: Lucid caps "none" vs listed; FundedNext add-on price; Topstep XFA page cap figures.
