# Lucid Trading: official rules (checked 2026-10-28)

Grade: OFFICIAL for rules (support.lucidtrading.com, read via the mirror `intercom.help/lucid-trading/...`). **Prices are not official:** the help centre gives no dollar prices, and lucidtrading.com returns 403.
JSON drafts: `brain/_system/prop/firms/lucid_{flex,pro,direct}_50k.json`.
Current plans in the help centre: LucidFlex, LucidDaily (new; not researched), LucidPro, LucidDirect, LucidMaxx, LucidBlack (legacy).

## Sources
| # | Page | Date |
|---|---|---|
| L1 | /articles/12945790-lucidflex-evaluation-account | "over a week ago" |
| L2 | /articles/12945795-lucidflex-funded-account | "over 2 weeks ago" |
| L3 | /articles/12945796-lucidflex-payouts | 2026-07-28 |
| L4 | /articles/12945815-lucidflex-drawdown | 2026-08-26 |
| L5 | /articles/12945805-lucidflex-consistency-percentage | "over a week ago" |
| L6 | /articles/12945808-lucidflex-scaling-plan | 2026-05-06 |
| L7 | /articles/12890029-lucidpro-evaluation-account | 2026-08-26 |
| L8 | /articles/12890069-lucidpro-funded-account | 2026-08-26 |
| L9 | /articles/12890092-lucidpro-payouts | "over a week ago" |
| L10 | /articles/12890122-lucidpro-daily-loss-limit | 2026-07-26 |
| L11 | /articles/12890109-lucidpro-consistency-percentage | (applies to purchases ≥ 2025-11-28) |
| L12 | /articles/12890136-lucidpro-drawdown | 2026-08-26 |
| L13 | /articles/12890148-luciddirect-funded-account | 2026-08-26 |
| L14 | /articles/12890164-luciddirect-payout-objectives | 2026-08-26 |
| L15 | /articles/12890185-luciddirect-daily-loss-limit | "over a week ago" |
| L16 | /articles/12890192-luciddirect-drawdown | 2026-08-26 |
| L17 | /articles/11404728-other-trading-activities | 2026-08-26 |
| L18 | /articles/11404736-prohibited-high-frequency-trading | 2026-08-26 |
| L19 | /articles/11404742-prohibited-microscalping | 2026-08-26 |
| L20 | /articles/11404614-lucid-trading-supported-platforms | |
| L21 | /articles/11404620-simulated-account-fees | |
(prefix: https://intercom.help/lucid-trading/en)

## 50K rules
| Item | LucidFlex | LucidPro | LucidDirect | Src |
|---|---|---|---|---|
| Price | one-time, $ not official (BLOG ~$146) | one-time, $ not official (BLOG $129.50–$192) | one-time, $ not official | L1, L7, L21 |
| Reset | paid, $ not official (BLOG ~$90) | (BLOG ~$115) | n/a | L21 |
| Activation | none ("No activation fees to upgrade") | none | n/a | L1, L21 |
| Target | $3,000 | $3,000 | none (straight to funded) | L1, L7 |
| Max Loss Limit | $2,000 EOD | $2,000 EOD | $2,000 EOD | L4, L12, L16 |
| Lock | at $50,100 once balance > $52,100; on payout request MLL jumps to $50,100 | at $50,100 once > $52,100 | at $50,100 once > $52,100 | L4, L12, L16 |
| Eval DLL | optional on/off at checkout (amount not stated) | $1,200 soft | n/a | L1, L10 |
| Eval consistency | 40% (50% add-on); blocks the upgrade, no fail | none stated ("pass in one trading day") | n/a | L5, L7 |
| Max size | 40 micros | 40 micros | 40 micros | L1, L7, L13 |
| Funded DLL | optional | $1,200; once closed above $52,100 becomes 60% of highest EOD profit (never decreases) | $1,200, then 60% scaling | L8, L10, L15 |
| Funded consistency | none | 40% per payout cycle (blocks payout) | 20% per cycle | L2, L11, L14 |
| Funded scaling | profit <$1k: 20 micros; $1k–2k: 30; ≥$2k: 40 | none | none | L6 |
| Payout gate | 5 days ≥$150 in cycle, positive net cycle profit | ≥$500 cycle profit; buffer $52,100 | profit goal $3,000 then $2,500 | L3, L9, L14 |
| Payout size | 50% of profit, cap $2,000 | cap $2,000 (payout 1), $2,500 (2+) | cap $2,000 (1–3), $2,500 (4–5) | L3, L9, L14 |
| Min payout | $500 | $500 | $500 | |
| Split | 90/10 | 90/10 | 90/10 | |
| Payout count | max 5, then moved live | not stated | caps listed for 5 payouts | L3 |
All DLLs are soft: "All DLLs at Lucid Trading are considered soft breaches" (L10). Trading stops until the next session.

## Automation (exact quotes)
- L17: "Automated trading systems and trade copiers are permitted." "All automated activity must comply with Lucid Trading rules." "Traders are fully responsible for any software errors, malfunctions, or unintended outcomes." No plan is named, so this reads as all plans.
- News (L17): "Trading red folder news on the LucidDaily is a hard breach." Flex, Pro and Direct may trade news.
- HFT (L18): banned, no numeric threshold given ("hundreds of orders being placed within minutes"). Penalties go warning → profits removed → accounts closed.
- Microscalping (L19): flagged when "More than 50% of your profits are generated from trades held for 5 seconds or less"; "prohibited on evaluation and funded accounts".
- VPS/VPN, ownership checks, device rules: not covered in the help centre (BLOG: shared devices forbidden).

## How a Python program would place orders
Platforms (L20): CQG feed (NinjaTrader, Tradovate, TradingView) or Rithmic (Quantower, Tradesea, R|Trader Pro, Sierra Chart, ATAS, MultiCharts, ...). "All listed platforms work with all Lucid account types." **No API is documented.** ProjectX is no longer offered (BLOG: dropped Dec 2025). Same candidate routes as Tradeify: NinjaTrader 8 locally, Tradovate API (reportedly disabled for prop accounts), Rithmic R|Protocol (gated), or webhook bridges. None is confirmed.

## Open questions
1. Official prices and reset fees for every plan (help centre has none; site blocks fetchers).
2. LucidFlex optional DLL amount (BLOG: $1,200).
3. LucidPro/Direct funded pages say "No simulated payout caps", but the payout pages list caps. The caps are used in the drafts.
4. LucidPro funded DLL: called "optional" on one page and "fixed $1,200" on another.
5. Does the eval MLL lock too? (L4 says the same EOD system applies to eval and funded.)
6. Python order route, and whether automation is allowed on Lucid Live.
