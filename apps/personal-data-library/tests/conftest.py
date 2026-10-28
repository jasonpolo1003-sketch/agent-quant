"""Portable test-only data. Never installed as application fallback/cache."""
from datetime import date
from pathlib import Path
import pytest
from data_library.core import Library
from data_library.metadata import SERIES


@pytest.fixture
def economic_fixture(tmp_path,monkeypatch):
    lib=Library(tmp_path/'economic-test-only')
    for sid in SERIES:
        rows=[f'{year}-{month:02d}-01,{100+(year-1999)*12+month}' for year in (1999,2000,2001) for month in range(1,13)]
        raw=(f'observation_date,{sid}\n'+'\n'.join(rows)+'\n').encode()
        lib.publish(sid,raw,'https://example.invalid/test-only')
    monkeypatch.setenv('PDL_DATA_DIR',str(lib.root))
    return lib
