# Tradeify: official rules (checked 2026-10-28)

Grade: OFFICIAL. help.tradeify.co returns 403 to fetchers; the same articles were read on the intercom mirror `intercom.help/tradeify/...`. Every page says "Updated over a week ago" and gives no calendar date.
JSON drafts: `brain/_system/prop/firms/tradeify_{growth,select_flex,select_daily,lightning}_50k.json`.

## Sources
| # | Page |
|---|---|
| T1 | https://intercom.help/tradeify/en/articles/14369021-tradeify-pricing-reference |
| T2 | https://intercom.help/tradeify/en/articles/12268167-essential-trading-rules-overview |
| T3 | https://intercom.help/tradeify/en/articles/10468318-guidelines-for-traders |
| T4 | https://intercom.help/tradeify/en/articles/10495915-growth-evaluation-accounts |
| T5 | https://intercom.help/tradeify/en/articles/11083796-advanced-and-growth-account-payout-policies |
| T6 | https://intercom.help/tradeify/en/articles/12853921-select-evaluation-accounts |
| T7 | https://intercom.help/tradeify/en/articles/12853966-select-flex-and-select-daily-payout-policies |
| T8 | https://intercom.help/tradeify/en/articles/10495938-lightning-funded-accounts |
| T9 | https://intercom.help/tradeify/en/articles/10495932-lightning-funded-account-payout-policy |
| T10 | https://intercom.help/tradeify/en/articles/10495897-rules-trailing-max-drawdowns |
| T11 | https://intercom.help/tradeify/en/articles/10468321-rules-daily-loss-limit |
| T12 | https://intercom.help/tradeify/en/articles/10468320-rules-consistency-rule |
| T13 | https://intercom.help/tradeify/en/articles/12268494-common-faqs |
| T14 | https://intercom.help/tradeify/en/articles/10468221-supported-platforms |

## Prices (T1): all one-time, no activation fees
| Plan | 25K | 50K | 100K | 150K | Reset 50K |
|---|---|---|---|---|---|
| Growth | $99 | $145 | $255 | $369 | $95 |
| Select (40% consistency) | $109 | $165 | $265 | $369 | $109 |
| Select + 50% consistency add-on | $135 | $205 | $329 | $459 | $135 |
| Lightning Funded (no eval, no reset) | $345 | $492 | $660 | $796 | n/a |
No platform fees. MNQ commission $1.82 round trip (T1). Non-pro CME data is free.

## Evaluation (50K)
| Item | Growth | Select | Src |
|---|---|---|---|
| Target | $3,000 | $3,000 (legacy accounts $2,500) | T4, T6 |
| Max drawdown | $2,000 EOD trailing; breach is intraday on net liq; never locks in eval | $2,000 EOD trailing; never locks | T10 |
| DLL | $1,250 soft ("trading stops for the day but your account is not failed") | none | T4, T11 |
| Consistency | none | 40% (50% add-on); can't pass until met | T6, T12 |
| Min days | 1 | 3 | T4, T6 |
| Max size | 4 minis / 40 micros | 4 / 40 | T2 |
Daily close: flat by 4:45 PM ET (T2). At least 1 trade per week per account.

## Funded (50K)
| Item | Growth funded | Select Flex | Select Daily | Lightning | Src |
|---|---|---|---|---|---|
| Drawdown | $2,000 EOD | $2,000 EOD | $2,000 EOD | $2,000 EOD | T10 |
| Lock | at $50,100 when EOD ≥ $52,100 or on payout request | same | at $50,100 when EOD ≥ $52,100 | same as Growth | T7, T10 |
| DLL (soft) | $1,250, rises to $2,000 at $53,000 | none | $1,000 | $1,250, rises to $2,000 at $53,000 | T11 |
| Consistency | 35% (blocks payout) | none | none | 20% / 25% / 30% for payouts 1 / 2 / 3+ | T12 |
| Payout gate | 5 days ≥$150; balance ≥ $53,000 | 5 winning days ≥$150; positive net cycle profit | daily; balance stays ≥ $52,100 buffer | profit goal $3,000 then $2,000 | T5, T7, T9 |
| Payout size | cap per request $1,500 / $2,000 / $2,500 / $3,000 (payout 1/2/3/4+) | 50% of total profit, cap $2,500 (bought ≥ 2026-09-01) | up to 2× profit since last request, cap $1,250 | cap $2,000 (payouts 1-3), $2,500 (4+) | T5, T7, T9 |
| Min payout | $500 | $250 | $250 | $1,000 | |
| Split | 90% | 90% | 90% | 90% | |
| Size | 40 micros | 20 → 30 (+$1,500) → 40 (+$2,000) | same | 40 | T2, T7 |
Max 5 sim funded accounts per household (T13). Elite Live selection is possible after 3 payouts on one account (T13).

## Automation (T3, exact quotes)
- "At Tradeify, we allow the use of bots and algorithms under certain conditions:"
  1. "You must be able to prove that you are the sole owner of the bot or strategy" ... "and that no one else has access to or is using it."
  2. "We scan to ensure there are no similar orders on other accounts." "We will also require a live video of you enabling the code on your own PC."
  3. "While you may use the bot on your personal accounts, using it across multiple firms is against Tradeify's policy."
  4. "Personal bots are allowed as long as they are not high-frequency trading (HFT) bots."
- Microscalping (funded only): payout needs "Over 50% of your trades are longer than 10 seconds" and "Over 50% of your profit must come from trades held longer than 10 seconds." Missing this blocks the payout; it does not fail the account.
- VPN/VPS (T13): "You cannot log in with VPN/VPS. After logging in normally, you may use VPS for trading at your own risk."
- News: no restrictions. Hedging, including across accounts, is banned.

## How a Python program would place orders
Brokers (T14): "Tradovate (NinjaTrader, TradingView), Rithmic (Tradesea, Quantower, Sierra Chart, R|Trader) or WealthCharts". **No API is mentioned anywhere in the help centre.** Possible routes, none confirmed:
- NinjaTrader 8 on Jason's PC with a NinjaScript strategy, or ATI fed by a local Python process, over the Tradovate or Rithmic login. Fits the "own PC + live video" rule.
- Tradovate REST API: Tradovate community posts (2024-2026) say prop accounts don't get direct API access (COMMUNITY, not official).
- Rithmic R|Protocol API: gated by Rithmic's dev-kit and conformance approval (BLOG).
- Paid webhook bridges (TradersPost, PickMyTrade): third-party servers (BLOG).

## Open questions
1. Does Tradeify allow a direct Tradovate or Rithmic API connection? Needs a written answer from support.
2. Is the DLL measured on realized P&L or on net liq? (T11 doesn't say.)
3. Growth funded: what share of profit can be withdrawn? Only per-request caps are stated.
4. The Lightning profit goal: per cycle or cumulative?
5. Using the same bot at Topstep and Tradeify breaks "using it across multiple firms". Jason should pick one firm per bot.

## QA corrections 2026-10-28
Made by the quality agent (review: `brain/05_Reviews/prop-firm-grid-QA-2026-10-28.md`); JSON regenerated from `gen_firms.py`.
- **Growth 50K payout (`tradeify_growth_50k.json`).** Was `payout_buffer_rel_start_usd: 3000` with share 1.0, so the simulator could only pay the excess over $53,000. Official (T5 mirror https://intercom.help/tradeify/en/articles/11083796-growth-funded-account-payout-policy, read 2026-10-28): $53,000 is the minimum balance to *request*; requests are hard-capped by payout number ($1,500 / $2,000 / $2,500 / $3,000) and "the remainder stays in your account"; worked example: $53,000 balance, $1,500 request leaves $51,500. Now `payout_min_balance_rel_start_usd: 3000`, `payout_buffer_rel_start_usd: 0`, `payout_share_of_profit: 1.0` (a request never takes the balance to the $50,100 floor: clipped $1 above it).
- **Growth 35% consistency base.** T12 (https://intercom.help/tradeify/en/articles/10468320-rules-consistency-rule): "total profits accumulated from the first day of trading up to the payout request date" and "After an approved payout, the consistency % will reset" -> profit since the last payout (`cycle`), unchanged.
- **Select Daily 2x rule (`tradeify_select_daily_50k.json`).** T7 (https://intercom.help/tradeify/en/articles/12853966-select-flex-and-select-daily-payout-policies): "They may request up to 2x the profit earned between each payout request". Was text only (ignored by the loader); now `payout_max_cycle_profit_multiple: 2`.
- Not changed, noted: Growth funded DLL rises to $2,000 at $53,000 (not simulated: conservative); MNQ commission $1.82 round trip vs the workbench L3 cost built on Topstep fees (see review, finding H2).
