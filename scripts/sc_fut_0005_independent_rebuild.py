"""Independent rebuild of SC-FUT-0005 from the frozen spec text only.

Does not import quant_brain. Decodes the dev DBN with databento_dbn, derives its own
volume roll from minute volumes, and runs the noise-area rule. Writes per-day results.
Usage: python -I rebuild_0005.py <dbn path> <calendar csv> <roll csv> <out csv> [ROOT]
"""

import csv
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import databento_dbn as dbn
import zstandard

CT = ZoneInfo("America/Chicago")
dbn_path, cal_path, roll_path, out_path = sys.argv[1:5]
ROOT = sys.argv[5] if len(sys.argv) > 5 else "MNQ"
TICK_C = {"MNQ": 50, "MES": 125}[ROOT]
L3_C = {"MNQ": 322, "MES": 622}[ROOT]
START, END = date(2019, 5, 1), date(2024, 12, 31)

# ---- decode ----
raw = zstandard.ZstdDecompressor().stream_reader(open(dbn_path, "rb")).read()
dec = dbn.DBNDecoder()
dec.write(raw)
recs = dec.decode()
meta = recs[0]
# raw_symbol -> list of (start_date, end_date, iid); outrights only (no '-' spreads)
sym_of = {}
for sym, ivs in meta.mappings.items():
    if not sym.startswith(ROOT) or "-" in sym or len(sym) > len(ROOT) + 2:
        continue
    for iv in ivs:
        sym_of[int(iv["symbol"])] = sym
print("contracts", sorted(set(sym_of.values())))

bars = defaultdict(dict)  # (sym, trade_date) -> {minute_time: (o,h,l,c,v)}
for r in recs[1:]:
    if not hasattr(r, "volume"):
        continue
    sym = sym_of.get(r.instrument_id)
    if sym is None:
        continue
    t = datetime.fromtimestamp(r.ts_event / 1e9, tz=CT)
    td = (t + timedelta(hours=7)).date()
    if t.date() != td:  # evening session belongs to next trade date; not needed beyond volume
        bars[(sym, td)].setdefault("_v", 0)
        bars[(sym, td)]["_v"] += r.volume
        continue
    px = [r.open / 1e9, r.high / 1e9, r.low / 1e9, r.close / 1e9]
    bars[(sym, td)][t.time().replace(tzinfo=None)] = (*px, r.volume)
    bars[(sym, td)].setdefault("_v", 0)
    bars[(sym, td)]["_v"] += r.volume

# ---- calendar ----
cal = []
with open(cal_path) as f:
    for row in csv.DictReader(f):
        d = date.fromisoformat(row["trade_date"])
        if START <= d <= END:
            cal.append((d, row["early_close"] == "True"))

# ---- volume roll, derived independently: switch on the first session after the
# next contract out-traded the current one over the whole trade date ----
syms = sorted(set(sym_of.values()), key=lambda s: (2019 if s[-1] == "9" else 2020 + int(s[-1]), "HMUZ".index(s[-2])))
def vol(s, d):
    return bars.get((s, d), {}).get("_v", 0)
cur = 0
front = {}
for i, (d, _) in enumerate(cal):
    front[d] = syms[cur]
    nxt = syms[cur + 1] if cur + 1 < len(syms) else None
    if nxt and vol(nxt, d) > vol(syms[cur], d):
        cur += 1  # effective next session
mine = {}
prev = None
for d, _ in cal:
    if front[d] != prev:
        mine[front[d]] = d
        prev = front[d]
theirs = {}
with open(roll_path) as f:
    for row in csv.DictReader(f):
        if row["root"] == ROOT and row.get("volume_roll_date"):
            theirs[row["to_contract"]] = row["volume_roll_date"]
for s, d in mine.items():
    if s in theirs and theirs[s] != d.isoformat():
        print("ROLL DIFF", s, "mine", d, "file", theirs[s])

# ---- strategy ----
CHECKS_FULL = [time(h, m) for h in range(9, 15) for m in (0, 30)]
def minus1(t):
    return (datetime.combine(date.min, t) - timedelta(minutes=1)).time()

def day_bars(sym, d):
    return bars.get((sym, d), {})

def reg_close(sym, d, early):
    b = day_bars(sym, d)
    cutoff = time(12, 15) if early else time(15, 0)
    ks = [k for k in b if k != "_v" and time(8, 30) <= k < cutoff]
    return b[max(ks)][3] if ks else None

def move(sym, d, m):
    b = day_bars(sym, d)
    o = b.get(time(8, 30))
    c = b.get(minus1(m))
    if o is None or c is None:
        return None
    return abs(c[3] / o[0] - 1)

import os
FILL = os.environ.get("FILL", "open")

def px(b, m, side):
    """Fill price for an order at check m; side +1 buy, -1 sell. Stress modes are adversarial."""
    if FILL == "open":
        return b[m][0]
    if FILL == "sigclose":  # close of the signal bar (one minute earlier)
        prev = (datetime.combine(date.min, m) - timedelta(minutes=1)).time()
        return b[prev][3]
    if FILL == "plus2":  # two extra ticks against us per side
        return b[m][0] + 0.5 * side
    if FILL == "worst":  # buy at the minute's high, sell at its low
        return b[m][1] if side > 0 else b[m][2]
    if FILL == "delay1":  # one minute late
        nxt = (datetime.combine(date.min, m) + timedelta(minutes=1)).time()
        return b[nxt][0] if nxt in b else b[m][3]
    raise ValueError(FILL)

out = []
for i, (d, early) in enumerate(cal):
    sym = front[d]
    b = day_bars(sym, d)
    flat_t = time(12, 0) if early else time(15, 0)
    checks = [m for m in CHECKS_FULL if m <= (time(11, 30) if early else time(14, 30))]
    row = {"date": d.isoformat(), "status": "", "gross": 0, "trades": 0, "detail": ""}
    if i == 0:
        row["status"] = "no_prev"; out.append(row); continue
    pd_, pe = cal[i - 1]
    prevc = reg_close(sym, pd_, pe)
    o = b.get(time(8, 30))
    if flat_t not in b:
        row["status"] = "non_evaluable"; out.append(row); continue
    if o is None or prevc is None:
        row["status"] = "missing_open_or_prev"; out.append(row); continue
    o = o[0]
    window = cal[max(0, i - 14): i]
    pos, entry, gross, trades, legs = 0, None, 0.0, 0, []
    cum_pv = cum_v = 0.0
    vw_t = time(8, 30)
    for m in checks:
        last = minus1(m)
        while vw_t <= last:
            x = b.get(vw_t)
            if x:
                cum_pv += (x[1] + x[2] + x[3]) / 3 * x[4]
                cum_v += x[4]
            vw_t = (datetime.combine(date.min, vw_t) + timedelta(minutes=1)).time()
        mv = [move(front[wd], wd, m) for wd, _ in window]
        mv = [x for x in mv if x is not None]
        if len(mv) < 10 or last not in b or m not in b:
            continue
        sigma = sum(mv) / len(mv)
        up = max(o, prevc) * (1 + sigma)
        lo = min(o, prevc) * (1 - sigma)
        p = b[last][3]
        vwap = cum_pv / cum_v if cum_v else p
        exited = False
        if pos == 1 and p < max(up, vwap):
            fill = px(b, m, -1)
            gross += fill - entry; trades += 1; legs.append(f"L{entry}->{fill}@{m}"); pos = 0; exited = True
        elif pos == -1 and p > min(lo, vwap):
            fill = px(b, m, 1)
            gross += entry - fill; trades += 1; legs.append(f"S{entry}->{fill}@{m}"); pos = 0; exited = True
        if pos == 0:
            if exited:
                # only the opposite band may be taken at the same check
                if legs[-1][0] == "L" and p < lo:
                    pos, entry = -1, fill
                elif legs[-1][0] == "S" and p > up:
                    pos, entry = 1, fill
            elif p > up:
                pos, entry = 1, px(b, m, 1)
            elif p < lo:
                pos, entry = -1, px(b, m, -1)
    if pos:
        fill = px(b, flat_t, -pos)
        gross += (fill - entry) * pos; trades += 1; legs.append(f"{'L' if pos>0 else 'S'}{entry}->{fill}@EOD")
    row.update(status="traded" if trades else "no_trade", gross=round(gross / 0.25 * TICK_C), trades=trades, detail=" ".join(legs), contract=sym)
    out.append(row)

with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "status", "gross", "trades", "contract", "detail"])
    w.writeheader()
    for r in out:
        w.writerow({k: r.get(k, "") for k in w.fieldnames})
ev = [r for r in out if r["status"] in ("traded", "no_trade")]
net = sum(r["gross"] - L3_C * r["trades"] for r in ev)
print(ROOT, "evaluable days", len(ev), "trades", sum(r["trades"] for r in ev), "net $/day", net / len(ev) / 100)
