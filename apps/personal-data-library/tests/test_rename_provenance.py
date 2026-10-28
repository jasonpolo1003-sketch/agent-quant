"""Regressions found by independent intake review."""
import shutil
from data_library.intake_store import IntakeStore
from data_library.intake_scan import scan
from data_library.intake_process import drain


def reconcile(store, inbox):
    scan(store, inbox, stability=0)
    scan(store, inbox, stability=0)
    return drain(store, inbox)


def test_old_path_reused_after_rename_retains_new_occurrence(tmp_path):
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    store = IntakeStore(tmp_path / 'data')
    original = inbox / 'a.md'
    original.write_bytes(b'# Research evidence\n')
    reconcile(store, inbox)
    item_id = store.items()[0]['id']
    renamed = inbox / 'renamed.md'
    original.rename(renamed)
    reconcile(store, inbox)
    assert store.items()[0]['id'] == item_id
    shutil.copy2(renamed, original)
    result = reconcile(store, inbox)
    assert result['processed'] == 1
    items = store.items()
    assert {item['path'] for item in items} == {'a.md', 'renamed.md'}
    assert len({item['id'] for item in items}) == 2
    assert all(item['version_count'] == 1 for item in items)
    assert reconcile(store, inbox)['processed'] == 0


def test_rename_preserves_capture_source_in_version_and_receipt(tmp_path):
    from data_library.intake_verify import verify
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    store = IntakeStore(tmp_path / 'data')
    original = inbox / 'original.md'
    original.write_bytes(b'# Original research\n')
    reconcile(store, inbox)
    item_id = store.items()[0]['id']
    original.rename(inbox / 'renamed.md')
    reconcile(store, inbox)
    assert store.items()[0]['path'] == 'renamed.md'
    version = store.versions(item_id)[0]
    assert version['source_path'] == 'original.md'
    assert version['source_alias'] == 'inbox'
    receipt = verify(store.root)['receipts'][0]
    assert receipt['source_path'] == 'original.md'
    assert receipt['current_source_path'] == 'renamed.md'
    assert receipt['provenance_status'] == 'recorded_at_capture'
