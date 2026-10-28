"""Run the frozen sizing-policy menu through the Phase 2 cash simulator (Q6-Q8).

    uv run python scripts/prop_policy.py --run <workbench fingerprint prefix>

Refuses unless brain/_system/prop/sizing-policies.v1.json matches its pinned hash.
Every policy x plan x payout-path cell is one trial in prop_trials.jsonl; the
menu's selection rule then picks at most one cell (or none).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime

from quant_brain.config import BRAIN_DIR, PROJECT_ROOT
from quant_brain.prop import funded, policy
from quant_brain.workbench import engine

PROP = BRAIN_DIR / "_system" / "prop"
MENU = PROP / "sizing-policies.v1.json"
PIN = PROP / "sizing-policies.v1.sha256"
COMBINE = PROP / "topstep_50k.json"
XFA = PROP / "topstep_50k_xfa.json"
OUT = PROJECT_ROOT / engine.WORKBENCH / "prop" / "policies"
LEDGER = PROJECT_ROOT / engine.WORKBENCH / "prop_trials.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run", required=True, help="workbench trial fingerprint (prefix ok)")
    parser.add_argument("--paths", type=int, default=2_000)
    parser.add_argument("--outer", type=int, default=40)
    parser.add_argument("--inner", type=int, default=300)
    args = parser.parse_args()

    pinned = PIN.read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(MENU.read_bytes()).hexdigest() != pinned:
        raise SystemExit("sizing-policy menu does not match its pinned hash; refusing")
    menu = json.loads(MENU.read_text(encoding="utf-8"))
    matches = [e for e in engine.read_ledger(PROJECT_ROOT) if e["fingerprint"].startswith(args.run)]
    if len(matches) != 1:
        raise SystemExit(f"need exactly one workbench trial matching {args.run!r}")
    trial = matches[0]
    table = engine.DayTable.load(PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz")
    if table.orb_rec_off.size != len(table.dates) + 1:
        raise SystemExit("cached table has no minute records; re-run the workbench trial")
    dll_usd = json.loads(COMBINE.read_text(encoding="utf-8"))["daily_loss_limit_usd"]
    grid = menu["grid"]
    cells = []
    for p in policy.load_policies(MENU):
        for plan in grid["plans"]:
            combine, activation = funded.plan_rules(COMBINE, plan)
            for path in grid["payout_paths"]:
                xr = funded.XfaRules.from_json(XFA, path, dll=p.dll, activation=activation)
                started = time.time()
                r = policy.evaluate_policy(
                    table,
                    trial["market"],
                    p,
                    combine,
                    xr,
                    horizon=grid["horizon_days"],
                    dll_usd=dll_usd,
                    n_paths=args.paths,
                    outer=args.outer,
                    inner=args.inner,
                    level=grid["cost_level"],
                )
                cell = {k: v for k, v in r.items() if k != "policy"} | {
                    "policy": p.name,
                    "plan": plan,
                    "payout_path": path,
                    "policy_detail": r["policy"],
                }
                cells.append(cell)
                st, lk = r["strategy"], r["luck"]
                lo, hi = r["net_cash_minus_luck_90ci"]
                print(
                    f"{p.name:20} {plan:17} {path:11} net ${st['mean_net_cash']:6.0f} "
                    f"(>$0 {st['chance_net_cash_positive']:4.0%}, payout by "
                    f"{st['median_days_to_first_payout']}) luck ${lk['mean_net_cash']:6.0f}  "
                    f"diff [{lo:+6.0f}, {hi:+6.0f}] {'ELIGIBLE' if r['eligible'] else ''}"
                    f"  ({time.time() - started:.0f}s)",
                    flush=True,
                )
                with LEDGER.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                                "menu_sha256": pinned,
                                "workbench_fingerprint": trial["fingerprint"],
                                "family": trial["family"],
                                "market": trial["market"],
                                "policy": p.name,
                                "plan": plan,
                                "payout_path": path,
                                "horizon": grid["horizon_days"],
                                "level": grid["cost_level"],
                                "net_cash_minus_luck_90ci": [lo, hi],
                                "gate": "eligible" if r["eligible"] else "fail",
                            }
                        )
                        + "\n"
                    )
    eligible = [c for c in cells if c["eligible"]]
    chosen = (
        max(
            eligible,
            key=lambda c: (
                c["net_cash_minus_luck_90ci"][0],
                -c["strategy"]["median_days_to_first_payout"],
            ),
        )
        if eligible
        else None
    )
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = OUT / f"{trial['fingerprint'][:12]}_{stamp}.json"
    result = {
        "menu": str(MENU.relative_to(PROJECT_ROOT)),
        "menu_sha256": pinned,
        "workbench_trial": trial,
        "settings": {"paths": args.paths, "outer": args.outer, "inner": args.inner},
        "cells": cells,
        "selected": None
        if chosen is None
        else {k: chosen[k] for k in ("policy", "plan", "payout_path")},
    }
    out.write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
    print(
        "selected:",
        "none (no cell beats luck)"
        if chosen is None
        else f"{chosen['policy']} / {chosen['plan']} / {chosen['payout_path']}",
    )
    print(f"written {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
