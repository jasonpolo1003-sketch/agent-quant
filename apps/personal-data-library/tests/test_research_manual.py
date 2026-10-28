def test_research_manual_button_uses_notes_only(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from data_library import worker
    monkeypatch.setenv('PDL_DATA_DIR',str(tmp_path))
    called=[]
    monkeypatch.setattr(worker,'load_config',lambda: {'data_dir':str(tmp_path)})
    monkeypatch.setattr(worker,'run_once',lambda config,notes_only=False: called.append(notes_only) or {'status':'ok','processed':0})
    app=AppTest.from_string('from data_library.research_view import render\nrender()').run()
    buttons=[b for b in app.button if b.label=='Process inbox now']
    assert buttons
    buttons[0].click().run()
    assert called == [True]
