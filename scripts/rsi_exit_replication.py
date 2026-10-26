"""RX-0001: RSI mean-reversion exit replication (exploratory; see brain/04_Backtest_Reports/RX-0001-rsi-exit-replication/RX-0001-plan.md).

Uses repo indicators, stats and engine.simulate_positions (next-open fill). Same-close fill is a local
sensitivity simulator. Writes results JSON/CSV; never touches DB, ledgers or cards.
Usage: python scripts/rsi_exit_replication.py --data-root . --out <dir>
"""
from __future__ import annotations
import argparse, itertools, json, math, sys, glob
from pathlib import Path
import numpy as np, pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument('--data-root', default='.'); ap.add_argument('--src', default='src'); ap.add_argument('--out', required=True)
A = ap.parse_args(); sys.path.insert(0, A.src)
from quant_brain.backtest import indicators as ind, stats, engine  # noqa: E402

DS = {'SPY': 'SPY-1d-tiingo-20261022T025225Z-b1fe5d43', 'QQQ': 'QQQ-1d-tiingo-20261022T025225Z-897e8d48', 'IWM': 'IWM-1d-tiingo-20261022T025225Z-b2ce5a4e'}
SPLIT = pd.Timestamp('2015-01-01')
ENTRIES = {'E1_rsi2<10': (2, 10), 'E2_rsi2<20': (2, 20), 'E3_rsi14<30': (14, 30)}
EXITS = ['A_close>sma5', 'B_rsi2>55_unverified', 'C50_rsi14_xup50', 'C70_rsi14_xup70']
FILTERS = ['none', 'sma200']; FILLS = ['next_open', 'same_close']; COSTS = [0, 2, 5, 10]

def load(s):
    d = pd.read_parquet(Path(A.data_root) / f'data/parquet/{s}/{DS[s]}.parquet'); d['date'] = pd.to_datetime(d['date']); return d.reset_index(drop=True)

def signals(d, entry, exit_, filt):
    c = d['adj_close']; rp, thr = ENTRIES[entry]
    r2, r14 = ind.rsi_wilder(c, 2), ind.rsi_wilder(c, 14); rsi_e = r2 if rp == 2 else r14
    en = rsi_e.notna() & (rsi_e < thr)
    if filt == 'sma200':
        t = ind.sma(c, 200); en &= t.notna() & (c > t)
    if exit_.startswith('A'):
        s5 = ind.sma(c, 5); ex = s5.notna() & (c > s5)
    elif exit_.startswith('B'):
        ex = r2.notna() & (r2 > 55)
    else:
        lv = 50 if 'xup50' in exit_ else 70; ex = r14.notna() & (r14 > lv) & (r14.shift(1) <= lv)
    return en.to_numpy(bool), ex.to_numpy(bool)

def same_close(closes, en, ex, cost, p0, p1):
    cash, sh, inpos, ent, base = 1.0, 0.0, False, -1, 1.0; eq = []; trades = []
    for t in range(p0, p1 + 1):
        if inpos and t > ent and (ex[t] or t == p1):
            pro = sh * closes[t] * (1 - cost); trades.append((ent, t, pro / base - 1, t == p1 and not ex[t])); cash, sh, inpos = pro, 0.0, False
        elif not inpos and en[t] and t < p1:
            base = cash; sh = cash * (1 - cost) / closes[t]; cash = 0.0; inpos, ent = True, t
        eq.append(cash + sh * closes[t])
    e = pd.Series(eq, index=range(p0, p1 + 1)); r = e / pd.concat([pd.Series([1.0]), e.iloc[:-1]]).to_numpy() - 1
    return trades, e, r

def run_one(d, en, ex, fill, cost, p0, p1):
    c = cost / 1e4
    if fill == 'next_open':
        res = engine.simulate_positions(d['adj_open'].to_numpy(), d['adj_close'].to_numpy(), en, ex, np.zeros(len(d), bool), unit_fraction=1.0, max_units=1, cost=c, p0=p0, p1=p1)
        tr = [(t.entry_index, t.exit_index, t.trade_return, t.forced) for t in res.trades]; r = res.daily_returns
    else:
        tr, _, r = same_close(d['adj_close'].to_numpy(), en, ex, c, p0, p1)
    invested = np.zeros(p1 - p0 + 1, bool)
    for a, b, _, _ in tr: invested[a - p0:b - p0 + (1 if fill == 'next_open' else 0)] = True
    return tr, pd.Series(r.to_numpy(), index=d['date'].iloc[p0:p1 + 1].to_numpy()), float(invested.mean())

def metrics(r, tr, expo):
    eq = (1 + r).cumprod(); rets = [x[2] for x in tr]
    return {'trades': len(tr), 'win_rate': float(np.mean([x > 0 for x in rets])) if rets else None, 'avg_trade_pct': float(np.mean(rets) * 100) if rets else None,
            'avg_hold_days': float(np.mean([b - a for a, b, _, _ in tr])) if tr else None, 'cagr': stats.cagr(eq), 'max_dd': stats.max_drawdown(eq), 'sharpe': stats.annualised_sharpe(r), 'exposure': expo}

data = {s: load(s) for s in DS}
periods = {}
for s, d in data.items():
    i = int((d['date'] < SPLIT).sum()); periods[s] = {'IS': (0, i - 1), 'OOS': (i, len(d) - 1), 'FULL': (0, len(d) - 1)}
rows, streams = [], {}
for entry, ex_, filt in itertools.product(ENTRIES, EXITS, FILTERS):
    sig = {s: signals(d, entry, ex_, filt) for s, d in data.items()}
    for fill, cost in itertools.product(FILLS, COSTS):
        cfg = f'{entry}|{ex_}|{filt}|{fill}|{cost}bps'
        for per in ['IS', 'OOS', 'FULL']:
            rs = {}
            for s, d in data.items():
                p0, p1 = periods[s][per]; tr, r, expo = run_one(d, *sig[s], fill, cost, p0, p1); rs[s] = (r, tr, expo)
                rows.append({'config': cfg, 'entry': entry, 'exit': ex_, 'filter': filt, 'fill': fill, 'cost_bps': cost, 'period': per, 'symbol': s, **metrics(r, tr, expo)})
            df = pd.concat({s: v[0] for s, v in rs.items()}, axis=1).dropna(); pr = df.mean(axis=1)
            alltr = sum((v[1] for v in rs.values()), []); streams[(cfg, per)] = pr
            rows.append({'config': cfg, 'entry': entry, 'exit': ex_, 'filter': filt, 'fill': fill, 'cost_bps': cost, 'period': per, 'symbol': 'POOLED', **metrics(pr, alltr, float(np.mean([v[2] for v in rs.values()])))})
R = pd.DataFrame(rows)
# buy and hold
bh = []
for per in ['IS', 'OOS', 'FULL']:
    rr = {}
    for s, d in data.items():
        p0, p1 = periods[s][per]; c = d['adj_close'].iloc[p0:p1 + 1].to_numpy(); r = pd.Series(np.r_[0, c[1:] / c[:-1] - 1], index=d['date'].iloc[p0:p1 + 1].to_numpy()); rr[s] = r
        bh.append({'symbol': s, 'period': per, **metrics(r, [], 1.0)})
    pr = pd.concat(rr, axis=1).dropna().mean(axis=1); bh.append({'symbol': 'POOLED', 'period': per, **metrics(pr, [], 1.0)})
BH = pd.DataFrame(bh)
# DSR over pooled trials
SC2 = 86; dsr = []
for per in ['IS', 'OOS']:
    cf = [c for (c, p) in streams if p == per]; srs = [stats.sharpe_per_period(streams[(c, per)]) for c in cf]
    for c in cf:
        a = stats.deflated_sharpe(streams[(c, per)].to_numpy(), srs)
        b = stats.deflated_sharpe(streams[(c, per)].to_numpy(), srs + [float(np.median(srs))] * 0)  # placeholder same as a
        dsr.append({'config': c, 'period': per, 'dsr_N192': a.get('dsr', a.get('probability')), 'raw': a})
# stricter N incl. SC-0002 trials: SR* with N=278 using same variance
from statistics import NormalDist
def dsr_N(r, srs, N):
    x = np.asarray(r, float); sr = stats.sharpe_per_period(x); V = float(np.var(srs, ddof=1)); nd = NormalDist(); g = stats.EULER_GAMMA
    srs_ = math.sqrt(V) * ((1 - g) * nd.inv_cdf(1 - 1 / N) + g * nd.inv_cdf(1 - 1 / (N * math.e)))
    sk, ku = stats._biased_moments(x); T = len(x)
    return nd.cdf((sr - srs_) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)), srs_
for row in dsr:
    per = row['period']; cf = [c for (c, p) in streams if p == per]; srs = [stats.sharpe_per_period(streams[(c, per)]) for c in cf]
    row['dsr_N278'], row['sr_star_N278'] = dsr_N(streams[(row['config'], per)], srs, 192 + SC2)
D = pd.DataFrame([{k: v for k, v in r.items() if k != 'raw'} | {'raw_keys': json.dumps({k: (float(v) if isinstance(v, (int, float)) else str(v)) for k, v in r['raw'].items()})} for r in dsr])
# PBO via CSCV on FULL pooled, 48 rule variants per fill at 5 bps
def cscv(M, S=16):
    T, N = M.shape; blocks = np.array_split(np.arange(T), S); lam = []
    for comb in itertools.combinations(range(S), S // 2):
        isx = np.concatenate([blocks[i] for i in comb]); oos = np.concatenate([blocks[i] for i in range(S) if i not in comb])
        def sh(X): m, s_ = X.mean(0), X.std(0, ddof=1); return np.where(s_ > 0, m / s_, 0)
        si, so = sh(M[isx]), sh(M[oos]); best = int(np.argmax(si)); rank = (so < so[best]).sum() + 1  # 1..N
        w = rank / (N + 1); lam.append(math.log(w / (1 - w)))
    lam = np.array(lam); return {'pbo': float((lam <= 0).mean()), 'n_splits': len(lam), 'S': S, 'N': N, 'logit_median': float(np.median(lam))}
pbo = {}
for fill in FILLS:
    cf = [c for (c, p) in streams if p == 'FULL' and f'|{fill}|5bps' in c]
    M = pd.concat({c: streams[(c, 'FULL')] for c in cf}, axis=1).dropna().to_numpy(); pbo[fill] = cscv(M)
out = Path(A.out); out.mkdir(parents=True, exist_ok=True)
R.to_csv(out / 'RX-0001-results.csv', index=False); BH.to_csv(out / 'RX-0001-buyhold.csv', index=False); D.to_csv(out / 'RX-0001-dsr.csv', index=False)
json.dump({'pbo': pbo, 'n_configs': len({r for r in R.config}), 'sc0002_trials_counted_in_strict_dsr': SC2, 'datasets': DS, 'split': str(SPLIT.date())}, open(out / 'RX-0001-summary.json', 'w'), indent=2)
print('configs', R.config.nunique(), 'rows', len(R)); print('PBO', pbo)
