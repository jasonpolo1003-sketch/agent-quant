"""Official FRED download adapter."""
import requests
from .metadata import SERIES
from .core import parse_csv


def fetch(sid, get=None):
    if sid not in SERIES:
        raise ValueError('Unsupported series identifier')
    get = get or requests.get
    urls = [f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=1999-01-01', f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}']
    failures = []
    for url in urls:
        try:
            response = get(url, timeout=(5, 20))
            response.raise_for_status()
            parse_csv(response.content, sid)
            return response.content, url, response.headers.get('Last-Modified')
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            failures.append(f'{url}: {type(exc).__name__}: {exc}')
    raise RuntimeError('Official CSV download failed: ' + '; '.join(failures) + '. API alternative requires a free user-provided FRED key; see README.')
