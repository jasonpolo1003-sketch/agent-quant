from data_library import core
import pandas as pd

RAW = b'observation_date,CPIAUCSL\n1999-01-01,100\n2000-01-01,110\n'


def test_publish_offline_reload_provenance_and_dedupe(tmp_path):
    lib = core.Library(tmp_path)
    first = lib.publish('CPIAUCSL', RAW, 'https://fred.stlouisfed.org/graph/graph.csv?id=CPIAUCSL', source_last_modified='Wed, 01 Jan 2020 00:00:00 GMT')
    again = lib.publish('CPIAUCSL', RAW, 'https://fred.stlouisfed.org/graph/graph.csv?id=CPIAUCSL')
    assert first == again
    lib = core.Library(tmp_path)
    versions = lib.versions('CPIAUCSL')
    assert len(versions) == 1
    row = versions[0]
    assert (tmp_path / row['raw_path']).read_bytes() == RAW
    assert row['origin'] == 'U.S. Bureau of Labor Statistics'
    assert row['units'] == 'Index 1982–1984=100'
    assert row['source_last_modified'] == 'Wed, 01 Jan 2020 00:00:00 GMT'
    assert row['source_release_at'] is None
    assert row['retrieved_at'].endswith('+00:00')
    assert row['rows'] == 2
    assert row['quality']['missing_months'] == 11
    assert len(lib.load('CPIAUCSL')) == 2
    assert lib.catalog('inflation')[0]['id'] == 'CPIAUCSL'
    assert lib.catalog('Board of Governors')[0]['id'] == 'FEDFUNDS'


def test_refresh_revisions_and_failures_preserve_success(tmp_path):
    lib = core.Library(tmp_path)
    def fetch(sid):
        return RAW, 'https://fred.stlouisfed.org/graph/graph.csv?id=' + sid, None
    first = lib.refresh('CPIAUCSL', fetch)
    assert first['ok']
    old = lib.versions('CPIAUCSL')[0]
    revised = RAW.replace(b'110', b'112')
    assert lib.refresh('CPIAUCSL', lambda sid: (revised, 'official-test-url', None))['ok']
    assert len(lib.versions('CPIAUCSL')) == 2
    assert lib.load('CPIAUCSL').value.iloc[-1] == 112
    assert lib.load('CPIAUCSL', old['checksum']).value.iloc[-1] == 110
    assert (tmp_path / old['raw_path']).read_bytes() == RAW
    assert not lib.refresh('CPIAUCSL', lambda sid: (b'<html>error</html>', 'bad', None))['ok']
    def offline(sid):
        raise ConnectionError('Network unavailable')
    assert not lib.refresh('CPIAUCSL', offline)['ok']
    assert lib.load('CPIAUCSL').value.iloc[-1] == 112
    assert len(lib.versions('CPIAUCSL')) == 2
    assert 'Network unavailable' in lib.attempts('CPIAUCSL')[0]['error']


def test_source_reversion_selects_old_checksum_without_duplicate(tmp_path):
    lib = core.Library(tmp_path)
    original = lib.publish('CPIAUCSL', RAW, 'official')
    lib.publish('CPIAUCSL', RAW.replace(b'110', b'112'), 'official')
    lib.publish('CPIAUCSL', RAW, 'official')
    assert len(lib.versions('CPIAUCSL')) == 2
    assert lib.versions('CPIAUCSL')[0]['checksum'] == original
    assert lib.load('CPIAUCSL').value.iloc[-1] == 110


def test_interrupted_file_publication_never_switches_active_snapshot(tmp_path, monkeypatch):
    lib = core.Library(tmp_path)
    original = lib.publish('CPIAUCSL', RAW, 'official')
    rename = core.os.rename
    def fail_clean(src, dst):
        if str(dst).endswith('.parquet'):
            raise OSError('Simulated interrupted publication')
        return rename(src, dst)
    monkeypatch.setattr(core.os, 'rename', fail_clean)
    result = lib.refresh('CPIAUCSL', lambda sid: (RAW.replace(b'110', b'113'), 'official', None))
    assert not result['ok']
    assert 'interrupted publication' in result['error']
    assert len(lib.versions('CPIAUCSL')) == 1
    assert lib.versions('CPIAUCSL')[0]['checksum'] == original
    assert lib.load('CPIAUCSL').value.iloc[-1] == 110
    assert not list(tmp_path.rglob('*.tmp'))
