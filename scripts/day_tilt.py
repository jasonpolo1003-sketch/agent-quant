"""SC-FUT-0005-TILT-v1: can pre-open facts tell good days from bad ones?

    .venv/Scripts/python.exe scripts/day_tilt.py

Reads the pinned spec brain/_system/futures/day-tilt.v1.json (refuses on a hash
mismatch). Buckets each practice day by four pre-open predictors, picks one
predictor on the train years, and judges a tilt and a skip rule on the test years
with a permutation test. Results: workbench/day_tilt/.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, date, datetime

import numpy as np

from quant_brain.config import PROJECT_ROOT
from quant_brain.prop.policy import Days
from quant_brain.workbench import engine

SPEC = PROJECT_ROOT / "brain" / "_system" / "futures" / "day-tilt.v1.json"
FOMC = PROJECT_ROOT / "brain" / "_system" / "futures" / "fomc_statement_days_2019_2024.csv"
RUN = "266777ef"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def buckets(table, net: np.ndarray) -> dict[str, np.ndarray]:
    dates = [date.fromisoformat(d) for d in table.dates]
    with FOMC.open(encoding="utf-8") as h:
        fed_days = {date.fromisoformat(r["statement_date"]) for r in csv.DictReader(h)}
    fed = np.array(["yes" if d in fed_days else "no" for d in dates])
    atr = table.atr.astype(float)
    vol = np.full(len(dates), "", dtype=object)
    for i in range(len(dates)):
        past = atr[max(0, i - 250) : i]
        if len(past) < 60:
            continue
        rank = np.mean(past < atr[i])
        vol[i] = "low" if rank < 1 / 3 else ("high" if rank > 2 / 3 else "mid")
    streak = np.full(len(dates), "", dtype=object)
    for i in range(5, len(dates)):
        streak[i] = "up" if net[i - 5 : i].sum() > 0 else "down"
    weekday = np.array([WEEKDAYS[d.weekday()] for d in dates])
    return {"fed": fed, "vol": vol.astype(str), "streak5": streak.astype(str), "weekday": weekday}


def tstat(a: np.ndarray, b: np.ndarray) -> float:
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def weights(
    labels: np.ndarray, best: str, worst: str, rule: str, norm_idx: np.ndarray
) -> np.ndarray:
    w = np.ones(len(labels))
    if rule == "tilt":
        w[labels == best], w[labels == worst] = 1.5, 0.5
    else:
        w[labels == worst] = 0.0
    return w / w[norm_idx].mean()


def sharpe(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252))


def main() -> int:
    raw = SPEC.read_bytes()
    pinned = SPEC.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(raw).hexdigest() != pinned:
        raise SystemExit("day-tilt spec does not match its pinned hash; refusing")
    spec = json.loads(raw)

    trial = next(e for e in engine.read_ledger(PROJECT_ROOT) if e["fingerprint"].startswith(RUN))
    table = engine.DayTable.load(PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz")
    days = Days(table, trial["market"], "L3")
    good = days.s_good & days.c_good
    net = np.where(days.s_good, days.s_net, 0.0)
    luck = np.where(days.c_good, days.c_net, 0.0).mean(axis=1)
    years = np.array([int(d[:4]) for d in table.dates])
    by = buckets(table, net)

    train_mask = np.isin(years, spec["split"]["train_years"]) & good
    test_mask = np.isin(years, spec["split"]["test_years"]) & good
    out: dict = {"spec_sha256": pinned, "workbench_trial": trial["fingerprint"], "train": {}}

    picks = {}
    for name, lab in by.items():
        m = train_mask & (lab != "")
        stats = {}
        for b in sorted(set(lab[m])):
            sel = m & (lab == b)
            stats[b] = {
                "days": int(sel.sum()),
                "net_per_day": float(net[sel].mean()),
                "luck_per_day": float(luck[sel].mean()),
                "test_days": int((test_mask & (lab == b)).sum()),
                "test_net_per_day": float(net[test_mask & (lab == b)].mean()),
            }
        best = max(stats, key=lambda b: stats[b]["net_per_day"])
        worst = min(stats, key=lambda b: stats[b]["net_per_day"])
        t = tstat(net[m & (lab == best)], net[m & (lab == worst)])
        out["train"][name] = {"buckets": stats, "best": best, "worst": worst, "t": float(t)}
        picks[name] = (best, worst, t)
        print(
            f"{name:8} t={t:5.2f}  "
            + "  ".join(
                f"{b}: ${s['net_per_day']:6.2f} ({s['days']}d) [test ${s['test_net_per_day']:6.2f}]"
                for b, s in stats.items()
            ),
            flush=True,
        )

    chosen = max(picks, key=lambda k: picks[k][2])
    best, worst, _ = picks[chosen]
    print(f"chosen on train: {chosen} (best {best}, worst {worst})")
    lab = by[chosen]
    test_idx = np.flatnonzero(test_mask & (lab != ""))
    train_idx = np.flatnonzero(train_mask & (lab != ""))
    rng = np.random.default_rng(20261028)  # seed fixed in the spec
    out["chosen"] = {"predictor": chosen, "best": best, "worst": worst}
    out["test"] = {}
    for rule in ("tilt", "skip"):
        w = weights(lab, best, worst, rule, train_idx)
        x, wx = net[test_idx], (w * net)[test_idx]
        obs = wx.mean() - x.mean()
        perm = np.empty(5_000)
        for k in range(len(perm)):
            wp = rng.permutation(w[test_idx])
            perm[k] = (wp * x).mean() - x.mean()
        p = float(np.mean(perm >= obs))
        lk = luck[test_idx]
        res = {
            "untilted_net_per_day": float(x.mean()),
            "tilted_net_per_day": float(wx.mean()),
            "improvement_per_day": float(obs),
            "permutation_p": p,
            "sharpe_untilted": sharpe(x),
            "sharpe_tilted": sharpe(wx),
            "luck_improvement_per_day": float((w[test_idx] * lk).mean() - lk.mean()),
            "mean_weight_test": float(w[test_idx].mean()),
            "gate": "pass" if p < 0.05 else "fail",
        }
        out["test"][rule] = res
        print(
            f"{rule}: test ${x.mean():.2f}/day -> ${wx.mean():.2f}/day (+{obs:.2f}), p={p:.3f}, "
            f"Sharpe {res['sharpe_untilted']:.2f} -> {res['sharpe_tilted']:.2f}, "
            f"luck change {res['luck_improvement_per_day']:+.2f}, {res['gate'].upper()}",
            flush=True,
        )

    out_dir = PROJECT_ROOT / engine.WORKBENCH / "day_tilt"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{trial['fingerprint'][:12]}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8")
    print("written", path.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
