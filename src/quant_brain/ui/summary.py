"""Plain-language summaries: turn database state and raw events into sentences.

The terminal's front page answers one question ("what is happening?") without
jargon. Everything here is derived from real rows; nothing is invented.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

STEPS = [
    ("research", "Research", "sources", "Collect sources that say what is worth testing."),
    ("data", "Data", "price_datasets", "Download price history and check it is clean."),
    ("strategy", "Strategy", "strategy_cards",
     "Write the trading rules down, and freeze them before seeing any result."),
    ("backtest", "Backtest", "backtests",
     "Test the frozen rules on past prices, with trading costs, against simple benchmarks."),
    ("review", "Review", "reviews", "Try hard to prove the result wrong. It may be rejected."),
]

STAGE_LABELS = {
    "run": "Run",
    "dispatch": "Routing the task",
    "discovery": "Finding and reading sources",
    "fetch": "Downloading sources",
    "qwen_validation": "Checking the model's answers",
    "evidence_extraction": "Pulling out evidence",
    "curation": "Curating notes",
    "health_check": "Health check",
    "data_refresh": "Market data refresh",
    "agent_prompt": "Scheduled prompt",
    "research_run": "Research run",
}


def steps(counts: dict[str, int]) -> list[dict[str, Any]]:
    """The five project steps. The first step with nothing in the database is 'now'."""
    out, current_found = [], False
    for key, title, table, meaning in STEPS:
        n = counts.get(table, 0)
        if n and not current_found:
            state = "done"
        elif not current_found:
            state, current_found = "now", True
        else:
            state = "later"
        out.append({"key": key, "title": title, "meaning": meaning, "count": n, "state": state})
    if not current_found:  # every step has something in it
        out[-1]["state"] = "now"
    return out


def headline(counts: dict[str, int]) -> dict[str, str]:
    st = steps(counts)
    now = next(s for s in st if s["state"] == "now")
    position = st.index(now) + 1
    cards, tests, reviews = (counts.get("strategy_cards", 0), counts.get("backtests", 0),
                             counts.get("reviews", 0))
    if now["key"] == "research":
        detail = "No curated sources yet. Research comes first."
    elif now["key"] == "data":
        detail = "Sources are in. Next, price history needs to be downloaded and verified."
    elif now["key"] == "strategy":
        detail = "Price data is ready. No strategy has been written down yet."
    elif now["key"] == "backtest":
        detail = (f"{cards} strateg{'y is' if cards == 1 else 'ies are'} written and frozen. "
                  "No backtest has run yet, so there are no results to judge.")
    elif not reviews:
        detail = (f"{tests} backtest{' has' if tests == 1 else 's have'} run. "
                  "Nobody has tried to prove the result wrong yet.")
    else:
        detail = f"{reviews} review{' is' if reviews == 1 else 's are'} recorded."
    return {"title": f"Step {position} of {len(st)}: {now['title'].lower()}",
            "detail": detail, "now": now["key"]}


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace(" ", "T").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def describe_run(events: list[dict[str, Any]]) -> dict[str, Any]:
    """One run in plain words: what it was for, how it ended, and why."""
    if not events:
        return {}
    ordered = sorted(events, key=lambda e: e["event_id"])
    first, last = ordered[0], ordered[-1]
    target = None
    for e in ordered:
        m = re.search(r"\b(RQ-[0-9a-f]+|SC-\d+|JOB-[\w-]+)\b", str(e.get("message") or ""))
        if m:
            target = m.group(1)
            break
    agents = sorted({e["agent_role"] for e in ordered})
    if agents == ["brain_terminal"]:
        kind = STAGE_LABELS.get(first["stage"], first["stage"]).lower()
        title = f"Terminal job: {kind}"
    elif "research_scout" in agents:
        title = f"Research run for {target}" if target else "Research run"
    else:
        title = f"{', '.join(agents)} run"
    failed = last["status"] in ("failed", "refused")
    reason = None
    if failed:
        # The last failing message is usually the cause; skip generic wrap-up lines.
        for e in reversed(ordered):
            msg = str(e.get("message") or "")
            if e["status"] in ("failed", "refused") and msg and not msg.startswith("Wrote "):
                reason = msg
                break
    start, end = _parse_time(first.get("created_at")), _parse_time(last.get("created_at"))
    seconds = int((end - start).total_seconds()) if start and end else None
    if last["status"] in ("completed", "passed"):
        outcome = "Finished successfully."
    elif last["status"] == "refused":
        outcome = "Refused before starting."
    elif failed:
        outcome = "Stopped with an error."
    else:
        outcome = "Still running, or stopped without a final record."
    tally: dict[str, Counter] = {}
    for e in ordered:
        tally.setdefault(e["stage"], Counter())[e["status"]] += 1
    phases = [{"stage": s, "label": STAGE_LABELS.get(s, s.replace("_", " ").capitalize()),
               "ok": c.get("completed", 0) + c.get("passed", 0),
               "failed": c.get("failed", 0) + c.get("refused", 0), "total": sum(c.values())}
              for s, c in tally.items()]
    return {
        "run_id": first["run_id"], "title": title, "target": target, "agents": agents,
        "status": "failed" if failed else ("completed" if last["status"] in
                                            ("completed", "passed") else "running"),
        "outcome": outcome, "reason": reason, "steps": len(ordered), "seconds": seconds,
        "started_at": first.get("created_at"), "ended_at": last.get("created_at"),
        "phases": phases,
    }


COMMIT_KINDS = {
    "feat": "Built", "fix": "Fixed", "docs": "Plan or notes updated", "chore": "Housekeeping",
    "test": "Tests", "refactor": "Code tidied", "evidence": "Evidence saved",
    "research": "Research saved", "perf": "Made faster",
}


def describe_commit(subject: str) -> tuple[str, str]:
    """'feat(backtest): add runner' -> ('Built: backtest', 'add runner'). Unknown forms pass through."""
    m = re.match(r"^(?:\[[^\]]+\]\s*)?(\w+)(?:\(([^)]+)\))?!?:\s*(.+)$", subject)
    if not m or m.group(1).lower() not in COMMIT_KINDS:
        return "Code change", subject
    label = COMMIT_KINDS[m.group(1).lower()]
    return (f"{label}: {m.group(2)}" if m.group(2) else label), m.group(3)


def timeline(commits: list[dict[str, Any]], runs: list[dict[str, Any]],
             jobs: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    """Commits, harness runs and terminal jobs merged newest-first, each as one sentence."""
    items = []
    for c in commits:
        who, text = describe_commit(c["subject"])
        items.append({"when": c["date"], "kind": "commit", "who": who,
                      "text": text, "ref": c["short"], "status": None})
    for r in runs:
        items.append({"when": r["ended_at"], "kind": "run", "who": r["title"],
                      "text": r["outcome"] + (f" {r['reason']}" if r.get("reason") else ""),
                      "ref": r["run_id"], "status": r["status"]})
    for j in jobs:
        items.append({"when": j.get("finished_at") or j["started_at"], "kind": "job",
                      "who": f"Automation: {j['job_id']}", "text": j.get("summary") or j["status"],
                      "ref": j["run_id"], "status": j["status"]})
    epoch = datetime.min.replace(tzinfo=UTC)
    items.sort(key=lambda i: _parse_time(i["when"]) or epoch, reverse=True)
    return items[:limit]
