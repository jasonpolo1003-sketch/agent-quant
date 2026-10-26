"""Build the physically separate development-only Databento view for SC-FUT-0001.

Approved by Jason 2026-10-26. Verifies source hashes against the download
receipt, copies OHLCV records before the first locked CME trade date (stopping
at the first locked record, which is never written), copies only pre-lock
definition chunks, and records counts/timestamps/hashes. Never prints prices.

    uv run python scripts/split_dev_partition.py \
        --source C:/Users/jason/OneDrive/Desktop/Quant/data/databento/rc_2026-10-22 \
        --out C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31

Refuses to overwrite an existing output directory.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from quant_brain.config import BRAIN_DIR
from quant_brain.futures.dev_partition import (
    ns_to_iso,
    sha256_file,
    split_ohlcv,
    trade_date_cutoff_ns,
)

OHLCV_FILES = (
    "glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-20261022.dbn.zst",
    "glbx-mdp3_ohlcv-1d_MES-MNQ-FUT_20190501-20261022.dbn.zst",
)
MANIFEST = BRAIN_DIR / "_system" / "futures" / "dev-partition-manifest.json"


def read_sums(path: Path) -> dict[str, str]:
    sums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            sums[name.strip().lstrip("*")] = digest
    return sums


def pre_lock_definition(name: str, first_locked: date) -> bool:
    """def_2019 / def_YYYYMM chunks; each quarter chunk ends before the next quarter starts."""
    stem = name.removeprefix("def_").removesuffix(".dbn.zst")
    if not stem.isdigit():
        return False
    year, month = (int(stem), 5) if len(stem) == 4 else (int(stem[:4]), int(stem[4:]))
    end_month = month + 3 if len(stem) == 6 else 13
    end_year, end_month = year + (end_month - 1) // 12, (end_month - 1) % 12 + 1
    return date(end_year, end_month, 1) <= first_locked


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--first-locked", type=date.fromisoformat, default=date(2025, 1, 1))
    args = parser.parse_args()

    if args.out.exists():
        print(f"FAIL  output directory exists: {args.out}")
        return 1
    cutoff = trade_date_cutoff_ns(args.first_locked)
    print(f"cutoff (exclusive): {ns_to_iso(cutoff)}  [first locked trade date {args.first_locked}]")

    sums = read_sums(args.source / "SHA256SUMS")
    def_dir = args.source / "def_years"
    def_sums = read_sums(def_dir / "SHA256SUMS_def_years")
    for name in OHLCV_FILES:
        if sha256_file(args.source / name) != sums.get(name):
            print(f"FAIL  source hash mismatch: {name}")
            return 1
    print("source hashes verified against receipt")

    staging = args.out.with_name(args.out.name + ".partial")
    if staging.exists():
        shutil.rmtree(staging)
    results = [
        split_ohlcv(args.source / name, staging / name.replace("20261022", "dev"), cutoff)
        for name in OHLCV_FILES
    ]
    for result in results:
        if not result.reached_cutoff:
            print(f"FAIL  {result.source} ended before cutoff; partition incomplete")
            return 1
        print(
            f"OK    {result.output}: {result.records_written} records, {result.first_ts_event} .. {result.last_ts_event}"
        )

    definitions = []
    (staging / "def_years").mkdir()
    for name in sorted(def_sums):
        if not pre_lock_definition(name, args.first_locked):
            continue
        target = staging / "def_years" / name
        shutil.copyfile(def_dir / name, target)
        digest = sha256_file(target)
        if digest != def_sums[name]:
            print(f"FAIL  definition hash mismatch: {name}")
            return 1
        definitions.append({"file": name, "sha256": digest})
    print(f"OK    {len(definitions)} pre-lock definition chunks copied and verified")

    lines = [f"{r.output_sha256}  {r.output}" for r in results]
    lines += [f"{d['sha256']}  def_years/{d['file']}" for d in definitions]
    (staging / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "status": "development_only_partition",
        "approved_by": "Jason 2026-10-26 (SC-FUT-0001 prefreeze defaults, Data row)",
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "first_locked_trade_date": args.first_locked.isoformat(),
        "cutoff_exclusive_utc": ns_to_iso(cutoff),
        "cutoff_rule": "Globex open (17:00 America/Chicago) of the first locked trade date",
        "source_dir": str(args.source),
        "output_dir": str(args.out),
        "source_sha256": {name: sums[name] for name in OHLCV_FILES},
        "ohlcv": [r.to_dict() for r in results],
        "definitions": definitions,
        "locked_access": "stopped at first record with ts_event >= cutoff; only its timestamp was read; no locked record written or printed",
        "excluded": "statistics schema (not time-ordered by ts_event; not needed under approved last-trade close)",
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    staging.rename(args.out)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} and {MANIFEST.relative_to(BRAIN_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
