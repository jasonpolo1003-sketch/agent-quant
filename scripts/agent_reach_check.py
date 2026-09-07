"""CLI health check for the Agent Reach adapter."""

from __future__ import annotations

import json
import sys

from quant_brain.discovery.agent_reach import AgentReachAdapter, AgentReachError


def main() -> int:
    try:
        health = AgentReachAdapter().check_health()
    except AgentReachError as exc:
        print(f"agent-reach check failed: {exc}", file=sys.stderr)
        return 2
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
