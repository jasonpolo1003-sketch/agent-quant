"""Cash gate for one or more sleeves in one Topstep account (bigger-edge plan A1/A2/B3).

    uv run python scripts/prop_portfolio.py --spec brain/_system/futures/sc-fut-0007-spec.v1.json \
        --sleeve <workbench fingerprint prefix>:<size> [--sleeve ...]

Refuses unless the spec matches its pinned .sha256. Reads the stated payout range from
the spec's gates. Every pricing plan x payout path is one cell and one prop trial.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from quant_brain.config import BRAIN_DIR, PROJECT_ROOT
from quant_brain.prop import funded, portfolio
from quant_brain.workbench import engine

PROP = BRAIN_DIR / "_system" / "prop"
COMBINE = PROP / "topstep_50k.json"
XFA = PROP / "topstep_50k_xfa.json"
OUT = PROJECT_ROOT / engine.WORKBENCH / "prop" / "portfolio"
LEDGER = PROJECT_ROOT / engine.WORKBENCH / "prop_trials.jsonl"
PLANS = ("standard", "no_activation_fee")
PAYOUT_PATHS = ("standard", "consistency")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--sleeve", action="append", required=True, help="fingerprint:size")
    parser.add_argument("--paths", type=int, default=2_000)
    parser.add_argument("--outer", type=int, default=40)
    parser.add_argument("--inner", type=int, default=300)
    args = parser.parse_args()

    spec_path = PROJECT_ROOT / args.spec
    pinned = spec_path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(spec_path.read_bytes()).hexdigest() != pinned:
        raise SystemExit(f"{args.spec} does not match its pinned hash; refusing")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    payout_range = tuple(spec["gates"]["stated_payout_range"])

    ledger = engine.read_ledger(PROJECT_ROOT)
    sleeves, trials = [], []
    for item in args.sleeve:
        prefix, size = item.rsplit(":", 1)
        matches = [e for e in ledger if e["fingerprint"].startswith(prefix)]
        if len(matches) != 1:
            raise SystemExit(f"need exactly one workbench trial matching {prefix!r}")
        trial = matches[0]
        table = engine.DayTable.load(PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz")
        sleeves.append(portfolio.Sleeve(trial["fingerprint"][:12], table, trial["market"], int(size)))
        trials.append(trial | {"size": int(size)})
    book = portfolio.combine(sleeves)
    dll = json.loads(COMBINE.read_text(encoding="utf-8"))["daily_loss_limit_usd"]

    cells = []
    for plan in PLANS:
        combine_rules, activation = funded.plan_rules(COMBINE, plan)
        for path in PAYOUT_PATHS:
            xr = funded.XfaRules.from_json(XFA, path, dll=True, activation=activation)
            started = time.time()
            r = portfolio.evaluate(
                book,
                combine_rules,
                xr,
                payout_range=payout_range,
                dll=dll,
                n_paths=args.paths,
                outer=args.outer,
                inner=args.inner,
            )
            st, lk = r["strategy"], r["luck"]
            lo, hi = r["net_cash_minus_luck_90ci"]
            print(
                f"{plan:17} {path:11} net ${st['mean_net_cash']:6.0f} "
                f"(>$0 {st['chance_net_cash_positive']:4.0%}, payout {st['chance_any_payout']:4.0%}, "
                f"first by {st['median_days_to_first_payout']}) luck ${lk['mean_net_cash']:6.0f} "
                f"diff [{lo:+6.0f}, {hi:+6.0f}] {r['gate'].upper()}  ({time.time() - started:.0f}s)",
                flush=True,
            )
            cells.append(r | {"plan": plan, "payout_path": path})
            with LEDGER.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps(
                        {
                            "at": datetime.now(UTC).isoformat(timespec="seconds"),
                            "spec": str(args.spec),
                            "spec_sha256": pinned,
                            "sleeves": [
                                {k: t[k] for k in ("fingerprint", "family", "market", "size")}
                                for t in trials
                            ],
                            "plan": plan,
                            "payout_path": path,
                            "horizon": r["horizon_days"],
                            "level": "L3",
                            "net_cash_minus_luck_90ci": [lo, hi],
                            "gate": r["gate"],
                        }
                    )
                    + "\n"
                )
    passing = [c for c in cells if c["gate"] == "pass"]
    chosen = max(passing, key=lambda c: c["net_cash_minus_luck_90ci"][0]) if passing else None
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = OUT / f"{spec['card_id']}_{stamp}.json"
    out.write_text(
        json.dumps(
            {
                "spec": str(args.spec),
                "spec_sha256": pinned,
                "sleeves": trials,
                "settings": {"paths": args.paths, "outer": args.outer, "inner": args.inner},
                "cells": cells,
                "selected": None
                if chosen is None
                else {k: chosen[k] for k in ("plan", "payout_path")},
            },
            indent=2,
            default=float,
        )
        + "\n",
        encoding="utf-8",
    )
    print("selected:", "none" if chosen is None else f"{chosen['plan']} / {chosen['payout_path']}")
    print(f"written {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
