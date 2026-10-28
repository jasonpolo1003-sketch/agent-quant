from data_library import refresh


def test_cli_reports_real_results_and_nonzero_failure(tmp_path, monkeypatch, capsys):
    from data_library.core import Library
    monkeypatch.setattr(Library, 'refresh', lambda self, sid: {'id': sid, 'ok': sid != 'UNRATE', 'error': None if sid != 'UNRATE' else 'Network unavailable'})
    assert refresh.main(['--data-dir', str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert 'CPIAUCSL' in output and 'FEDFUNDS' in output
    assert 'Network unavailable' in output
