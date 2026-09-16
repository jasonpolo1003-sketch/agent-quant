import json
import os
from pathlib import Path

from quant_brain.llm.qwen_call import qwen_call
from quant_brain.ops.events import list_events

snapshot = Path("tests/fixtures/ollama/gate_b_snapshot.md").read_text(encoding="utf-8")
evidence = [{
    "source_id": "S1",
    "title": "Recorded RSI fixture",
    "url_or_citation": "https://example.test/recorded-rsi",
    "source_quality": "primary",
    "snapshot_text": snapshot,
}]
prompt = """Return one raw research JSON payload for research_id RQ-gate-b-smoke.
Use source S1 only. Preserve its title, URL, and source_quality exactly.
Use the exact string QAB_GATE_B_EVIDENCE_7F3A. as the sole evidence value. Do not invent facts.
Use status raw_saved and curator_recommendation needs_more_work.
Required source_type is docs. Use valid values for every shared raw research schema field.
"""
db = Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "gate_b_live_smoke.sqlite"
if db.exists():
    db.unlink()
result = qwen_call(prompt, evidence, expected_research_id="RQ-gate-b-smoke",
                   db_path=db, run_id="RUN-gate-b-live-smoke", task_id="SMOKE")
events = [e for e in list_events(db, run_id="RUN-gate-b-live-smoke")
          if e["event_type"] == "qwen_attempt"]
print(json.dumps({
    "model_used": result.model_used,
    "repaired": result.repaired,
    "escalated": result.escalated,
    "attempts": len(result.attempts),
    "event_count": len(events),
    "event_payloads": [e["payload"] for e in events],
    "curated_writes": 0,
}, indent=2))
