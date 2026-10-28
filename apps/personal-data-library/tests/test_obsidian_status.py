def test_managed_output_idempotent_and_user_edits_preserved(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.obsidian_status import publish_status
    s = IntakeStore(tmp_path / 'data')
    output = tmp_path / 'Automation' / 'Research intake status.md'
    assert publish_status(s, output)['status'] == 'written'
    first = output.read_bytes(); modified = output.stat().st_mtime_ns
    assert publish_status(s, output)['status'] == 'unchanged'
    assert output.stat().st_mtime_ns == modified
    output.write_bytes(first + b'\nUser edit')
    assert publish_status(s, output)['status'] == 'conflict'
    assert output.read_bytes() == first + b'\nUser edit'
    assert s.health()['events'][0]['kind'] == 'status_conflict'
