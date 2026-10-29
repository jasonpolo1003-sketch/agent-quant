"""Zero-edge 'bold play' on Topstep 50K (standard payout path): what does the rules' convexity alone pay?

Every trade is a bracket on a driftless price: P(win) = stop / (target + stop) (gross distances).
Costs: $10/trade + $10 slippage on stop-outs (2 NQ). Grind trades: $5 + $5 (1 NQ).
Eval: bold (stop = whole cushion) to the consistency-safe step (55% of 3000 = 1650), then the rest.
Funded: bold to +G (stop = whole cushion), then grind 50/50 $150 days to 5 winning days -> payout
min(50% of profit, $2000) x 90%. After payout the floor sits at the start balance.
Budget: stop buying evals once fees would exceed BUDGET.
"""

import numpy as np

rng = np.random.default_rng(20261028)
START, MAXLOSS, TARGET, CONS = 50_000.0, 2000.0, 3000.0, 0.55
PRICE, RESET, ACT, API = 49.0, 49.0, 149.0, 29.0


def bracket(win_net, stop_gross, c, slip):
    tg = win_net + c
    p = stop_gross / (tg + stop_gross)
    return (win_net, True) if rng.random() < p else (-stop_gross - c - slip, False)


def eval_attempt():
    """One bold attempt -> (passed, days)."""
    bal, peak, best, days = START, START, 0.0, 0
    while True:
        floor = min(START, peak - MAXLOSS)
        cushion = bal - floor
        profit = bal - START
        need = max(TARGET, best / CONS) - profit
        step = min(need, CONS * TARGET) if days == 0 else need
        pnl, _ = bracket(step, cushion, 10, 10)
        days += 1
        if pnl <= -cushion:
            return False, days
        bal += pnl
        best = max(best, pnl)
        peak = max(peak, bal)
        if bal - START >= max(TARGET, best / CONS) and days >= 2:
            return True, days


def funded(G, days_left):
    """-> (trader cash, days used)."""
    bal, peak, locked_floor, cash, wins, d = START, START, None, 0.0, 0, 0
    while d < days_left:
        floor = locked_floor if locked_floor is not None else min(START, peak - MAXLOSS)
        cushion = bal - floor
        if wins == 0:
            pnl, _ = bracket(G, cushion, 10, 10)
        else:
            pnl, _ = bracket(150, min(150, cushion), 5, 5)
        d += 1
        if pnl <= -cushion:
            return cash, d
        bal += pnl
        peak = max(peak, bal)
        wins += pnl >= 150
        if wins >= 5:
            amt = min(0.5 * (bal - START), 2000)
            if amt >= 125:
                bal -= amt
                cash += 0.9 * amt
                locked_floor, wins = START, 0
    return cash, d


def run(G, horizon, budget, n=20_000):
    nets, first = [], []
    for _ in range(n):
        spent, cash, d, fp = API, 0.0, 0, None
        bought = False
        while d < horizon:
            fee = PRICE if not bought else RESET
            if spent + fee > budget:
                break
            spent += fee
            bought = True
            ok, used = eval_attempt()
            d += used
            if not ok:
                continue
            if spent + ACT > budget:
                break
            spent += ACT
            bought = False
            c, used = funded(G, horizon - d)
            if c > 0 and fp is None:
                fp = d + used
            cash += c
            d += used
        months = int(np.ceil(max(d, 1) / 21))
        spent += API * (months - 1)
        nets.append(cash - spent)
        first.append(fp)
    nets = np.array(nets)
    got = np.array([f is not None for f in first])
    return nets, got


if __name__ == "__main__":
    passes = [eval_attempt()[0] for _ in range(50_000)]
    print(f"bold eval pass rate per attempt: {np.mean(passes):.3f}")
    for G in (1000, 2000, 3000, 4000, 6000):
        cash = np.array([funded(G, 63)[0] for _ in range(20_000)])
        print(
            f"funded G={G}: P(any payout)={np.mean(cash > 0):.3f}  mean cash ${cash.mean():.0f}  "
            f"median ${np.median(cash):.0f}"
        )
    for G in (2000, 4000):
        for budget in (500, 1000):
            nets, got = run(G, 63, budget)
            print(
                f"G={G} budget ${budget} 3mo: mean net ${nets.mean():.0f}, median ${np.median(nets):.0f}, "
                f"P(net>0)={np.mean(nets > 0):.3f}, P(any payout)={got.mean():.3f}, "
                f"P(net>=+500)={np.mean(nets >= 500):.3f}"
            )
