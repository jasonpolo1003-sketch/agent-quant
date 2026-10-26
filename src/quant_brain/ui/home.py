"""Home page: three plain answers. Where are we? What needs Jason? What did we learn?

"Needs you" combines decisions derived from the SC-FUT-0001 trial ledger with a
short curated list (`brain/_system/needs_you.json`) that agents keep current for
items the ledger cannot know about, such as an open pull request.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_brain.futures import runner
from quant_brain.ui import study

NEEDS_YOU = "brain/_system/needs_you.json"
CARD_TITLE = "MNQ opening-range breakout (SC-FUT-0001)"
CARD_IDEA = (
    "Buy when the Nasdaq micro future breaks above its first-15-minute range "
    "(sell when it breaks below), with a fixed stop, flat by 3:07 pm Chicago."
)
CLOSED_EVENTS = {"card_closed"}


def _events(root: Path) -> list[dict[str, Any]]:
    return runner.read_ledger(root)


def _has(events: list[dict], *names: str) -> bool:
    return any(e["event"] in names for e in events)


def _dev_result(root: Path) -> dict[str, Any] | None:
    report = root / runner.REPORTS / "development" / "report.json"
    if not report.exists():
        return None
    return json.loads(report.read_text(encoding="utf-8")).get("MNQ/development")


def where_we_are(root: Path) -> dict[str, Any]:
    events = _events(root)
    trail = study.trail(root)
    if _has(events, *CLOSED_EVENTS):
        now, next_step = (
            "Closed. The card is finished and counted as a tried idea.",
            "Pick the next strategy idea.",
        )
    elif _has(events, "held_out_completed", "held_out_failed"):
        now, next_step = "Final exam done.", "Adversarial review of the result."
    elif _has(events, "development_completed"):
        now, next_step = (
            "Practice run done; final exam not opened.",
            "Decide: close the card, or spend the final exam on it.",
        )
    elif _has(events, "development_authorized"):
        now, next_step = "Practice run approved.", "Run the practice run."
    elif _has(events, "frozen", "freeze_provenance_corrected"):
        now, next_step = (
            "Rules frozen.",
            "Build and verify the engine, then approve the practice run.",
        )
    else:
        now, next_step = "Drafting rules.", "Freeze the rules."
    return {"card": CARD_TITLE, "idea": CARD_IDEA, "now": now, "next": next_step, "trail": trail}


def _derived_needs(root: Path) -> list[dict[str, Any]]:
    events = _events(root)
    if _has(events, "development_completed") and not _has(
        events, "held_out_authorized", "held_out_started", *CLOSED_EVENTS
    ):
        return [
            {
                "id": "sc-fut-0001-final-exam",
                "title": "Close SC-FUT-0001, or spend the one-time final exam on it?",
                "why": "The practice run showed no edge. The 2025-26 data has never been looked at, so it is "
                "the only clean test left, and it can be used once.",
                "recommendation": "Close the card and save the unseen data for the next idea: a result this "
                "far below the $15/day goal is very unlikely to pass.",
                "action": {"label": "See the evidence", "page": "study"},
            }
        ]
    return []


def needs_you(root: Path) -> list[dict[str, Any]]:
    curated: list[dict[str, Any]] = []
    path = root / NEEDS_YOU
    if path.exists():
        try:
            curated = [i for i in json.loads(path.read_text(encoding="utf-8")) if not i.get("done")]
        except (ValueError, TypeError):
            curated = [
                {
                    "id": "needs-you-file",
                    "title": "The needs-you list file is unreadable",
                    "why": NEEDS_YOU,
                }
            ]
    return _derived_needs(root) + curated


def _plain_finding(entry: dict[str, Any]) -> str:
    v = entry["verdict"]
    if v.get("absolute_mean_cents") is None:
        return "Not enough trades to judge."
    per_day = v["absolute_mean_cents"] / 100
    better = v["observed_paired_cents"] / 100
    luck = "could not be told apart from luck" if v["p_value"] >= 0.05 else "beat random entries"
    goal = "below" if per_day < 15 else "above"
    return (
        f"About ${per_day:,.2f} a day after costs ({goal} the $15 goal). It made ${better:,.2f} a day "
        f"more than random entries, but that {luck} (p = {v['p_value']:.2f})."
    )


def learned(root: Path) -> list[dict[str, Any]]:
    out = []
    entry = _dev_result(root)
    if entry:
        out.append(
            {
                "id": "SC-FUT-0001",
                "title": "Opening-range breakout on MNQ, practice years 2019-2023",
                "outcome": entry["verdict"]["outcome"],
                "plain": _plain_finding(entry),
                "takeaway": "No edge: the same result the source paper found after trading costs.",
                "page": "study",
            }
        )
    out.append(
        {
            "id": "SC-0002",
            "title": "RSI(2) dip-buying on SPY, 2016-2026 held-out",
            "outcome": "not_demonstrated",
            "plain": "It made money, but its return for the risk taken was lower than simply buying "
            "and holding (Sharpe 0.46 vs 0.89), and it only just missed beating random entries "
            "(94.9th percentile; 95th needed).",
            "takeaway": "Closed 2026-09-29. Most of its profit came from 2020-2022.",
            "page": "strategies",
        }
    )
    return out


def home(root: Path) -> dict[str, Any]:
    return {"where": where_we_are(root), "needs": needs_you(root), "learned": learned(root)}
