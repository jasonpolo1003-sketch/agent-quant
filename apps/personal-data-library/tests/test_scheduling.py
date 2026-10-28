import subprocess
import xml.etree.ElementTree as ET
import pytest


def test_schedule_fixed_target_nonoverlap_and_explicit_activation(tmp_path):
    from data_library.scheduling import task_xml, enable, status
    root=tmp_path/'library'
    xml=task_xml(root,'DOMAIN\\user')
    assert 'IgnoreNew' in xml and 'StartWhenAvailable>true' in xml
    assert 'PT2M' in xml and 'PT90S' in xml
    assert str(root/'scripts/run_intake_once.py') in xml
    assert str(root/'.venv/Scripts/python.exe') in xml
    assert str(root) in xml
    called=[]
    def runner(*args, **kwargs): called.append(args); raise AssertionError('must not execute')
    with pytest.raises(PermissionError): enable(confirmed=False, runner=runner)
    assert called==[]


def test_absent_task_is_not_enabled_and_query_failure_is_unknown():
    from data_library.scheduling import status
    def absent(*args,**kwargs): return subprocess.CompletedProcess(args,1,'','ERROR: The system cannot find the file specified.')
    assert status(runner=absent)['enabled'] is False
    def denied(*args,**kwargs): return subprocess.CompletedProcess(args,1,'','ERROR: Access denied.')
    assert status(runner=denied)['enabled'] is None


def test_readback_detects_wrong_command_or_unexpected_task():
    from data_library.scheduling import task_xml,status
    from pathlib import Path
    xml=task_xml(Path('C:/wrong-library'),'user')
    def runner(*args,**kwargs): return subprocess.CompletedProcess(args,0,xml,'')
    assert status(runner=runner)['drift'] is True
