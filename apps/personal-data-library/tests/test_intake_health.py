def test_health_counts_backlog_and_review_separately(tmp_path):
    from data_library.intake_store import IntakeStore
    s=IntakeStore(tmp_path)
    with s.connect() as db:
        for n,state in enumerate(['queued','retry_wait','processing','needs_review','failed','organized']):
            db.execute('INSERT INTO jobs(path,status) VALUES(?,?)',(f'{n}.md',state))
    health=s.health()
    assert health['pending_count']==3
    assert health['needs_review_count']==1
    assert health['failed_count']==1
