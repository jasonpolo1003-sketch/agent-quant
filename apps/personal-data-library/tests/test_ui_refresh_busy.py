def test_busy_refresh_never_replays_cached_success(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from data_library import ui_library
    from data_library.locking import Busy
    monkeypatch.setattr(ui_library,'st',SimpleNamespace(session_state={},warning=lambda *a:None,info=lambda *a:None,stop=lambda:None))
    calls=[]
    def refresh(self,sid):
        calls.append(sid)
        if len(calls)>1: raise Busy('update in progress')
        return {'id':sid,'ok':True}
    monkeypatch.setattr(ui_library.Library,'refresh',refresh)
    lib=ui_library.UILibrary(tmp_path)
    assert lib.refresh('UNRATE')['ok'] is True
    result=lib.refresh('UNRATE')
    assert result['ok'] is False
    assert result['deferred'] is True
