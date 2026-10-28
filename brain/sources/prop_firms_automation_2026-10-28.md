# Prop firms: can a self-written Python bot trade fully automated? (2026-10-28, first pass)

Requirement from Jason: fully automated order entry (no clicking). Grade: OFFICIAL = firm's own help centre; BLOG = third-party (often affiliates), conflicting.

| Firm | Full automation | How orders get in | Notes | Grade |
|---|---|---|---|---|
| **Topstep** | Yes: Combine + XFA (sim). **No on Live** (API not available on Live) | TopstepX / ProjectX API | HFT banned. **All trading must originate from your personal device: VPS, VPN and remote servers are prohibited** (a server may watch/record, not trade). No API support from Topstep. API subscription ~$29/mo (blog; check) | OFFICIAL ([API access](https://help.topstep.com/en/articles/11187768-topstepx-api-access)) |
| **Tradeify** | Yes, if you own the strategy exclusively, it is not HFT, and you can prove ownership (blog: may ask for a live video) | Unclear (Tradovate platform mentioned; API route not stated) | Funded payouts need >50% of trades AND profits from holds >10 s. Growth eval 50K: DLL $1,250, no consistency; EOD trailing DD enforced in real time. 40 micros max. Price not read (plan page 403) | OFFICIAL ([rules](https://intercom.help/tradeify/en/articles/12268167-essential-trading-rules-overview)) + BLOG |
| **Lucid Trading** | Likely yes (eval + funded, per several blogs); one listing says no for LucidDirect | Unclear | HFT/microscalping banned (automated detection). LucidFlex 50K ~$140 (blog) | BLOG |
| **FundedNext Futures** | Likely yes, all accounts incl. EAs (blog) | Unclear | Copy trading up to 5 accounts; microscalping limited. 50K from ~$100–200 (blog, conflicting) | BLOG |
| MyFundedFutures | Unclear; most say fully autonomous bots banned | Tradovate | | BLOG |
| TradeDay | Custom strategies only via NinjaTrader/Tradovate/TradingView; no direct API | | | BLOG |
| Apex | **No** for funded (bots/algos/AI banned in PA accounts); DCA-on-losers banned since 2026-03-01 | | | BLOG |
| Take Profit Trader | **No** ("No Trading Bots or Algos") | | | BLOG |
| Alpha Futures | **No / disputed** (manual or semi-automated only) | | | BLOG |

## Takeaways
- Topstep is the only firm whose official pages confirm a supported API for bots. The bot must run on Jason's own PC (no VPS). Any firm we add needs its official rules plus a working API route confirmed first.
- Candidates worth verifying officially: Tradeify, Lucid, FundedNext Futures. The open question for each is the order-entry route for Python (ProjectX-style API vs Tradovate/Rithmic).
- Live (real-money) Topstep accounts can't use the API, so the bot only works through the Combine and XFA stages.
