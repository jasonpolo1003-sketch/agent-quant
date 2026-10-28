# ProjectX Gateway API (TopstepX) — notes for the SC-FUT-0005 bot (2026-10-28)

Read from the public docs at gateway.docs.projectx.com and Topstep's help centre on 2026-10-28. Code: `src/quant_brain/live/projectx.py` (inert skeleton; not yet run against the API). Grade: OFFICIAL unless marked.

## Topstep rules for API use (OFFICIAL, [help.topstep.com 11187768](https://help.topstep.com/en/articles/11187768-topstepx-api-access))
- Works on simulated accounts only (Trading Combine, Express Funded). **Not on Live Funded.**
- **Orders must come from your personal device.** VPS, VPN and remote servers are banned for anything that can place, modify or cancel orders (a server may only watch and record). Breaking this can mean suspension.
- API access is a separate subscription: $29/month, $14.50 with code "topstep" (billed by Sim2Funded Solutions). HFT banned. API orders are final. No sandbox: test on a Practice account. Topstep gives no API coding support.

## REST (all POST JSON; base `https://api.topstepx.com`; token as `Authorization: Bearer <token>`)
| Endpoint | Body | Returns |
|---|---|---|
| `/api/Auth/loginKey` | `userName`, `apiKey` | `token` (24 h). A failed login is HTTP 200 with `success:false`: read the body |
| `/api/Auth/validate` | — | `newToken` |
| `/api/Account/search` | `onlyActiveAccounts` | `accounts[{id, name, canTrade, isVisible}]` |
| `/api/Contract/search` | `searchText`, `live` | up to 20 `contracts[{id, name, description, tickSize, tickValue, activeContract, symbolId}]` |
| `/api/Contract/available` | `live` | all contracts |
| `/api/History/retrieveBars` | `contractId, live, startTime, endTime, unit (1 s, 2 min, 3 h, 4 day, 5 wk, 6 mo), unitNumber, limit (≤ 20,000), includePartialBar` | `bars[{t,o,h,l,c,v}]`, UTC, example newest first |
| `/api/Order/place` | `accountId, contractId, type (1 limit, 2 market, 4 stop, 5 trailing stop, 6 join bid, 7 join ask), side (0 bid/buy, 1 ask/sell), size`, optional `limitPrice, stopPrice, trailPrice, customTag (unique per account), stopLossBracket, takeProfitBracket` | `orderId` |
| `/api/Order/cancel` | `accountId, orderId` | — |
| `/api/Order/searchOpen` | `accountId` | `orders[{id, contractId, status, type, side, size, limitPrice, stopPrice, filledPrice, ...}]` |
| `/api/Order/search`, `/api/Order/modify` | — | not used |
| `/api/Position/searchOpen` | `accountId` | `positions[{contractId, type (1 long, 2 short), size, averagePrice}]` |
| `/api/Position/closeContract` | `accountId, contractId` | — |
| `/api/Trade/search` | `accountId, startTimestamp, endTimestamp?` | `trades[{profitAndLoss (null = opening half-turn), fees, side, size, voided, orderId}]` |

Every response has `success`, `errorCode`, `errorMessage`. Rate limits: retrieveBars 50 / 30 s; all else 200 / 60 s; HTTP 429 beyond. Brackets need the account in Auto OCO Brackets mode (else errorCode 2, order still created).

## Realtime (SignalR over WebSockets; token as `access_token` query parameter)
- User hub `https://rtc.topstepx.com/hubs/user`: `SubscribeAccounts`, `SubscribeOrders(accountId)`, `SubscribePositions(accountId)`, `SubscribeTrades(accountId)`; events `GatewayUserAccount/Order/Position/Trade`.
- Market hub `https://rtc.topstepx.com/hubs/market`: `SubscribeContractQuotes/Trades/MarketDepth(contractId)`; events `GatewayQuote`, `GatewayTrade`, `GatewayDepth`.
- OrderStatus 0 none, 1 open, 2 filled, 3 cancelled, 4 expired, 5 rejected, 6 pending.

## Open questions (settle on a Practice account, read-only calls first)
- Is a bar's `t` its start? (assumed). Are minute bars available within ~1 s of the close via retrieveBars, or must we build them from `GatewayTrade`? This decides the feed; the 5-second order rule needs the bar for HH:29 within a second or two.
- Side codes in Trade/search and Order/searchOpen (assumed the Order/place codes); is `size` unsigned there?
- MNQ contract id format (likely `CON.F.US.MNQ.<month><yy>`; find with Contract/search "MNQ") and which contract TopstepX treats as front vs our volume roll.
- Does `live: true` on retrieveBars need a paid CME data subscription on TopstepX?
- Doc pages for Account search returned 403 to the fetcher; fields above come from the "placing your first order" guide.
- Older snippets show a demo host `gateway-api-demo.s2f.projectx.com`; TopstepX docs show `api.topstepx.com`.
