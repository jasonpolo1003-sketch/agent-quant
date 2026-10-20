"""Build the terminal's market snapshot from local accepted datasets (PROP-010).

Read-only over the data; writes data/processed/market_snapshot.json (gitignored):
one screener row per universe symbol with its provenance badge, the screener
presets, and a 1-year correlation matrix of the universe.

    uv run python scripts/market_snapshot.py
    uv run python scripts/market_snapshot.py --preset oversold_uptrend
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH
from quant_brain.market import risk, screener
from quant_brain.market.universe import latest_accepted, load_universe, provenance, read_frame

OUT = "data/processed/market_snapshot.json"


def build(universe_name: str = "starter") -> dict:
    universe = load_universe(PROJECT_ROOT, universe_name)
    manifests = latest_accepted(PROJECT_ROOT, DEFAULT_DB_PATH)
    rows, closes, missing = [], {}, []
    for entry in universe["symbols"]:
        manifest = manifests.get(entry["symbol"])
        if manifest is None:
            missing.append(entry["symbol"])
            continue
        frame = read_frame(PROJECT_ROOT, manifest)
        rows.append({**entry, **screener.screen_row(frame), "provenance": provenance(manifest)})
        closes[entry["symbol"]] = frame.set_index("date")["adj_close"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "universe": universe_name,
        "survivorship_note": universe["survivorship_note"],
        "missing": missing,
        "rows": rows,
        "presets": screener.presets_public(),
        "correlation_1y": risk.correlation_matrix(closes, window=252),
        "note": "End-of-day data. Nothing here is a recommendation to trade.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--universe", default="starter")
    parser.add_argument("--preset", choices=sorted(screener.PRESETS))
    args = parser.parse_args()
    snapshot = build(args.universe)
    path = PROJECT_ROOT / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, separators=(",", ":")) + "\n", encoding="utf-8")
    shown = screener.screen(snapshot["rows"], args.preset)
    if args.preset:
        print(f"{screener.PRESETS[args.preset]['title']}: {len(shown)} of {len(snapshot['rows'])}")
    for r in shown:
        print(f"{r['symbol']:6} {r['last_date']}  {r['close']:>10.2f}  1d {r['change_1d_pct'] or 0:+6.2f}%  "
              f"1y {r['change_1y_pct'] or 0:+7.2f}%  RSI2 {r['rsi_2'] or 0:5.1f}  "
              f"vs200 {r['vs_sma_200_pct'] or 0:+6.1f}%")
    print(f"wrote {OUT}: {len(snapshot['rows'])} rows, missing {snapshot['missing'] or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
