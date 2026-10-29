"""Bold play on Topstep 50K (standard path) with brackets replayed on real NQ minute bars.

    .venv/Scripts/python.exe scripts/bold_play_real.py

Same policy as scripts/bold_play_model.py, but each trade is a random-direction bracket on a
random practice day (MNQ dev bars 2019-05..2024-12; NQ prices, $5/tick per NQ). Entry at the
open of a random bar in the first hour; stop first in a shared bar; a bar opening through the
stop fills at its open, +1 tick slippage; the target needs a 1-tick trade-through; unresolved
trades exit at the session close. Costs: $4.50 per NQ round trip. Bold trades: 2 NQ (the
scaling plan's starting size); grind trades: 1 NQ.
`deny` = chance a payout request is refused for rule reasons and the account closed.
No exam data is touched (dev file ends 2024-12-31).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workbench as wb

TICK_USD = 5.0  # NQ
RT = 4.5
START, MAXLOSS, TARGET, CONS = 50_000.0, 2000.0, 3000.0, 0.55
PRICE, RESET, ACT, API = 49.0, 49.0, 149.0, 29.0
rng = np.random.default_rng(20261028)


def load():
    days = wb.dev_loader(wb.DEV_DIR)("MNQ", date(2019, 5, 1), date(2024, 12, 31), "volume_roll_date")
    out = []
    for d in days:
        ts = sorted(t for t in d.bars if t < d.exit_minute)
        if len(ts) < 120:
            continue
        a = np.array([d.bars[t] for t in ts], dtype=float)  # open, high, low, close in ticks
        out.append(a)
    return out


DAYS: list[np.ndarray] = []
STATS = {"n": 0, "unresolved": 0}


def bracket(win_net, stop_gross, n_nq, slip_ticks=1):
    """-> (net $, low $ until exit)."""
    cost = RT * n_nq
    per = TICK_USD * n_nq
    t = max(1, int(np.ceil((win_net + cost) / per)))
    s = max(1, int(np.floor(stop_gross / per)))
    a = DAYS[rng.integers(len(DAYS))]
    k = int(rng.integers(60))
    side = 1 if rng.random() < 0.5 else -1
    o, h, lo, c = a[k:, 0], a[k:, 1], a[k:, 2], a[k:, 3]
    e = o[0]
    if side == 1:
        adverse, favor, gap = e - lo, h - e, e - o
    else:
        adverse, favor, gap = h - e, e - lo, o - e
    hit_s = adverse >= s
    hit_t = favor >= t + 1
    i_s = int(np.argmax(hit_s)) if hit_s.any() else None
    i_t = int(np.argmax(hit_t)) if hit_t.any() else None
    STATS["n"] += 1
    if i_s is not None and (i_t is None or i_s <= i_t):
        loss = max(s, gap[i_s]) + slip_ticks
        return -loss * per - cost, -loss * per - cost
    if i_t is not None:
        low = -adverse[: i_t + 1].max() * per if i_t >= 0 else 0.0
        return t * per - cost, min(0.0, low)
    STATS["unresolved"] += 1
    pnl = side * (c[-1] - e) * per - cost
    return pnl, min(pnl, -adverse.max() * per)


def eval_attempt(R=None):
    """R: max $ risked per day (None = whole cushion, bold)."""
    bal, peak, best, days = START, START, 0.0, 0
    while True:
        floor = min(START, peak - MAXLOSS)
        cushion = bal - floor
        need = max(TARGET, best / CONS) - (bal - START)
        step = min(need, CONS * TARGET) if days == 0 else max(need, 150)
        risk = cushion
        if R is not None:
            step, risk = max(min(step, R), 150), min(cushion, R)
        pnl, low = bracket(step, risk, 2)
        days += 1
        if low <= -cushion:
            return False, days
        bal += pnl
        best = max(best, pnl)
        peak = max(peak, bal)
        if bal - START >= max(TARGET, best / CONS) and days >= 2:
            return True, days
        if days > 30:
            return False, days


def funded(G, days_left, deny, R=None):
    bal, peak, locked, cash, wins, d = START, START, False, 0.0, 0, 0
    while d < days_left:
        floor = START if locked else min(START, peak - MAXLOSS)
        cushion = bal - floor
        if R is not None and bal - START < G and not locked:
            pnl, low = bracket(max(min(G - (bal - START), R), 150), min(cushion, R), 2)
        elif R is None and wins == 0:
            pnl, low = bracket(G, cushion, 2)
        else:
            pnl, low = bracket(150, min(150, cushion), 1)
        d += 1
        if low <= -cushion:
            return cash, d
        bal += pnl
        peak = max(peak, bal)
        wins += pnl >= 150
        if wins >= 5:
            amt = min(0.5 * (bal - START), 2000)
            if amt >= 125:
                if rng.random() < deny:
                    return cash, d
                bal -= amt
                cash += 0.9 * amt
                locked, wins = True, 0
    return cash, d


def run(G, horizon, budget, deny, n=10_000, R=None, per_month=None):
    """per_month: at most this many eval purchases/resets per 21 trading days."""
    nets = []
    for _ in range(n):
        spent, cash, d, bought = API, 0.0, 0, False
        buys: list[int] = []
        while d < horizon:
            if per_month is not None and sum(b > d - 21 for b in buys) >= per_month:
                d = min(b for b in buys if b > d - 21) + 21  # wait for the window to clear
                continue
            fee = RESET if bought else PRICE
            if spent + fee > budget:
                break
            spent += fee
            bought = True
            buys.append(d)
            ok, used = eval_attempt(R)
            d += used
            if not ok:
                continue
            if spent + ACT > budget:
                break
            spent += ACT
            bought = False
            c, used = funded(G, horizon - d, deny, R)
            cash += c
            d += used
        spent += API * (int(np.ceil(max(d, 1) / 21)) - 1)
        nets.append(cash - spent)
    return np.array(nets)


def main() -> int:
    DAYS.extend(load())
    print(f"{len(DAYS)} practice days loaded")
    if "--moderate" not in sys.argv:
        wins = [bracket(1650, 2000, 2)[0] > 0 for _ in range(20_000)]
        print(f"eval step 1: real win rate {np.mean(wins):.3f}, coin-flip {2000 / 3659:.3f}")
    for R in (None, 1000, 700, 500):
        p = np.mean([eval_attempt(R)[0] for _ in range(10_000)])
        print(f"R={R}: eval pass per attempt {p:.3f}")
        for G in (2000, 4000):
            for budget in (500, 1000):
                for deny in (0.0, 0.25):
                    x = run(G, 63, budget, deny, n=5000, R=R, per_month=3)
                    print(f"  G={G} budget ${budget} deny {deny:.2f} (<=3 buys/mo): mean ${x.mean():.0f}, "
                          f"median ${np.median(x):.0f}, P(ahead) {np.mean(x > 0):.2f}, P(+$500) {np.mean(x >= 500):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
