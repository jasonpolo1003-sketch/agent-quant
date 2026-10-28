import os
import subprocess
import sys
import time
from pathlib import Path
import pytest


def test_separate_process_numerical_connection_exclusion_and_release(tmp_path):
    from data_library.core import Library
    from data_library.locking import Busy
    lib = Library(tmp_path)
    script = 'from data_library.core import Library; import sys,time; l=Library(sys.argv[1]);\nwith l.connect():\n print("LOCKED",flush=True); time.sleep(30)'
    child = subprocess.Popen([sys.executable, '-c', script, str(tmp_path)], stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'LOCKED'
        started = time.monotonic()
        with pytest.raises(Busy): Library(tmp_path).catalog()
        assert time.monotonic() - started < 4
    finally:
        child.kill(); child.wait()
    assert len(Library(tmp_path).catalog()) == 3


def test_network_fetch_is_outside_numerical_lock(tmp_path):
    from data_library.core import Library
    lib = Library(tmp_path)
    def fetcher(sid):
        child = subprocess.run([sys.executable,'-c','from data_library.core import Library; import sys; print(len(Library(sys.argv[1]).catalog()))',str(tmp_path)], capture_output=True,text=True,timeout=10)
        assert child.returncode == 0, child.stderr
        return b'observation_date,UNRATE\n1999-01-01,4.3\n', 'https://example.test', None
    assert lib.refresh('UNRATE', fetcher)['ok']
