from data_library import fred
import pytest


def test_official_download_validates_and_falls_back():
    calls = []
    class Response:
        headers = {'Last-Modified': 'publisher-header'}
        def __init__(self, content):
            self.content = content
        def raise_for_status(self):
            pass
    def get(url, **kwargs):
        assert 'headers' not in kwargs  # standard requests UA is accepted by this official endpoint
        calls.append(url)
        return Response(b'<html>blocked</html>' if len(calls) == 1 else b'observation_date,UNRATE\n1999-01-01,4.3\n')
    raw, url, modified = fred.fetch('UNRATE', get=get)
    assert len(calls) == 2
    assert '/graph/fredgraph.csv?' in calls[0]
    assert all(u.startswith('https://fred.stlouisfed.org/') for u in calls)
    assert b'4.3' in raw
    assert url == calls[-1]
    assert modified == 'publisher-header'
    with pytest.raises(ValueError):
        fred.fetch('../invalid', get=get)
