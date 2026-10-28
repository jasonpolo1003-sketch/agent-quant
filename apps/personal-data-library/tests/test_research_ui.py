from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_research_search_versions_preview_and_unresolved(tmp_path, monkeypatch):
    from data_library.intake_store import IntakeStore
    s = IntakeStore(tmp_path)
    item = s.retain('inbox', 'question.md', b'# Question\n<script>bad()</script>', {'title':'Integration question','strategy_id':'SC-missing'}, 1)
    s.retain('inbox', 'question.md', b'# Question\nSecond version', {'title':'Integration question','strategy_id':'SC-missing'}, 2)
    monkeypatch.setenv('PDL_DATA_DIR', str(tmp_path))
    app = AppTest.from_string('from data_library.research_view import render\nrender()').run()
    assert not app.exception
    assert any('Research library' in h.value for h in app.subheader)
    assert any('unverified' in c.value for c in app.caption)
    assert any('Unresolved' in w.value for w in app.warning)
    assert len(app.selectbox[-1].options) == 2
    app.selectbox[-1].select_index(1).run()
    assert '<script>bad()</script>' in app.code[0].value
    app.text_input[0].set_value('NO-MATCH').run()
    assert any('No research' in i.value for i in app.info)
    assert not app.exception
