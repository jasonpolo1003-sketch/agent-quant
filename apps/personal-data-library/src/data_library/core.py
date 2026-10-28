
from io import BytesIO
import pandas as pd
import duckdb
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from .metadata import SERIES
from contextlib import contextmanager
from .locking import lock


def parse_csv(raw: bytes, series: str) -> pd.DataFrame:
    df = pd.read_csv(BytesIO(raw), na_values=['.'], keep_default_na=True)
    df = df.rename(columns={df.columns[0]: 'date', series: 'value'})[['date', 'value']]
    df['date'] = pd.to_datetime(df.date, errors='raise')
    df['value'] = pd.to_numeric(df.value, errors='raise')
    if df.date.isna().any() or (df.date.dt.day != 1).any() or df.date.duplicated().any():
        raise ValueError('Dates must be unique, non-null calendar month starts')
    if df.value.isin([float('inf'), -float('inf')]).any():
        raise ValueError('Infinite numeric value')
    df = df[df.date >= '1999-01-01'].sort_values('date').reset_index(drop=True)
    if df.empty or df.value.notna().sum() == 0:
        raise ValueError('No usable observations from January 1999')
    return df


def with_yoy(df):
    out = df.copy()
    previous = df.set_index('date').value.reindex(df.date - pd.DateOffset(years=1)).to_numpy()
    previous = pd.Series(previous, index=out.index).replace(0, float('nan'))
    out['yoy_pct'] = (out.value / previous - 1) * 100
    return out


def quality(df):
    months = pd.date_range(df.date.min(), df.date.max(), freq='MS')
    return {'missing_values': int(df.value.isna().sum()), 'missing_months': len(months.difference(df.date))}


def select_dates(df, start, end):
    return df[df.date.between(pd.Timestamp(start), pd.Timestamp(end))].reset_index(drop=True)


def csv_bytes(df):
    return BytesIO(df.to_csv(index=False, date_format='%Y-%m-%d').encode('utf-8'))


class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS datasets (id VARCHAR PRIMARY KEY, metadata JSON)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (id VARCHAR, attempted_at VARCHAR, metadata JSON)')
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (id VARCHAR, checksum VARCHAR, retrieved_at VARCHAR, metadata JSON, PRIMARY KEY(id, checksum))')
            db.execute('CREATE TABLE IF NOT EXISTS active_snapshots (id VARCHAR PRIMARY KEY, checksum VARCHAR)')
            for sid, meta in SERIES.items():
                db.execute('INSERT OR REPLACE INTO datasets VALUES (?, ?)', [sid, json.dumps(meta)])

    @contextmanager
    def connect(self):
        with lock(self.root, 'numerical'):
            db = duckdb.connect(str(self.root / 'catalog.duckdb'))
            try:
                yield db
            finally:
                db.close()

    def refresh(self, sid, fetcher=None):
        if fetcher is None:
            from .fred import fetch
            fetcher = fetch
        result = dict(id=sid, attempted_at=datetime.now(timezone.utc).isoformat(), ok=False, error=None)
        try:
            raw, url, modified = fetcher(sid)
            result['checksum'] = self.publish(sid, raw, url, modified)
            result['ok'] = True
        except Exception as exc:
            result['error'] = f'{type(exc).__name__}: {exc}'
        with self.connect() as db:
            db.execute('INSERT INTO attempts VALUES (?, ?, ?)', [sid, result['attempted_at'], json.dumps(result)])
        return result

    def attempts(self, sid):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT metadata FROM attempts WHERE id=? ORDER BY attempted_at DESC', [sid]).fetchall()]

    def catalog(self, search=''):
        with self.connect() as db:
            rows = db.execute('SELECT metadata FROM datasets ORDER BY id').fetchall()
        return [json.loads(r[0]) for r in rows if search.casefold() in r[0].casefold()]

    def versions(self, sid):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT s.metadata FROM snapshots s LEFT JOIN active_snapshots a ON s.id=a.id WHERE s.id=? ORDER BY (s.checksum=a.checksum) DESC NULLS LAST, s.retrieved_at DESC', [sid]).fetchall()]

    def publish(self, sid, raw, download_url, source_last_modified=None):
        meta = SERIES[sid]
        df = parse_csv(raw, sid)
        checksum = hashlib.sha256(raw).hexdigest()
        if any(r['checksum'] == checksum for r in self.versions(sid)):
            with self.connect() as db:
                db.execute('INSERT OR REPLACE INTO active_snapshots VALUES (?, ?)', [sid, checksum])
            return checksum
        # Unique staged names + atomic rename; DB pointer is committed only after both files exist.
        token = uuid4().hex
        raw_path = Path('raw') / sid / f'{checksum}-{token}.csv'
        clean_path = Path('clean') / sid / f'{checksum}-{token}.parquet'
        for relative in (raw_path, clean_path):
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
        staged_raw = (self.root / raw_path).with_suffix('.tmp')
        staged_clean = (self.root / clean_path).with_suffix('.tmp')
        try:
            with staged_raw.open('xb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            df.to_parquet(staged_clean, index=False)
            os.rename(staged_raw, self.root / raw_path)
            os.rename(staged_clean, self.root / clean_path)
            record = dict(meta, checksum=checksum, retrieved_at=datetime.now(timezone.utc).isoformat(), source_release_at=None, source_last_modified=source_last_modified, download_url=download_url, raw_path=raw_path.as_posix(), clean_path=clean_path.as_posix(), rows=len(df), observation_start=str(df.date.min().date()), observation_end=str(df.date.max().date()), quality=quality(df), transformation_version='1-calendar-yoy', latest_vintage_warning='Latest-available history; revisions and publication delays make this unsuitable for point-in-time backtests.')
            with self.connect() as db:
                db.execute('BEGIN TRANSACTION')
                db.execute('INSERT INTO snapshots VALUES (?, ?, ?, ?)', [sid, checksum, record['retrieved_at'], json.dumps(record)])
                db.execute('INSERT OR REPLACE INTO active_snapshots VALUES (?, ?)', [sid, checksum])
                db.execute('COMMIT')
        finally:
            staged_raw.unlink(missing_ok=True)
            staged_clean.unlink(missing_ok=True)
        return checksum

    def load(self, sid, checksum=None):
        records = self.versions(sid)
        record = next((r for r in records if checksum is None or r['checksum'] == checksum), None)
        if record is None:
            return pd.DataFrame(columns=['date', 'value'])
        with self.connect() as db:
            return db.execute('SELECT * FROM read_parquet(?) ORDER BY date', [str(self.root / record['clean_path'])]).df()
