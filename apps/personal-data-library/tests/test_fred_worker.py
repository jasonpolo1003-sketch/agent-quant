import json
import subprocess


def test_fred_child_gets_explicit_store_root_and_keeps_failure_detail(tmp_path,monkeypatch):
    from data_library.worker import refresh_due
    from data_library.intake_store import IntakeStore
    import data_library.worker as worker
    import time
    seen=[]
    def run(args,**kwargs):
        seen.append(kwargs.get('env',{}).get('PDL_DATA_DIR'))
        return subprocess.CompletedProcess(args,1,json.dumps({'id':args[-1],'ok':False,'error':'publication failed'}),'')
    monkeypatch.setattr(worker.subprocess,'run',run)
    result=refresh_due(IntakeStore(tmp_path),time.monotonic()+90)
    assert seen==[str(tmp_path)]*3
    assert all(r['error']=='publication failed' for r in result)
