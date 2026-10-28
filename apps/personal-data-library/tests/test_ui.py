from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / 'app.py'


def test_dashboard_offline_search_dates_details_and_export(monkeypatch, economic_fixture):
    import requests
    monkeypatch.setattr(requests, 'get', lambda *a, **k: (_ for _ in ()).throw(AssertionError('Unexpected network request')))
    at = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not at.exception
    assert at.title[0].value == 'Personal Data Library'
    assert len(at.get('plotly_chart')) == 3
    assert at.sidebar.date_input[0].value.isoformat() == '2000-01-01'
    at.sidebar.radio[0].set_value('Library & explore').run()
    assert not at.exception
    at.sidebar.text_input[0].set_value('inflation').run()
    assert at.selectbox[0].options == ['Consumer Price Index · CPIAUCSL']
    assert len(at.get('download_button')) == 1
    assert any('Bureau of Labor Statistics' in x.value for x in at.markdown)
    assert 'yoy_pct' in at.dataframe[0].value.columns
    at.sidebar.text_input[0].set_value('no-such-series').run()
    assert any('No datasets match' in x.value for x in at.info)
    assert not at.exception


def test_ui_date_selection_and_failed_refresh_are_honest(tmp_path, monkeypatch, economic_fixture):
    from datetime import date
    from data_library.core import Library, select_dates, with_yoy
    from data_library.metadata import SERIES
    import requests
    cached = economic_fixture
    local = Library(tmp_path)
    for sid in SERIES:
        row = cached.versions(sid)[0]
        local.publish(sid, (cached.root / row['raw_path']).read_bytes(), row['download_url'])
    monkeypatch.setenv('PDL_DATA_DIR', str(tmp_path))
    def offline(*a, **k):
        raise requests.ConnectionError('Offline verification')
    monkeypatch.setattr(requests, 'get', offline)
    at = AppTest.from_file(str(APP), default_timeout=15).run()
    at.sidebar.radio[0].set_value('Library & explore').run()
    at.sidebar.date_input[0].set_value(date(2000, 1, 1)).run()
    at.sidebar.date_input[1].set_value(date(2000, 3, 1)).run()
    expected = select_dates(with_yoy(local.load('CPIAUCSL')), '2000-01-01', '2000-03-01')
    assert at.dataframe[0].value.equals(expected)
    at.button[0].click().run()
    assert any('Offline verification' in x.value for x in at.error)
    assert at.dataframe[0].value.equals(expected)
    assert len(local.versions('CPIAUCSL')) == 1
    assert not at.exception
