---
id: SUM-quant-research-universe
type: research_summary
status: active
title: What Professional Quants Actually Research and Trade
source_policy: brain/_system/research_source_quality_policy.md
---

# What Professional Quants Actually Research and Trade

## Bottom Line

The project should not be restricted to US equity ETFs, RSI, or even traditional assets. Professional quantitative investing spans multiple asset classes, time horizons, data types, and strategy families. The system should therefore keep a broad **research universe**, while applying increasingly strict evidence and testing gates as an idea moves toward a backtest.

Broad intake is useful; broad approval is not. A YouTube interview, practitioner blog, Reddit discussion, or unusual market observation can create a research lead, but it should not become a durable claim or strategy merely because it sounds sophisticated.

## Markets Used by Quantitative Firms

### Equities and ETFs

Quant firms trade individual equities, equity indices, and ETFs. Jane Street describes quantitative ETF liquidity provision and an offering spanning ETFs, equities, bonds, and options; its ETF underliers include equity, fixed-income, commodity, and crypto assets.[5]

### Government Bonds, Interest Rates, Currencies, and Commodities

Man Group describes traditional trend-following markets as liquid futures and forwards covering equity indices, government bonds, major foreign exchange, and core commodities.[2] These markets are useful because systematic strategies can take both long and short positions and diversify across different macroeconomic drivers.

### Futures and Forwards

In a J.P. Morgan interview, Aspect Capital co-founder Martin Lueck explains that liquid futures provide access to hundreds of markets and allow systematic trend strategies to participate in both rising and falling markets.[9] Futures are therefore a major professional quant research area, but they require correct contract rolls, margin treatment, and realistic execution costs.

### Options and Volatility

Jane Street reports active trading in index, ETF, and single-stock options as part of a broader cross-asset business.[5] Options and volatility strategies belong in the long-term research universe, but they require substantially better data and modeling than daily adjusted-close backtests.

### Digital Assets and Crypto

Crypto is a legitimate quantitative market rather than an automatic exclusion. Jane Street explicitly includes crypto-asset underliers in its ETP liquidity work,[5] while Wintermute describes algorithmic liquidity across digital-asset spot, options, forwards, CFDs, OTC, and DeFi markets.[6] Crypto ideas should still face market-specific checks for venue quality, fragmented liquidity, funding, custody, survivorship, manipulation, and 24/7 execution.

### Multi-Asset Portfolios

Two Sigma's factor-lens work argues that portfolios should be understood through overlapping risk factors rather than asset-class labels alone.[3] J.P. Morgan's quantitative-investing discussion similarly covers systematic macro, tactical allocation, and multi-asset research.[10]

## Strategy Families Used by Quants

### 1. Trend Following and Systematic Macro

Trend following is used across futures and forwards in equity indices, rates, currencies, and commodities.[2][9] Practitioner interviews emphasize that trends are episodic and unpredictable, so diversification across markets and disciplined risk management matter more than guessing which market will trend next.[8][9]

### 2. Style Premia and Factor Investing

AQR identifies value, momentum, carry, and defensive as major style-premia families studied across geographies and asset groups.[1] Two Sigma separates portfolio risks into macro factors, macro styles, and equity styles rather than treating every asset as independent.[3]

### 3. Statistical, Relative-Value, and Mean-Reversion Research

Professional systematic firms also look for small pricing, liquidity, and behavioral inefficiencies rather than relying on one indicator. Man AHL's Russell Korgaonkar describes many small opportunities across markets and stresses efficient execution and diversification.[8] Mean reversion belongs in the pool, but RSI is only one possible expression of that larger family.

### 4. Market Making and Liquidity Provision

HRT describes automated algorithms used to provide liquidity and competitive prices,[4] while Jane Street operates a broad cross-asset liquidity business.[5] This is genuine quant trading, but most market-making ideas are not realistic for the current daily-data MVP because they require order-book data, latency-aware execution, inventory models, and exchange-level fee details.

### 5. Alternative Data and Machine Learning

BlackRock describes alternative datasets ranging from satellite imagery and job postings to shipping records and scraped web content.[7] Its process emphasizes originality, coverage, timestamp reliability, data lineage, statistical power, economic intuition, and redundancy checks.[7] J.P. Morgan's practitioner discussion also portrays quantitative models as evolving research systems rather than one-time formulas.[10]

### 6. Portfolio Construction and Risk Models

Quant research is not only about finding entry signals. Factor exposure, position sizing, diversification, correlations, capacity, turnover, and risk budgeting are core parts of the investment process.[3][10]

## What This Means for Quant Agent Brain

The project should maintain an open opportunity map that includes:

- equities and ETFs;
- futures and systematic macro;
- bonds and interest rates;
- foreign exchange;
- commodities;
- options and volatility;
- crypto and digital-asset markets;
- factor and style premia;
- statistical arbitrage and relative value;
- market microstructure and liquidity;
- alternative-data and machine-learning signals;
- portfolio construction and risk allocation.

This list is a research universe, not a promise that every category is affordable or testable today.

## Recommended Research Funnel

```text
broad discovery
→ traceable research question
→ raw evidence with uncertainty labels
→ curated source note
→ method/strategy door
→ frozen strategy card
→ deterministic backtest
→ robustness and multiple-testing review
→ paper-trading review
```

The filters should become stricter at each stage:

1. **Discovery:** Allow unconventional ideas from blogs, videos, social discussions, papers, and practitioner interviews.
2. **Curation:** Require provenance, identifiable claims, conflicts, caveats, and an evidence-quality label.
3. **Strategy Door:** Require a plausible mechanism, accessible data, known risks, and a clear statement of what remains unresolved.
4. **Strategy Card:** Require exact rules, timing, universe, costs, sizing, benchmark, and validation plan before seeing results.
5. **Backtest promotion:** Require reproducible code, realistic data handling, multiple-testing controls, robustness checks, and an untouched evaluation period.

## Practical Scope Recommendation

Continue finishing one RSI strategy end to end so the testing pipeline is proven. In parallel, create a broader research map with several independent doors rather than collecting dozens of random parameter variations:

1. ETF mean reversion — current tracer strategy.
2. Multi-asset trend following — futures/ETF proxy first.
3. Cross-sectional factor investing — value, momentum, quality/defensive.
4. Carry and systematic macro — research first; data feasibility check required.
5. Options/volatility — parked until options-chain data is available.
6. Crypto systematic strategies — allowed, but only after a venue/data/cost policy exists.
7. Market making — educational research only until high-frequency data and infrastructure exist.
8. Alternative data/ML — later stage after the baseline research and validation process is trustworthy.

This avoids two bad extremes: an unrealistic system that rejects everything unusual, and a noisy system that promotes every polished-sounding idea.

## Sources

[1] https://www.aqr.com/Insights/Research/Journal-Article/Understanding-Style-Premia — AQR - Understanding Style Premia
[2] https://www.man.com/insights/trend-following-optimal-market-mix — Man Group - Optimal Market Mix for Trend Following
[3] https://www.twosigma.com/articles/revisiting-the-two-sigma-factor-lens — Two Sigma - Revisiting the Factor Lens
[4] https://www.hudsonrivertrading.com/liquidity — Hudson River Trading - Liquidity
[5] https://www.janestreet.com/what-we-do/client-offering — Jane Street - Client Offering
[6] https://www.wintermute.com — Wintermute - Digital Asset Markets
[7] https://www.blackrock.com/institutions/en-global/institutional-insights/thought-leadership/investment-actions/alt-data-for-systematic-investing — BlackRock - Alternative Data for Systematic Investing
[8] https://www.youtube.com/watch?v=ha0vIX3QKgw — Top Traders Unplugged - Russell Korgaonkar of Man AHL
[9] https://www.youtube.com/watch?v=RuJD_YWeoQY — J.P. Morgan - Aspect Capital Systematic Investing Interview
[10] https://www.youtube.com/watch?v=rmS9INWqJrg — J.P. Morgan Asset Management - Quantitative Investing Explained
