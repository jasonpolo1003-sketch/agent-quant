---
type: cost_assumption_note
research_question: RQ-80be8cf7
status: unreviewed
promoted: false
created: "2026-10-21"
---
# Transaction-cost assumptions for SPY / QQQ / IWM daily backtests (RQ-80be8cf7)

## 1. Direct evidence (quoted spreads)
| Source | SPY | QQQ | IWM | Notes |
|---|---|---|---|---|
| Issuer 30-day median bid/ask spread (NBBO every 10 seconds, relative to midpoint) | 0.00% (SSGA, as of 2026-10-20) | 0.00% (Invesco page, as of 2026-02-23) | 0.00% (iShares, as of 2026-10-20) | Displayed as 0.00%, which means under 0.5 bp. One-cent tick at current prices (~$670 / ~$600 / ~$240) is about 0.15 / 0.17 / 0.4 bp. |
| SSGA "SPY liquidity" insight | ~0.11 bp half-spread plus ~0.08 bp impact for a $25m VWAP trade (search-summary figure; **not yet verified on the page**) | | | https://www.ssga.com/us/en/institutional/insights/spy-liquidity-flexibility-to-navigate-any-market |
| Frazzini-Israel-Moskowitz 2018 (brain/sources/papers) | "actual trading costs to be an order of magnitude smaller than previous studies suggest" | | | Institutional stock trades, not ETFs |

Links:
- https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy
- https://www.invesco.com/us/en/financial-products/etfs/invesco-qqq-trust-series-1.html
- https://www.ishares.com/us/products/239710/ishares-russell-2000-etf

SEC Rule 605 reports (market-center execution quality for SPY/QQQ/IWM, which give effective vs quoted spreads) were **not retrieved**. Each market center publishes its own reports, and the amended 605 (compliance 2025-2026) format varies. Next step: pull Virtu, Citadel Securities or another wholesaler's monthly 605 files and filter by symbol.

## 2. Historical eras (no tick data; anchored to tick size and price)
- **Pre-decimalization (before April 2001):** 1/16 or 1/8 dollar ticks. SPY at ~$100–150 gives one tick of $0.0625, about 4–6 bp quoted. QQQ (1999–2001, ~$50–100) is about 6–12 bp. IWM launched in 2000.
- **2001–2007:** one-cent ticks with lower depth. Roughly 1–3 bp SPY/QQQ, 2–5 bp IWM.
- **2008–2009 and March 2020 stress:** spreads and impact widened. Use 2–3 times the calm-era level.
- **2010–2026:** SPY/QQQ about 0.2–1 bp, IWM about 0.4–1.5 bp quoted. For retail-size market orders the effective cost is about half the spread or less.

These ranges are reasoned estimates from tick size and price, **not** measured data. Label them that way.

## 3. OHLC estimators computed from repo Tiingo raw OHLC (`ohlc_spread_estimates.csv`, `spread_est.py`)
| | SPY 2015-19 | SPY 2021-26 | QQQ 2015-19 | IWM 2015-19 |
|---|---|---|---|---|
| Corwin-Schultz | 18 bp | 23 bp | 23 bp | 28 bp |
| EDGE (simplified) | 19 bp | 37 bp | 19 bp | 21 bp |

**Do not use these as cost inputs.** They overstate spreads by about two orders of magnitude for these ETFs, because the estimators assume the spread is the main source of high-low range and close-to-mid noise. For instruments with spreads under 1 bp, volatility dominates. Supporting evidence:
- they spike with volatility (2020: 40–127 bp)
- Abdi-Ranaldo clips to 0 in several eras

Ardia et al. (2024) note small-spread regimes are the hard case for these estimators. The EDGE implementation here is a simplified version, not the reference package; validate with the official `bidask` package before reuse.
**Use:** relative stress indicator only.

## 4. Recommended backtest cost levels (per side, applied to traded notional)
| Level | SPY | QQQ | IWM | Purpose |
|---|---|---|---|---|
| Base (2010+) | 1 bp | 1 bp | 2 bp | Half-spread, small slippage and a buffer for open/close auction prints |
| Base (2001–2009) | 2 bp | 3 bp | 4 bp | |
| Base (pre-2001) | 5 bp | 8 bp | 8 bp | |
| Stress | 2× base | 2× base | 2× base | Required pass gate |
| Severe | 10 bp | 10 bp | 15 bp | Shows breakeven sensitivity |

Also report the **breakeven cost per side** (gross edge per trade ÷ 2). RX-0001 already showed no edge before cost concerns, so costs are not the binding constraint there. Next-open vs same-close **fill timing** matters more (see Lou-Polk-Skouras note).

## Caveats
- Commissions are assumed 0 (current retail). Add about 1 bp or more before 2019 if modeling a retail account.
- Auction (MOO/MOC) fills have no spread but carry auction-imbalance risk.
- Issuer figures are current snapshots, not history.
