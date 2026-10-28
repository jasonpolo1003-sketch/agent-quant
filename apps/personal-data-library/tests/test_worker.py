import time


def test_bounded_manual_worker_due_refresh_and_nonoverlap(tmp_path):
    from data_library.worker import run_once
    from data_library.intake_store import IntakeStore
    from data_library.locking import lock
    inbox = tmp_path/'inbox'; inbox.mkdir()
    (inbox/'a.md').write_text('# Question')
    data = tmp_path/'data'
    config = {'inbox':str(inbox),'output':str(tmp_path/'Automation/status.md'),'data_dir':str(data),'stability_seconds':0,'refresh_fred':True}
    calls=[]
    def refresh(sid): calls.append(sid); return {'id':sid,'ok':True}
    a=run_once(config, refresher=refresh)
    b=run_once(config, refresher=refresh)
    c=run_once(config, refresher=refresh)
    assert b['processed'] == 1
    assert len(calls) == 3
    assert c['processed'] == 0
    with lock(data,'worker'):
        assert run_once(config, refresher=refresh)['status']=='busy'
    assert IntakeStore(data).state('fred_due')['last_success']


def test_failed_due_refresh_backoff_and_notes_still_process(tmp_path):
    from data_library.worker import run_once
    from data_library.intake_store import IntakeStore
    inbox=tmp_path/'inbox'; inbox.mkdir()
    (inbox/'a.md').write_text('# Offline question')
    config={'inbox':str(inbox),'output':str(tmp_path/'out/status.md'),'data_dir':str(tmp_path/'data'),'stability_seconds':0,'refresh_fred':True}
    calls=[]
    def failure(sid): calls.append(sid); return {'id':sid,'ok':False,'error':'offline'}
    run_once(config,refresher=failure)
    result=run_once(config,refresher=failure)
    assert result['processed']==1
    assert len(calls)==3
    state=IntakeStore(tmp_path/'data').state('fred_due')
    assert state['next_retry']>time.time()
    assert not state.get('last_success')
