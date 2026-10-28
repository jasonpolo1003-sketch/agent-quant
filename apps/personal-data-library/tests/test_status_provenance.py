def test_status_pins_reference_revision_without_inventing_current_strategy(tmp_path):
    from data_library.intake_store import IntakeStore
    from data_library.obsidian_status import publish_status
    s=IntakeStore(tmp_path/'data')
    s.state('quant_catalog',[{'id':'DEV','path':'development.md','revision':'head-one','checksum':'abc','source_verdict':None,'status':'indexed'}])
    output=tmp_path/'out/status.md'
    publish_status(s,output)
    text=output.read_text()
    assert 'head-one' in text
    assert 'unknown' in text
    assert 'latest approved strategy' in text
