# SC-0002: held-out report (2016-01-04..2026-09-25)

> A backtest is not proof of future profit.

Second-implementation cross-check of rule A: not re-run on this period; the in-sample cross-check matched (required before the held-out read).

## Verdict: **no edge shown**

| Criterion | Value | Test | Passed |
| --- | --- | --- | --- |
| positive average trade | 0.003 | > 0.0 | yes |
| beats random entry | 94.900 | >= 95.0 | no |
| deflated Sharpe | 0.896 | >= 0.95 | no |
| beats buy-and-hold risk-adjusted | -0.426 | > 0.0 | no |

## Trials

| Rule | Symbol | Cost bps | Trades | Avg trade | Win rate | Total return | CAGR | Sharpe | Max DD | Days held |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buy&hold | SPY | 2.0 | 1 | 357.30% | 100.00% | 357.30% | 15.26% | 0.890 | -33.72% | 100.00% |
| buy&hold | SPY | 5.0 | 1 | 357.03% | 100.00% | 357.03% | 15.25% | 0.890 | -33.72% | 100.00% |
| buy&hold | SPY | 10.0 | 1 | 356.57% | 100.00% | 356.57% | 15.24% | 0.890 | -33.72% | 100.00% |
| buy&hold | QQQ | 2.0 | 1 | 633.54% | 100.00% | 633.54% | 20.46% | 0.949 | -35.12% | 100.00% |
| buy&hold | QQQ | 5.0 | 1 | 633.10% | 100.00% | 633.10% | 20.45% | 0.949 | -35.12% | 100.00% |
| buy&hold | QQQ | 10.0 | 1 | 632.37% | 100.00% | 632.37% | 20.44% | 0.948 | -35.12% | 100.00% |
| buy&hold | IWM | 2.0 | 1 | 192.06% | 100.00% | 192.06% | 10.53% | 0.555 | -41.13% | 100.00% |
| buy&hold | IWM | 5.0 | 1 | 191.88% | 100.00% | 191.88% | 10.52% | 0.554 | -41.13% | 100.00% |
| buy&hold | IWM | 10.0 | 1 | 191.59% | 100.00% | 191.59% | 10.51% | 0.554 | -41.13% | 100.00% |
| A | SPY | 2.0 | 91 | 0.38% | 72.53% | 40.01% | 3.19% | 0.548 | -12.03% | 11.19% |
| B | SPY | 2.0 | 68 | 0.38% | 79.41% | 28.40% | 2.36% | 0.407 | -8.49% | 13.53% |
| D | SPY | 2.0 | 174 | 0.25% | 65.52% | 47.78% | 3.72% | 0.385 | -36.62% | 17.94% |
| A | SPY | 5.0 | 91 | 0.32% | 68.13% | 32.57% | 2.67% | 0.464 | -12.98% | 11.19% |
| B | SPY | 5.0 | 68 | 0.34% | 79.41% | 24.52% | 2.07% | 0.361 | -8.95% | 13.53% |
| D | SPY | 5.0 | 174 | 0.19% | 63.79% | 33.12% | 2.71% | 0.296 | -37.79% | 17.94% |
| A | SPY | 10.0 | 91 | 0.22% | 68.13% | 21.03% | 1.80% | 0.324 | -14.53% | 11.19% |
| B | SPY | 10.0 | 68 | 0.26% | 79.41% | 18.32% | 1.58% | 0.284 | -9.69% | 13.53% |
| D | SPY | 10.0 | 174 | 0.09% | 58.05% | 11.85% | 1.05% | 0.150 | -39.94% | 17.94% |
| A | QQQ | 2.0 | 89 | 0.37% | 69.66% | 37.16% | 3.00% | 0.411 | -10.64% | 12.27% |
| B | QQQ | 2.0 | 69 | 0.50% | 81.16% | 38.82% | 3.11% | 0.403 | -11.94% | 15.20% |
| D | QQQ | 2.0 | 173 | 0.41% | 66.47% | 94.66% | 6.42% | 0.543 | -22.83% | 18.38% |
| A | QQQ | 5.0 | 89 | 0.31% | 67.42% | 30.03% | 2.48% | 0.348 | -11.20% | 12.27% |
| B | QQQ | 5.0 | 69 | 0.45% | 79.71% | 34.46% | 2.80% | 0.368 | -11.94% | 15.20% |
| D | QQQ | 5.0 | 173 | 0.35% | 64.74% | 75.46% | 5.39% | 0.469 | -24.14% | 18.38% |
| A | QQQ | 10.0 | 89 | 0.21% | 65.17% | 18.95% | 1.63% | 0.243 | -12.81% | 12.27% |
| B | QQQ | 10.0 | 69 | 0.37% | 78.26% | 27.50% | 2.30% | 0.309 | -11.94% | 15.20% |
| D | QQQ | 10.0 | 173 | 0.25% | 61.85% | 47.57% | 3.70% | 0.344 | -26.27% | 18.38% |
| A | IWM | 2.0 | 77 | 0.31% | 74.03% | 24.52% | 2.07% | 0.318 | -19.63% | 11.23% |
| B | IWM | 2.0 | 57 | 0.14% | 77.19% | 1.17% | 0.11% | 0.065 | -39.87% | 14.83% |
| D | IWM | 2.0 | 169 | 0.22% | 61.54% | 33.02% | 2.70% | 0.274 | -37.21% | 20.42% |
| A | IWM | 5.0 | 77 | 0.25% | 71.43% | 18.90% | 1.63% | 0.259 | -20.32% | 11.23% |
| B | IWM | 5.0 | 57 | 0.10% | 77.19% | -1.45% | -0.14% | 0.042 | -40.18% | 14.83% |
| D | IWM | 5.0 | 169 | 0.16% | 60.36% | 20.19% | 1.73% | 0.200 | -38.31% | 20.42% |
| A | IWM | 10.0 | 77 | 0.15% | 67.53% | 10.08% | 0.90% | 0.160 | -21.47% | 11.23% |
| B | IWM | 10.0 | 57 | 0.02% | 70.18% | -5.66% | -0.54% | 0.004 | -40.69% | 14.83% |
| D | IWM | 10.0 | 169 | 0.06% | 59.17% | 1.49% | 0.14% | 0.075 | -40.11% | 20.42% |

## Data

```json
{
 "card_id": "SC-0002",
 "phase": "held_out",
 "period": [
  "2016-01-04",
  "2026-09-25"
 ],
 "trials": [
  {
   "at": "2026-09-30T01:08:36.587759+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "2e81fb9b99e94561a12e44f4e00b6ea8",
   "kind": "buy_and_hold",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 3.573035312130978,
    "cagr": 0.1525632542743105,
    "sharpe": 0.8904348605931036,
    "sharpe_per_period": 0.05609212380551952,
    "max_drawdown": -0.33717265401236196,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 3.573035312130978,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.623787+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "ba35e5cc19d34801bd1c100f47e738f0",
   "kind": "buy_and_hold",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 3.570291353807545,
    "cagr": 0.1524986420823462,
    "sharpe": 0.890122165002351,
    "sharpe_per_period": 0.05607242583482433,
    "max_drawdown": -0.33717265401236207,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 3.570291353807545,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.656338+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "9fb5cfe81fcf4246a69a676f3f846e88",
   "kind": "buy_and_hold",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 3.5657199198811833,
    "cagr": 0.15239092004149168,
    "sharpe": 0.8895999310953652,
    "sharpe_per_period": 0.05603952819091742,
    "max_drawdown": -0.33717265401236196,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 3.5657199198811833,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.687448+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "ee2d62e7f5e948c0867c2f1e508b11f5",
   "kind": "buy_and_hold",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 6.335400192938616,
    "cagr": 0.20457200388356078,
    "sharpe": 0.9488099830669986,
    "sharpe_per_period": 0.05976941087263532,
    "max_drawdown": -0.35118731568587624,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 6.335400192938616,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.720965+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "09b6e2e6b0654214a7b02a71f982d443",
   "kind": "buy_and_hold",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 6.330998732848916,
    "cagr": 0.20450447610383926,
    "sharpe": 0.9485587227131035,
    "sharpe_per_period": 0.05975358295809397,
    "max_drawdown": -0.35118731568587613,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 6.330998732848916,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.754473+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "8ca14c7c2fba4cc0bc754ac552ee7a17",
   "kind": "buy_and_hold",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 6.323665901366843,
    "cagr": 0.20439189316825357,
    "sharpe": 0.9481392337486869,
    "sharpe_per_period": 0.05972715763719916,
    "max_drawdown": -0.35118731568587613,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 6.323665901366843,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.790476+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "8d6140bde4b24dc2ac3c15f2014b1338",
   "kind": "buy_and_hold",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 1.9205518690543673,
    "cagr": 0.10528836157045518,
    "sharpe": 0.5545202887036887,
    "sharpe_per_period": 0.03493149478213571,
    "max_drawdown": -0.41133272337996307,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 1.9205518690543673,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.823854+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "eec03a0d39d74755ad59ea0def15891e",
   "kind": "buy_and_hold",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 1.9187994503514427,
    "cagr": 0.10522639958830027,
    "sharpe": 0.5542726059268579,
    "sharpe_per_period": 0.03491589223376598,
    "max_drawdown": -0.41133272337996307,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 1.9187994503514427,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.856853+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "39820c91dde64c4a89c370d51fe2bd82",
   "kind": "buy_and_hold",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 1.9158799212014106,
    "cagr": 0.10512309600162117,
    "sharpe": 0.5538594066908753,
    "sharpe_per_period": 0.034889863128519986,
    "max_drawdown": -0.41133272337996307,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 1.9158799212014106,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 2697.0,
    "holding_days_max": 2697
   }
  },
  {
   "at": "2026-09-30T01:08:36.600268+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "a2d93270124d42779cda07a0c1928492",
   "kind": "rule",
   "rule": "A",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.400099375179485,
    "cagr": 0.03193324988950952,
    "sharpe": 0.5479256142260568,
    "sharpe_per_period": 0.03451606933820145,
    "max_drawdown": -0.12034371667031407,
    "exposure": 0.11193476649369903,
    "trades": 91,
    "average_trade": 0.0038125759074149118,
    "win_rate": 0.7252747252747253,
    "profit_factor": 1.9554479970611072,
    "holding_days_mean": 3.318681318681319,
    "holding_days_max": 10
   }
  },
  {
   "at": "2026-09-30T01:08:36.610271+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "b4ad71b5d8284a4795dd54b858cf1ce3",
   "kind": "rule",
   "rule": "B",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.28402487502628615,
    "cagr": 0.02362535016848688,
    "sharpe": 0.4070999965124048,
    "sharpe_per_period": 0.02564488927397822,
    "max_drawdown": -0.08493382736792277,
    "exposure": 0.13528539659006672,
    "trades": 68,
    "average_trade": 0.003809702423856931,
    "win_rate": 0.7941176470588235,
    "profit_factor": 1.9651810566005299,
    "holding_days_mean": 5.367647058823529,
    "holding_days_max": 18
   }
  },
  {
   "at": "2026-09-30T01:08:36.617774+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "6e1a1d82f26a4ffa9d43d4f2f10a9abe",
   "kind": "rule",
   "rule": "D",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.477790120761024,
    "cagr": 0.03715164180817232,
    "sharpe": 0.38450606934763204,
    "sharpe_per_period": 0.024221605644971184,
    "max_drawdown": -0.3662125628668722,
    "exposure": 0.1793921423276501,
    "trades": 174,
    "average_trade": 0.0025145984775136695,
    "win_rate": 0.6551724137931034,
    "profit_factor": 1.457133757038476,
    "holding_days_mean": 2.7758620689655173,
    "holding_days_max": 9
   }
  },
  {
   "at": "2026-09-30T01:08:36.633825+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "b38730d01bfc4b9d8ea88dbbf31da84c",
   "kind": "rule",
   "rule": "A",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.3256780962360466,
    "cagr": 0.026682182912308727,
    "sharpe": 0.4638474703399849,
    "sharpe_per_period": 0.02921964411395259,
    "max_drawdown": -0.12979617776276242,
    "exposure": 0.11193476649369903,
    "trades": 91,
    "average_trade": 0.0032102582595450392,
    "win_rate": 0.6813186813186813,
    "profit_factor": 1.769813396309912,
    "holding_days_mean": 3.318681318681319,
    "holding_days_max": 10
   }
  },
  {
   "at": "2026-09-30T01:08:36.642828+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "c25921d02cb74529847f0b0053b511cf",
   "kind": "rule",
   "rule": "B",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.24523307065898559,
    "cagr": 0.020696558397103493,
    "sharpe": 0.3610727496260519,
    "sharpe_per_period": 0.022745445255067224,
    "max_drawdown": -0.08945692077614709,
    "exposure": 0.13528539659006672,
    "trades": 68,
    "average_trade": 0.0033573939971618264,
    "win_rate": 0.7941176470588235,
    "profit_factor": 1.8270500992319083,
    "holding_days_mean": 5.367647058823529,
    "holding_days_max": 18
   }
  },
  {
   "at": "2026-09-30T01:08:36.650830+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "e7cbe2d68c834391bad6edbf7d5f70db",
   "kind": "rule",
   "rule": "D",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.3312405564101144,
    "cagr": 0.02708378765681574,
    "sharpe": 0.2964795415610587,
    "sharpe_per_period": 0.018676455614023806,
    "max_drawdown": -0.377896104633889,
    "exposure": 0.1793921423276501,
    "trades": 174,
    "average_trade": 0.0019130596550254698,
    "win_rate": 0.6379310344827587,
    "profit_factor": 1.334791078394489,
    "holding_days_mean": 2.7758620689655173,
    "holding_days_max": 9
   }
  },
  {
   "at": "2026-09-30T01:08:36.665348+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "e4ea13553218460caab016bac676eaf9",
   "kind": "rule",
   "rule": "A",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.21028491174862274,
    "cagr": 0.01798625125147213,
    "sharpe": 0.32352302076175826,
    "sharpe_per_period": 0.020380034674761873,
    "max_drawdown": -0.14533126267653362,
    "exposure": 0.11193476649369903,
    "trades": 91,
    "average_trade": 0.002206797198783599,
    "win_rate": 0.6813186813186813,
    "profit_factor": 1.4920650778193445,
    "holding_days_mean": 3.318681318681319,
    "holding_days_max": 10
   }
  },
  {
   "at": "2026-09-30T01:08:36.673844+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "6fb6ea23728c4b5c82df7a0cfe0f9433",
   "kind": "rule",
   "rule": "B",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.18315069256669148,
    "cagr": 0.01583255287765062,
    "sharpe": 0.2841921244179661,
    "sharpe_per_period": 0.01790242108983488,
    "max_drawdown": -0.09694845063182367,
    "exposure": 0.13528539659006672,
    "trades": 68,
    "average_trade": 0.0026038482638632405,
    "win_rate": 0.7941176470588235,
    "profit_factor": 1.6131542733350483,
    "holding_days_mean": 5.367647058823529,
    "holding_days_max": 18
   }
  },
  {
   "at": "2026-09-30T01:08:36.681447+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "d3002c4f5a594a218b57b61a7aee44bc",
   "kind": "rule",
   "rule": "D",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.11849122332633533,
    "cagr": 0.01051416484214518,
    "sharpe": 0.1498078108868369,
    "sharpe_per_period": 0.00943700504908488,
    "max_drawdown": -0.3993716098265364,
    "exposure": 0.1793921423276501,
    "trades": 174,
    "average_trade": 0.0009108961171681029,
    "win_rate": 0.5804597701149425,
    "profit_factor": 1.1490716593656694,
    "holding_days_mean": 2.7758620689655173,
    "holding_days_max": 9
   }
  },
  {
   "at": "2026-09-30T01:08:36.696447+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "b43a07509c92435491e717a76f4b0424",
   "kind": "rule",
   "rule": "A",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.37163067071192035,
    "cagr": 0.0299551161178937,
    "sharpe": 0.4108852173193562,
    "sharpe_per_period": 0.02588333577189871,
    "max_drawdown": -0.10643123492123385,
    "exposure": 0.12268346923647146,
    "trades": 89,
    "average_trade": 0.0036991842842578264,
    "win_rate": 0.6966292134831461,
    "profit_factor": 1.7734306008403051,
    "holding_days_mean": 3.7191011235955056,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-30T01:08:36.706453+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "015ea0bc66ba435b9202ef46753afa2f",
   "kind": "rule",
   "rule": "B",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.3882117842020194,
    "cagr": 0.031111721613941823,
    "sharpe": 0.40252672755497965,
    "sharpe_per_period": 0.02535680040874111,
    "max_drawdown": -0.11940115792306105,
    "exposure": 0.15196441808747221,
    "trades": 69,
    "average_trade": 0.004950997733405238,
    "win_rate": 0.8115942028985508,
    "profit_factor": 2.014250081378226,
    "holding_days_mean": 5.942028985507246,
    "holding_days_max": 21
   }
  },
  {
   "at": "2026-09-30T01:08:36.714452+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "204d085b474944b1ac07e0a7cf63ad30",
   "kind": "rule",
   "rule": "D",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.9465724183933875,
    "cagr": 0.06418859412146949,
    "sharpe": 0.5431082251061026,
    "sharpe_per_period": 0.0342126023482008,
    "max_drawdown": -0.2283182240202788,
    "exposure": 0.18383988139362492,
    "trades": 173,
    "average_trade": 0.004140359930998197,
    "win_rate": 0.6647398843930635,
    "profit_factor": 1.7250245017791788,
    "holding_days_mean": 2.867052023121387,
    "holding_days_max": 10
   }
  },
  {
   "at": "2026-09-30T01:08:36.730472+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "3057cabe579b4e70bb4fe39e646cc84a",
   "kind": "rule",
   "rule": "A",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.3002825742794586,
    "cagr": 0.02482901472947452,
    "sharpe": 0.348144203726223,
    "sharpe_per_period": 0.021931023415433154,
    "max_drawdown": -0.11204498112003591,
    "exposure": 0.12268346923647146,
    "trades": 89,
    "average_trade": 0.0030969346747622374,
    "win_rate": 0.6741573033707865,
    "profit_factor": 1.6232639242023255,
    "holding_days_mean": 3.7191011235955056,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-30T01:08:36.739471+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "032b24eefedf4c72a2b4fa1cf83e6540",
   "kind": "rule",
   "rule": "B",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.3446399776802669,
    "cagr": 0.028045002698212418,
    "sharpe": 0.36751442665116385,
    "sharpe_per_period": 0.023151232765415905,
    "max_drawdown": -0.11940115792306083,
    "exposure": 0.15196441808747221,
    "trades": 69,
    "average_trade": 0.004487134386821107,
    "win_rate": 0.7971014492753623,
    "profit_factor": 1.8982973676425765,
    "holding_days_mean": 5.942028985507246,
    "holding_days_max": 21
   }
  },
  {
   "at": "2026-09-30T01:08:36.747471+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "9d6a23a6f7404eaebccde77cb49373a0",
   "kind": "rule",
   "rule": "D",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.7545874328623334,
    "cagr": 0.05391736860321217,
    "sharpe": 0.468652292739461,
    "sharpe_per_period": 0.029522319474972743,
    "max_drawdown": -0.24140634089455826,
    "exposure": 0.18383988139362492,
    "trades": 173,
    "average_trade": 0.0035378456028845847,
    "win_rate": 0.6473988439306358,
    "profit_factor": 1.598258668856153,
    "holding_days_mean": 2.867052023121387,
    "holding_days_max": 10
   }
  },
  {
   "at": "2026-09-30T01:08:36.765472+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "c0b71f66e1274e7a83af858ff12c3e86",
   "kind": "rule",
   "rule": "A",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.18947829534183125,
    "cagr": 0.01633876123204825,
    "sharpe": 0.24346956277724213,
    "sharpe_per_period": 0.015337140831481215,
    "max_drawdown": -0.1281321230883785,
    "exposure": 0.12268346923647146,
    "trades": 89,
    "average_trade": 0.0020935869659164247,
    "win_rate": 0.651685393258427,
    "profit_factor": 1.3946586287286962,
    "holding_days_mean": 3.7191011235955056,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-30T01:08:36.774471+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "6f492bb3891b4d9cb4dede63ceea9412",
   "kind": "rule",
   "rule": "B",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.2750191742999215,
    "cagr": 0.02295263933647651,
    "sharpe": 0.3091165568843539,
    "sharpe_per_period": 0.01947251275353694,
    "max_drawdown": -0.11940115792306094,
    "exposure": 0.15196441808747221,
    "trades": 69,
    "average_trade": 0.003714338159684467,
    "win_rate": 0.782608695652174,
    "profit_factor": 1.7158572785174522,
    "holding_days_mean": 5.942028985507246,
    "holding_days_max": 21
   }
  },
  {
   "at": "2026-09-30T01:08:36.783474+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "6d9c7c3b5196404f9c4ac59a80efd4d0",
   "kind": "rule",
   "rule": "D",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.47565786022726164,
    "cagr": 0.037011775670248825,
    "sharpe": 0.34436413835258717,
    "sharpe_per_period": 0.021692901679285368,
    "max_drawdown": -0.26273685382600687,
    "exposure": 0.18383988139362492,
    "trades": 173,
    "average_trade": 0.002534056872882968,
    "win_rate": 0.6184971098265896,
    "profit_factor": 1.4041311779576406,
    "holding_days_mean": 2.867052023121387,
    "holding_days_max": 10
   }
  },
  {
   "at": "2026-09-30T01:08:36.800343+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "45be60cf8f09401d81a3c9ebf408dae8",
   "kind": "rule",
   "rule": "A",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.24520682235249458,
    "cagr": 0.020694548795178624,
    "sharpe": 0.3177791105870978,
    "sharpe_per_period": 0.02001820234439889,
    "max_drawdown": -0.196252763597626,
    "exposure": 0.1123054114158636,
    "trades": 77,
    "average_trade": 0.003147232035452964,
    "win_rate": 0.7402597402597403,
    "profit_factor": 1.4562633750494811,
    "holding_days_mean": 3.935064935064935,
    "holding_days_max": 15
   }
  },
  {
   "at": "2026-09-30T01:08:36.809346+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "d0ab402f27604da79d8ab7bd6f2f0c1d",
   "kind": "rule",
   "rule": "B",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.011676190738538539,
    "cagr": 0.001084855862454992,
    "sharpe": 0.06505747791853736,
    "sharpe_per_period": 0.004098235892798235,
    "max_drawdown": -0.3987262046440352,
    "exposure": 0.14825796886582654,
    "trades": 57,
    "average_trade": 0.0014255824291387058,
    "win_rate": 0.7719298245614035,
    "profit_factor": 1.1417714629141993,
    "holding_days_mean": 7.017543859649122,
    "holding_days_max": 22
   }
  },
  {
   "at": "2026-09-30T01:08:36.817345+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "61edd343841247c9bb62605f3fc1fe8b",
   "kind": "rule",
   "rule": "D",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.3302254770100139,
    "cagr": 0.027010613436851294,
    "sharpe": 0.27410222967741743,
    "sharpe_per_period": 0.017266817465113205,
    "max_drawdown": -0.3721042213980694,
    "exposure": 0.20422535211267606,
    "trades": 169,
    "average_trade": 0.002206858300480233,
    "win_rate": 0.6153846153846154,
    "profit_factor": 1.2615572006526294,
    "holding_days_mean": 3.260355029585799,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-30T01:08:36.833852+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "c615f25c45534045bbaebd63fcbef7cc",
   "kind": "rule",
   "rule": "A",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.1889677128751186,
    "cagr": 0.016298005285978467,
    "sharpe": 0.25861610338196034,
    "sharpe_per_period": 0.01629128320441041,
    "max_drawdown": -0.203217461868336,
    "exposure": 0.1123054114158636,
    "trades": 77,
    "average_trade": 0.0025453136138586263,
    "win_rate": 0.7142857142857143,
    "profit_factor": 1.3607187198455204,
    "holding_days_mean": 3.935064935064935,
    "holding_days_max": 15
   }
  },
  {
   "at": "2026-09-30T01:08:36.843855+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "b9e5ea755c614eff836d527d9ed38756",
   "kind": "rule",
   "rule": "B",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": -0.014473604009611063,
    "cagr": -0.0013608229922559278,
    "sharpe": 0.04220694958373347,
    "sharpe_per_period": 0.0026587879094571404,
    "max_drawdown": -0.40178970490485844,
    "exposure": 0.14825796886582654,
    "trades": 57,
    "average_trade": 0.0009668094145144499,
    "win_rate": 0.7719298245614035,
    "profit_factor": 1.0949616765988164,
    "holding_days_mean": 7.017543859649122,
    "holding_days_max": 22
   }
  },
  {
   "at": "2026-09-30T01:08:36.851855+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "0c99317784ca4260a78cea4e71ddb44b",
   "kind": "rule",
   "rule": "D",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.20191119970197935,
    "cagr": 0.017326322804138927,
    "sharpe": 0.19956204810484887,
    "sharpe_per_period": 0.01257122739076521,
    "max_drawdown": -0.3831240206695544,
    "exposure": 0.20422535211267606,
    "trades": 169,
    "average_trade": 0.0016055041313267758,
    "win_rate": 0.6035502958579881,
    "profit_factor": 1.18522026952881,
    "holding_days_mean": 3.260355029585799,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-30T01:08:36.866860+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "ad9e851103c542bfac93fb69ba946d15",
   "kind": "rule",
   "rule": "A",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.10078951969996286,
    "cagr": 0.00900957021119786,
    "sharpe": 0.1597604124897679,
    "sharpe_per_period": 0.010063960019071982,
    "max_drawdown": -0.21469599716736865,
    "exposure": 0.1123054114158636,
    "trades": 77,
    "average_trade": 0.0015425176639789421,
    "win_rate": 0.6753246753246753,
    "profit_factor": 1.2099073458680552,
    "holding_days_mean": 3.935064935064935,
    "holding_days_max": 15
   }
  },
  {
   "at": "2026-09-30T01:08:36.875859+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "21de6ad704df483ab7c3630ce6e30516",
   "kind": "rule",
   "rule": "B",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": -0.05657458131078397,
    "cagr": -0.005424805006931321,
    "sharpe": 0.004089966633080093,
    "sharpe_per_period": 0.00025764368051624015,
    "max_drawdown": -0.40686255730275667,
    "exposure": 0.14825796886582654,
    "trades": 57,
    "average_trade": 0.000202493679234783,
    "win_rate": 0.7017543859649122,
    "profit_factor": 1.0194416463035072,
    "holding_days_mean": 7.017543859649122,
    "holding_days_max": 22
   }
  },
  {
   "at": "2026-09-30T01:08:36.884859+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "f463db8a89834afaf4fa9c8ce0344c0db9525a5e",
   "phase": "held_out",
   "period": [
    "2016-01-04",
    "2026-09-25"
   ],
   "trial_id": "f5c8e942bcf543c5abeeee1659e782a5",
   "kind": "rule",
   "rule": "D",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.014895962866624979,
    "cagr": 0.0013820138188158637,
    "sharpe": 0.0752097835503065,
    "sharpe_per_period": 0.004737771034121607,
    "max_drawdown": -0.40106932579579824,
    "exposure": 0.20422535211267606,
    "trades": 169,
    "average_trade": 0.0006036482258819536,
    "win_rate": 0.591715976331361,
    "profit_factor": 1.0665887375521699,
    "holding_days_mean": 3.260355029585799,
    "holding_days_max": 13
   }
  }
 ],
 "primary_trades": [
  {
   "signal": "2016-04-29",
   "entry": "2016-05-02",
   "exit": "2016-05-10",
   "holding_days": 6,
   "return": -0.001965657957706979,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2016-06-13",
   "entry": "2016-06-14",
   "exit": "2016-06-21",
   "holding_days": 5,
   "return": 0.0056435088296160054,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2016-08-02",
   "entry": "2016-08-03",
   "exit": "2016-08-08",
   "holding_days": 3,
   "return": 0.012538028905519097,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2016-08-26",
   "entry": "2016-08-29",
   "exit": "2016-08-30",
   "holding_days": 1,
   "return": 0.0027676850173427993,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2016-09-09",
   "entry": "2016-09-12",
   "exit": "2016-09-16",
   "holding_days": 4,
   "return": 0.00919920195395405,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2016-10-28",
   "entry": "2016-10-31",
   "exit": "2016-11-08",
   "holding_days": 6,
   "return": -0.0021255478972265437,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2016-12-30",
   "entry": "2017-01-03",
   "exit": "2017-01-04",
   "holding_days": 1,
   "return": 0.0015749850511072934,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2017-03-21",
   "entry": "2017-03-22",
   "exit": "2017-03-29",
   "holding_days": 5,
   "return": 0.004213774454454077,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2017-04-12",
   "entry": "2017-04-13",
   "exit": "2017-04-18",
   "holding_days": 2,
   "return": -0.0006577141942111146,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2017-05-17",
   "entry": "2017-05-18",
   "exit": "2017-05-22",
   "holding_days": 2,
   "return": 0.012434298497946443,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2017-06-27",
   "entry": "2017-06-28",
   "exit": "2017-06-29",
   "holding_days": 1,
   "return": 0.0037792371787374913,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2017-08-10",
   "entry": "2017-08-11",
   "exit": "2017-08-15",
   "holding_days": 2,
   "return": 0.011118174684219032,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2017-11-15",
   "entry": "2017-11-16",
   "exit": "2017-11-17",
   "holding_days": 1,
   "return": 0.0017155788497959705,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-02-02",
   "entry": "2018-02-05",
   "exit": "2018-02-13",
   "holding_days": 6,
   "return": -0.03563309759123681,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-03-01",
   "entry": "2018-03-02",
   "exit": "2018-03-06",
   "holding_days": 2,
   "return": 0.027188818469465893,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-03-19",
   "entry": "2018-03-20",
   "exit": "2018-04-02",
   "holding_days": 8,
   "return": -0.031935000823580244,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-04-24",
   "entry": "2018-04-25",
   "exit": "2018-04-27",
   "holding_days": 2,
   "return": 0.014541598560790018,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-05-29",
   "entry": "2018-05-30",
   "exit": "2018-05-31",
   "holding_days": 1,
   "return": 0.005094084013781329,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-06-19",
   "entry": "2018-06-20",
   "exit": "2018-07-02",
   "holding_days": 8,
   "return": -0.025444189685139583,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-08-13",
   "entry": "2018-08-14",
   "exit": "2018-08-17",
   "holding_days": 3,
   "return": 0.002213853644037054,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-09-06",
   "entry": "2018-09-07",
   "exit": "2018-09-12",
   "holding_days": 3,
   "return": 0.0062412958222234395,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2018-10-04",
   "entry": "2018-10-05",
   "exit": "2018-10-17",
   "holding_days": 8,
   "return": -0.03289837019004711,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-03-06",
   "entry": "2019-03-07",
   "exit": "2019-03-12",
   "holding_days": 3,
   "return": 0.007047720900509131,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-05-09",
   "entry": "2019-05-10",
   "exit": "2019-05-16",
   "holding_days": 4,
   "return": -0.00023052998882865293,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-05-29",
   "entry": "2019-05-30",
   "exit": "2019-06-05",
   "holding_days": 4,
   "return": 0.010525756513982704,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-07-31",
   "entry": "2019-08-01",
   "exit": "2019-08-09",
   "holding_days": 6,
   "return": -0.017851039589044233,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-09-23",
   "entry": "2019-09-24",
   "exit": "2019-10-01",
   "holding_days": 5,
   "return": -0.006571992970226812,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-10-02",
   "entry": "2019-10-03",
   "exit": "2019-10-07",
   "holding_days": 2,
   "return": 0.01864631575526179,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2019-12-03",
   "entry": "2019-12-04",
   "exit": "2019-12-06",
   "holding_days": 2,
   "return": 0.009996930377743409,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-01-27",
   "entry": "2020-01-28",
   "exit": "2020-01-31",
   "holding_days": 3,
   "return": 0.004962593052640923,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-02-24",
   "entry": "2020-02-25",
   "exit": "2020-03-03",
   "holding_days": 5,
   "return": -0.04553143083961099,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-06-11",
   "entry": "2020-06-12",
   "exit": "2020-06-17",
   "holding_days": 3,
   "return": 0.0178954564558379,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-09-08",
   "entry": "2020-09-09",
   "exit": "2020-09-15",
   "holding_days": 4,
   "return": 0.00956612469386155,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-09-18",
   "entry": "2020-09-21",
   "exit": "2020-09-28",
   "holding_days": 5,
   "return": 0.022066196013174617,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-10-19",
   "entry": "2020-10-20",
   "exit": "2020-10-23",
   "holding_days": 3,
   "return": 0.006184658656200997,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-10-28",
   "entry": "2020-10-29",
   "exit": "2020-11-04",
   "holding_days": 4,
   "return": 0.041629740098705494,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2020-12-14",
   "entry": "2020-12-15",
   "exit": "2020-12-16",
   "holding_days": 1,
   "return": 0.005580219437784558,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-01-27",
   "entry": "2021-01-28",
   "exit": "2021-02-03",
   "holding_days": 4,
   "return": 0.015138568530300732,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-02-22",
   "entry": "2021-02-23",
   "exit": "2021-02-25",
   "holding_days": 2,
   "return": 0.01393353327975051,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-05-12",
   "entry": "2021-05-13",
   "exit": "2021-05-17",
   "holding_days": 2,
   "return": 0.01941871851582132,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-06-18",
   "entry": "2021-06-21",
   "exit": "2021-06-22",
   "holding_days": 1,
   "return": 0.008707488276952119,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-07-16",
   "entry": "2021-07-19",
   "exit": "2021-07-22",
   "holding_days": 3,
   "return": 0.019041762461194052,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-08-18",
   "entry": "2021-08-19",
   "exit": "2021-08-23",
   "holding_days": 2,
   "return": 0.019357003828215518,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-09-09",
   "entry": "2021-09-10",
   "exit": "2021-09-16",
   "holding_days": 4,
   "return": -0.009239115243130605,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-09-20",
   "entry": "2021-09-21",
   "exit": "2021-09-24",
   "holding_days": 3,
   "return": 0.010236862389040806,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-09-30",
   "entry": "2021-10-01",
   "exit": "2021-10-06",
   "holding_days": 3,
   "return": -0.00496329557712262,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2021-11-26",
   "entry": "2021-11-29",
   "exit": "2021-12-07",
   "holding_days": 6,
   "return": -0.0002677285921323927,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2022-01-05",
   "entry": "2022-01-06",
   "exit": "2022-01-12",
   "holding_days": 4,
   "return": 0.006900074405051735,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2022-01-18",
   "entry": "2022-01-19",
   "exit": "2022-01-31",
   "holding_days": 8,
   "return": -0.03783023635160304,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-02-21",
   "entry": "2023-02-22",
   "exit": "2023-03-03",
   "holding_days": 7,
   "return": -0.0005247620396545298,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-03-09",
   "entry": "2023-03-10",
   "exit": "2023-03-15",
   "holding_days": 3,
   "return": -0.014030453562638436,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-04-25",
   "entry": "2023-04-26",
   "exit": "2023-04-28",
   "holding_days": 2,
   "return": 0.010716520919228041,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-05-04",
   "entry": "2023-05-05",
   "exit": "2023-05-08",
   "holding_days": 1,
   "return": 0.008919022626397804,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-05-24",
   "entry": "2023-05-25",
   "exit": "2023-05-30",
   "holding_days": 2,
   "return": 0.016559923304495676,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-08-03",
   "entry": "2023-08-04",
   "exit": "2023-08-08",
   "holding_days": 2,
   "return": -0.006851119125546624,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-08-16",
   "entry": "2023-08-17",
   "exit": "2023-08-22",
   "holding_days": 3,
   "return": -0.0009544687206680521,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-09-07",
   "entry": "2023-09-08",
   "exit": "2023-09-12",
   "holding_days": 2,
   "return": 0.0036034938136218744,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-09-20",
   "entry": "2023-09-21",
   "exit": "2023-10-03",
   "holding_days": 8,
   "return": -0.025395730432522277,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-10-03",
   "entry": "2023-10-04",
   "exit": "2023-10-09",
   "holding_days": 3,
   "return": 0.012041870961681833,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2023-10-19",
   "entry": "2023-10-20",
   "exit": "2023-11-01",
   "holding_days": 8,
   "return": -0.016900095197388304,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-01-03",
   "entry": "2024-01-04",
   "exit": "2024-01-09",
   "holding_days": 3,
   "return": 0.00661583556858595,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-01-17",
   "entry": "2024-01-18",
   "exit": "2024-01-19",
   "holding_days": 1,
   "return": 0.006671556328361743,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-04-04",
   "entry": "2024-04-05",
   "exit": "2024-04-08",
   "holding_days": 1,
   "return": 0.008107343274790353,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-04-15",
   "entry": "2024-04-16",
   "exit": "2024-04-23",
   "holding_days": 5,
   "return": -0.007251651790191575,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-05-30",
   "entry": "2024-05-31",
   "exit": "2024-06-03",
   "holding_days": 1,
   "return": 0.009360703089557141,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-07-19",
   "entry": "2024-07-22",
   "exit": "2024-07-24",
   "holding_days": 2,
   "return": -0.0084787088369189,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-07-24",
   "entry": "2024-07-25",
   "exit": "2024-07-30",
   "holding_days": 3,
   "return": 0.008060996162801792,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-08-05",
   "entry": "2024-08-06",
   "exit": "2024-08-09",
   "holding_days": 3,
   "return": 0.019375825325455065,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-09-06",
   "entry": "2024-09-09",
   "exit": "2024-09-11",
   "holding_days": 2,
   "return": 0.006428704732061984,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-10-23",
   "entry": "2024-10-24",
   "exit": "2024-10-29",
   "holding_days": 3,
   "return": -0.0012237850720126671,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-10-31",
   "entry": "2024-11-01",
   "exit": "2024-11-06",
   "holding_days": 3,
   "return": 0.030264962663437877,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-11-15",
   "entry": "2024-11-18",
   "exit": "2024-11-21",
   "holding_days": 3,
   "return": 0.011235953966019438,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-12-18",
   "entry": "2024-12-19",
   "exit": "2024-12-24",
   "holding_days": 3,
   "return": 0.010329221211418042,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2024-12-31",
   "entry": "2025-01-02",
   "exit": "2025-01-06",
   "holding_days": 2,
   "return": 0.01066177962896064,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-02-21",
   "entry": "2025-02-24",
   "exit": "2025-03-03",
   "holding_days": 5,
   "return": -0.010690838329387217,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-05-21",
   "entry": "2025-05-22",
   "exit": "2025-05-28",
   "holding_days": 3,
   "return": 0.014260055793024995,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-07-31",
   "entry": "2025-08-01",
   "exit": "2025-08-05",
   "holding_days": 2,
   "return": 0.007757344045667192,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-08-19",
   "entry": "2025-08-20",
   "exit": "2025-08-25",
   "holding_days": 3,
   "return": 0.006249807151949688,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-10-10",
   "entry": "2025-10-13",
   "exit": "2025-10-16",
   "holding_days": 3,
   "return": 0.008330202817766313,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-11-17",
   "entry": "2025-11-18",
   "exit": "2025-11-25",
   "holding_days": 5,
   "return": 0.008852865921522452,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-12-17",
   "entry": "2025-12-18",
   "exit": "2025-12-22",
   "holding_days": 2,
   "return": 0.01132715546178231,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2025-12-31",
   "entry": "2026-01-02",
   "exit": "2026-01-06",
   "holding_days": 2,
   "return": 0.0022344994146869983,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-01-20",
   "entry": "2026-01-21",
   "exit": "2026-01-23",
   "holding_days": 2,
   "return": 0.011494122145249964,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-02-05",
   "entry": "2026-02-06",
   "exit": "2026-02-09",
   "holding_days": 1,
   "return": 0.010669392809107002,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-02-12",
   "entry": "2026-02-13",
   "exit": "2026-02-19",
   "holding_days": 3,
   "return": 0.002151027420830336,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-03-03",
   "entry": "2026-03-04",
   "exit": "2026-03-18",
   "holding_days": 10,
   "return": -0.020448391560743465,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-06-05",
   "entry": "2026-06-08",
   "exit": "2026-06-12",
   "holding_days": 4,
   "return": -0.004561037101867466,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-07-20",
   "entry": "2026-07-21",
   "exit": "2026-07-22",
   "holding_days": 1,
   "return": -0.0005580072081559951,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-07-29",
   "entry": "2026-07-30",
   "exit": "2026-07-31",
   "holding_days": 1,
   "return": 0.010713341692131156,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-09-01",
   "entry": "2026-09-02",
   "exit": "2026-09-04",
   "holding_days": 2,
   "return": 0.011526249337905775,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2026-09-10",
   "entry": "2026-09-11",
   "exit": "2026-09-14",
   "holding_days": 1,
   "return": -0.008472127076377522,
   "forced": false,
   "units": 1
  }
 ],
 "verdict": {
  "verdict": "no edge shown",
  "criteria": [
   {
    "name": "positive average trade",
    "value": 0.0032102582595450392,
    "comparator": ">",
    "threshold": 0.0,
    "passed": true
   },
   {
    "name": "beats random entry",
    "value": 94.9,
    "comparator": ">=",
    "threshold": 95.0,
    "passed": false
   },
   {
    "name": "deflated Sharpe",
    "value": 0.8964725533282583,
    "comparator": ">=",
    "threshold": 0.95,
    "passed": false
   },
   {
    "name": "beats buy-and-hold risk-adjusted",
    "value": -0.42627469466236606,
    "comparator": ">",
    "threshold": 0.0,
    "passed": false
   }
  ],
  "dsr": {
   "dsr": 0.8964725533282583,
   "sr": 0.02921964411395259,
   "sr_star": 0.004534465990995204,
   "variance": 2.8271791884723635e-05,
   "n_trials": 3,
   "t": 2698,
   "skew": -0.8313379802352722,
   "kurtosis": 38.87425245058275
  },
  "random_entry": {
   "completed": 1000,
   "discarded": 0
  },
  "note": "A backtest is not proof of future profit."
 },
 "reference_match": null
}
```
