# FundedNext Futures: official rules (checked 2026-10-28)

Grade: OFFICIAL (helpfutures.fundednext.com, the futures help centre; help.fundednext.com covers CFDs only). Dates are the page `dateModified`.
JSON drafts: `brain/_system/prop/firms/fundednext_{rapid_pro,rapid_daily,flex,direct}_50k.json`.

**Product changes:** "As of October 11, Legacy Accounts are no longer available for purchase" (existing Legacy accounts can't be reset). **Bolt** has no help-centre collection any more; only an old FAQ line on fundednext.com/futures mentions it, so it's treated as discontinued. Current lineup: Rapid Pro, Rapid Daily, Flex, Direct.

## Sources (prefix https://helpfutures.fundednext.com/en/articles/)
| # | Article | Date |
|---|---|---|
| F1 | 14298560-is-the-usage-of-automated-trading-systems-eas-and-bots-allowed-in-fundednext-futures | 2026-04-09 |
| F2 | 17230388-does-fundednext-futures-allow-high-frequency-trading-hft | 2026-09-30 |
| F3 | 17230319-what-is-copy-group-trading-policy-at-fundednext-futures | 2026-09-30 |
| F4 | 17225812-how-many-accounts-can-i-hold-... | 2026-09-30 |
| F5 | 17228899-what-are-the-available-account-sizes-and-their-prices-in-fundednext-futures | 2026-10-13 |
| F6 | 17228852-what-are-the-reset-conditions-and-fees-at-fundednext-futures | "over 2 weeks ago" |
| F7 | 17230292-daily-loss-limit-and-maximum-loss-limit-at-fundednext-futures | 2026-10-24 |
| F8 | 17230245-is-there-any-consistency-rule-... | 2026-10-24 |
| F9 | 17229677-fundednext-futures-rapid-pro-challenge-all-rules | 2026-09-30 |
| F10 | 17229713-fundednext-futures-rapid-pro-fundednext-account-all-rules | 2026-09-30 |
| F11 | 17229762-fundednext-futures-rapid-daily-challenge-all-rules | 2026-09-30 |
| F12 | 17229779-fundednext-futures-rapid-daily-fundednext-account-all-rules | 2026-09-30 |
| F13 | 17229829-fundednext-futures-flex-challenge-all-rules | 2026-10-13 |
| F14 | 17229848-fundednext-futures-flex-fundednext-account-all-rules | 2026-10-25 |
| F15 | 17430065-fundednext-futures-direct-account-all-rules | 2026-10-07 |
| F16 | 17229536 / 17229581 Legacy challenge / funded rules | 2026-10-24 |
| F17 | 14298337-what-are-the-prohibited-trading-strategies-of-fundednext-futures | 2026-09-30 |

## 50K rules
| Item | Rapid Pro | Rapid Daily | Flex | Direct | Src |
|---|---|---|---|---|---|
| Price (offer / list) | $169.99 / $299.98; with DLL add-on $129.99 | $169.99 / $299.98 (shared table) | $74.99 first 2 buys, $84.99 after / $141.99 | $169.99 / $283.99 | F5 |
| Reset | $174.99 (add-on $134.99) | $189.99 | $82.99 | none | F6 |
| Target | $3,000 | $3,000 | $2,500 | none | F9, F11, F13 |
| MLL | $2,000 EOD trailing | $2,000 EOD | $1,500 EOD | $2,000 EOD | |
| MLL updates / breach | trail updates at 5 PM CT close; a floating loss that touches MLL breaches instantly | | | | F7 |
| Lock | at start+$100 ($50,100) | same | same | same | F7 |
| DLL | none; add-on $1,000 | $1,000 soft | none | $1,000 soft | F7 |
| Eval consistency | none | none | single day ≤40% of target ($1,000); otherwise target = best day / 0.40 | n/a | F8, F13 |
| Max size | 40 micros | 40 | 30 | 30 | |
| Funded consistency | 40%, ≥3 days (blocks payout) | none | none | 20% perpetual (best day ever ≤20% of cycle profit) | F8 |
| Payout gate | every 3 days, ≥$500 cycle profit | daily, ≥$500 cycle profit, withdraw EOD profit above $52,100 buffer | 5 benchmark days ≥$200, ≥$500 cycle profit | clear $2,100 buffer in cycle, no profit goal | F10, F12, F14, F15 |
| Payout size | $250–$1,200 | $250–$1,200 | 50% of profit, max $1,500 (min $250) | $800–$1,200 | |
| Split | 90% | 90% | 95% | 90% | |
| After payouts | concluded after 5th reward | concluded after 5th | first withdrawal moves MLL to $50,100; concluded after 5th | concluded after 5th | |
DLL (F7): "Hitting the daily loss limit is a soft breach: trading is disabled for the rest of the day." It counts closed and floating losses.
Accounts (F4): up to 5 active FundedNext accounts, 10 issued per calendar month, $750K total challenge allocation, per user and household.
Legacy 50K (discontinued, F16): $199.99, target $3,000, MLL $2,000 EOD locking at the initial balance, 40% eval consistency; funded 80% split, 5 benchmark days ≥$200, 50% of profit capped at $3,000 (cap removed after 30 benchmark days).

## Automation (exact quotes)
- F1: "FundedNext Futures allows the use of automated trading systems, including Expert Advisors (EAs) and trading bots", in the Challenge and on FundedNext Accounts. FundedNext gives no setup support and isn't liable for malfunctions. Latency abuse and order flooding are "strictly prohibited".
- F2: "No, FundedNext Futures does not allow High-Frequency Trading." "Automated trading systems and algorithms are monitored on FundedNext Futures Accounts." "The use of automated tools does not exempt a trader from compliance".
- Copy trading (F3): "Copy trading within FundedNext is allowed." Copying between your own accounts, or to other firms where you own all accounts, is fine. Signal services and group trading are banned.
- Micro-scalping (F9, F10): if trades closed within 10 s make up ≥30% of cycle profit you get a warning. At ≥40% that profit is deducted (funded) or target progress is paused (challenge).
- VPS/VPN: not mentioned in the futures help centre.

## How a Python program would place orders
Platforms: Tradovate, NinjaTrader, TradingView (help-centre platform FAQ; fundednext.com/futures). **No API is documented.** Same candidate routes as Tradeify/Lucid (NinjaTrader 8 locally; Tradovate API reportedly disabled for prop accounts; webhook bridges). None is confirmed.

## Open questions
1. Billing type isn't stated explicitly (no recurring charge is mentioned; drafted as one-time). Activation fee isn't stated (website/blog: $0).
2. Rapid Pro + DLL add-on price: $129.99 (F5) vs $109.99 (F6).
3. The Direct "$2,100 buffer" may mean cycle profit ≥ $2,100 or balance ≥ start + $2,100.
4. F6 contradicts itself on when trading resumes after a DLL breach.
5. Python order route (needs written confirmation that Tradovate API or NinjaTrader ATI is allowed).

## QA corrections 2026-10-28
Made by the quality agent (review: `brain/05_Reviews/prop-firm-grid-QA-2026-10-28.md`); JSON regenerated from `gen_firms.py`.
- **Flex payout base (`fundednext_flex_50k.json`).** F14 (https://helpfutures.fundednext.com/en/articles/17229848-fundednext-futures-flex-fundednext-account-all-rules, read 2026-10-28): "Up to 50% of your profit per cycle", max $1,500. The loader applied 50% to total profit (balance - start), which after the first payout double-counts the unpaid half. Now `payout_base: "cycle"` (50% of profit since the last payout).
- **Direct perpetual consistency (`fundednext_direct_50k.json`).** F15 (https://helpfutures.fundednext.com/en/articles/17430065-fundednext-futures-direct-account-all-rules): best day "may not exceed 20% of your current cycle's total profit"; "perpetual" = "tracks your all-time best trading day across every trading cycle". The text was in `funded_consistency_effect` only and the loader defaulted the scope to `cycle`. Now `funded_consistency_scope: "best_ever"`.
- Open, not changed: Direct "$2,100 buffer in your current cycle" may mean cycle profit >= $2,100 each cycle (stricter than the balance reading the JSON uses); Flex price rises to $84.99 from the 3rd purchase (simulator uses $74.99 for every purchase).
