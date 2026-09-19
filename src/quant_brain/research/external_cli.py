"""Explicit isolated-workspace CLI. Never runs production curation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quant_brain.research.external_intake import Intake
from quant_brain.research.external_reports import import_candidates


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--workspace", required=True, help="Isolated directory outside repository and vault"
    )
    sub = p.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("pdf")
    imp.add_argument("--provider", required=True)
    imp.add_argument("--research-id", default="")
    sub.add_parser("leads")
    sub.add_parser("handoff")
    verify = sub.add_parser("verify")
    verify.add_argument("--claim-id")
    verify.add_argument("--allow-network", action="store_true")
    verify.add_argument("--force", action="store_true")
    verify.add_argument("--limit", type=int, default=8)
    add = sub.add_parser("add-claim")
    add.add_argument("json_path", help="Explicit candidate mapping; creates no trusted evidence")
    review = sub.add_parser("review")
    review.add_argument("claim_id")
    review.add_argument("--state", required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--reviewer", required=True)
    a = p.parse_args(argv)
    try:
        store = Intake(a.workspace, create=a.command == "import")
        if a.command == "import":
            result = import_candidates(store, a.pdf, provider=a.provider, research_id=a.research_id)
        elif a.command == "leads":
            result = store.summary()
        elif a.command == "handoff":
            result = store.handoff()
        elif a.command == "add-claim":
            candidate = json.loads(Path(a.json_path).read_text(encoding="utf-8"))
            result = store.add_claim(**candidate)
        elif a.command == "review":
            if a.state == "supported_in_scope":
                seq = store.approve_scope(a.claim_id, reason=a.reason, reviewer=a.reviewer)
            else:
                seq = store.record_review(
                    a.claim_id, state=a.state, reason=a.reason, reviewer=a.reviewer
                )
            result = {"event": seq}
        else:
            if not 1 <= a.limit <= 20:
                raise ValueError("limit must be between 1 and 20")
            ids = (
                [a.claim_id]
                if a.claim_id
                else [c["id"] for c in store.summary()["claims"]][: a.limit]
            )
            result = [store.verify(i, allow_network=a.allow_network, force=a.force) for i in ids]
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
