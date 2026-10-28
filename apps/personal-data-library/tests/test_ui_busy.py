def test_dashboard_shows_busy_without_crashing(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from data_library.locking import Busy
    import data_library.core as core
    monkeypatch.setenv('PDL_DATA_DIR', str(tmp_path))
    def busy(*args, **kwargs): raise Busy('update in progress')
    monkeypatch.setattr(core.Library, '__init__', busy)
    app = AppTest.from_file('../app.py').run()
    assert not app.exception
    assert any('update in progress' in w.value for w in app.warning)
