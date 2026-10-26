---
type: reading_list
status: unreviewed
retrieved: 2026-10-21
promoted: false
---
# Quant Trading Reading List (unreviewed)

> Links and notes only; no PDFs stored. Descriptions are from general knowledge of each work and are **not verified quotes**. Check against the source before citing. Buy, use a library copy, or use the free author copies linked.

## Textbooks
| Work | Link | What it teaches | Tags |
|---|---|---|---|
| Ernest Chan, *Quantitative Trading* (2nd ed., 2021) | https://www.wiley.com/en-us/Quantitative+Trading%3A+How+to+Build+Your+Own+Algorithmic+Trading+Business%2C+2nd+Edition-p-9781119800064 | Retail quant workflow: finding ideas, backtesting, execution, Kelly sizing | strategies, risk, fundamentals |
| Ernest Chan, *Algorithmic Trading: Winning Strategies and Their Rationale* (2013) | https://www.wiley.com/en-us/Algorithmic+Trading%3A+Winning+Strategies+and+Their+Rationale-p-9781118460146 | Mean reversion (cointegration, Kalman), momentum, risk | strategies, risk |
| Marcos López de Prado, *Advances in Financial Machine Learning* (2018) | https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086 | Labeling, meta-labeling, purged CV, backtest overfitting, bet sizing | AI/ML, backtesting |
| López de Prado, *Machine Learning for Asset Managers* (2020) | https://www.cambridge.org/core/elements/machine-learning-for-asset-managers/6D9211305EA2E425D33A9F38D0AE3545 | Denoising covariance, clustering, HRP, feature importance | AI/ML, portfolio |
| Robert Carver, *Systematic Trading* (2015) | https://www.harriman-house.com/authors/robert-carver/systematic-trading/9780857194459 | Framework for systematic rules, volatility targeting, forecast scaling | risk, strategies |
| Robert Carver, *Leveraged Trading* (2019) / *Advanced Futures Trading Strategies* (2023) | https://www.harriman-house.com/leveragedtrading , https://www.harriman-house.com/authors/robert-carver/advanced-futures-trading-strategies/9780857199683 | Position sizing with leverage; trend/carry futures strategies | risk, strategies |
| John Hull, *Options, Futures, and Other Derivatives* | https://www.pearson.com/en-us/subject-catalog/p/options-futures-and-other-derivatives/P200000005938 | Derivatives pricing, Greeks, volatility | fundamentals, risk |
| John Hull, *Risk Management and Financial Institutions* | https://www.wiley.com/en-us/Risk+Management+and+Financial+Institutions-p-9781119932482 | VaR, expected shortfall, stress testing | risk |
| Rishi Narang, *Inside the Black Box* (2nd ed.) | https://onlinelibrary.wiley.com/doi/book/10.1002/9781118662717 | Anatomy of a quant system: alpha, risk, cost, portfolio construction, execution | fundamentals |
| Ruey Tsay, *Analysis of Financial Time Series* (3rd ed.) | https://www.wiley.com/en-us/Analysis+of+Financial+Time+Series%2C+3rd+Edition-p-9780470414354 | ARMA, GARCH, multivariate/time-series econometrics | fundamentals, data |
| Stefan Jansen, *Machine Learning for Algorithmic Trading* (2nd ed.) | https://github.com/stefan-jansen/machine-learning-for-trading | Full ML pipeline with free code notebooks | AI/ML, data |
| Grinold & Kahn, *Active Portfolio Management* | https://www.mheducation.com/highered/product/active-portfolio-management-quantitative-approach-providing-superior-returns-controlling-risk-grinold-kahn/M9780070248823.html | Fundamental law of active management, IC, risk models | portfolio, fundamentals |
| Larry Harris, *Trading and Exchanges* | https://global.oup.com/academic/product/trading-and-exchanges-9780195144703 | Market microstructure, who trades and why | microstructure |
| Antti Ilmanen, *Expected Returns* | https://www.wiley.com/en-us/Expected+Returns%3A+An+Investor%27s+Guide+to+Harvesting+Market+Rewards-p-9781119990727 | Evidence on premia: value, momentum, carry, volatility | strategies |
| Edward Thorp, *A Man for All Markets* + Kelly papers | http://www.edwardothorp.com/ | Kelly criterion origins and practice | risk |
| Hastie, Tibshirani, Friedman, *Elements of Statistical Learning* (free from authors) | https://hastie.su.domains/ElemStatLearn/ | ML foundations | AI/ML |

## Key papers (free/official pages)
| Paper | Link | Why | Tags |
|---|---|---|---|
| Jegadeesh & Titman (1993), Returns to Buying Winners and Selling Losers | https://doi.org/10.1111/j.1540-6261.1993.tb04702.x | Cross-sectional momentum | strategies |
| Moskowitz, Ooi, Pedersen (2012), Time Series Momentum | https://doi.org/10.1016/j.jfineco.2011.11.003 | Trend following evidence | strategies |
| Asness, Moskowitz, Pedersen (2013), Value and Momentum Everywhere | https://doi.org/10.1111/jofi.12021 | Factors across asset classes | strategies |
| Gatev, Goetzmann, Rouwenhorst (2006), Pairs Trading | https://doi.org/10.1093/rfs/hhj020 | Stat-arb baseline | strategies |
| Avellaneda & Lee (2010), Statistical Arbitrage in the US Equities Market | https://doi.org/10.1080/14697680903124632 | PCA/ETF residual stat-arb | strategies |
| Fama & French (1993) / (2015) five-factor | https://doi.org/10.1016/0304-405X(93)90023-5 | Factor models | fundamentals |
| Bailey, Borwein, López de Prado, Zhu (2014), Probability of Backtest Overfitting | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 | PBO, CSCV | backtesting |
| Bailey & López de Prado (2014), The Deflated Sharpe Ratio | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 | Multiple-testing-adjusted Sharpe | backtesting |
| Harvey, Liu, Zhu (2016), ...and the Cross-Section of Expected Returns | https://doi.org/10.1093/rfs/hhv059 | Factor zoo / t>3 hurdle | backtesting |
| Gu, Kelly, Xiu (2020), Empirical Asset Pricing via Machine Learning | https://doi.org/10.1093/rfs/hhaa009 | ML return prediction benchmark | AI/ML |
| Kelly (1956), A New Interpretation of Information Rate | https://doi.org/10.1002/j.1538-7305.1956.tb03809.x | Kelly criterion | risk |
| Moreira & Muir (2017), Volatility-Managed Portfolios | https://doi.org/10.1111/jofi.12513 | Vol targeting | risk |
| Almgren & Chriss (2000), Optimal Execution | https://www.smallake.kr/wp-content/uploads/2016/03/optliq.pdf | Execution / market impact | microstructure |
| Connors & Alvarez (2009), *Short Term Trading Strategies That Work* | https://www.connorsresearch.com/ | RSI(2) mean reversion (Brain's existing RQ) | strategies |

## Articles / blogs / courses
| Source | Link | Tags |
|---|---|---|
| Robert Carver, Investment Idiocy blog | https://qoppac.blogspot.com/ | risk, strategies |
| Quantocracy (curated quant blog aggregator) | https://quantocracy.com/ | strategies |
| AQR research library | https://www.aqr.com/Insights/Research | strategies, fundamentals |
| Alpha Architect blog | https://alphaarchitect.com/blog/ | strategies |
| Hudson & Thames (ArbitrageLab, mlfinlab docs) | https://hudsonthames.org/ | AI/ML, strategies |
| QuantStart articles | https://www.quantstart.com/articles/ | fundamentals, backtesting |
| MIT OCW 18.S096 Topics in Mathematics with Applications in Finance | https://ocw.mit.edu/courses/18-s096-topics-in-mathematics-with-applications-in-finance-fall-2013/ | fundamentals |
| Quantopian lecture archive (community mirror) | https://github.com/quantopian/research_public | fundamentals, backtesting |

## Free data sources
| Source | Link | What | Tags |
|---|---|---|---|
| Kenneth French Data Library | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html | Factor returns, sorted portfolios | data |
| FRED | https://fred.stlouisfed.org/ | Macro & rates | data |
| SEC EDGAR APIs | https://www.sec.gov/edgar/sec-api-documentation | Filings, XBRL fundamentals (already used in repo data/raw/edgar) | data |
| yfinance (unofficial Yahoo) | https://github.com/ranaroussi/yfinance | Daily OHLCV; check survivorship/adjustments | data |
| Stooq | https://stooq.com/db/ | Free bulk daily data | data |
| AQR datasets | https://www.aqr.com/Insights/Datasets | Factor/TSMOM data | data |
| Open Source Asset Pricing (Chen & Zimmermann) | https://www.openassetpricing.com/ | 200+ replicated anomaly signals | data, strategies |
| Nasdaq Data Link (free tier) | https://data.nasdaq.com/ | Misc datasets | data |
| CBOE VIX history | https://www.cboe.com/tradable_products/vix/vix_historical_data/ | Volatility index | data, risk |
| Alpaca / Tiingo free tiers | https://alpaca.markets/ , https://www.tiingo.com/ | API price data, paper trading | data |
| WRDS/CRSP via St. John's library (if available) | https://wrds-www.wharton.upenn.edu/ | Survivorship-free research data | data |

## Link check (2026-10-21)
- Fixed 3 dead links (404): Carver *Systematic Trading* and *Advanced Futures Trading Strategies* (Harriman House moved pages), Narang *Inside the Black Box* (now Wiley Online Library page).
- 403/000 on doi.org (Wiley/OUP), SSRN, SEC, FRED, Stooq, Thorp site, QuantStart = bot-blocking/timeouts from the check script, not confirmed dead; open in a browser.
- Free author/official PDFs + quote notes saved under `brain/sources/papers/` (see `papers/_INDEX.md`).
