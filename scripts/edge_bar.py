"""What daily edge pays out within 42 trading days? Synthetic days only (no market data).

    uv run python scripts/edge_bar.py

Topstep 50K standard plan, $1,000 DLL. Rows: mean and sd of daily net P&L at the traded size,
and the share of days traded. No-edge rows (mean 0) are the luck reference.
"""

import numpy as np

from quant_brain.config import BRAIN_DIR
from quant_brain.prop import funded

P = BRAIN_DIR / "_system" / "prop"
combine, act = funded.plan_rules(P / "topstep_50k.json", "standard")
xfa = funded.XfaRules.from_json(P / "topstep_50k_xfa.json", "standard", dll=True, activation=act)
rng = np.random.default_rng(1)
H, N = 42, 3000
print("mean/day  sd/day  trade-days  | net cash  P(net>0)  P(payout)  median 1st payout")
for trade_share in (1.0, 0.4):  # trade every day, or only 40% of days (fewer, bigger)
    for sd in (300, 600, 1000):
        for mu in (0, 50, 100, 150, 250):
            nets, pays, firsts = [], [], []
            for _ in range(N):
                on = rng.random(H) < trade_share
                close = np.where(
                    on, rng.normal(mu / trade_share, sd / np.sqrt(trade_share), H), 0.0
                )
                low = np.minimum(close, 0) - np.where(
                    on, np.abs(rng.normal(0, 0.3 * sd / np.sqrt(trade_share), H)), 0
                )
                close, low = funded.apply_dll(close, low, 1000, 4)
                o = funded.lifecycle(close, low, combine, xfa, H)
                nets.append(o.net)
                pays.append(o.first_payout_day is not None)
                if o.first_payout_day:
                    firsts.append(o.first_payout_day)
            print(
                f"{mu:8} {sd:7} {trade_share:9.0%}   | {np.mean(nets):8.0f} {np.mean(np.array(nets) > 0):8.0%} {np.mean(pays):9.0%}  {np.median(firsts) if firsts else '-':>8}"
            )
