from streamlit.testing.v1 import AppTest


def test_blocked_artifact_not_presented_as_linked_development_evidence(tmp_path,monkeypatch):
    from data_library.intake_store import IntakeStore
    s=IntakeStore(tmp_path)
    s.retain('inbox','a.md',b'# A',{'title':'A','strategy_id':'SC-X'},1)
    s.state('quant_catalog',[{'id':'BAD','strategy_id':'SC-X','status':'blocked','path':'locked.md','source_verdict':'SHOULD NOT DISPLAY','error':'not reviewed'}])
    monkeypatch.setenv('PDL_DATA_DIR',str(tmp_path))
    app=AppTest.from_string('from data_library.research_view import render\nrender()').run()
    assert not any('SHOULD NOT DISPLAY' in t.value for t in app.text)
    assert any('Unresolved' in w.value for w in app.warning)
    assert any('blocked' in w.value.lower() for w in app.warning)


def test_type_and_source_filters_are_available(tmp_path,monkeypatch):
    from data_library.intake_store import IntakeStore
    s=IntakeStore(tmp_path)
    s.retain('inbox','a.md',b'# A',{'title':'A','type':'research_note','source_urls':['https://example.org']},1)
    monkeypatch.setenv('PDL_DATA_DIR',str(tmp_path))
    app=AppTest.from_string('from data_library.research_view import render\nrender()').run()
    assert any(b.label=='Research type' for b in app.selectbox)
    assert any(b.label=='Research source' for b in app.selectbox)
