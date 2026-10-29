"""SC-FUT-0013 runs: month-end rebalancing (T1) and turn of the month (T2), practice only.

    PYTHONPATH=src .venv/Scripts/python.exe scripts/month_end_report.py

Runs, in the addendum's order, MES T1, MES T2 (gated) and MNQ T1, MNQ T2 (diagnostics) through
the workbench (each is one logged trial), then the spec diagnostics. Writes one JSON per run to
the workbench results folder and a combined report to results/sc-fut-0013-month-end.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workbench as wb

from quant_brain.config import PROJECT_ROOT
from quant_brain.workbench import analysis, engine, month_end

RUNS = [
    ("MES", "T1_rebalance"),
    ("MES", "T2_turn_of_month"),
    ("MNQ", "T1_rebalance"),
    ("MNQ", "T2_turn_of_month"),
]


def main() -> int:
    base = month_end.loader(wb.DEV_DIR, wb.MULTI_DIR)
    memo: dict = {}

    def load(market, start, end, roll_column):
        key = (market, start, end, roll_column)
        if key not in memo:
            memo[key] = base(market, start, end, roll_column)
        return memo[key]

    report: dict = {"runs": {}, "diagnostics": {}}
    tables = {}
    for market, trial in RUNS:
        strategy = month_end.MonthEnd(trial)
        table, record, cached = engine.run(PROJECT_ROOT, strategy, market, "volume", load)
        tables[(market, trial)] = table
        generic = analysis.summary(PROJECT_ROOT, table, record)
        spec = month_end.spec_verdict(table, market)
        generic["spec_verdict"] = spec
        out = PROJECT_ROOT / wb.RESULTS / f"{record['fingerprint']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(generic, indent=2, default=float) + "\n", encoding="utf-8")
        entry = {
            "fingerprint": record["fingerprint"],
            "cached": cached,
            "workbench_honesty_bar": generic["honesty"],
            "spec_verdict": spec,
            "per_year": month_end.per_year(table, market),
            "status_counts": dict(Counter(table.status.tolist())),
        }
        if trial == "T1_rebalance":
            entry["hit_rate_by_sign_of_rel"] = month_end.hit_rate_by_side(table)
        report["runs"][f"{market} {trial}"] = entry
        print(
            f"{market} {trial}: {spec['outcome']} n={spec['trade_days']} "
            f"$/trade {spec.get('per_trade', 0):.2f} $/session {spec.get('per_session', 0):.3f} "
            f"p {spec.get('p_value', 1):.4f} (bar {spec['alpha']:.4f}); {'; '.join(spec['reasons'])}",
            flush=True,
        )

    # signal coverage (MES-minus-ZN, shared by both markets)
    signals = base.cache["signals"]
    rels = [s.rel if s is not None else None for s in signals.values()]
    report["diagnostics"]["signal_months"] = {
        "months": len(rels),
        "rel>0": sum(r is not None and r > 0 for r in rels),
        "rel<0": sum(r is not None and r < 0 for r in rels),
        "missing": [f"{k[0]}-{k[1]:02d}" for k, s in signals.items() if s is None or s.rel is None],
        "rel_values": {
            f"{k[0]}-{k[1]:02d}": None if s is None or s.rel is None else float(s.rel)
            for k, s in signals.items()
        },
    }
    # T2 vs always-long on every other session
    start, end = engine.PRACTICE
    for market in ("MES", "MNQ"):
        days = load(market, start, end, "volume_roll_date")
        cost = analysis.COSTS["L3"][market]
        other = month_end.always_long_other(days, cost)
        t2 = tables[(market, "T2_turn_of_month")]
        trade = t2.evaluable & (t2.orb_trades > 0)
        t2_net = (t2.orb_gross[trade] - cost).astype(float)
        report["diagnostics"][f"{market} T2 vs always-long other sessions"] = {
            "T2_per_trade": float(t2_net.mean() / 100),
            "T2_trade_days": int(trade.sum()),
            "other_per_session": other["per_session"],
            "other_sessions": other["sessions"],
            "other_missing_bars": other["missing_bars"],
            "difference": float(t2_net.mean() / 100 - other["per_session"]),
            "welch_t": month_end.welch_t(t2_net, other["values_cents"]),
        }
    out = PROJECT_ROOT / wb.RESULTS / "sc-fut-0013-month-end.json"
    out.write_text(json.dumps(report, indent=2, default=float) + "\n", encoding="utf-8")
    print(json.dumps(report["diagnostics"], indent=1, default=float)[:4000])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    np.seterr(all="raise")
    sys.exit(main())
