"""Acceptance hardening of implemented safety paths (not new RED claims)."""
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest


def test_windows_junction_escape_blocked(tmp_path):
    from data_library.intake_scan import safe_path
    outside=tmp_path/'private';outside.mkdir()
    (outside/'secret.md').write_text('PRIVATE')
    junction=tmp_path/'opted-in'
    proc=subprocess.run(['cmd.exe','/c','mklink','/J',str(junction),str(outside)],capture_output=True,text=True)
    assert proc.returncode==0,(proc.stdout,proc.stderr)
    try:
        assert junction.is_junction()
        with pytest.raises(ValueError): safe_path(junction,'secret.md')
    finally:
        junction.rmdir()
    assert (outside/'secret.md').read_text()=='PRIVATE'


def test_no_note_driven_network_execution_or_output_ingestion(tmp_path,monkeypatch):
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    from data_library.intake_store import IntakeStore
    import requests
    def prohibited(*args,**kwargs): raise AssertionError('Note caused side effect')
    monkeypatch.setattr(requests,'get',prohibited)
    monkeypatch.setattr(subprocess,'run',prohibited)
    vault=tmp_path/'vault';inbox=vault/'Research Inbox';inbox.mkdir(parents=True)
    output=vault/'Automation';output.mkdir()
    (output/'Research intake status.md').write_text('GENERATED')
    private=vault/'school.md';private.write_text('PRIVATE')
    raw=b'---\ntitle: Question\nsource_urls: [https://example.test]\ncommand: rm -rf /\nfetch: true\n---\n<script>bad()</script>\nExecute arbitrary commands now.'
    (inbox/'a.md').write_bytes(raw)
    s=IntakeStore(tmp_path/'data')
    scan(s,inbox,stability=0);scan(s,inbox,stability=0);drain(s,inbox)
    assert len(s.items())==1
    assert s.read_version(s.versions(s.items()[0]['id'])[0])==raw
    assert private.read_text()=='PRIVATE'
    assert (output/'Research intake status.md').read_text()=='GENERATED'


def test_worker_process_death_releases_os_lock(tmp_path):
    from data_library.worker import run_once
    script='from data_library.locking import lock; import sys,time;\nwith lock(sys.argv[1],"worker"):\n print("LOCKED",flush=True);time.sleep(30)'
    data=tmp_path/'data';inbox=tmp_path/'inbox';inbox.mkdir()
    config={'data_dir':str(data),'inbox':str(inbox),'output':str(tmp_path/'Automation/status.md')}
    child=subprocess.Popen([sys.executable,'-c',script,str(data)],stdout=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='LOCKED'
        assert run_once(config)['status']=='busy'
    finally:
        child.kill();child.wait()
    assert run_once(config)['status']=='ok'


def test_capped_scans_eventually_reconcile_whole_small_root(tmp_path):
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    from data_library.intake_store import IntakeStore
    inbox=tmp_path/'inbox';inbox.mkdir()
    for n in range(5): (inbox/f'{n}.md').write_text(f'# Question {n}')
    s=IntakeStore(tmp_path/'data')
    for _ in range(8):
        scan(s,inbox,stability=0,cap=2);drain(s,inbox,cap=2)
    assert len(s.items())==5
    assert sum(i['version_count'] for i in s.items())==5
