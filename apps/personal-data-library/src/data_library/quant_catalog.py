"""Explicit reviewed development references only; never import Quant modules."""
from pathlib import Path
import re
import subprocess
from .intake_store import digest


def catalog(root, entries, revision=None):
    root = Path(root)
    if revision is None:
        proc = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10)
        revision = proc.stdout.strip() if proc.returncode == 0 else 'unknown'
    results = []
    for entry in entries[:100]:
        out = dict(entry, root_alias='quant', revision=revision, status='blocked', checksum=None)
        try:
            relative = Path(entry['path'])
            forbidden = ('held-out', 'held_out', 'holdout', 'locked', 'exam')
            if (entry.get('reviewed') is not True or entry.get('classification') != 'development'
                or entry.get('kind') not in ('report', 'strategy_card', 'dataset_manifest', 'rulebook_metadata')
                or not re.fullmatch('[0-9a-f]{64}', entry.get('sha256', ''))
                or relative.is_absolute() or '..' in relative.parts or relative.suffix.lower() not in ('.md', '.json')
                or any(word in relative.as_posix().lower() for word in forbidden)):
                raise ValueError('Not an explicit reviewed development metadata identity/type')
            path = root / relative
            for part in [path, *path.parents]:
                if part.exists() and (part.is_symlink() or part.is_junction()):
                    raise ValueError('Symlink/junction blocked')
            if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size > 2*1024*1024:
                raise ValueError('Root/size boundary')
            attrs = getattr(path.stat(), 'st_file_attributes', 0)
            if attrs & (0x400 | 0x1000 | 0x40000 | 0x400000):
                raise ValueError('Unavailable/reparse input blocked')
            checksum = digest(path.read_bytes())
            if checksum != entry['sha256']:
                raise ValueError('Changed since explicit review; re-review manifest before exposing')
            # No decoding required. Displayed identifiers/verdict are attributed reviewed metadata.
            out.update(status='indexed', checksum=checksum, error=None)
            for key in ('source_run_id', 'ledger_location', 'data_id', 'code_id', 'spec_id', 'source_verdict', 'diagnostic_type'):
                out.setdefault(key, None)
        except (ValueError, OSError, KeyError) as exc:
            out['error'] = str(exc)
        results.append(out)
    return results


def update(store, root, entries):
    results = catalog(root, entries)
    store.state('quant_catalog', results)
    with store.connect() as db:
        import json
        for row in results:
            db.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?)', (row['id'], json.dumps(row)))
    store.event('quant_catalog', f'{len(results)} explicitly reviewed references; no engine/ledger writes or verdict inference')
    return results
