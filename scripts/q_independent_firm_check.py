"""Independent recomputation of two firm cells (plan workstream Q, 2026-10-28).

    .venv/Scripts/python.exe scripts/q_independent_firm_check.py [--paths 400] [--seed 7]

Part 1 (`indep_*`) is a separate implementation of the evaluation + funded lifecycle
for Topstep 50K Standard (standard payout path, with and without the optional DLL) and
Tradeify Growth 50K, written from the rule text in brain/sources/prop_firms/*.md and the
official pages (QA review 2026-10-28). It imports nothing from quant_brain.prop.

Part 2 runs the project's `firm_sim.lifecycle_arrays` on the same synthetic day sequences
and compares net, fees, payouts, passes and first payout day path by path.

Two modes for the independent model:
- "match": the conventions the project documents where the rules are silent or where
  the project deliberately simplifies (soft DLL keeps the full-day low for the floor
  check; Topstep rebills every 21 trading days from the subscription start, resets do not
  move it; Tradeify funded DLL stays $1,250). Expect zero differences.
- "official": the official reading (Topstep: a reset/credit pushes the rebill 21 trading
  days out and every rebill adds a free reset credit; the floor check uses the low until
  the DLL exit; Tradeify funded DLL rises to $2,000 once the balance is >= start + $3,000).
  Differences are expected and are reported in aggregate.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass

HORIZON = 42
MONTH = 21


@dataclass
class Cash:
    net: float
    payouts: float
    fees: float
    passed: int
    closed: int
    first_payout: int | None


FEATURES = ("dll_low", "billing", "dll_rise")  # the official-reading items, see the docstring


def _dll_day(close: float, low: float, limit: float | None, feats: frozenset):
    """Soft daily loss: flatten at -limit (no slippage). Returns (close, low used for the floor)."""
    if limit is not None and low <= -limit:
        return -limit, (-limit if "dll_low" in feats else min(low, -limit))
    return close, low


# ------------------------------------------------------------------ Topstep 50K Standard
def indep_topstep(days, dll: bool, feats: frozenset) -> Cash:
    official = "billing" in feats
    price, reset, activation, api = 49.0, 49.0, 149.0, 29.0
    cap = 4000.0 if dll else 2000.0
    limit = 1000.0 if dll else None
    fees = payouts = 0.0
    passed = closed = 0
    first = None
    t = 0
    while t < HORIZON:
        # --- Trading Combine (a new subscription) ---
        fees += price
        sub_start, next_bill, credits = t, t + MONTH, 0
        bal, floor, best = 0.0, -2000.0, 0.0
        ok = False
        while t < HORIZON:
            if official and t == next_bill:
                fees += price
                credits += 1
                next_bill = t + MONTH
            if not official and t > sub_start and (t - sub_start) % MONTH == 0:
                fees += price
            c, lo = _dll_day(*days[t][:2], limit, feats)
            if bal + min(lo, c) <= floor:  # MLL touched intraday: reset
                if official and credits:
                    credits -= 1
                else:
                    fees += reset
                if official:
                    next_bill = t + 1 + MONTH  # reset pushes the rebill out a month
                bal, floor, best = 0.0, -2000.0, 0.0
                t += 1
                continue
            bal += c
            best = max(best, c)
            floor = max(floor, min(bal - 2000.0, 0.0))  # trails EOD, locks at the start
            t += 1
            if bal >= max(3000.0, best / 0.55):
                ok = True
                break
        if not ok:
            break
        passed += 1
        fees += activation
        # --- XFA ---
        bal, floor, locked = 0.0, -2000.0, False
        wins, cycle, n_paid = 0, 0.0, 0
        while t < HORIZON:
            c, lo = _dll_day(*days[t][:2], limit, feats)
            if bal + min(lo, c) <= floor:
                closed += 1
                t += 1
                break
            bal += c
            cycle += c
            wins += c >= 150.0
            if not locked:
                floor = max(floor, min(bal - 2000.0, 0.0))
            t += 1
            if wins >= 5 and (n_paid == 0 or cycle > 0):
                amount = min(0.5 * bal, cap)
                if amount >= 125.0 and bal - amount > 0.0:
                    bal -= amount
                    payouts += 0.9 * amount
                    n_paid += 1
                    first = t if first is None else first
                    floor, locked, wins, cycle = 0.0, True, 0, 0.0
    fees += api * math.ceil(HORIZON / MONTH)
    return Cash(payouts - fees, payouts, fees, passed, closed, first)


# ------------------------------------------------------------------ Tradeify Growth 50K
def indep_tradeify_growth(days, feats: frozenset) -> Cash:
    official = "dll_rise" in feats
    price, reset = 145.0, 95.0
    caps = (1500.0, 2000.0, 2500.0, 3000.0)
    fees = payouts = 0.0
    passed = closed = 0
    first = None
    t = 0
    while t < HORIZON:
        fees += price
        bal, peak = 0.0, 0.0
        ok = False
        while t < HORIZON:
            c, lo = _dll_day(*days[t][:2], 1250.0, feats)
            if bal + min(lo, c) <= peak - 2000.0:  # never locks in the evaluation
                fees += reset
                bal = peak = 0.0
                t += 1
                continue
            bal += c
            peak = max(peak, bal)
            t += 1
            if bal >= 3000.0:  # min 1 trading day, no consistency
                ok = True
                break
        if not ok:
            break
        passed += 1
        bal, floor, locked = 0.0, -2000.0, False
        wins, cycle_days, n_paid = 0, [], 0
        while t < HORIZON:
            limit = 2000.0 if (official and bal >= 3000.0) else 1250.0
            c, lo = _dll_day(*days[t][:2], limit, feats)
            if bal + min(lo, c) <= floor:
                closed += 1
                t += 1
                break
            bal += c
            cycle_days.append(c)
            wins += c >= 150.0
            if not locked:
                floor = max(floor, min(bal - 2000.0, 100.0))  # locks at +100
            t += 1
            profit = sum(cycle_days)
            if wins >= 5 and bal >= 3000.0 and profit > 0 and max(cycle_days) <= 0.35 * profit:
                amount = min(caps[min(n_paid, 3)], bal - 100.0 - 1.0)  # request the cap
                if amount >= 500.0:
                    bal -= amount
                    payouts += 0.9 * amount
                    n_paid += 1
                    first = t if first is None else first
                    floor, locked, wins, cycle_days = 100.0, True, 0, []
    return Cash(payouts - fees, payouts, fees, passed, closed, first)


# ------------------------------------------------------------------ synthetic days
def make_paths(n: int, seed: int):
    rng = random.Random(seed)
    out = []
    for k in range(n):
        size = (1, 2, 4, 8)[k % 4]
        mu = rng.choice((-20.0, 0.0, 15.0, 40.0)) * size
        sd = rng.choice((150.0, 250.0)) * size
        path = []
        for _ in range(HORIZON):
            c = rng.gauss(mu, sd)
            lo = min(0.0, c) - rng.expovariate(1 / (0.4 * sd))
            hi = max(0.0, c) + rng.expovariate(1 / (0.4 * sd))
            path.append((round(c, 2), round(lo, 2), round(hi, 2)))
        out.append(path)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    from pathlib import Path

    from quant_brain.prop import firm_sim, firms  # project side (comparison only)

    root = Path(__file__).resolve().parents[1] / "brain" / "_system" / "prop" / "firms"
    ts = firms.load_firm(root / "topstep_50k_standard.json")["standard"]
    tg = firms.load_firm(root / "tradeify_growth_50k.json")["default"]
    cells = {
        "topstep_50k_standard/standard no DLL": (ts, lambda d, o: indep_topstep(d, False, o)),
        "topstep_50k_standard/standard DLL": (
            ts.with_optional_daily_loss(True),
            lambda d, o: indep_topstep(d, True, o),
        ),
        "tradeify_growth_50k": (tg, indep_tradeify_growth),
    }
    paths = make_paths(a.paths, a.seed)
    bad = 0
    for name, (firm, indep) in cells.items():
        modes = {"match": frozenset(), "official": frozenset(FEATURES)}
        modes |= {f"only {f}": frozenset({f}) for f in FEATURES}
        for mode, feats in modes.items():
            diffs, tot_p, tot_i = 0, [0.0] * 4, [0.0] * 4
            example = None
            for path in paths:
                closes, lows, highs = zip(*path, strict=True)
                p = firm_sim.lifecycle_arrays(firm, closes, lows, highs, horizon=HORIZON)
                i = indep(path, feats)
                pv = (p.net, p.fees, p.payouts, p.combines_passed)
                iv = (i.net, i.fees, i.payouts, i.passed)
                for k in range(4):
                    tot_p[k] += pv[k]
                    tot_i[k] += iv[k]
                same = all(abs(x - y) < 1e-6 for x, y in zip(pv, iv, strict=True)) and (
                    p.first_payout_day == i.first_payout and p.xfas_closed == i.closed
                )
                if not same:
                    diffs += 1
                    example = example or (pv, p.first_payout_day, iv, i.first_payout)
            n = len(paths)
            print(
                f"{name:40} {mode:14} paths {n}  differing {diffs:4}  "
                f"mean net project {tot_p[0] / n:9.2f} indep {tot_i[0] / n:9.2f}  "
                f"fees {tot_p[1] / n:7.2f}/{tot_i[1] / n:7.2f}  "
                f"payouts {tot_p[2] / n:8.2f}/{tot_i[2] / n:8.2f}  "
                f"passes {tot_p[3] / n:5.3f}/{tot_i[3] / n:5.3f}"
            )
            if example and mode == "match":
                print("   first differing path (project, indep):", example)
            if mode == "match":
                bad += diffs
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
