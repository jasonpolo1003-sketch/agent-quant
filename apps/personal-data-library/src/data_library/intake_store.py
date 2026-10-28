"""Local operational catalog. Never a Quant trial ledger."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4
from contextlib import contextmanager


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class IntakeStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, root TEXT, path TEXT,
              available INTEGER DEFAULT 1, status TEXT, evidence_status TEXT DEFAULT 'unverified',
              error TEXT, UNIQUE(root,path));
            CREATE TABLE IF NOT EXISTS versions(seq INTEGER PRIMARY KEY, item_id TEXT, checksum TEXT,
              retained_path TEXT, captured_at REAL, observed_mtime REAL, metadata TEXT);
            CREATE TABLE IF NOT EXISTS observations(path TEXT PRIMARY KEY, signature TEXT, seen REAL);
            CREATE TABLE IF NOT EXISTS jobs(path TEXT PRIMARY KEY, status TEXT, attempts INTEGER DEFAULT 0,
              due REAL DEFAULT 0, lease REAL DEFAULT 0, error TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, at REAL, kind TEXT, detail TEXT);
            CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, metadata TEXT);
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(versions)')}
            for column in ('source_alias', 'source_path'):
                if column not in columns:
                    db.execute(f'ALTER TABLE versions ADD COLUMN {column} TEXT')
            # Legacy capture paths cannot be inferred from mutable current locations.
            db.execute('PRAGMA user_version=2')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / 'intake.sqlite', timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA busy_timeout=5000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, kind, detail):
        with self.connect() as db:
            db.execute('INSERT INTO events(at,kind,detail) VALUES(?,?,?)', (time.time(), kind, str(detail)))

    def state(self, key, value=None):
        with self.connect() as db:
            if value is not None:
                db.execute('INSERT OR REPLACE INTO state VALUES(?,?)', (key, json.dumps(value)))
            row = db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def retain(self, alias, path, raw, metadata, mtime):
        checksum = digest(raw)
        relative = f'research/raw/{checksum}.md'
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if digest(target.read_bytes()) != checksum:
                raise ValueError('Retained blob integrity mismatch: manual review required')
        else:
            staged = target.with_suffix(f'.{uuid4().hex}.tmp')
            try:
                with staged.open('xb') as f:
                    f.write(raw)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(staged, target)
            finally:
                staged.unlink(missing_ok=True)
        with self.connect() as db:
            row = db.execute('SELECT id FROM items WHERE root=? AND path=?', (alias, path)).fetchone()
            item = row[0] if row else 'ITEM-' + uuid4().hex[:16]
            if not row:
                db.execute('INSERT INTO items(id,root,path,status) VALUES(?,?,?,?)', (item, alias, path, 'organized'))
            latest = db.execute('SELECT checksum FROM versions WHERE item_id=? ORDER BY seq DESC LIMIT 1', (item,)).fetchone()
            if not latest or latest[0] != checksum:
                db.execute('INSERT INTO versions(item_id,checksum,retained_path,captured_at,observed_mtime,metadata,source_alias,source_path) VALUES(?,?,?,?,?,?,?,?)',
                           (item, checksum, relative, time.time(), mtime, json.dumps(metadata), alias, path))
            db.execute("UPDATE items SET available=1,status=?,error=NULL WHERE id=?", (metadata.get('processing_status', 'organized'), item))
        return item

    def items(self, search=''):
        with self.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM items ORDER BY path')]
        for row in rows:
            versions = self.versions(row['id'])
            row['version_count'] = len(versions)
            row['metadata'] = versions[0]['metadata'] if versions else {}
        return [r for r in rows if search.casefold() in json.dumps(r, ensure_ascii=False).casefold()]

    def versions(self, item):
        with self.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM versions WHERE item_id=? ORDER BY seq DESC', (item,))]
        for row in rows:
            row['metadata'] = json.loads(row['metadata'])
        return rows

    def read_version(self, version):
        raw = (self.root / version['retained_path']).read_bytes()
        if digest(raw) != version['checksum']:
            raise ValueError('Retained blob integrity mismatch')
        return raw

    def health(self):
        with self.connect() as db:
            queue = [dict(r) for r in db.execute('SELECT * FROM jobs ORDER BY path')]
            return {'queue': queue,
                    'pending_count': sum(r['status'] in ('queued','processing','retry_wait') for r in queue),
                    'needs_review_count': sum(r['status']=='needs_review' for r in queue),
                    'failed_count': sum(r['status']=='failed' for r in queue),
                    'events': [dict(r) for r in db.execute('SELECT * FROM events ORDER BY id DESC LIMIT 50')],
                    'last_scan': self.state('last_scan'), 'last_success': self.state('last_success')}
