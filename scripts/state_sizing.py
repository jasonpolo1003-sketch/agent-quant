"""PROP-STATE-SIZING-v1: size from the account's cushion, train/test by alternating years.

    .venv/Scripts/python.exe scripts/state_sizing.py

Reads the pinned spec brain/_system/prop/state-sizing.v1.json (refuses on a hash
mismatch). Q1: the best (a_eval, a_funded) for SC-FUT-0005 on the train years,
judged on the test years against luck. Q2 (JJ Simon's claim): the best pair for the
zero-edge control on its own, judged on the test years. Q3: a $500 live account at
1 MNQ. One ledger line per test cell (kind state_sizing) in prop_trials.jsonl;
full results in workbench/prop/state_sizing/.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from datetime import UTC, datetime

import numpy as np

from quant_brain.config import PROJECT_ROOT
from quant_brain.prop import firms, play
from quant_brain.prop.play import Play
from quant_brain.prop.policy import Days
from quant_brain.prop.replay import DLL_SLIP_TICKS, block_paths
from quant_brain.workbench import engine

SPEC = PROJECT_ROOT / "brain" / "_system" / "prop" / "state-sizing.v1.json"
RUN = "266777ef"
FIRM_FILES = {
    "topstep_50k_standard": "brain/_system/prop/firms/topstep_50k_standard.json",
    "tradeify_growth_50k": "brain/_system/prop/firms/tradeify_growth_50k.json",
}
DEFAULT_CAP = 50


def sizer(a_eval: float, a_funded: float, r_usd: float, firm):
    def size(ctx, ph) -> int:
        a = a_eval if ctx.phase == "eval" else a_funded
        cap = firm.max_micros if ctx.phase == "eval" else firm.funded_max_micros
        n = math.floor(a * max(ctx.cushion, 0.0) / r_usd)
        return max(1, min(n, cap or DEFAULT_CAP))

    return size


def live_500(days: Days, spec: dict, rng: np.random.Generator, n_paths: int = 20_000) -> dict:
    """$500 cash account, 1 MNQ: liquidated at $50 equity intraday, or stop at +$50."""
    cfg = spec["live_500"]
    start, floor = cfg["account_usd"], 50.0
    slip = DLL_SLIP_TICKS * days.tick
    out = {}
    for horizon in cfg["horizons_days"]:
        idx = block_paths(days.n_days, horizon, n_paths, rng)
        goal_hit = lost = 0
        ends, days_to_goal = [], []
        for path in idx:
            eq = float(start)
            for k, d in enumerate(path):
                close, low = days.outcome(int(d), None, cfg["contracts"], None, None)
                if eq + low <= floor:
                    eq = floor - slip
                    lost += 1
                    break
                eq += close
                if horizon == cfg["horizons_days"][0] and eq >= start + 50:
                    goal_hit += 1
                    days_to_goal.append(k + 1)
                    break
            ends.append(eq)
        ends = np.array(ends)
        out[str(horizon)] = {
            "chance_goal_+50": goal_hit / n_paths if horizon == cfg["horizons_days"][0] else None,
            "median_days_to_goal": float(np.median(days_to_goal)) if days_to_goal else None,
            "chance_liquidated": lost / n_paths,
            "mean_end_equity": float(ends.mean()),
            "median_end_equity": float(np.median(ends)),
            "p5_end_equity": float(np.percentile(ends, 5)),
            "p95_end_equity": float(np.percentile(ends, 95)),
        }
    return out


def main() -> int:
    raw = SPEC.read_bytes()
    pinned = SPEC.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(raw).hexdigest() != pinned:
        raise SystemExit("state-sizing spec does not match its pinned hash; refusing")
    spec = json.loads(raw)
    st = spec["settings"]
    rule = spec["sizing_rule"]

    trial = next(e for e in engine.read_ledger(PROJECT_ROOT) if e["fingerprint"].startswith(RUN))
    table = engine.DayTable.load(PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz")
    years = np.array([int(d[:4]) for d in table.dates])
    train = np.flatnonzero(np.isin(years, spec["split"]["train_years"]))
    test = np.flatnonzero(np.isin(years, spec["split"]["test_years"]))
    print(f"days: train {len(train)}, test {len(test)}", flush=True)

    kw = dict(horizon=st["horizon_days"], n_paths=st["paths"], outer=st["outer"], inner=st["inner"])
    base = Play("state", 1, 1)  # sizes come from the sizer; firm DLL taken, stop at target
    ledger = PROJECT_ROOT / engine.WORKBENCH / "prop_trials.jsonl"
    results: dict = {"spec_sha256": pinned, "workbench_trial": trial, "firms": {}}

    def log(cell: dict) -> None:
        with ledger.open("a", encoding="utf-8", newline="\n") as h:
            h.write(json.dumps(cell, default=float) + "\n")

    def brief(r: dict) -> dict:
        return {
            "mean_net_cash": r["strategy"]["mean_net_cash"],
            "net_cash_90ci": r["net_cash_90ci"],
            "chance_any_payout": r["strategy"]["chance_any_payout"],
            "net_cash_5th_percentile": r["strategy"]["net_cash_5th_percentile"],
            "luck_mean_net_cash": r["luck"]["mean_net_cash"],
            "luck_net_cash_90ci": r["luck_net_cash_90ci"],
            "luck_chance_any_payout": r["luck"]["chance_any_payout"],
            "net_cash_minus_luck_90ci": r["net_cash_minus_luck_90ci"],
            "gate": r["gate"],
        }

    for label, rel in FIRM_FILES.items():
        path = PROJECT_ROOT / rel
        fsha = hashlib.sha256(path.read_bytes()).hexdigest()
        for variant, firm in firms.load_firm(path).items():
            key = f"{label}/{variant}"
            t0 = time.time()
            grid = []
            for ae in rule["a_eval"]:
                for af in rule["a_funded"]:
                    r = play.evaluate_play(
                        table,
                        trial["market"],
                        base,
                        firm,
                        level="L3",
                        subset=train,
                        sizer=sizer(ae, af, rule["R_usd"], firm),
                        **kw,
                    )
                    grid.append({"a_eval": ae, "a_funded": af} | brief(r))
            best_s = max(grid, key=lambda g: g["mean_net_cash"])
            best_l = max(grid, key=lambda g: g["luck_mean_net_cash"])
            test_cells = {}
            for name, pick in (("Q1_strategy_pick", best_s), ("Q2_luck_pick", best_l)):
                r = play.evaluate_play(
                    table,
                    trial["market"],
                    base,
                    firm,
                    level="L3",
                    subset=test,
                    sizer=sizer(pick["a_eval"], pick["a_funded"], rule["R_usd"], firm),
                    **kw,
                )
                test_cells[name] = {"a_eval": pick["a_eval"], "a_funded": pick["a_funded"]} | brief(
                    r
                )
            p4 = Play("P4_sprint_both", 12, 4, "consistency_safe", "funded_consistency_safe")
            r = play.evaluate_play(table, trial["market"], p4, firm, level="L3", subset=test, **kw)
            test_cells["P4_baseline"] = brief(r)
            q2 = test_cells["Q2_luck_pick"]
            test_cells["Q2_zero_edge_supported"] = q2["luck_net_cash_90ci"][0] > 0
            results["firms"][key] = {"firm_sha256": fsha, "train_grid": grid, "test": test_cells}
            for name in ("Q1_strategy_pick", "Q2_luck_pick", "P4_baseline"):
                c = test_cells[name]
                log(
                    {
                        "at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "kind": "state_sizing",
                        "spec_sha256": pinned,
                        "workbench_fingerprint": trial["fingerprint"],
                        "firm_file": rel,
                        "firm_sha256": fsha,
                        "variant": variant,
                        "cell": name,
                        "split": "test",
                        "a_eval": c.get("a_eval"),
                        "a_funded": c.get("a_funded"),
                        **{
                            k: c[k]
                            for k in (
                                "mean_net_cash",
                                "net_cash_90ci",
                                "luck_mean_net_cash",
                                "luck_net_cash_90ci",
                                "net_cash_minus_luck_90ci",
                                "chance_any_payout",
                                "gate",
                            )
                        },
                    }
                )
                print(
                    f"{key[:36]:36} {name:17} a=({c.get('a_eval')},{c.get('a_funded')}) "
                    f"net ${c['mean_net_cash']:6.0f} [{c['net_cash_90ci'][0]:+5.0f},{c['net_cash_90ci'][1]:+5.0f}] "
                    f"payout {c['chance_any_payout']:4.0%} luck ${c['luck_mean_net_cash']:6.0f} "
                    f"[{c['luck_net_cash_90ci'][0]:+5.0f},{c['luck_net_cash_90ci'][1]:+5.0f}] "
                    f"diff lo {c['net_cash_minus_luck_90ci'][0]:+5.0f} {c['gate'].upper()}",
                    flush=True,
                )
            print(f"  ({time.time() - t0:.0f}s)", flush=True)

    days = Days(table, trial["market"], "L3")
    results["live_500"] = live_500(days, spec, np.random.default_rng(20261028))
    print("live $500, 1 MNQ:", json.dumps(results["live_500"], indent=1), flush=True)

    out_dir = PROJECT_ROOT / engine.WORKBENCH / "prop" / "state_sizing"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{trial['fingerprint'][:12]}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8")
    print("written", out.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
