"""Offline operational integrity and paired-catalog backup, no source fetches."""
from pathlib import Path
import shutil
import sqlite3
import time
from .intake_store import IntakeStore,digest
from .locking import lock


def verify(root, inbox=None):
    store=IntakeStore(root)
    errors=[]
    receipts=[]
    with store.connect() as db:
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity!='ok': errors.append(integrity)
        orphan_versions=db.execute('SELECT count(*) FROM versions WHERE item_id NOT IN (SELECT id FROM items)').fetchone()[0]
        if orphan_versions: errors.append('Unowned version rows')
    for item in store.items():
        for version in store.versions(item['id']):
            try:
                raw=store.read_version(version)
                receipt={k:version[k] for k in ('seq','checksum','retained_path','captured_at','observed_mtime')}
                captured_source = version.get('source_path')
                receipt.update(item_id=item['id'], source_alias=version.get('source_alias'),
                               source_path=captured_source, current_source_alias=item['root'],
                               current_source_path=item['path'],
                               provenance_status='recorded_at_capture' if captured_source is not None else 'unknown_legacy',
                               bytes=len(raw), evidence_status=item['evidence_status'])
                receipts.append(receipt)
            except (ValueError,OSError) as exc:
                errors.append(f"{item['id']} version {version['seq']}: {exc}")
        if inbox and item['available']:
            from .intake_scan import safe_path
            try:
                path,info=safe_path(inbox,item['path'])
                current=digest(path.read_bytes())
                if current != store.versions(item['id'])[0]['checksum']:
                    errors.append(f"{item['id']}: source changed; rescan current saved version")
            except (ValueError,OSError) as exc: errors.append(str(exc))
    artifacts=store.state('quant_catalog') or []
    for a in artifacts:
        if a['status']!='indexed': errors.append(f"Blocked artifact {a['id']}: {a.get('error')}")
    return {'ok':not errors,'checked_at':time.time(),'items':len(store.items()),'versions':len(receipts),
            'receipts':receipts,'artifacts':artifacts,'errors':errors,'offline':True,
            'retained_bytes':sum(r['bytes'] for r in receipts),'health':store.health()}


def backup(root,target):
    root,target=Path(root),Path(target)
    if target.exists() or target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Use a new isolated backup directory outside source')
    with lock(root,'worker',timeout=2), lock(root,'numerical',timeout=2):
        target.mkdir(parents=True)
        # All intake writes occur under worker lock; SQLite backup includes committed WAL.
        with sqlite3.connect(root/'intake.sqlite') as source, sqlite3.connect(target/'intake.sqlite') as dest:
            source.backup(dest)
        for name in ('research','raw','clean'):
            if (root/name).exists(): shutil.copytree(root/name,target/name)
        if (root/'catalog.duckdb').exists():
            import duckdb
            db=duckdb.connect(str(root/'catalog.duckdb'))
            try: db.execute('CHECKPOINT')
            finally: db.close()
            shutil.copy2(root/'catalog.duckdb',target/'catalog.duckdb')
    return verify(target)
