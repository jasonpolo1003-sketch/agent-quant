"""PROP-PLAY-v2: bigger sizes, picked on train years, judged once on test years.

    .venv/Scripts/python.exe scripts/menu_v2.py

Reads the pinned menu brain/_system/prop/account-play-menu.v2.json (refuses on a hash
mismatch) and its addendum 1. Units: the Topstep 50K adapter variants (as firm_grid.py
--topstep), firms/topstep_50k_standard.json, and LucidFlex 50K at its indicative price
(reported, never selectable). Per unit: every (eval, funded) size pair on the train
years (strategy and luck on the same paths, same sizes); the pick is the highest lower
90% bound of mean net cash; the pick alone runs on the test years against the gate (net
lower bound > $0 AND (net - luck) lower bound > $0); a test pass is re-run on test with a
fresh seed and outer 200. One ledger line per cell (kind menu_v2) in prop_trials.jsonl;
full results in workbench/prop/menu_v2/.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import UTC, datetime

import numpy as np

from quant_brain.config import PROJECT_ROOT
from quant_brain.prop import firms, play
from quant_brain.prop.play import Play
from quant_brain.prop.replay import SEED
from quant_brain.workbench import engine

PROP = PROJECT_ROOT / "brain" / "_system" / "prop"
MENU = PROP / "account-play-menu.v2.json"
ADDENDUM = PROP / "account-play-menu.v2-addendum-1.md"
RUN = "266777ef"
CONFIRM_SEED = 20261029  # addendum 1, item 8
CONFIRM_OUTER = 200
STOPS = ("consistency_safe", "funded_consistency_safe")
# Funded scaling-plan start sizes stated in the firm files (addendum 1, item 4).
SCALING_START = {"topstep": 20, "lucid_flex_50k": 20}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def units() -> list[dict]:
    """[(label, firm file, sha, variant, Firm, selectable)] as dicts."""
    out = []
    combine, xfa = PROP / "topstep_50k.json", PROP / "topstep_50k_xfa.json"
    sha = _sha(combine.read_bytes() + xfa.read_bytes())
    for v, f in firms.topstep(combine, xfa).items():
        out.append(
            dict(
                label="topstep_50k (adapter)",
                sha=sha,
                variant=v,
                firm=f,
                sel=True,
                scaling=SCALING_START["topstep"],
            )
        )
    for rel, sel, scal in (
        ("firms/topstep_50k_standard.json", True, SCALING_START["topstep"]),
        ("firms_indicative/lucid_flex_50k.json", False, SCALING_START["lucid_flex_50k"]),
    ):
        path = PROP / rel
        for v, f in firms.load_firm(path).items():
            out.append(
                dict(
                    label=f"brain/_system/prop/{rel}",
                    sha=_sha(path.read_bytes()),
                    variant=v,
                    firm=f,
                    sel=sel,
                    scaling=scal,
                )
            )
    return out


def pairs(menu: dict, firm, scaling: int | None) -> list[dict]:
    """Size pairs cut to the caps; a cut that duplicates an earlier pair is dropped."""
    e_cap = firm.max_micros
    f_cap = min(x for x in (firm.funded_max_micros, scaling) if x is not None)
    seen, out = set(), []
    for e in menu["policies"]["eval_sizes_mnq"]:
        for f in menu["policies"]["funded_sizes_mnq"]:
            ce = min(e, e_cap) if e_cap else e
            cf = min(f, f_cap) if f_cap else f
            if (ce, cf) in seen:
                continue
            seen.add((ce, cf))
            out.append({"eval": ce, "funded": cf, "menu_eval": e, "menu_funded": f})
    return out


def brief(r: dict) -> dict:
    st, lk = r["strategy"], r["luck"]
    return {
        "mean_net_cash": st["mean_net_cash"],
        "net_cash_90ci": r["net_cash_90ci"],
        "net_cash_minus_luck_90ci": r["net_cash_minus_luck_90ci"],
        "chance_any_payout": st["chance_any_payout"],
        "chance_net_cash_positive": st["chance_net_cash_positive"],
        "net_cash_5th_percentile": st["net_cash_5th_percentile"],
        "median_days_to_first_payout": st["median_days_to_first_payout"],
        "mean_fees": st["mean_fees"],
        "mean_payouts": st["mean_payouts"],
        "luck_mean_net_cash": lk["mean_net_cash"],
        "luck_net_cash_90ci": r["luck_net_cash_90ci"],
        "luck_chance_any_payout": lk["chance_any_payout"],
        "luck_mean_fees": lk["mean_fees"],
        "luck_positive_flag": r["luck_positive_flag"],
        "resolved": r["resolved"],
        "gate": r["gate"],
    }


def main() -> int:
    raw = MENU.read_bytes()
    pinned = MENU.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    if _sha(raw) != pinned:
        raise SystemExit("account-play menu v2 does not match its pinned hash; refusing")
    if not ADDENDUM.exists():
        raise SystemExit("addendum 1 missing; refusing")
    menu = json.loads(raw)
    st = menu["settings"]

    trial = next(e for e in engine.read_ledger(PROJECT_ROOT) if e["fingerprint"].startswith(RUN))
    table = engine.DayTable.load(PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz")
    years = np.array([int(d[:4]) for d in table.dates])
    if years.max() >= 2025:
        raise SystemExit("table holds 2025+ (exam) days; refusing")
    train = np.flatnonzero(np.isin(years, menu["split"]["train_years"]))
    test = np.flatnonzero(np.isin(years, menu["split"]["test_years"]))
    print(f"days: train {len(train)}, test {len(test)}", flush=True)

    kw = dict(horizon=st["horizon_days"], n_paths=st["paths"], inner=st["inner"], level="L3")
    ledger = PROJECT_ROOT / engine.WORKBENCH / "prop_trials.jsonl"
    results: dict = {
        "menu": MENU.relative_to(PROJECT_ROOT).as_posix(),
        "menu_sha256": pinned,
        "addendum": ADDENDUM.relative_to(PROJECT_ROOT).as_posix(),
        "addendum_sha256": _sha(ADDENDUM.read_bytes()),
        "workbench_trial": trial,
        "days": {"train": len(train), "test": len(test)},
        "settings": st
        | {"seed": SEED, "confirm_seed": CONFIRM_SEED, "confirm_outer": CONFIRM_OUTER},
        "units": [],
    }

    def log(u: dict, split: str, pr: dict, c: dict, outer: int, seed: int) -> None:
        line = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "kind": "menu_v2",
            "menu_sha256": pinned,
            "workbench_fingerprint": trial["fingerprint"],
            "family": trial.get("family"),
            "market": trial["market"],
            "firm_file": u["label"],
            "firm_sha256": u["sha"],
            "variant": u["variant"],
            "selectable": u["sel"],
            "split": split,
            "eval_size": pr["eval"],
            "funded_size": pr["funded"],
            "horizon": st["horizon_days"],
            "level": "L3",
            "outer": outer,
            "seed": seed,
            **{
                k: c[k]
                for k in (
                    "mean_net_cash",
                    "net_cash_90ci",
                    "luck_mean_net_cash",
                    "luck_net_cash_90ci",
                    "net_cash_minus_luck_90ci",
                    "chance_any_payout",
                    "net_cash_5th_percentile",
                    "luck_positive_flag",
                    "gate",
                )
            },
        }
        with ledger.open("a", encoding="utf-8", newline="\n") as h:
            h.write(json.dumps(line, default=float) + "\n")

    def run(u, pr, subset, outer, seed) -> dict:
        p = Play(f"v2_{pr['eval']}_{pr['funded']}", pr["eval"], pr["funded"], *STOPS)
        r = play.evaluate_play(
            table, trial["market"], p, u["firm"], subset=subset, outer=outer, seed=seed, **kw
        )
        return brief(r)

    def show(tag, u, pr, c):
        lo, hi = c["net_cash_90ci"]
        dlo, dhi = c["net_cash_minus_luck_90ci"]
        print(
            f"{tag:7} {u['label'][-28:]:28} {u['variant'][:28]:28} ({pr['eval']:2},{pr['funded']}) "
            f"net ${c['mean_net_cash']:6.0f} [{lo:+5.0f},{hi:+5.0f}] payout {c['chance_any_payout']:4.0%} "
            f"luck ${c['luck_mean_net_cash']:6.0f} diff [{dlo:+5.0f},{dhi:+5.0f}] {c['gate'].upper()}",
            flush=True,
        )

    for u in units():
        t0 = time.time()
        grid = []
        for pr in pairs(menu, u["firm"], u["scaling"]):
            c = run(u, pr, train, st["outer"], SEED)
            log(u, "train", pr, c, st["outer"], SEED)
            show("train", u, pr, c)
            grid.append(pr | c)
        pick = max(grid, key=lambda g: g["net_cash_90ci"][0])  # first in grid order on ties
        pr = {k: pick[k] for k in ("eval", "funded", "menu_eval", "menu_funded")}
        tc = run(u, pr, test, st["outer"], SEED)
        log(u, "test", pr, tc, st["outer"], SEED)
        show("TEST", u, pr, tc)
        conf = None
        if tc["gate"] == "pass":
            conf = run(u, pr, test, CONFIRM_OUTER, CONFIRM_SEED)
            log(u, "confirm", pr, conf, CONFIRM_OUTER, CONFIRM_SEED)
            show("CONFIRM", u, pr, conf)
        results["units"].append(
            {
                "firm_file": u["label"],
                "firm_sha256": u["sha"],
                "variant": u["variant"],
                "selectable": u["sel"],
                "caps": {
                    "eval": u["firm"].max_micros,
                    "funded": min(x for x in (u["firm"].funded_max_micros, u["scaling"]) if x),
                },
                "train_grid": grid,
                "pick": pr,
                "test": tc,
                "confirm": conf,
            }
        )
        print(f"  ({time.time() - t0:.0f}s)", flush=True)

    # stricter reading: one pick per firm file (addendum 1, item 1)
    per_file = {}
    for x in results["units"]:
        best = per_file.get(x["firm_file"])
        lo = max(g["net_cash_90ci"][0] for g in x["train_grid"])
        if best is None or lo > best[1]:
            per_file[x["firm_file"]] = (x["variant"], lo)
    results["per_file_pick"] = {
        k: {"variant": v, "train_net_lo": lo} for k, (v, lo) in per_file.items()
    }

    ok = [
        x
        for x in results["units"]
        if x["selectable"]
        and x["test"]["gate"] == "pass"
        and x["confirm"]
        and x["confirm"]["gate"] == "pass"
    ]
    final = max(ok, key=lambda x: x["confirm"]["net_cash_90ci"][0]) if ok else None
    results["final"] = (
        None if final is None else {k: final[k] for k in ("firm_file", "variant", "pick")}
    )
    results["trials"] = {
        s: sum(
            1
            for x in results["units"]
            for _ in (x["train_grid"] if s == "train" else [x[s]] if x[s] else [])
        )
        for s in ("train", "test", "confirm")
    }
    print(
        "final:",
        "none" if final is None else f"{final['firm_file']} / {final['variant']} / {final['pick']}",
    )

    out_dir = PROJECT_ROOT / engine.WORKBENCH / "prop" / "menu_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{trial['fingerprint'][:12]}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8")
    print("written", out.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
