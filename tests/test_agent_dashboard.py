from quant_brain.db.init_db import init_database
from quant_brain.ops.dashboard import list_recent_runs, load_run_dashboard
from quant_brain.ops.events import record_event


def test_dashboard_lists_recent_runs_and_loads_agent_lanes(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    record_event(
        db_path,
        run_id="RUN-older",
        task_id="RQ-1",
        agent_role="orchestrator",
        stage="run",
        status="completed",
        event_type="run_completed",
        message="Older run",
    )
    record_event(
        db_path,
        run_id="RUN-newer",
        task_id="RQ-2",
        agent_role="research_scout",
        stage="discovery",
        status="running",
        event_type="candidates_ranked",
        message="Ranked sources",
        payload={"candidate_count": 8},
    )

    runs = list_recent_runs(db_path, limit=10)
    dashboard = load_run_dashboard(db_path, "RUN-newer")

    assert [run["run_id"] for run in runs] == ["RUN-newer", "RUN-older"]
    assert dashboard["state"]["run_id"] == "RUN-newer"
    assert dashboard["state"]["agents"]["research_scout"]["status"] == "running"
    assert dashboard["events"][0]["payload"] == {"candidate_count": 8}
    assert dashboard["task"]["research_id"] == "RQ-2"
