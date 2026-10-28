"""Run a workbench trial through the Topstep 50K simulator.

    uv run python scripts/prop_eval.py --run <workbench fingerprint prefix> --size 1
    uv run python scripts/prop_eval.py --run <prefix> --size 2 --cash --plan standard         --payout-path standard --dll        # Phase 2: net cash through Combine -> XFA -> payouts

Reads the trial's cached day table, so run `scripts/workbench.py run ...` first.
Every simulator run is fingerprinted (day data + rules + simulator code + seed +
settings) and logged as a trial in brain/04_Backtest_Reports/workbench/prop_trials.jsonl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from quant_brain.config import BRAIN_DIR, PROJECT_ROOT
from quant_brain.prop import funded, replay
from quant_brain.prop.account import Rules
from quant_brain.workbench import engine

RULES = BRAIN_DIR / "_system" / "prop" / "topstep_50k.json"
XFA_RULES = BRAIN_DIR / "_system" / "prop" / "topstep_50k_xfa.json"
OUT = PROJECT_ROOT / engine.WORKBENCH / "prop"
LEDGER = PROJECT_ROOT / engine.WORKBENCH / "prop_trials.jsonl"
SIM_CODE = (
    "src/quant_brain/prop/account.py",
    "src/quant_brain/prop/replay.py",
    "src/quant_brain/prop/paths.py",
    "src/quant_brain/prop/funded.py",
)


def _sha(*blobs: bytes) -> str:
    digest = hashlib.sha256()
    for blob in blobs:
        digest.update(blob.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--run", required=True, help="workbench trial fingerprint (prefix ok)")
    parser.add_argument("--size", type=int, required=True, help="frozen micro-contract size")
    parser.add_argument(
        "--horizon", type=int, help="trading days (default 126 for Phase 1, 42 with --cash)"
    )
    parser.add_argument("--cash", action="store_true", help="Phase 2: net cash incl. payouts")
    parser.add_argument("--plan", default="standard", choices=["standard", "no_activation_fee"])
    parser.add_argument("--payout-path", default="standard", choices=["standard", "consistency"])
    parser.add_argument("--dll", action="store_true", help="$1,000 daily loss limit at purchase")
    parser.add_argument("--level", default="L3")
    parser.add_argument(
        "--rules", type=Path, default=RULES, help="prop rules JSON (default: Topstep 50K)"
    )
    args = parser.parse_args()
    rules_path = args.rules if args.rules.is_absolute() else PROJECT_ROOT / args.rules

    matches = [e for e in engine.read_ledger(PROJECT_ROOT) if e["fingerprint"].startswith(args.run)]
    if len(matches) != 1:
        raise SystemExit(
            f"need exactly one workbench trial matching {args.run!r}, found {len(matches)}"
        )
    trial = matches[-1]
    cache = PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz"
    if not cache.exists():
        raise SystemExit("no cached day table for that trial; re-run it with scripts/workbench.py")
    table = engine.DayTable.load(cache)
    if "orb_low" not in table.__dict__ or table.orb_low.size == 0:
        raise SystemExit("cached table predates intraday lows; re-run the workbench trial")
    rules = Rules.from_json(rules_path)
    args.horizon = args.horizon or (42 if args.cash else 126)
    settings = {
        "size": args.size,
        "horizon": args.horizon,
        "level": args.level,
        "seed": replay.SEED,
    }
    if args.cash:
        rules, activation = funded.plan_rules(rules_path, args.plan)
        xfa_rules = funded.XfaRules.from_json(
            XFA_RULES, args.payout_path, dll=args.dll, activation=activation
        )
        dll = json.loads(rules_path.read_text(encoding="utf-8"))["daily_loss_limit_usd"]
        settings |= {
            "phase": 2,
            "plan": args.plan,
            "payout_path": args.payout_path,
            "dll": dll if args.dll else None,
        }
    fp = _sha(
        cache.read_bytes(),
        rules_path.read_bytes(),
        XFA_RULES.read_bytes() if args.cash else b"",
        *[(PROJECT_ROOT / f).read_bytes() for f in SIM_CODE],
        json.dumps(settings, sort_keys=True).encode(),
    )
    out = OUT / f"{fp}.json"
    if out.exists():
        result = json.loads(out.read_text(encoding="utf-8"))
        print("cached simulator result")
    elif args.cash:
        result = replay.evaluate_cash(
            table,
            trial["market"],
            rules,
            xfa_rules,
            frozen_size=args.size,
            horizon=args.horizon,
            dll=settings["dll"],
            level=args.level,
        )
    else:
        result = replay.evaluate(
            table,
            trial["market"],
            rules,
            frozen_size=args.size,
            horizon=args.horizon,
            level=args.level,
        )
    if not out.exists():
        result |= {
            "workbench_trial": trial,
            "simulator_fingerprint": fp,
            "rules_file": str(rules_path.relative_to(PROJECT_ROOT)),
        }
        OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
        with LEDGER.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "simulator_fingerprint": fp,
                        "workbench_fingerprint": trial["fingerprint"],
                        "family": trial["family"],
                        "market": trial["market"],
                        **settings,
                        "gate": result.get("phase2_gate", result.get("phase1_gate")),
                    }
                )
                + "\n"
            )
    s = result["by_size"][str(args.size)]
    if args.cash:
        st, luck = s["strategy"], result["by_size"][str(result["luck_best_size"])]["luck"]
        lo, hi = result["net_cash_minus_luck_90ci"]
        print(
            f"{trial['family']} {trial['market']} size {args.size}, {args.horizon} days: "
            f"net cash ${st['mean_net_cash']:.0f} (chance > $0 {st['chance_net_cash_positive']:.0%}, "
            f"first payout median {st['median_days_to_first_payout']} days) vs luck "
            f"${luck['mean_net_cash']:.0f} at size {result['luck_best_size']}; "
            f"difference 90% range [${lo:+.0f}, ${hi:+.0f}]; gate {result['phase2_gate']}"
        )
        return 0
    lo, hi = result["first_account_pass_minus_luck_90ci"]
    print(
        f"{trial['family']} {trial['market']} size {args.size}: first-account pass {s['strategy']['first_account_pass_rate']:.1%} "
        f"vs luck {result['by_size'][str(result['luck_best_size'])]['luck']['first_account_pass_rate']:.1%} "
        f"(luck best size {result['luck_best_size']}); difference 90% range [{lo:+.1%}, {hi:+.1%}]; "
        f"fees per pass ${s['strategy']['fees_per_pass'] or float('nan'):.0f}; gate {result['phase1_gate']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
