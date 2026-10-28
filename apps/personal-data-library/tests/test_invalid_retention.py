def test_invalid_metadata_retains_original_for_review(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.intake_scan import scan
    from data_library.intake_process import drain
    inbox=tmp_path/'inbox';inbox.mkdir()
    raw=b'---\ntitle: !!python/object:os.system [bad]\n---\nUntrusted'
    (inbox/'bad.md').write_bytes(raw)
    store=IntakeStore(tmp_path/'data')
    scan(store,inbox,stability=0);scan(store,inbox,stability=0)
    drain(store,inbox)
    assert len(store.items())==1
    item=store.items()[0]
    assert item['status']=='needs_review'
    assert store.read_version(store.versions(item['id'])[0])==raw
    assert item['metadata']['error']
