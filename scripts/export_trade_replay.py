"""Export a frozen card's trade replay for the terminal's chart page (PROP-010 phase 1).

Read-only: it re-runs the frozen engine over one period and writes a JSON file
with every bar's prices, indicators and signal flags, and every trade with the
reason it fired. For rule A it first checks the trades against the independent
reference implementation and refuses to write on a mismatch.

    uv run python scripts/export_trade_replay.py SC-0002 --phase held-out
    uv run python scripts/export_trade_replay.py SC-0002 --phase in-sample --rule B --symbol QQQ --cost 10
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime

from quant_brain.backtest import engine, reference
from quant_brain.backtest.run import _period, gated_inputs
from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH
from quant_brain.market.replay import build_replay

OUT_DIR = "brain/04_Backtest_Reports"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("card_id")
    parser.add_argument("--phase", choices=["in-sample", "held-out"], default="held-out")
    parser.add_argument("--rule", help="rule id (default: the card's primary rule)")
    parser.add_argument("--symbol", help="symbol (default: the card's primary symbol)")
    parser.add_argument("--cost", type=float, help="bps per side (default: the card's headline)")
    args = parser.parse_args()

    card, entry, frames = gated_inputs(PROJECT_ROOT, DEFAULT_DB_PATH, args.card_id)
    rule_id = args.rule or card.verdict.applies_to
    symbol = args.symbol or card.universe["primary"][0]
    cost = args.cost if args.cost is not None else card.costs.headline_bps
    phase = args.phase.replace("-", "_")
    start, end = _period(card, phase)
    spec = engine.RuleSpec.from_card_rule(next(r for r in card.rules if r.rule_id == rule_id))
    frame = frames[symbol].reset_index(drop=True)

    replay = build_replay(frame, spec, cost_bps=cost, start=start, end=end)

    check = "not available for this rule"
    if spec.exit_kind == "close_above_sma" and spec.max_units == 1 and spec.filter_sma:
        p0, p1 = engine.period_bounds(frame["date"], start, end)
        ref = reference.rule_a_trades(
            frame["adj_open"].tolist(), frame["adj_close"].tolist(), rsi_period=spec.rsi_period,
            entry_below=spec.entry_below, filter_sma=spec.filter_sma,
            exit_sma=int(spec.exit_value), cost=cost / 10_000, p0=p0, p1=p1)
        dates = frame["date"].astype(str)
        ref_rows = [(dates[s], dates[f], dates[o]) for s, f, o, _ in ref]
        ours = [(t["signal_date"], t["entry_date"], t["exit_date"]) for t in replay["trades"]]
        if ref_rows != ours:
            print(f"REFUSED: engine ({len(ours)} trades) and reference ({len(ref_rows)}) differ")
            return 1
        check = f"match ({len(ours)} trades)"

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                            text=True, check=True).stdout.strip()
    dataset = next(d for d in card.data if d.symbol == symbol)
    replay = {
        "card_id": card.card_id,
        "spec_sha256": entry["spec_sha256"],
        "phase": phase,
        "symbol": symbol,
        "dataset_id": dataset.dataset_id,
        "content_sha256": dataset.content_sha256,
        "code_commit": commit,
        "generated_at": datetime.now(UTC).isoformat(),
        "reference_check": check,
        "note": "A replay of a past backtest. It is not proof of future profit.",
        **replay,
    }
    name = f"{card.card_id}-{args.phase}-{rule_id}-{symbol}-{cost:g}bps.replay.json"
    path = PROJECT_ROOT / OUT_DIR / name
    path.write_text(json.dumps(replay, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"OK  {path.relative_to(PROJECT_ROOT)}: {len(replay['bars'])} bars, "
          f"{len(replay['trades'])} trades; reference check: {check}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
