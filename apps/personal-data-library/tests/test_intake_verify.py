def test_verifier_hashes_catalog_and_detects_corruption(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.intake_verify import verify
    s=IntakeStore(tmp_path)
    item=s.retain('inbox','question.md',b'# Question',{'title':'Question'},1)
    result=verify(tmp_path)
    assert result['ok'] and result['versions']==1
    v=s.versions(item)[0]
    (tmp_path/v['retained_path']).write_bytes(b'broken')
    result=verify(tmp_path)
    assert not result['ok']
    assert result['errors']


def test_backup_restore_preserves_versions_in_isolated_directory(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.intake_verify import backup,verify
    source=tmp_path/'source'
    s=IntakeStore(source)
    item=s.retain('inbox','a.md',b'# A',{},1)
    target=tmp_path/'restored'
    backup(source,target)
    assert verify(target)['ok']
    restored=IntakeStore(target)
    assert restored.read_version(restored.versions(item)[0])==b'# A'
