"""Content-only UTF-8 processing. No fetches, subprocesses, or Quant imports."""
from pathlib import Path
import time
import yaml
from .intake_scan import MAX_BYTES, safe_path, signature
from .intake_store import digest


def metadata(raw, name):
    text = raw.decode('utf-8-sig')
    front = {}
    if text.startswith('---\n') or text.startswith('---\r\n'):
        lines = text.splitlines()
        try:
            end = lines[1:].index('---') + 1
        except ValueError:
            raise ValueError('Unclosed YAML frontmatter')
        header = '\n'.join(lines[1:end])
        if len(header) > 16384 or header.count('&') + header.count('*') > 16:
            raise ValueError('Metadata too large/complex')
        front = yaml.safe_load(header) or {}
        if not isinstance(front, dict):
            raise ValueError('Frontmatter must be a mapping')
    out = {'title': Path(name).stem, 'type': 'research_note', 'parse_version': '1',
           'source_urls': [], 'research_id': None, 'strategy_id': None,
           'source_publication_at': None, 'evidence_status': 'unverified'}
    for key in ('title', 'research_id', 'strategy_id'):
        if key in front:
            if not isinstance(front[key], str) or len(front[key]) > 500:
                raise ValueError(f'Invalid {key}')
            out[key] = front[key]
    urls = front.get('source_urls', [])
    if not isinstance(urls, list) or len(urls) > 30 or any(not isinstance(u, str) or len(u)>2048 or not u.startswith(('https://', 'http://')) for u in urls):
        raise ValueError('source_urls must be a bounded HTTP(S) list; never fetched')
    out['source_urls'] = urls
    return out


def drain(store, inbox, cap=100, deadline=None):
    processed = 0
    with store.connect() as db:
        db.execute("UPDATE jobs SET status='retry_wait',due=0,error='Expired processing lease; retrying' WHERE status='processing' AND lease<?", (time.time(),))
    for _ in range(cap):
        if deadline is not None and time.monotonic() >= deadline:
            break
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM jobs WHERE status IN ('queued','retry_wait') AND due<=? ORDER BY path LIMIT 1", (time.time(),)).fetchone()
            if not row:
                break
            name = row['path']
            db.execute("UPDATE jobs SET status='processing',lease=?,attempts=attempts+1 WHERE path=?", (time.time()+120, name))
        try:
            path, before = safe_path(inbox, name)
            if before.st_size > MAX_BYTES:
                raise ValueError('Note exceeds 2 MiB; split or review manually')
            expected = signature(before)
            with store.connect() as db:
                obs = db.execute('SELECT signature FROM observations WHERE path=?', (name,)).fetchone()
            if not obs or obs[0] != expected:
                raise OSError('Input changed since stable observation; rescan')
            raw = path.read_bytes()
            _, after = safe_path(inbox, name)
            if signature(after) != expected or len(raw) != before.st_size:
                raise OSError('Input changed during capture; rescan')
            try:
                meta = metadata(raw, name)
            except (ValueError, UnicodeError, yaml.YAMLError) as exc:
                # A malformed note is still user evidence: keep exact bounded bytes,
                # but never interpret malformed metadata or execute constructors.
                meta = {'title': Path(name).stem, 'type': 'research_note', 'parse_version': '1',
                        'processing_status': 'needs_review', 'evidence_status': 'unverified',
                        'source_urls': [], 'error': str(exc)}
            checksum = digest(raw)
            # A unique missing occurrence and a unique new matching file preserve rename identity.
            with store.connect() as db:
                known = db.execute("SELECT id FROM items WHERE root='inbox' AND path=?", (name,)).fetchone()
                missing = list(db.execute('''SELECT i.id, i.path FROM items i JOIN versions v ON v.item_id=i.id
                    WHERE i.available=0 AND v.seq=(SELECT max(seq) FROM versions WHERE item_id=i.id)
                    AND v.checksum=?''', (checksum,)))
                matches = []
                for candidate in Path(inbox).iterdir():
                    if candidate.suffix.lower() == '.md' and candidate.name != name:
                        # Use stable observation signatures only; do not open other files.
                        if candidate.stat().st_size == len(raw):
                            matches.append(candidate.name)
                if not known and len(missing) == 1 and not matches:
                    old_path = missing[0]['path']
                    db.execute('UPDATE items SET path=?,available=1 WHERE id=?', (name, missing[0]['id']))
                    db.execute('DELETE FROM state WHERE key=?', ('processed:' + old_path,))
                    db.execute('DELETE FROM observations WHERE path=?', (old_path,))
                    db.execute("UPDATE jobs SET status='superseded',lease=0 WHERE path=?", (old_path,))
                    db.execute('INSERT INTO events(at,kind,detail) VALUES(?,?,?)',
                               (time.time(), 'renamed', f"{missing[0]['id']}: {old_path} -> {name}"))
                elif not known and missing:
                    meta['processing_status'] = 'needs_review'
                    store.event('needs_review', f'{name}: ambiguous rename/copy; separate occurrence retained')
            item = store.retain('inbox', name, raw, meta, before.st_mtime)
            store.state('processed:' + name, expected)
            with store.connect() as db:
                db.execute("UPDATE jobs SET status=?,lease=0,error=? WHERE path=?", (meta.get('processing_status', 'organized'), meta.get('error'), name))
            store.state('last_success', {'at': time.time(), 'item_id': item})
            store.event('organized', f'{item}: {name} sha256={checksum}')
            processed += 1
        except (ValueError, UnicodeError, yaml.YAMLError) as exc:
            with store.connect() as db:
                db.execute("UPDATE jobs SET status='needs_review',error=?,lease=0 WHERE path=?", (str(exc), name))
            store.event('needs_review', f'{name}: {exc}')
        except OSError as exc:
            status = 'failed' if row['attempts'] + 1 >= 3 else 'retry_wait'
            with store.connect() as db:
                db.execute('UPDATE jobs SET status=?,error=?,lease=0,due=? WHERE path=?', (status, str(exc), time.time()+60*(2**row['attempts']), name))
            store.event(status, f'{name}: {exc}')
    return {'processed': processed}
