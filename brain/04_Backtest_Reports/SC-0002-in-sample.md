# SC-0002: in-sample report (2000-01-03..2015-12-31)

> A backtest is not proof of future profit.

Second-implementation cross-check of rule A: **match**.

## Trials

| Rule | Symbol | Cost bps | Trades | Avg trade | Win rate | Total return | CAGR | Sharpe | Max DD | Days held |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buy&hold | SPY | 2.0 | 1 | 84.95% | 100.00% | 84.95% | 3.92% | 0.291 | -55.19% | 100.00% |
| buy&hold | SPY | 5.0 | 1 | 84.83% | 100.00% | 84.83% | 3.92% | 0.291 | -55.19% | 100.00% |
| buy&hold | SPY | 10.0 | 1 | 84.65% | 100.00% | 84.65% | 3.91% | 0.291 | -55.19% | 100.00% |
| buy&hold | QQQ | 2.0 | 1 | 28.01% | 100.00% | 28.01% | 1.56% | 0.199 | -82.96% | 100.00% |
| buy&hold | QQQ | 5.0 | 1 | 27.93% | 100.00% | 27.93% | 1.55% | 0.199 | -82.96% | 100.00% |
| buy&hold | QQQ | 10.0 | 1 | 27.81% | 100.00% | 27.81% | 1.55% | 0.199 | -82.96% | 100.00% |
| buy&hold | IWM | 2.0 | 1 | 203.41% | 100.00% | 203.41% | 7.39% | 0.413 | -58.64% | 100.00% |
| buy&hold | IWM | 5.0 | 1 | 203.23% | 100.00% | 203.23% | 7.38% | 0.413 | -58.64% | 100.00% |
| buy&hold | IWM | 10.0 | 1 | 202.93% | 100.00% | 202.93% | 7.38% | 0.413 | -58.64% | 100.00% |
| A | SPY | 2.0 | 101 | 0.41% | 72.28% | 48.92% | 2.52% | 0.475 | -14.91% | 8.84% |
| B | SPY | 2.0 | 80 | 0.76% | 91.25% | 82.40% | 3.83% | 0.788 | -14.42% | 9.79% |
| D | SPY | 2.0 | 285 | 0.38% | 66.67% | 178.44% | 6.62% | 0.602 | -19.19% | 20.84% |
| A | SPY | 5.0 | 101 | 0.35% | 71.29% | 40.16% | 2.14% | 0.407 | -14.99% | 8.84% |
| B | SPY | 5.0 | 80 | 0.72% | 91.25% | 75.77% | 3.59% | 0.741 | -14.47% | 9.79% |
| D | SPY | 5.0 | 285 | 0.32% | 64.56% | 134.66% | 5.49% | 0.512 | -19.43% | 20.84% |
| A | SPY | 10.0 | 101 | 0.25% | 67.33% | 26.69% | 1.49% | 0.293 | -15.48% | 8.84% |
| B | SPY | 10.0 | 80 | 0.64% | 90.00% | 65.26% | 3.20% | 0.663 | -14.56% | 9.79% |
| D | SPY | 10.0 | 285 | 0.22% | 60.70% | 76.43% | 3.62% | 0.360 | -19.84% | 20.84% |
| A | QQQ | 2.0 | 117 | 0.54% | 67.52% | 84.02% | 3.89% | 0.583 | -13.94% | 10.71% |
| B | QQQ | 2.0 | 86 | 0.89% | 83.72% | 111.91% | 4.81% | 0.787 | -11.12% | 12.62% |
| D | QQQ | 2.0 | 292 | 0.68% | 67.12% | 521.99% | 12.12% | 0.745 | -26.85% | 21.42% |
| A | QQQ | 5.0 | 117 | 0.48% | 66.67% | 71.54% | 3.44% | 0.519 | -14.02% | 10.71% |
| B | QQQ | 5.0 | 86 | 0.84% | 82.56% | 103.29% | 4.54% | 0.745 | -11.13% | 12.62% |
| D | QQQ | 5.0 | 292 | 0.62% | 65.07% | 422.00% | 10.90% | 0.682 | -27.05% | 21.42% |
| A | QQQ | 10.0 | 117 | 0.38% | 66.67% | 52.59% | 2.68% | 0.414 | -14.22% | 10.71% |
| B | QQQ | 10.0 | 86 | 0.76% | 81.40% | 89.69% | 4.09% | 0.675 | -11.15% | 12.62% |
| D | QQQ | 10.0 | 292 | 0.52% | 63.70% | 289.73% | 8.89% | 0.576 | -27.38% | 21.42% |
| A | IWM | 2.0 | 116 | 0.52% | 73.28% | 77.67% | 3.76% | 0.518 | -20.07% | 10.68% |
| B | IWM | 2.0 | 85 | 0.69% | 80.00% | 76.58% | 3.72% | 0.557 | -18.33% | 12.67% |
| D | IWM | 2.0 | 269 | 0.39% | 66.17% | 158.77% | 6.30% | 0.509 | -25.13% | 21.00% |
| A | IWM | 5.0 | 116 | 0.46% | 71.55% | 65.72% | 3.30% | 0.460 | -20.14% | 10.68% |
| B | IWM | 5.0 | 85 | 0.64% | 80.00% | 69.65% | 3.45% | 0.520 | -18.33% | 12.67% |
| D | IWM | 5.0 | 269 | 0.33% | 65.06% | 120.18% | 5.20% | 0.434 | -25.40% | 21.00% |
| A | IWM | 10.0 | 116 | 0.36% | 69.83% | 47.56% | 2.53% | 0.363 | -20.26% | 10.68% |
| B | IWM | 10.0 | 85 | 0.57% | 78.82% | 58.70% | 3.01% | 0.459 | -18.33% | 12.67% |
| D | IWM | 10.0 | 269 | 0.23% | 63.94% | 68.22% | 3.40% | 0.310 | -25.85% | 21.00% |

## Data

```json
{
 "card_id": "SC-0002",
 "phase": "in_sample",
 "period": [
  "2000-01-03",
  "2015-12-31"
 ],
 "trials": [
  {
   "at": "2026-09-29T03:55:19.951628+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "509c73ff0eeb4faabd23e124fb36ee50",
   "kind": "buy_and_hold",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.8494568502334852,
    "cagr": 0.039248219798669215,
    "sharpe": 0.2914249175873542,
    "sharpe_per_period": 0.018358044232943634,
    "max_drawdown": -0.5518946653145416,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 0.8494568502334852,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 4024.0,
    "holding_days_max": 4024
   }
  },
  {
   "at": "2026-09-29T03:55:19.985340+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "49cb8b02e52e472492e76f8efd683896",
   "kind": "buy_and_hold",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.8483471206618443,
    "cagr": 0.03920916727820645,
    "sharpe": 0.29123777497134534,
    "sharpe_per_period": 0.018346255356237406,
    "max_drawdown": -0.5518946653145416,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 0.8483471206618443,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 4024.0,
    "holding_days_max": 4024
   }
  },
  {
   "at": "2026-09-29T03:55:20.017439+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "e9d6257b7ede42548d976ef97d43338b",
   "kind": "buy_and_hold",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.8464983114545177,
    "cagr": 0.03914405695188883,
    "sharpe": 0.2909257089000683,
    "sharpe_per_period": 0.018326597041541694,
    "max_drawdown": -0.5518946653145416,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 0.8464983114545177,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 4024.0,
    "holding_days_max": 4024
   }
  },
  {
   "at": "2026-09-29T03:55:20.049285+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "2ed7947d12ee45dfb469fda7eafa38a1",
   "kind": "buy_and_hold",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.28010715124372054,
    "cagr": 0.015580965309175854,
    "sharpe": 0.198957720935035,
    "sharpe_per_period": 0.0125331583573879,
    "max_drawdown": -0.8296390929673658,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 0.28010715124372054,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 4024.0,
    "holding_days_max": 4024
   }
  },
  {
   "at": "2026-09-29T03:55:20.081308+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "471bdfbc3c854b659b4674b4eb38290d",
   "kind": "buy_and_hold",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.2793390485651288,
    "cagr": 0.015542802148851287,
    "sharpe": 0.19883031253354233,
    "sharpe_per_period": 0.012525132382500045,
    "max_drawdown": -0.8296390929673658,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 0.2793390485651288,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 4024.0,
    "holding_days_max": 4024
   }
  },
  {
   "at": "2026-09-29T03:55:20.112570+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "37c0c839705049c0aa679e1dae1ae8c0",
   "kind": "buy_and_hold",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.2780593896818815,
    "cagr": 0.015479174608487467,
    "sharpe": 0.19861791257591652,
    "sharpe_per_period": 0.012511752442824842,
    "max_drawdown": -0.8296390929673658,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 0.2780593896818815,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 4024.0,
    "holding_days_max": 4024
   }
  },
  {
   "at": "2026-09-29T03:55:20.146088+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "4711b7dbcd484fb8851d78a9f41b7b60",
   "kind": "buy_and_hold",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 2.034147038784726,
    "cagr": 0.07388179586293053,
    "sharpe": 0.41343944722412457,
    "sharpe_per_period": 0.026044237131882076,
    "max_drawdown": -0.5863998570849995,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 2.034147038784726,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 3923.0,
    "holding_days_max": 3923
   }
  },
  {
   "at": "2026-09-29T03:55:20.179312+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "89921a1e8a404c43ac2b6bbfbde473b3",
   "kind": "buy_and_hold",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 2.0323264595734716,
    "cagr": 0.07384040324109642,
    "sharpe": 0.41328175771452014,
    "sharpe_per_period": 0.02603430362648262,
    "max_drawdown": -0.5863998570849995,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 2.0323264595734716,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 3923.0,
    "holding_days_max": 3923
   }
  },
  {
   "at": "2026-09-29T03:55:20.209412+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "0b89fb30aacf40e1b0d940ed70967219",
   "kind": "buy_and_hold",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 2.0292933750324726,
    "cagr": 0.0737713914690954,
    "sharpe": 0.4130187692555716,
    "sharpe_per_period": 0.026017736910766958,
    "max_drawdown": -0.5863998570849995,
    "exposure": 1.0,
    "trades": 1,
    "average_trade": 2.0292933750324726,
    "win_rate": 1.0,
    "profit_factor": null,
    "holding_days_mean": 3923.0,
    "holding_days_max": 3923
   }
  },
  {
   "at": "2026-09-29T03:55:19.963328+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "acf6ac040a064c4ab152b8fff0b2293a",
   "kind": "rule",
   "rule": "A",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.4891984245467911,
    "cagr": 0.02524659286225539,
    "sharpe": 0.4753626092466599,
    "sharpe_per_period": 0.029945029682034167,
    "max_drawdown": -0.14913319007040815,
    "exposure": 0.0884472049689441,
    "trades": 101,
    "average_trade": 0.004088933749321577,
    "win_rate": 0.7227722772277227,
    "profit_factor": 2.071358640795203,
    "holding_days_mean": 3.5247524752475248,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:19.972340+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "0e7894db4f6c4b248fd3525895e65846",
   "kind": "rule",
   "rule": "B",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.8239668955781105,
    "cagr": 0.03834560950948296,
    "sharpe": 0.7876738982724979,
    "sharpe_per_period": 0.04961879164394805,
    "max_drawdown": -0.14421317028498182,
    "exposure": 0.09788819875776397,
    "trades": 80,
    "average_trade": 0.007638022736704794,
    "win_rate": 0.9125,
    "profit_factor": 5.593483900154906,
    "holding_days_mean": 4.925,
    "holding_days_max": 16
   }
  },
  {
   "at": "2026-09-29T03:55:19.980328+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "ef0daa380ab745e985d335651493091c",
   "kind": "rule",
   "rule": "D",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 1.7844378711001387,
    "cagr": 0.06621413753731642,
    "sharpe": 0.6023866899045122,
    "sharpe_per_period": 0.03794679463292195,
    "max_drawdown": -0.19191255682924913,
    "exposure": 0.2084472049689441,
    "trades": 285,
    "average_trade": 0.0037877857392630385,
    "win_rate": 0.6666666666666666,
    "profit_factor": 1.7897476068447113,
    "holding_days_mean": 2.943859649122807,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-29T03:55:19.995755+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "bc6b7410e12a45c1b7257e9178c55dc4",
   "kind": "rule",
   "rule": "A",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.4016032881793896,
    "cagr": 0.02136273127134114,
    "sharpe": 0.4071822342423534,
    "sharpe_per_period": 0.0256500697640218,
    "max_drawdown": -0.1498988935830352,
    "exposure": 0.0884472049689441,
    "trades": 101,
    "average_trade": 0.003486450278459135,
    "win_rate": 0.7128712871287128,
    "profit_factor": 1.8749768722758742,
    "holding_days_mean": 3.5247524752475248,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.003759+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "f3769042ee774a408f115c33c6700c71",
   "kind": "rule",
   "rule": "B",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.757723668329858,
    "cagr": 0.03594342324847477,
    "sharpe": 0.7409112074605879,
    "sharpe_per_period": 0.04667301901241189,
    "max_drawdown": -0.1447266680461412,
    "exposure": 0.09788819875776397,
    "trades": 80,
    "average_trade": 0.007172166640743471,
    "win_rate": 0.9125,
    "profit_factor": 5.192901255380216,
    "holding_days_mean": 4.925,
    "holding_days_max": 16
   }
  },
  {
   "at": "2026-09-29T03:55:20.010766+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "df00fc851dba477f9ac33cfada26a643",
   "kind": "rule",
   "rule": "D",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 1.3466438047305846,
    "cagr": 0.05485608951578347,
    "sharpe": 0.5115077042899462,
    "sharpe_per_period": 0.03222195664868486,
    "max_drawdown": -0.194334032662977,
    "exposure": 0.2084472049689441,
    "trades": 285,
    "average_trade": 0.00318548296623746,
    "win_rate": 0.6456140350877193,
    "profit_factor": 1.6368189552480623,
    "holding_days_mean": 2.943859649122807,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-29T03:55:20.026439+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "e2f38e0f80704b7c8387bffc254d75e3",
   "kind": "rule",
   "rule": "A",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.26685946824248363,
    "cagr": 0.014919726441687597,
    "sharpe": 0.2933828375758988,
    "sharpe_per_period": 0.01848138159905438,
    "max_drawdown": -0.1547604480061746,
    "exposure": 0.0884472049689441,
    "trades": 101,
    "average_trade": 0.002482712956630761,
    "win_rate": 0.6732673267326733,
    "profit_factor": 1.5794945973549035,
    "holding_days_mean": 3.5247524752475248,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.035438+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "1965595188ac45aab01535b706663024",
   "kind": "rule",
   "rule": "B",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.6525927665926923,
    "cagr": 0.031951006934757276,
    "sharpe": 0.6626408427054307,
    "sharpe_per_period": 0.04174244948459139,
    "max_drawdown": -0.1455821551963744,
    "exposure": 0.09788819875776397,
    "trades": 80,
    "average_trade": 0.006396050493609523,
    "win_rate": 0.9,
    "profit_factor": 4.5522373737291915,
    "holding_days_mean": 4.925,
    "holding_days_max": 16
   }
  },
  {
   "at": "2026-09-29T03:55:20.043449+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "0a0a245028c642439fd09682b43a43b2",
   "kind": "rule",
   "rule": "D",
   "symbol": "SPY",
   "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.7643321310474935,
    "cagr": 0.036186843344889974,
    "sharpe": 0.35985070192062607,
    "sharpe_per_period": 0.022668463485571656,
    "max_drawdown": -0.19835531695203623,
    "exposure": 0.2084472049689441,
    "trades": 285,
    "average_trade": 0.0021820466869631274,
    "win_rate": 0.6070175438596491,
    "profit_factor": 1.4067139850305064,
    "holding_days_mean": 2.943859649122807,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-29T03:55:20.058299+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "3a501538e73a4f72b9961b2f21f2835e",
   "kind": "rule",
   "rule": "A",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.8402379826342201,
    "cagr": 0.038923129477860696,
    "sharpe": 0.5827365686429742,
    "sharpe_per_period": 0.036708953345057846,
    "max_drawdown": -0.13940243314288703,
    "exposure": 0.10708074534161491,
    "trades": 117,
    "average_trade": 0.0053739703625663325,
    "win_rate": 0.6752136752136753,
    "profit_factor": 2.2403119399165723,
    "holding_days_mean": 3.6837606837606836,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.067304+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "2a6c60f892774a9a85f0510c0e1f65cf",
   "kind": "rule",
   "rule": "B",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 1.1190885722554937,
    "cagr": 0.04814114666772107,
    "sharpe": 0.7865449520452068,
    "sharpe_per_period": 0.049547674716305744,
    "max_drawdown": -0.11117593347076127,
    "exposure": 0.1262111801242236,
    "trades": 86,
    "average_trade": 0.008901648077934041,
    "win_rate": 0.8372093023255814,
    "profit_factor": 4.278849626791486,
    "holding_days_mean": 5.906976744186046,
    "holding_days_max": 20
   }
  },
  {
   "at": "2026-09-29T03:55:20.075304+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "0f4ced9788d243248e9703786494ff32",
   "kind": "rule",
   "rule": "D",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 5.219887414178194,
    "cagr": 0.12123769116109351,
    "sharpe": 0.7446996925981404,
    "sharpe_per_period": 0.04691167114383161,
    "max_drawdown": -0.2685414413077124,
    "exposure": 0.21416149068322982,
    "trades": 292,
    "average_trade": 0.006767758202119133,
    "win_rate": 0.6712328767123288,
    "profit_factor": 1.9718040792996663,
    "holding_days_mean": 2.952054794520548,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-29T03:55:20.090308+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "23f5dc06441c4bc388002dbb762a5d5b",
   "kind": "rule",
   "rule": "A",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.715441226603809,
    "cagr": 0.03436535490318038,
    "sharpe": 0.5193985128698466,
    "sharpe_per_period": 0.03271903086643798,
    "max_drawdown": -0.14017689346054285,
    "exposure": 0.10708074534161491,
    "trades": 117,
    "average_trade": 0.004770715831200268,
    "win_rate": 0.6666666666666666,
    "profit_factor": 2.0531904393547085,
    "holding_days_mean": 3.6837606837606836,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.099568+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "20df3c8f475245418a6a24940d3b1b27",
   "kind": "rule",
   "rule": "B",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 1.0329067577070257,
    "cagr": 0.04542006713825586,
    "sharpe": 0.7447780470954457,
    "sharpe_per_period": 0.046916607013211924,
    "max_drawdown": -0.11130903991715368,
    "exposure": 0.1262111801242236,
    "trades": 86,
    "average_trade": 0.008414887413172813,
    "win_rate": 0.8255813953488372,
    "profit_factor": 3.9952875774752816,
    "holding_days_mean": 5.906976744186046,
    "holding_days_max": 20
   }
  },
  {
   "at": "2026-09-29T03:55:20.107570+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "fb14a60f38de4455ab5fc24a718207fc",
   "kind": "rule",
   "rule": "D",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 4.219963780077257,
    "cagr": 0.10900173459893026,
    "sharpe": 0.6815544483261186,
    "sharpe_per_period": 0.04293389464811266,
    "max_drawdown": -0.27051440526802806,
    "exposure": 0.21416149068322982,
    "trades": 292,
    "average_trade": 0.006163667356252438,
    "win_rate": 0.6506849315068494,
    "profit_factor": 1.8601379955456387,
    "holding_days_mean": 2.952054794520548,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-29T03:55:20.122087+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "ca00895e33e94cffbc374539b23c4230",
   "kind": "rule",
   "rule": "A",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.5258971073473311,
    "cagr": 0.02681044197169613,
    "sharpe": 0.4137550049817226,
    "sharpe_per_period": 0.02606411540214116,
    "max_drawdown": -0.1422245271305549,
    "exposure": 0.10708074534161491,
    "trades": 117,
    "average_trade": 0.0037656939227528477,
    "win_rate": 0.6666666666666666,
    "profit_factor": 1.7750476992357598,
    "holding_days_mean": 3.6837606837606836,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.131081+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "5a2539c03c394db5b55de1842a60f4be",
   "kind": "rule",
   "rule": "B",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.8969489172064533,
    "cagr": 0.04089926215783857,
    "sharpe": 0.6749656635742598,
    "sharpe_per_period": 0.04251884022202807,
    "max_drawdown": -0.11153097296113001,
    "exposure": 0.1262111801242236,
    "trades": 86,
    "average_trade": 0.007603944259297747,
    "win_rate": 0.813953488372093,
    "profit_factor": 3.5551364570039286,
    "holding_days_mean": 5.906976744186046,
    "holding_days_max": 20
   }
  },
  {
   "at": "2026-09-29T03:55:20.140082+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "94e2d1fc6c1c4417849a7399e3cd0a02",
   "kind": "rule",
   "rule": "D",
   "symbol": "QQQ",
   "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 2.8972504540567314,
    "cagr": 0.08889651443696978,
    "sharpe": 0.5761376694677286,
    "sharpe_per_period": 0.03629326177018906,
    "max_drawdown": -0.2737921683326887,
    "exposure": 0.21416149068322982,
    "trades": 292,
    "average_trade": 0.005157252148042181,
    "win_rate": 0.636986301369863,
    "profit_factor": 1.6864111857977766,
    "holding_days_mean": 2.952054794520548,
    "holding_days_max": 13
   }
  },
  {
   "at": "2026-09-29T03:55:20.155086+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "134d9b9e1ae143a7bc48f5c84137d10d",
   "kind": "rule",
   "rule": "A",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.7766992642771067,
    "cagr": 0.037600690057163044,
    "sharpe": 0.5184992971931446,
    "sharpe_per_period": 0.03266238560321026,
    "max_drawdown": -0.2007249474817009,
    "exposure": 0.10677879714576963,
    "trades": 116,
    "average_trade": 0.005189060286316264,
    "win_rate": 0.7327586206896551,
    "profit_factor": 2.004196842212961,
    "holding_days_mean": 3.6120689655172415,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.165311+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "f4b1b5b844584d35aec90c7f53d247b6",
   "kind": "rule",
   "rule": "B",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 0.7658228949540622,
    "cagr": 0.03719160002536026,
    "sharpe": 0.55662857093672,
    "sharpe_per_period": 0.035064304079329436,
    "max_drawdown": -0.18334586842541478,
    "exposure": 0.1266564729867482,
    "trades": 85,
    "average_trade": 0.006919511792755739,
    "win_rate": 0.8,
    "profit_factor": 2.658384348623568,
    "holding_days_mean": 5.847058823529411,
    "holding_days_max": 17
   }
  },
  {
   "at": "2026-09-29T03:55:20.173309+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "69524bd03c4b45d6be08d3f7999bee2b",
   "kind": "rule",
   "rule": "D",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 2.0,
   "metrics": {
    "total_return": 1.5876519341438717,
    "cagr": 0.06295992172949472,
    "sharpe": 0.5090337078784071,
    "sharpe_per_period": 0.03206610952369917,
    "max_drawdown": -0.25132229354723723,
    "exposure": 0.20998980632008155,
    "trades": 269,
    "average_trade": 0.003880334869236918,
    "win_rate": 0.6617100371747212,
    "profit_factor": 1.5548111795968038,
    "holding_days_mean": 3.063197026022305,
    "holding_days_max": 14
   }
  },
  {
   "at": "2026-09-29T03:55:20.187765+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "0abbf852aee34f81883e53e7ac19e66c",
   "kind": "rule",
   "rule": "A",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.657205794727832,
    "cagr": 0.03297163336037001,
    "sharpe": 0.4601711757786611,
    "sharpe_per_period": 0.028988059324536353,
    "max_drawdown": -0.20144422305823806,
    "exposure": 0.10677879714576963,
    "trades": 116,
    "average_trade": 0.0045859167065410425,
    "win_rate": 0.7155172413793104,
    "profit_factor": 1.8607579356424768,
    "holding_days_mean": 3.6120689655172415,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.197268+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "d6e7dc2b700a4b64b4174c02349a38a3",
   "kind": "rule",
   "rule": "B",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 0.6965444111350918,
    "cagr": 0.034529123927017125,
    "sharpe": 0.519982537871687,
    "sharpe_per_period": 0.032755820983445455,
    "max_drawdown": -0.18334586842541478,
    "exposure": 0.1266564729867482,
    "trades": 85,
    "average_trade": 0.006445924652276681,
    "win_rate": 0.8,
    "profit_factor": 2.5038034284575703,
    "holding_days_mean": 5.847058823529411,
    "holding_days_max": 17
   }
  },
  {
   "at": "2026-09-29T03:55:20.204472+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "1d9e539dc1464719b227fab033a4d306",
   "kind": "rule",
   "rule": "D",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 5.0,
   "metrics": {
    "total_return": 1.201842179698716,
    "cagr": 0.051995281359345835,
    "sharpe": 0.43439868846242646,
    "sharpe_per_period": 0.02736454522676675,
    "max_drawdown": -0.25401362796809046,
    "exposure": 0.20998980632008155,
    "trades": 269,
    "average_trade": 0.0032779765639579994,
    "win_rate": 0.6505576208178439,
    "profit_factor": 1.4555873911698611,
    "holding_days_mean": 3.063197026022305,
    "holding_days_max": 14
   }
  },
  {
   "at": "2026-09-29T03:55:20.219476+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "9e4afaa353d24bd2af812bc63e57f400",
   "kind": "rule",
   "rule": "A",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.47557221980647446,
    "cagr": 0.025299327231347757,
    "sharpe": 0.3629125049231187,
    "sharpe_per_period": 0.022861338945287524,
    "max_drawdown": -0.20264205652386202,
    "exposure": 0.10677879714576963,
    "trades": 116,
    "average_trade": 0.00358107964341807,
    "win_rate": 0.6982758620689655,
    "profit_factor": 1.6374510289621567,
    "holding_days_mean": 3.6120689655172415,
    "holding_days_max": 11
   }
  },
  {
   "at": "2026-09-29T03:55:20.227485+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "9656b02ee8b94836b81f19771990b863",
   "kind": "rule",
   "rule": "B",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.5870368194747713,
    "cagr": 0.030105566701410735,
    "sharpe": 0.458780001553659,
    "sharpe_per_period": 0.02890042358573353,
    "max_drawdown": -0.18334586842541478,
    "exposure": 0.1266564729867482,
    "trades": 85,
    "average_trade": 0.005656928586780742,
    "win_rate": 0.788235294117647,
    "profit_factor": 2.26126219215937,
    "holding_days_mean": 5.847058823529411,
    "holding_days_max": 17
   }
  },
  {
   "at": "2026-09-29T03:55:20.236492+00:00",
   "card_id": "SC-0002",
   "spec_sha256": "4b838196776934cd6e2643e67da25811ad3cc33696d9fa6d800cdbfb109ef106",
   "file_sha256": "dbfe0fa259faad357b3f7ae13ad42fbb7e9b03e3a724808aa983c956815b35c0",
   "code_commit": "cc0375bd883350cc6ecceea0a872c8dee8c32947",
   "phase": "in_sample",
   "period": [
    "2000-01-03",
    "2015-12-31"
   ],
   "trial_id": "a0f231e655664dfeabb62c304a82e2c0",
   "kind": "rule",
   "rule": "D",
   "symbol": "IWM",
   "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
   "cost_bps": 10.0,
   "metrics": {
    "total_return": 0.6821831726978609,
    "cagr": 0.03396448990042922,
    "sharpe": 0.3098968435060738,
    "sharpe_per_period": 0.01952166619049936,
    "max_drawdown": -0.2584794847081079,
    "exposure": 0.20998980632008155,
    "trades": 269,
    "average_trade": 0.002274447767962541,
    "win_rate": 0.6394052044609665,
    "profit_factor": 1.3015995406131224,
    "holding_days_mean": 3.063197026022305,
    "holding_days_max": 14
   }
  }
 ],
 "primary_trades": [
  {
   "signal": "2003-05-19",
   "entry": "2003-05-20",
   "exit": "2003-05-23",
   "holding_days": 3,
   "return": 0.006641567224018985,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2003-06-23",
   "entry": "2003-06-24",
   "exit": "2003-06-27",
   "holding_days": 3,
   "return": 0.004391666469732478,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2003-07-17",
   "entry": "2003-07-18",
   "exit": "2003-07-23",
   "holding_days": 3,
   "return": 0.0009169736267318988,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2003-08-05",
   "entry": "2003-08-06",
   "exit": "2003-08-08",
   "holding_days": 2,
   "return": 0.01584071890017918,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2003-09-25",
   "entry": "2003-09-26",
   "exit": "2003-10-02",
   "holding_days": 4,
   "return": 0.0138199947154573,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2003-11-18",
   "entry": "2003-11-19",
   "exit": "2003-11-25",
   "holding_days": 4,
   "return": 0.015325509574612064,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-02-24",
   "entry": "2004-02-25",
   "exit": "2004-02-26",
   "holding_days": 1,
   "return": 0.00030929177477816855,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-03-10",
   "entry": "2004-03-11",
   "exit": "2004-03-18",
   "holding_days": 5,
   "return": 0.0016665572581613809,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-03-22",
   "entry": "2004-03-23",
   "exit": "2004-03-26",
   "holding_days": 3,
   "return": 0.0054334372654691624,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-04-29",
   "entry": "2004-04-30",
   "exit": "2004-05-05",
   "holding_days": 3,
   "return": 0.0011374466711577915,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-05-07",
   "entry": "2004-05-10",
   "exit": "2004-05-13",
   "holding_days": 3,
   "return": 0.0019214387113374466,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-07-06",
   "entry": "2004-07-07",
   "exit": "2004-07-14",
   "holding_days": 5,
   "return": -0.005914028378017182,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-07-15",
   "entry": "2004-07-16",
   "exit": "2004-07-21",
   "holding_days": 3,
   "return": 0.001238128055326779,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2004-12-07",
   "entry": "2004-12-08",
   "exit": "2004-12-10",
   "holding_days": 2,
   "return": 0.005000676473805243,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-01-03",
   "entry": "2005-01-04",
   "exit": "2005-01-11",
   "holding_days": 5,
   "return": -0.016093503081351376,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-01-24",
   "entry": "2005-01-25",
   "exit": "2005-01-27",
   "holding_days": 2,
   "return": 0.0013933793265622928,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-02-22",
   "entry": "2005-02-23",
   "exit": "2005-02-25",
   "holding_days": 2,
   "return": 0.010256078413404578,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-03-21",
   "entry": "2005-03-22",
   "exit": "2005-03-29",
   "holding_days": 4,
   "return": -0.011380594100526395,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-04-14",
   "entry": "2005-04-15",
   "exit": "2005-04-22",
   "holding_days": 5,
   "return": -0.0009996707311966447,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-06-23",
   "entry": "2005-06-24",
   "exit": "2005-06-29",
   "holding_days": 3,
   "return": 0.003083556085401132,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-08-08",
   "entry": "2005-08-09",
   "exit": "2005-08-11",
   "holding_days": 2,
   "return": 0.0007051917368618536,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-08-24",
   "entry": "2005-08-25",
   "exit": "2005-08-30",
   "holding_days": 3,
   "return": -0.0018232921265360351,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-09-21",
   "entry": "2005-09-22",
   "exit": "2005-09-27",
   "holding_days": 3,
   "return": 0.003708320197706193,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-10-05",
   "entry": "2005-10-06",
   "exit": "2005-10-17",
   "holding_days": 7,
   "return": -0.00917243079066323,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-11-30",
   "entry": "2005-12-01",
   "exit": "2005-12-02",
   "holding_days": 1,
   "return": 0.00494496326772586,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2005-12-30",
   "entry": "2006-01-03",
   "exit": "2006-01-04",
   "holding_days": 1,
   "return": 0.012326478421608247,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-01-18",
   "entry": "2006-01-19",
   "exit": "2006-01-27",
   "holding_days": 6,
   "return": -0.004664590320015098,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-03-28",
   "entry": "2006-03-29",
   "exit": "2006-03-30",
   "holding_days": 1,
   "return": 0.004403824753923729,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-04-11",
   "entry": "2006-04-12",
   "exit": "2006-04-19",
   "holding_days": 4,
   "return": 0.014361084843971186,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-05-11",
   "entry": "2006-05-12",
   "exit": "2006-05-25",
   "holding_days": 9,
   "return": -0.027361996705403888,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-06-07",
   "entry": "2006-06-08",
   "exit": "2006-06-16",
   "holding_days": 6,
   "return": 0.001098860554418537,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-08-09",
   "entry": "2006-08-10",
   "exit": "2006-08-16",
   "holding_days": 4,
   "return": 0.02062493171693339,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-11-01",
   "entry": "2006-11-02",
   "exit": "2006-11-07",
   "holding_days": 3,
   "return": 0.011367705259479428,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-11-27",
   "entry": "2006-11-28",
   "exit": "2006-11-30",
   "holding_days": 2,
   "return": 0.01489855977457562,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2006-12-22",
   "entry": "2006-12-26",
   "exit": "2006-12-28",
   "holding_days": 2,
   "return": 0.010351540071216397,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-02-09",
   "entry": "2007-02-12",
   "exit": "2007-02-14",
   "holding_days": 2,
   "return": 0.004969104155239923,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-02-23",
   "entry": "2007-02-26",
   "exit": "2007-03-07",
   "holding_days": 7,
   "return": -0.04374666586039294,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-03-28",
   "entry": "2007-03-29",
   "exit": "2007-04-04",
   "holding_days": 4,
   "return": 0.007060605207040403,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-05-24",
   "entry": "2007-05-25",
   "exit": "2007-05-30",
   "holding_days": 2,
   "return": -0.0012632353038328382,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-06-06",
   "entry": "2007-06-07",
   "exit": "2007-06-14",
   "holding_days": 5,
   "return": 0.002296060734472447,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-06-26",
   "entry": "2007-06-27",
   "exit": "2007-06-28",
   "holding_days": 1,
   "return": 0.014175080072861886,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-07-24",
   "entry": "2007-07-25",
   "exit": "2007-08-03",
   "holding_days": 7,
   "return": -0.0321483870122885,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2007-10-19",
   "entry": "2007-10-22",
   "exit": "2007-10-25",
   "holding_days": 3,
   "return": 0.017723895452714942,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-06-16",
   "entry": "2009-06-17",
   "exit": "2009-06-22",
   "holding_days": 3,
   "return": -0.0004017552255169892,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-07-07",
   "entry": "2009-07-08",
   "exit": "2009-07-14",
   "holding_days": 4,
   "return": 0.01918554985159019,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-09-01",
   "entry": "2009-09-02",
   "exit": "2009-09-08",
   "holding_days": 3,
   "return": 0.031238676940177346,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-09-25",
   "entry": "2009-09-28",
   "exit": "2009-09-29",
   "holding_days": 1,
   "return": 0.014817330140595202,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-10-01",
   "entry": "2009-10-02",
   "exit": "2009-10-07",
   "holding_days": 3,
   "return": 0.03082499397504037,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-10-27",
   "entry": "2009-10-28",
   "exit": "2009-10-30",
   "holding_days": 2,
   "return": 0.0004116461755705904,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2009-12-31",
   "entry": "2010-01-04",
   "exit": "2010-01-05",
   "holding_days": 1,
   "return": 0.006912437105471202,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2010-01-22",
   "entry": "2010-01-25",
   "exit": "2010-02-02",
   "holding_days": 6,
   "return": -0.009610834001948001,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2010-04-27",
   "entry": "2010-04-28",
   "exit": "2010-04-30",
   "holding_days": 2,
   "return": 0.014356868504061657,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2010-05-06",
   "entry": "2010-05-07",
   "exit": "2010-05-11",
   "holding_days": 2,
   "return": 0.020551612085894285,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2010-05-18",
   "entry": "2010-05-19",
   "exit": "2010-05-28",
   "holding_days": 7,
   "return": -0.011099622569987736,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2010-11-12",
   "entry": "2010-11-15",
   "exit": "2010-11-19",
   "holding_days": 4,
   "return": -0.00663368710050225,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-02-23",
   "entry": "2011-02-24",
   "exit": "2011-02-28",
   "holding_days": 2,
   "return": 0.013808210103614963,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-03-16",
   "entry": "2011-03-17",
   "exit": "2011-03-21",
   "holding_days": 2,
   "return": 0.01392206890884228,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-04-11",
   "entry": "2011-04-12",
   "exit": "2011-04-18",
   "holding_days": 4,
   "return": -0.009569565209034422,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-05-04",
   "entry": "2011-05-05",
   "exit": "2011-05-10",
   "holding_days": 3,
   "return": 0.007121458383048225,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-05-23",
   "entry": "2011-05-24",
   "exit": "2011-05-27",
   "holding_days": 3,
   "return": 0.006015338540499713,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-06-03",
   "entry": "2011-06-06",
   "exit": "2011-06-10",
   "holding_days": 4,
   "return": -0.010522378334054245,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2011-07-27",
   "entry": "2011-07-28",
   "exit": "2011-08-12",
   "holding_days": 11,
   "return": -0.09432136611884788,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-03-06",
   "entry": "2012-03-07",
   "exit": "2012-03-09",
   "holding_days": 2,
   "return": 0.015568800949133613,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-03-22",
   "entry": "2012-03-23",
   "exit": "2012-03-27",
   "holding_days": 2,
   "return": 0.01635298608644461,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-04-09",
   "entry": "2012-04-10",
   "exit": "2012-04-13",
   "holding_days": 3,
   "return": 0.0027658027499728017,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-05-04",
   "entry": "2012-05-07",
   "exit": "2012-05-22",
   "holding_days": 11,
   "return": -0.03173574888165673,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-06-01",
   "entry": "2012-06-04",
   "exit": "2012-06-07",
   "holding_days": 3,
   "return": 0.038527201999427434,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-07-10",
   "entry": "2012-07-11",
   "exit": "2012-07-16",
   "holding_days": 3,
   "return": 0.008156082052681519,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-07-24",
   "entry": "2012-07-25",
   "exit": "2012-07-27",
   "holding_days": 2,
   "return": 0.018948848854056,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-08-23",
   "entry": "2012-08-24",
   "exit": "2012-08-28",
   "holding_days": 2,
   "return": 0.005194501009617619,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-08-30",
   "entry": "2012-08-31",
   "exit": "2012-09-07",
   "holding_days": 4,
   "return": 0.018232470496723233,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-09-25",
   "entry": "2012-09-26",
   "exit": "2012-10-02",
   "holding_days": 4,
   "return": 0.004894121654631372,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-10-09",
   "entry": "2012-10-10",
   "exit": "2012-10-16",
   "holding_days": 4,
   "return": 0.0030191895199949055,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-10-23",
   "entry": "2012-10-24",
   "exit": "2012-11-01",
   "holding_days": 4,
   "return": -0.0029706309491871158,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-11-08",
   "entry": "2012-11-09",
   "exit": "2012-11-20",
   "holding_days": 7,
   "return": 0.008365136764780649,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2012-12-28",
   "entry": "2012-12-31",
   "exit": "2013-01-02",
   "holding_days": 1,
   "return": 0.0379847174900635,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2013-06-05",
   "entry": "2013-06-06",
   "exit": "2013-06-10",
   "holding_days": 2,
   "return": 0.024471176464555145,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2013-06-20",
   "entry": "2013-06-21",
   "exit": "2013-06-27",
   "holding_days": 4,
   "return": 0.008137023388492873,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2013-08-15",
   "entry": "2013-08-16",
   "exit": "2013-08-23",
   "holding_days": 5,
   "return": 0.001947746259566821,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2013-09-25",
   "entry": "2013-09-26",
   "exit": "2013-10-02",
   "holding_days": 4,
   "return": -0.006722984711467055,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2013-12-03",
   "entry": "2013-12-04",
   "exit": "2013-12-09",
   "holding_days": 3,
   "return": 0.012219705615690718,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2013-12-12",
   "entry": "2013-12-13",
   "exit": "2013-12-17",
   "holding_days": 2,
   "return": 0.003925632739457184,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-01-24",
   "entry": "2014-01-27",
   "exit": "2014-01-31",
   "holding_days": 4,
   "return": -0.012437403923508856,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-02-03",
   "entry": "2014-02-04",
   "exit": "2014-02-07",
   "holding_days": 3,
   "return": 0.018186470642763408,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-03-13",
   "entry": "2014-03-14",
   "exit": "2014-03-18",
   "holding_days": 2,
   "return": 0.009052436453862844,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-04-07",
   "entry": "2014-04-08",
   "exit": "2014-04-10",
   "holding_days": 2,
   "return": 0.014289332671247868,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-06-12",
   "entry": "2014-06-13",
   "exit": "2014-06-18",
   "holding_days": 3,
   "return": 0.0036883419317476694,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-07-29",
   "entry": "2014-07-30",
   "exit": "2014-08-11",
   "holding_days": 8,
   "return": -0.019599786745465995,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-09-23",
   "entry": "2014-09-24",
   "exit": "2014-10-06",
   "holding_days": 8,
   "return": -0.004530990839152719,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-12-10",
   "entry": "2014-12-11",
   "exit": "2014-12-18",
   "holding_days": 5,
   "return": 0.003214494218442307,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2014-12-31",
   "entry": "2015-01-02",
   "exit": "2015-01-09",
   "holding_days": 5,
   "return": -0.0009030806660787944,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-01-15",
   "entry": "2015-01-16",
   "exit": "2015-01-20",
   "holding_days": 1,
   "return": 0.017243936825899323,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-01-28",
   "entry": "2015-01-29",
   "exit": "2015-02-03",
   "holding_days": 3,
   "return": 0.01206175210553132,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-03-06",
   "entry": "2015-03-09",
   "exit": "2015-03-13",
   "holding_days": 4,
   "return": -0.005664237385667628,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-03-25",
   "entry": "2015-03-26",
   "exit": "2015-03-31",
   "holding_days": 3,
   "return": 0.010210545875107722,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-04-30",
   "entry": "2015-05-01",
   "exit": "2015-05-04",
   "holding_days": 1,
   "return": 0.0077313356866342015,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-05-26",
   "entry": "2015-05-27",
   "exit": "2015-05-28",
   "holding_days": 1,
   "return": 0.004107939229473327,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-06-08",
   "entry": "2015-06-09",
   "exit": "2015-06-11",
   "holding_days": 2,
   "return": 0.013521543248335646,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-06-29",
   "entry": "2015-06-30",
   "exit": "2015-07-06",
   "holding_days": 3,
   "return": -0.008181424947765371,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-07-23",
   "entry": "2015-07-24",
   "exit": "2015-07-29",
   "holding_days": 3,
   "return": -0.004895719576946498,
   "forced": false,
   "units": 1
  },
  {
   "signal": "2015-11-09",
   "entry": "2015-11-10",
   "exit": "2015-11-18",
   "holding_days": 6,
   "return": -0.008077000744242639,
   "forced": false,
   "units": 1
  }
 ],
 "verdict": null,
 "reference_match": true
}
```
