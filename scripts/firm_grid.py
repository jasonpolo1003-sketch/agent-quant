"""Run a frozen account-play menu across prop firms (plan E1/O: prop_firm_grid_plan.md).

    .venv/Scripts/python.exe scripts/firm_grid.py \
        --menu brain/_system/prop/account-play-menu.v1.json --run <workbench fingerprint prefix> \
        [--firms "brain/_system/prop/firms/*.json"] [--topstep]

Refuses unless the menu matches its pinned hash (<menu stem>.sha256 beside it), every
firm file loads (a missing required field stops the run before anything is written;
--skip-invalid runs the rest and lists the invalid files with their errors), and the
workbench table has minute records. Firms not marked automation-allowed in
both phases are skipped and listed. --topstep adds the Topstep 50K adapter over the
existing topstep_50k*.json files.

Each firm x variant x play cell: a 42-day lifecycle bootstrap (strategy and luck on
the same resampled days, the same play), outer resampling for 90% bounds on mean net
cash and on (net - luck). Gate: both lower bounds > $0. One ledger line per cell in
prop_trials.jsonl; the full results in workbench/prop/firm_grid/. Selection: the
passing cell with the highest lower bound of mean net cash, or none.
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
from quant_brain.prop import firms, play
from quant_brain.workbench import engine

PROP = BRAIN_DIR / "_system" / "prop"
DEFAULT_FIRMS = "brain/_system/prop/firms/*.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _abs(root: Path, p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else root / q


def _load_firms(root: Path, pattern: str, topstep: bool):
    """(cells: [(firm file label, sha, variant, Firm)], skipped, errors)."""
    files = (
        sorted(root.glob(pattern))
        if not Path(pattern).is_absolute()
        else sorted(Path(pattern).parent.glob(Path(pattern).name))
    )
    out, skipped, errors = [], [], []
    for path in files:
        try:
            variants = firms.load_firm(path)
        except ValueError as exc:
            where = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
            errors.append({"firm_file": where, "error": str(exc)})
            continue
        label = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        for name, f in variants.items():
            if not f.automation_allowed:
                skipped.append(
                    {"firm_file": label, "variant": name, "reason": "automation not allowed"}
                )
                continue
            out.append((label, _sha(path), name, f))
    if topstep:
        combine, xfa = PROP / "topstep_50k.json", PROP / "topstep_50k_xfa.json"
        sha = hashlib.sha256(combine.read_bytes() + xfa.read_bytes()).hexdigest()
        for name, f in firms.topstep(combine, xfa).items():
            out.append(("topstep_50k (adapter)", sha, name, f))
    return out, skipped, errors


def main(argv: list[str] | None = None, root: Path = PROJECT_ROOT) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--menu", required=True, help="pinned account-play menu JSON")
    parser.add_argument("--run", required=True, help="workbench trial fingerprint (prefix ok)")
    parser.add_argument("--firms", default=DEFAULT_FIRMS, help="glob of firm rules JSON")
    parser.add_argument("--topstep", action="store_true", help="add the Topstep 50K adapter")
    parser.add_argument(
        "--skip-invalid", action="store_true", help="run the firms that load; list the rest"
    )
    parser.add_argument("--paths", type=int, default=2_000)
    parser.add_argument("--outer", type=int, default=40)
    parser.add_argument("--inner", type=int, default=300)
    args = parser.parse_args(argv)

    menu_path = _abs(root, args.menu)
    pin_path = menu_path.with_suffix(".sha256")
    if not pin_path.exists():
        raise SystemExit(f"no pinned hash {pin_path.name} beside the menu; refusing")
    pinned = pin_path.read_text(encoding="utf-8").split()[0]
    if _sha(menu_path) != pinned:
        raise SystemExit("account-play menu does not match its pinned hash; refusing")
    menu = json.loads(menu_path.read_text(encoding="utf-8"))
    plays = play.load_plays(menu_path)
    horizon, level = menu["grid"]["horizon_days"], menu["grid"]["cost_level"]

    matches = [e for e in engine.read_ledger(root) if e["fingerprint"].startswith(args.run)]
    if len(matches) != 1:
        raise SystemExit(f"need exactly one workbench trial matching {args.run!r}")
    trial = matches[0]
    table = engine.DayTable.load(root / engine.CACHE / f"{trial['fingerprint']}.npz")
    n = len(table.dates)
    if table.orb_rec_off.size != n + 1 or table.ctrl_rec_idx.shape[0] != n:
        raise SystemExit("cached table has no minute records; re-run the workbench trial")

    cells_in, skipped, errors = _load_firms(root, args.firms, args.topstep)
    for e in errors:
        print(f"INVALID {e['firm_file']}: {e['error']}", flush=True)
    if errors and not args.skip_invalid:
        raise SystemExit(
            "firm rules failed to load; nothing run:\n  "
            + "\n  ".join(f"{e['firm_file']}: {e['error']}" for e in errors)
        )
    if not cells_in:
        raise SystemExit("no firm to run (check --firms and the automation flags)")

    ledger = root / engine.WORKBENCH / "prop_trials.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    cells = []
    for label, sha, variant, f in cells_in:
        for p in plays:
            started = time.time()
            r = play.evaluate_play(
                table,
                trial["market"],
                p,
                f,
                horizon=horizon,
                n_paths=args.paths,
                outer=args.outer,
                inner=args.inner,
                level=level,
            )
            cell = {"firm_file": label, "firm_sha256": sha, "variant": variant, "policy": p.name}
            cells.append(cell | r)
            st, lk = r["strategy"], r["luck"]
            (nlo, _), (dlo, dhi) = r["net_cash_90ci"], r["net_cash_minus_luck_90ci"]
            print(
                f"{label[:28]:28} {variant[:24]:24} {p.name:16} net ${st['mean_net_cash']:6.0f} "
                f"[lo {nlo:+6.0f}] payout {st['chance_any_payout']:4.0%} 5% ${st['net_cash_5th_percentile']:6.0f} "
                f"luck ${lk['mean_net_cash']:6.0f}{' (!)' if r['luck_positive_flag'] else ''} "
                f"diff [{dlo:+6.0f}, {dhi:+6.0f}] {r['gate'].upper()}  ({time.time() - started:.0f}s)",
                flush=True,
            )
            with ledger.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps(
                        {
                            "at": datetime.now(UTC).isoformat(timespec="seconds"),
                            "kind": "firm_grid",
                            "menu_sha256": pinned,
                            "workbench_fingerprint": trial["fingerprint"],
                            "family": trial["family"],
                            "market": trial["market"],
                            "firm_file": label,
                            "firm_sha256": sha,
                            "variant": variant,
                            "policy": p.name,
                            "horizon": horizon,
                            "level": level,
                            "mean_net_cash": st["mean_net_cash"],
                            "net_cash_90ci": r["net_cash_90ci"],
                            "luck_mean_net_cash": lk["mean_net_cash"],
                            "net_cash_minus_luck_90ci": r["net_cash_minus_luck_90ci"],
                            "chance_any_payout": st["chance_any_payout"],
                            "net_cash_5th_percentile": st["net_cash_5th_percentile"],
                            "luck_positive_flag": r["luck_positive_flag"],
                            "gate": r["gate"],
                        }
                    )
                    + "\n"
                )
    passing = [c for c in cells if c["gate"] == "pass"]
    chosen = max(passing, key=lambda c: c["net_cash_90ci"][0]) if passing else None
    out_dir = root / engine.WORKBENCH / "prop" / "firm_grid"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"{trial['fingerprint'][:12]}_{stamp}.json"
    result = {
        "menu": menu_path.relative_to(root).as_posix()
        if menu_path.is_relative_to(root)
        else str(menu_path),
        "menu_sha256": pinned,
        "workbench_trial": trial,
        "settings": {"paths": args.paths, "outer": args.outer, "inner": args.inner},
        "firms_glob": args.firms,
        "skipped": skipped,
        "invalid": errors,
        "luck_positive_cells": [
            {k: c[k] for k in ("firm_file", "variant", "policy")}
            for c in cells
            if c["luck_positive_flag"]
        ],
        "cells": cells,
        "selected": None
        if chosen is None
        else {k: chosen[k] for k in ("firm_file", "variant", "policy")},
    }
    out.write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
    print(
        "selected:",
        "none (no cell passes)"
        if chosen is None
        else f"{chosen['firm_file']} / {chosen['variant']} / {chosen['policy']}",
    )
    if result["luck_positive_cells"]:
        print(f"WARNING: luck averages positive in {len(result['luck_positive_cells'])} cells")
    print(f"written {out.relative_to(root).as_posix() if out.is_relative_to(root) else out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
