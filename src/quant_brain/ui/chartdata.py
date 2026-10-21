"""Data behind the Chart workspace: bars, indicators, formulas, selection stats, replays.

Read-only. Prices come only from accepted Gate F datasets (via
``quant_brain.market.universe``). SMA and RSI reuse the backtest engine's own
functions, so an indicator on the chart equals the one a backtest uses. The
other indicators (EMA, Bollinger, MACD, ATR) are display-only.
"""

from __future__ import annotations

import json
import math
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_brain.backtest import indicators as engine_ind
from quant_brain.data.market_data import MANIFEST_DIR
from quant_brain.market import universe as uni

REPORTS_DIR = "brain/04_Backtest_Reports"
TIMEFRAMES = {"D", "W", "M"}
BASES = {"split": "As traded (split-adjusted)", "total": "Total return (dividends added back)"}
MAX_FORMULA_LEN = 120


class ChartError(ValueError):
    """A request the chart cannot serve; the message is shown to the user."""


def _num(value: Any) -> float | None:
    if value is None:
        return None
    f = float(value)
    return None if math.isnan(f) or math.isinf(f) else round(f, 6)


# --- indicators -------------------------------------------------------------------------

def ema(values: pd.Series, n: int) -> pd.Series:
    return values.ewm(span=n, adjust=False, min_periods=n).mean()


def bollinger(values: pd.Series, n: int, k: float) -> dict[str, pd.Series]:
    mid = engine_ind.sma(values, n)
    sd = values.rolling(n, min_periods=n).std(ddof=0)
    return {"upper": mid + k * sd, "middle": mid, "lower": mid - k * sd}


def macd(values: pd.Series, fast: int, slow: int, signal: int) -> dict[str, pd.Series]:
    line = ema(values, fast) - ema(values, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return {"macd": line, "signal": sig, "histogram": line - sig}


def atr(frame: pd.DataFrame, n: int) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat([frame["high"] - frame["low"], (frame["high"] - prev).abs(),
                    (frame["low"] - prev).abs()], axis=1).max(axis=1)
    out = np.full(len(tr), np.nan)
    if len(tr) > n:
        out[n] = tr.iloc[1:n + 1].mean()
        for i in range(n + 1, len(tr)):
            out[i] = (out[i - 1] * (n - 1) + tr.iloc[i]) / n
    return pd.Series(out, index=frame.index)


INDICATORS: dict[str, dict[str, Any]] = {
    "sma": {"label": "SMA", "pane": "price", "params": {"n": 50}, "engine": True,
            "about": "Simple moving average: the average close of the last n bars."},
    "ema": {"label": "EMA", "pane": "price", "params": {"n": 21}, "engine": False,
            "about": "Exponential moving average: like SMA but recent bars count more."},
    "bb": {"label": "Bollinger Bands", "pane": "price", "params": {"n": 20, "k": 2.0},
           "engine": False,
           "about": "SMA with bands k standard deviations above and below. Wide bands mean volatile prices."},
    "rsi": {"label": "RSI", "pane": "own", "params": {"n": 14}, "engine": True,
            "levels": [30, 70],
            "about": "Relative Strength Index (Wilder), 0 to 100. Low means recent falls outweighed rises."},
    "macd": {"label": "MACD", "pane": "own", "params": {"fast": 12, "slow": 26, "signal": 9},
             "engine": False,
             "about": "Difference of two EMAs, and its own average. Crossings are a momentum signal."},
    "atr": {"label": "ATR", "pane": "own", "params": {"n": 14}, "engine": False,
            "about": "Average True Range: the typical daily move in price units. Used to size stops."},
}
PARAM_LIMITS = {"n": (1, 500), "fast": (1, 200), "slow": (2, 400), "signal": (1, 200), "k": (0.1, 5.0)}


def _params(kind: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    params = dict(INDICATORS[kind]["params"])
    for key, value in (raw or {}).items():
        if key not in params:
            raise ChartError(f"{INDICATORS[kind]['label']} has no setting '{key}'")
        lo, hi = PARAM_LIMITS[key]
        try:
            num = float(value)
        except (TypeError, ValueError) as exc:
            raise ChartError(f"{key} must be a number") from exc
        if not lo <= num <= hi:
            raise ChartError(f"{key} must be between {lo} and {hi}")
        params[key] = num if key == "k" else int(num)
    if kind == "macd" and params["fast"] >= params["slow"]:
        raise ChartError("MACD fast must be shorter than slow")
    return params


def compute_indicator(frame: pd.DataFrame, kind: str, raw_params: dict | None) -> dict[str, Any]:
    if kind not in INDICATORS:
        raise ChartError(f"unknown indicator '{kind}'")
    p = _params(kind, raw_params)
    close = frame["close"].astype(float)
    if kind == "sma":
        lines = {"sma": engine_ind.sma(close, p["n"])}
    elif kind == "ema":
        lines = {"ema": ema(close, p["n"])}
    elif kind == "bb":
        lines = bollinger(close, p["n"], p["k"])
    elif kind == "rsi":
        lines = {"rsi": engine_ind.rsi_wilder(close, p["n"])}
    elif kind == "macd":
        lines = macd(close, p["fast"], p["slow"], p["signal"])
    else:
        lines = {"atr": atr(frame, p["n"])}
    times = frame["time"].tolist()
    meta = INDICATORS[kind]
    name = f"{meta['label']}({', '.join(str(v) for v in p.values())})"
    return {
        "kind": kind, "name": name, "pane": meta["pane"], "params": p,
        "engine_parity": meta["engine"], "levels": meta.get("levels", []),
        "lines": {k: [{"time": t, "value": _num(v)} for t, v in zip(times, s, strict=True)
                      if _num(v) is not None] for k, s in lines.items()},
    }


# --- safe formula grammar ------------------------------------------------------------------

_NUM = re.compile(r"\d+(?:\.\d+)?")
_SYM = re.compile(r"[A-Z][A-Z0-9.]*")


def parse_formula(text: str, known: set[str] | None = None) -> tuple[Any, set[str]]:
    """Parse e.g. ``SPY/TLT`` or ``(XLK-XLU)*100`` into a small AST. Never evaluates code.

    ``known`` symbols are matched longest-first, so ``BRK-B/SPY`` reads BRK-B as one
    symbol while ``SPY-V`` reads as SPY minus V.
    """
    text = text.strip().upper()
    if not text or len(text) > MAX_FORMULA_LEN:
        raise ChartError("write a formula like SPY/TLT")
    ordered = sorted(known or (), key=len, reverse=True)

    def bounded(sym: str, at: int) -> bool:
        end = at + len(sym)
        return text.startswith(sym, at) and (end == len(text) or not (
            text[end].isalnum() or text[end] == "."))

    tokens: list[tuple[str, Any]] = []
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        hit = next((s for s in ordered if bounded(s, pos)), None)
        if hit:
            tokens.append(("sym", hit))
            pos += len(hit)
        elif m := _NUM.match(text, pos):
            tokens.append(("num", float(m.group())))
            pos = m.end()
        elif text[pos] in "+-*/()":
            tokens.append(("op", text[pos]))
            pos += 1
        elif m := _SYM.match(text, pos):
            tokens.append(("sym", m.group()))
            pos = m.end()
        else:
            raise ChartError(f"can't read the formula near '{text[pos:pos + 8]}'")
    symbols: set[str] = set()
    i = 0

    def peek():
        return tokens[i] if i < len(tokens) else (None, None)

    def eat():
        nonlocal i
        i += 1
        return tokens[i - 1]

    def factor():
        kind, val = peek()
        if kind == "num":
            eat()
            return ("num", val)
        if kind == "sym":
            eat()
            symbols.add(val)
            return ("sym", val)
        if (kind, val) == ("op", "("):
            eat()
            node = expr()
            if peek() != ("op", ")"):
                raise ChartError("a bracket is not closed")
            eat()
            return node
        if (kind, val) == ("op", "-"):
            eat()
            return ("neg", factor())
        raise ChartError("the formula is incomplete")

    def term():
        node = factor()
        while peek() in (("op", "*"), ("op", "/")):
            node = (eat()[1], node, factor())
        return node

    def expr():
        node = term()
        while peek() in (("op", "+"), ("op", "-")):
            node = (eat()[1], node, term())
        return node

    tree = expr()
    if i != len(tokens):
        raise ChartError("unexpected text at the end of the formula")
    if not symbols:
        raise ChartError("the formula needs at least one symbol")
    if len(symbols) > 6:
        raise ChartError("use at most 6 symbols in one formula")
    return tree, symbols


def eval_formula(tree: Any, series: dict[str, pd.Series]) -> pd.Series | float:
    kind = tree[0]
    if kind == "num":
        return tree[1]
    if kind == "sym":
        return series[tree[1]]
    if kind == "neg":
        return -eval_formula(tree[1], series)
    a, b = eval_formula(tree[1], series), eval_formula(tree[2], series)
    if kind == "+":
        return a + b
    if kind == "-":
        return a - b
    if kind == "*":
        return a * b
    with np.errstate(divide="ignore", invalid="ignore"):
        out = a / b
    return out.replace([np.inf, -np.inf], np.nan) if isinstance(out, pd.Series) else out


# --- the service ---------------------------------------------------------------------------

class ChartData:
    def __init__(self, project_root: Path, db_path: Path, max_frames: int = 64) -> None:
        self.root = Path(project_root)
        self.db = Path(db_path)
        self._lock = threading.Lock()
        self._catalog: dict[str, dict[str, Any]] | None = None
        self._catalog_key: tuple | None = None
        self._frames: OrderedDict[str, pd.DataFrame] = OrderedDict()
        self._max_frames = max_frames

    # catalog of the newest accepted dataset per symbol, rebuilt only when datasets change
    def _key(self) -> tuple:
        mdir = self.root / MANIFEST_DIR
        names = tuple(sorted(p.name for p in mdir.glob("*.json"))) if mdir.is_dir() else ()
        db_mtime = self.db.stat().st_mtime if self.db.is_file() else 0
        return names, db_mtime

    def catalog(self) -> dict[str, dict[str, Any]]:
        key = self._key()
        with self._lock:
            if self._catalog is None or key != self._catalog_key:
                self._catalog = uni.latest_accepted(self.root, self.db)
                self._catalog_key = key
            return self._catalog

    def manifest(self, symbol: str) -> dict[str, Any]:
        cat = self.catalog()
        sym = symbol.strip().upper()
        if sym not in cat:
            raise ChartError(f"no verified price data for {sym}")
        return cat[sym]

    def daily(self, symbol: str) -> pd.DataFrame:
        man = self.manifest(symbol)
        with self._lock:
            frame = self._frames.get(man["dataset_id"])
            if frame is not None:
                self._frames.move_to_end(man["dataset_id"])
                return frame
        frame = uni.read_frame(self.root, man)
        frame["time"] = frame["date"].astype(str).str[:10]
        with self._lock:
            self._frames[man["dataset_id"]] = frame
            while len(self._frames) > self._max_frames:
                self._frames.popitem(last=False)
        return frame

    def frame(self, symbol: str, tf: str = "D", basis: str = "split") -> pd.DataFrame:
        """OHLCV on the chosen price basis and timeframe, with a ``time`` column (YYYY-MM-DD)."""
        if tf not in TIMEFRAMES:
            raise ChartError("timeframe must be D, W or M")
        if basis not in BASES:
            raise ChartError("basis must be split or total")
        d = self.daily(symbol)
        cols = ("adj_open", "adj_high", "adj_low", "adj_close") if basis == "total" else (
            "open", "high", "low", "close")
        out = pd.DataFrame({"time": d["time"], "open": d[cols[0]], "high": d[cols[1]],
                            "low": d[cols[2]], "close": d[cols[3]], "volume": d["volume"]})
        if tf == "D":
            return out.reset_index(drop=True)
        period = pd.to_datetime(out["time"]).dt.to_period("W-FRI" if tf == "W" else "M")
        grouped = out.groupby(period.to_numpy(), sort=True)
        res = pd.DataFrame({
            "time": grouped["time"].last(), "open": grouped["open"].first(),
            "high": grouped["high"].max(), "low": grouped["low"].min(),
            "close": grouped["close"].last(), "volume": grouped["volume"].sum(),
        })
        return res.reset_index(drop=True)

    def badge(self, symbol: str) -> dict[str, Any]:
        return uni.provenance(self.manifest(symbol))

    def bars(self, symbol: str, tf: str = "D", basis: str = "split") -> dict[str, Any]:
        f = self.frame(symbol, tf, basis)
        rows = [{"time": t, "open": _num(o), "high": _num(h), "low": _num(lo), "close": _num(c),
                 "volume": _num(v)}
                for t, o, h, lo, c, v in f[["time", "open", "high", "low", "close", "volume"]]
                .itertuples(index=False, name=None)]
        return {"symbol": symbol.upper(), "tf": tf, "basis": basis, "basis_label": BASES[basis],
                "bars": rows, "provenance": self.badge(symbol)}

    def indicators(self, symbol: str, tf: str, basis: str, specs: list[dict]) -> list[dict]:
        if len(specs) > 12:
            raise ChartError("at most 12 indicators at once")
        f = self.frame(symbol, tf, basis)
        return [dict(compute_indicator(f, s.get("kind", ""), s.get("params")),
                     id=str(s.get("id") or s.get("kind"))) for s in specs]

    def formula(self, text: str, tf: str = "D", basis: str = "split") -> dict[str, Any]:
        cat = self.catalog()
        tree, symbols = parse_formula(text, set(cat))
        missing = sorted(s for s in symbols if s not in cat)
        if missing:
            raise ChartError(f"no verified data for {', '.join(missing)}")
        closes = {s: self.frame(s, tf, basis).set_index("time")["close"].astype(float)
                  for s in symbols}
        aligned = pd.concat(closes, axis=1, join="inner").dropna()
        if aligned.empty:
            raise ChartError("those symbols share no trading days")
        result = eval_formula(tree, {s: aligned[s] for s in symbols})
        if not isinstance(result, pd.Series):
            raise ChartError("the formula needs at least one symbol")
        return {"formula": text.strip().upper(), "tf": tf, "basis": basis,
                "points": [{"time": t, "value": _num(v)} for t, v in result.items()
                           if _num(v) is not None],
                "provenance": [self.badge(s) for s in sorted(symbols)],
                "first": str(aligned.index[0]), "last": str(aligned.index[-1])}

    def compare(self, symbols: list[str], start: str | None, tf: str = "D") -> dict[str, Any]:
        if not 1 <= len(symbols) <= 5:
            raise ChartError("compare 1 to 5 symbols")
        out = []
        for sym in symbols:
            f = self.frame(sym, tf, "total")
            if start:
                f = f[f["time"] >= start]
            if f.empty:
                continue
            base = float(f["close"].iloc[0])
            out.append({"symbol": sym.upper(), "points": [
                {"time": t, "value": _num(c / base * 100)} for t, c in zip(f["time"], f["close"],
                                                                           strict=True)],
                "change_pct": _num((float(f["close"].iloc[-1]) / base - 1) * 100)})
        return {"basis": "total", "series": out}

    def stats(self, symbol: str, start: str, end: str, benchmark: str = "SPY") -> dict[str, Any]:
        if start > end:
            start, end = end, start

        def one(sym: str) -> dict[str, Any] | None:
            f = self.frame(sym, "D", "total")
            f = f[(f["time"] >= start) & (f["time"] <= end)]
            if len(f) < 2:
                return None
            c = f["close"].astype(float).reset_index(drop=True)
            r = c.pct_change().dropna()
            dd = (c / c.cummax() - 1)
            best, worst = r.idxmax(), r.idxmin()
            times = f["time"].reset_index(drop=True)
            return {
                "symbol": sym.upper(), "from": times.iloc[0], "to": times.iloc[-1],
                "days": len(c) - 1, "return_pct": _num((c.iloc[-1] / c.iloc[0] - 1) * 100),
                "max_drawdown_pct": _num(dd.min() * 100),
                "volatility_pct": _num(r.std(ddof=1) * math.sqrt(252) * 100) if len(r) > 1 else None,
                "best_day": {"date": times.iloc[best], "pct": _num(r.loc[best] * 100)},
                "worst_day": {"date": times.iloc[worst], "pct": _num(r.loc[worst] * 100)},
                "up_days_pct": _num((r > 0).mean() * 100),
            }

        main = one(symbol)
        if main is None:
            raise ChartError("select at least two trading days")
        bench = None
        if benchmark and benchmark.upper() != symbol.upper() and benchmark.upper() in self.catalog():
            bench = one(benchmark)
        return {"basis": "total", "selection": main, "benchmark": bench,
                "note": "Total return, dividends included. A past move says nothing certain about the next one."}

    def watchlist(self, name: str = "starter") -> dict[str, Any]:
        try:
            uni_list = uni.load_universe(self.root, name)
        except FileNotFoundError:
            uni_list = {"symbols": [{"symbol": s, "name": s, "group": "Available"}
                                    for s in sorted(self.catalog())]}
        cat = self.catalog()
        rows = []
        for item in uni_list["symbols"]:
            sym = item["symbol"]
            row = {"symbol": sym, "name": item.get("name", sym), "group": item.get("group", ""),
                   "available": sym in cat}
            if sym in cat:
                d = self.daily(sym)
                c = d["close"].astype(float)
                row.update({"last": _num(c.iloc[-1]), "last_date": d["time"].iloc[-1],
                            "change_pct": _num((c.iloc[-1] / c.iloc[-2] - 1) * 100)
                            if len(c) > 1 else None})
            rows.append(row)
        return {"name": uni_list.get("name", name), "note": uni_list.get("survivorship_note"),
                "symbols": rows}


# --- trade replays ---------------------------------------------------------------------------

def list_replays(project_root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((Path(project_root) / REPORTS_DIR).glob("*.replay.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append({"id": path.name.removesuffix(".replay.json"), "card_id": d.get("card_id"),
                    "phase": d.get("phase"), "symbol": d.get("symbol"), "rule_id": d.get("rule_id"),
                    "cost_bps_per_side": d.get("cost_bps_per_side"),
                    "trades": len(d.get("trades") or []), "period": d.get("period"),
                    "reference_check": d.get("reference_check")})
    return out


def get_replay(project_root: Path, replay_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", replay_id):
        raise ChartError("bad replay id")
    path = Path(project_root) / REPORTS_DIR / f"{replay_id}.replay.json"
    if not path.is_file():
        raise ChartError("no such replay")
    return json.loads(path.read_text(encoding="utf-8"))
