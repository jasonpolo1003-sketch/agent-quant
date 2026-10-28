from hashlib import sha256


def test_durable_exact_bytes_and_idempotent_versions(tmp_path):
    from data_library.intake_store import IntakeStore
    store = IntakeStore(tmp_path)
    raw = b'# Question\r\nUnverified.\r\n'
    item = store.retain('inbox', 'question.md', raw, {'title': 'Question'}, 123)
    assert store.retain('inbox', 'question.md', raw, {'title': 'Question'}, 123) == item
    assert len(store.versions(item)) == 1
    assert store.read_version(store.versions(item)[0]) == raw
    store.retain('inbox', 'question.md', raw + b'Edited', {}, 124)
    other = store.retain('inbox', 'copy.md', raw, {}, 123)
    reopened = IntakeStore(tmp_path)
    assert other != item
    assert len(reopened.versions(item)) == 2
    assert reopened.versions(item)[1]['checksum'] == sha256(raw).hexdigest()
    assert reopened.items()[0]['evidence_status'] == 'unverified'
