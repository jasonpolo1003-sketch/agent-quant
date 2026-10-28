---
plan: brain/_system/plan/prop_eval_simulator_plan.md
reviewed: 2026-10-27
---

# Prop-evaluation simulator plan: independent reviews

## Engineering (verdict: ready with changes)
1. **Fake luck baseline:** only daily means of the 500 control draws are stored, which removes their variance. Store each draw's day net and lowest equity, and pick one draw per day on the same bootstrap indices (F6). For random-direction controls, the flipped worst open loss = the original's best open gain.
2. **Lowest equity computed inside `run_trade`:** stop bars beyond the stop, the flatten-bar low, gap stops, and multi-trade days (realized P&L plus the current open loss).
3. **No dropping non-evaluable or ineligible days** (survivorship). Use stress bounds and count them in the fee calendar.
4. **False tests:** size monotonicity holds only with the target and lock off; 40% gambler's ruin holds only for a fixed floor.
5. **Walk-forward:** overlapping starts. Report censored paths and confidence intervals, and use a non-wrapping bootstrap.
6. **Target on end-of-day balance** plus consistency rules. "Adverse first" equals the F4 "failure wins" rule.
7. **Separate fingerprint** (day data, rules config, simulator code, seed). Freeze the size, and count gate runs as trials.
8. **Build the XFA phase later**, once its rules are verified. Effort: Combine phase 3-4 sessions; everything 5-7.

## Prop trader (verdict: build, change two things)
1. **Rules update** (Topstep help centre, Sept 2026):
   - Combine consistency target is **55%** (a best day above 55% of profit raises the target).
   - No minimum days.
   - XFA payouts are capped at 50% of the balance, at most $2,000 (Standard) or $3,000 (Consistency).
   - The loss limit locks at $0 after the first payout.
   - Two payout paths: 5 days of at least $150, or 3 days with the best day at most 40%.
   - Sources: the [consistency target](https://intercom.help/topstep-llc/en/articles/8284208-what-is-the-consistency-target), [Combine parameters](https://intercom.help/topstep-llc/en/articles/8284197-trading-combine-parameters), [XFA payout policy](https://help.topstep.com/en/articles/8284233) and [payout FAQs](https://intercom.help/topstep-llc/en/articles/8284234-payout-faqs) pages.
2. **Rare strategies vs payout rules:** few trades make 5 qualifying days slow, while $49/month fees keep accruing.
3. **Main output = net cash per attempt over a fixed horizon** (90% of payouts minus fees, resets and activation). Beat the random version's net cash at its own best size, not just its pass rate. Asymmetric payoffs mean even a no-edge strategy can be near break-even.
4. **Small samples:** use regime-aware or longer bootstrap blocks; put ranges on every rate.
5. **Stop slippage** should grow with volatility.
6. **Bot-failure scenario** (stuck position, disconnect). Promotion to Live ends the bot run (no API in Live).
