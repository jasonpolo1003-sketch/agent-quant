from quant_brain.db.init_db import init_database
from quant_brain.ops.events import list_events, record_event, summarize_run


def test_event_store_records_ordered_agent_events_and_builds_run_state(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)

    record_event(
        db_path,
        run_id="RUN-1",
        task_id="RQ-1",
        agent_role="research_scout",
        stage="discovery",
        status="running",
        event_type="stage_started",
        message="Searching live sources",
        payload={"query": "RSI exit rules"},
    )
    record_event(
        db_path,
        run_id="RUN-1",
        task_id="RQ-1",
        agent_role="qwen3:14b",
        stage="evidence_extraction",
        status="waiting",
        event_type="handoff_ready",
        message="Five source snapshots ready",
        payload={"source_count": 5},
    )
    record_event(
        db_path,
        run_id="RUN-OTHER",
        task_id="RQ-2",
        agent_role="research_scout",
        stage="discovery",
        status="completed",
        event_type="stage_completed",
        message="Other run",
    )

    events = list_events(db_path, run_id="RUN-1")
    state = summarize_run(events)

    assert [event["event_id"] for event in events] == sorted(
        event["event_id"] for event in events
    )
    assert len(events) == 2
    assert events[0]["payload"] == {"query": "RSI exit rules"}
    assert state["run_id"] == "RUN-1"
    assert state["task_id"] == "RQ-1"
    assert state["latest_event_id"] == events[-1]["event_id"]
    assert state["agents"]["research_scout"]["status"] == "running"
    assert state["agents"]["qwen3:14b"]["status"] == "waiting"


def test_list_events_supports_incremental_polling(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    first_id = record_event(
        db_path,
        run_id="RUN-1",
        task_id="RQ-1",
        agent_role="research_scout",
        stage="discovery",
        status="running",
        event_type="stage_started",
        message="Started",
    )
    second_id = record_event(
        db_path,
        run_id="RUN-1",
        task_id="RQ-1",
        agent_role="research_scout",
        stage="discovery",
        status="completed",
        event_type="stage_completed",
        message="Finished",
    )

    events = list_events(db_path, run_id="RUN-1", after_event_id=first_id)

    assert second_id > first_id
    assert [event["event_id"] for event in events] == [second_id]
