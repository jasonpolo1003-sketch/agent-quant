import json
from hashlib import sha256
from pathlib import Path


def test_explicit_hash_bound_metadata_only_and_block_before_open(tmp_path, monkeypatch):
    from data_library.quant_catalog import catalog
    root = tmp_path / 'quant'; root.mkdir()
    safe = root / 'development.md'; safe.write_bytes(b'# Development summary\nSource verdict: inconclusive')
    locked = root / 'locked.npz'; locked.write_bytes(b'DO NOT OPEN')
    entry = {'id':'DEV-1','path':'development.md','classification':'development','kind':'report',
             'strategy_id':'SC-example','reviewed':True,'sha256':sha256(safe.read_bytes()).hexdigest(),
             'source_verdict':'inconclusive','source_run_id':None}
    original = Path.read_bytes
    opened=[]
    def traced(p):
        opened.append(p.name)
        assert p.name != 'locked.npz'
        return original(p)
    monkeypatch.setattr(Path, 'read_bytes', traced)
    results = catalog(root, [entry, {**entry,'id':'BAD','path':'locked.npz','classification':'unknown'}], revision='test-head')
    assert results[0]['checksum'] == entry['sha256']
    assert results[0]['source_verdict'] == 'inconclusive'
    assert results[0]['source_run_id'] is None
    assert results[1]['status'] == 'blocked'
    assert opened == ['development.md']
    safe.write_bytes(b'Changed after review')
    assert catalog(root, [entry])[0]['status'] == 'blocked'
