"""CLI health check for the Agent Reach adapter.

Answers one question: *are any lanes working right now?* It deliberately does
not judge whether a working lane is a good fit for a particular research
question -- that is `scripts/gate_readiness.py`. A lane is not unhealthy merely
because it is unsuitable for a given topic.

Exit codes:
    0  at least one search lane is usable
    2  the doctor is unusable and no independent lane is available
    3  the doctor answered, but no search lane is usable
"""

from __future__ import annotations

import json
import sys
from typing import Any

from quant_brain.discovery.agent_reach import (
    SEARCH_CHANNELS,
    SEARCH_LANES,
    AgentReachAdapter,
    AgentReachError,
    ChannelHealth,
    is_channel_usable,
)


def _console_safe(text: str) -> str:
    """Make text printable on a non-UTF-8 console.

    A doctor reason may be Chinese while this console is cp1252. A diagnostic
    that crashes while reporting the encoding problem it exists to report is
    worse than useless, so unprintable characters are replaced rather than
    raising.
    """
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def lane_verdicts(health: dict[str, ChannelHealth]) -> list[dict[str, Any]]:
    """Per-lane readiness right now, with the doctor's own reason when not."""
    rows: list[dict[str, Any]] = []
    for lane in SEARCH_LANES:
        if lane.channel is None:
            # Not routed through Agent Reach, so the doctor has no opinion on
            # it. Saying "absent from doctor output" would read as a fault when
            # the lane simply needs no router or account.
            rows.append(
                {
                    "lane": lane.name,
                    "channel": None,
                    "declared": lane.status,
                    "usable_now": True,
                    "reason": "zero-account lane; not routed through Agent Reach",
                }
            )
            continue
        info = health.get(lane.channel)
        usable = is_channel_usable(health, lane.channel)
        if info is None:
            reason = f"channel {lane.channel!r} absent from doctor output"
        elif usable:
            reason = f"status={info.status}, backend={info.active_backend}"
        else:
            first_line = info.message.splitlines()[0] if info.message else "no reason given"
            reason = f"status={info.status}: {first_line}"
        rows.append(
            {
                "lane": lane.name,
                "channel": lane.channel,
                "declared": lane.status,
                "usable_now": usable,
                "reason": reason,
            }
        )
    return rows


def main() -> int:
    doctor_error: str | None = None
    try:
        health = AgentReachAdapter().check_health()
    except AgentReachError as exc:
        health = {}
        doctor_error = str(exc)
        print(
            f"agent-reach routed lanes unavailable: {exc}; independent lanes remain available",
            file=sys.stderr,
        )

    rows = [
        {
            "channel": item.channel,
            "status": item.status,
            "active_backend": item.active_backend,
            "message": item.message,
        }
        for item in health.values()
    ]
    print(json.dumps(rows, indent=2))

    verdicts = lane_verdicts(health)
    print("\nLane readiness:")
    for row in verdicts:
        mark = "usable    " if row["usable_now"] else "NOT usable"
        print(f"  {mark} {row['lane']:<10} ({row['channel']}, declared {row['declared']})")
        print(f"             {_console_safe(row['reason'])}")

    search_ready = any(row["usable_now"] for row in verdicts if row["channel"] in SEARCH_CHANNELS)
    github_ready = is_channel_usable(health, "github")
    any_ready = any(row["usable_now"] for row in verdicts)
    if not any_ready:
        print(
            "\nNO SEARCH LANE USABLE - live discovery will fail closed.",
            file=sys.stderr,
        )
        return 2 if doctor_error else 3

    print("\nAt least one search lane is usable.")
    if not (search_ready or github_ready):
        # Worth saying plainly: a usable lane is not the same as a lane that can
        # answer a given question. See scripts/gate_readiness.py.
        print(
            "  Note: the semantic search lane is not usable. GitHub returns code "
            "repositories and arXiv returns academic preprints, so a "
            "documentation or practitioner question may still find nothing. "
            "Run scripts/gate_readiness.py to ask about a specific question.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
