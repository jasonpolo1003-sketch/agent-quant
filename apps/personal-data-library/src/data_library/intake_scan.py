"""Bounded direct-child scan: no traversal, hydration, or URL following."""
import json
import os
from pathlib import Path
import stat
import time

MAX_BYTES = 2 * 1024 * 1024


def safe_path(root, relative):
    root = Path(root)
    path = root / relative
    if Path(relative).name != relative or root.is_symlink() or root.is_junction():
        raise ValueError('Only direct children of the opted-in root are supported')
    # Reject reparse points on the whole root chain (junctions included).
    for part in [path, *path.parents]:
        if part.exists() and (part.is_symlink() or part.is_junction()):
            raise ValueError('Symlink/junction/reparse path blocked')
    if path.resolve().parent != root.resolve():
        raise ValueError('Path escape blocked')
    info = path.stat()
    attrs = getattr(info, 'st_file_attributes', 0)
    if attrs & (0x1000 | 0x40000 | 0x400000):
        raise OSError('OneDrive placeholder/offline input: save locally and retry')
    if attrs & 0x400:
        raise ValueError('Reparse input blocked')
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Not a regular file')
    return path, info


def signature(info):
    return f'{info.st_size}:{info.st_mtime_ns}'


def scan(store, inbox, stability=1.0, cap=100, dry_run=False):
    inbox = Path(inbox)
    result = {'queued': 0, 'deferred': 0, 'candidates': [], 'limit': cap}
    if not inbox.is_dir() or inbox.is_symlink() or inbox.is_junction():
        raise ValueError('Opt-in inbox missing or unsafe; create/configure it explicitly')
    # Paths only. Content is never opened by discovery.
    entries = sorted(p.name for p in inbox.iterdir())
    result['backlog_candidates'] = max(0, len(entries) - cap)
    if dry_run:
        result['candidates'] = entries[:cap]
        return result
    with store.connect() as db:
        existing = list(db.execute("SELECT id,path FROM items WHERE root='inbox'"))
        for row in existing:
            db.execute('UPDATE items SET available=? WHERE id=?', (int(row['path'] in entries), row['id']))
    # Rotate bounded batches so large folders do not starve later names.
    offset = store.state('scan_offset') or 0
    names = (entries[offset:] + entries[:offset])[:cap]
    store.state('scan_offset', (offset + cap) % max(len(entries), 1))
    for name in names:
        try:
            path, info = safe_path(inbox, name)
            if path.suffix.lower() != '.md':
                raise ValueError('unsupported attachment: Markdown only; review manually')
            sig = signature(info)
            now = time.time()
            with store.connect() as db:
                old = db.execute('SELECT * FROM observations WHERE path=?', (name,)).fetchone()
                if not old or old['signature'] != sig:
                    db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?)', (name, sig, now))
                    result['deferred'] += 1
                    continue
                if now - old['seen'] < stability:
                    result['deferred'] += 1
                    continue
                job = db.execute('SELECT status FROM jobs WHERE path=?', (name,)).fetchone()
                state_key = 'processed:' + name
                prior = store.state(state_key)
                owned = db.execute("SELECT 1 FROM items WHERE root='inbox' AND path=?", (name,)).fetchone()
                if (prior != sig or not owned) and (not job or job[0] not in ('processing', 'queued', 'retry_wait', 'needs_review')):
                    db.execute("INSERT OR REPLACE INTO jobs(path,status) VALUES(?,'queued')", (name,))
                    result['queued'] += 1
        except (OSError, ValueError) as exc:
            result['deferred'] += 1
            # Keep one visible review record per rejected path, without opening it.
            with store.connect() as db:
                db.execute("INSERT OR REPLACE INTO jobs(path,status,error) VALUES(?,'needs_review',?)", (name, str(exc)))
            store.event('needs_review', f'{name}: {exc}')
    store.state('last_scan', {'at': time.time(), **result})
    return result
