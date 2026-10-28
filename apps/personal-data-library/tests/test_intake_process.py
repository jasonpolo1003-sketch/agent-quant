import time
from pathlib import Path
import pytest


def test_partial_save_and_expired_lease_catch_up(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    inbox = tmp_path / 'inbox'; inbox.mkdir()
    note = inbox / 'a.md'; note.write_bytes(b'# First')
    s = IntakeStore(tmp_path / 'data')
    scan(s, inbox, stability=0)
    note.write_bytes(b'# Changed before capture')
    scan(s, inbox, stability=0)
    assert not s.items()
    scan(s, inbox, stability=0)
    with s.connect() as db:
        db.execute("UPDATE jobs SET status='processing',lease=0")
    assert drain(s, inbox)['processed'] == 1
    assert s.read_version(s.versions(s.items()[0]['id'])[0]) == note.read_bytes()


def test_no_publish_after_blob_save_failure_and_integrity_reject(tmp_path, monkeypatch):
    from data_library.intake_store import IntakeStore
    import data_library.intake_store as mod
    s = IntakeStore(tmp_path)
    original = mod.os.replace
    def fail(*args): raise OSError('Disk full')
    monkeypatch.setattr(mod.os, 'replace', fail)
    with pytest.raises(OSError): s.retain('inbox', 'a.md', b'# A', {}, 1)
    assert s.items() == []
    monkeypatch.setattr(mod.os, 'replace', original)
    item = s.retain('inbox', 'a.md', b'# A', {}, 1)
    v = s.versions(item)[0]
    (s.root / v['retained_path']).write_bytes(b'corrupt')
    with pytest.raises(ValueError): s.read_version(v)
    with pytest.raises(ValueError): s.retain('inbox', 'b.md', b'# A', {}, 1)


def test_symlink_escape_rejected_before_read(tmp_path):
    from data_library.intake_scan import safe_path
    root = tmp_path / 'inbox'; root.mkdir()
    with pytest.raises(ValueError): safe_path(root, '../private.md')
    outside = tmp_path / 'private.md'; outside.write_text('PRIVATE')
    try: (root / 'escape.md').symlink_to(outside)
    except OSError: pytest.skip('OS symlink privilege unavailable; junction test covers Windows')
    with pytest.raises(ValueError): safe_path(root, 'escape.md')
