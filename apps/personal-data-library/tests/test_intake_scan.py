from pathlib import Path
import time
import pytest


def test_scans_only_stable_opted_in_notes_and_recovers_queue(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    inbox = tmp_path / 'vault' / 'Research Inbox'
    inbox.mkdir(parents=True)
    outside = inbox.parent / 'private.md'
    outside.write_text('PRIVATE')
    note = inbox / 'question.md'
    raw = b'---\ntitle: Question\nstrategy_id: SC-example\nsource_urls: [https://example.com/source]\n---\n# Question\n<script>alert(1)</script>\n'
    note.write_bytes(raw)
    store = IntakeStore(tmp_path / 'data')
    assert scan(store, inbox, stability=0)['queued'] == 0
    assert scan(store, inbox, stability=0)['queued'] == 1
    assert drain(store, inbox)['processed'] == 1
    assert len(store.items()) == 1
    item = store.items()[0]
    assert item['metadata']['source_urls'] == ['https://example.com/source']
    assert store.read_version(store.versions(item['id'])[0]) == raw
    scan(store, inbox, stability=0)
    drain(store, inbox)
    assert len(store.versions(item['id'])) == 1
    note.write_bytes(raw + b'Edit')
    scan(store, inbox, stability=0)
    scan(store, inbox, stability=0)
    drain(store, inbox)
    assert len(store.versions(item['id'])) == 2
    note.rename(inbox / 'renamed.md')
    scan(store, inbox, stability=0)
    scan(store, inbox, stability=0)
    drain(store, inbox)
    assert len(store.items()) == 1
    assert store.items()[0]['path'] == 'renamed.md'
    (inbox / 'renamed.md').unlink()
    scan(store, inbox, stability=0)
    assert store.items()[0]['available'] == 0
    assert len(store.versions(item['id'])) == 2
    assert outside.read_text() == 'PRIVATE'


@pytest.mark.parametrize('raw', [b'\xff', b'---\ntitle: !!python/object:os.system [bad]\n---\nQuestion', b'---\n[broken\n---\nx', b'x' * (2*1024*1024+1)])
def test_invalid_notes_need_review_not_silent_drop(tmp_path, raw):
    from data_library.intake_store import IntakeStore
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    (inbox / 'bad.md').write_bytes(raw)
    store = IntakeStore(tmp_path / 'data')
    scan(store, inbox, stability=0)
    scan(store, inbox, stability=0)
    drain(store, inbox)
    assert store.health()['queue'][0]['status'] == 'needs_review'
    assert store.health()['queue'][0]['error']


def test_copies_ambiguous_rename_and_unsupported_are_visible(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    store = IntakeStore(tmp_path / 'data')
    for name in ['a.md', 'b.md']:
        (inbox / name).write_bytes(b'# Same')
    (inbox / 'attachment.pdf').write_bytes(b'not parsed')
    for _ in range(2): scan(store, inbox, stability=0)
    drain(store, inbox)
    assert len(store.items()) == 2
    (inbox / 'a.md').rename(inbox / 'c.md')
    (inbox / 'b.md').rename(inbox / 'd.md')
    for _ in range(2): scan(store, inbox, stability=0)
    drain(store, inbox)
    assert len(store.items()) == 4
    assert any('ambiguous' in e['detail'] for e in store.health()['events'])
    assert any('unsupported' in e['detail'] for e in store.health()['events'])
