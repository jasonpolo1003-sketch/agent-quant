"""One generated page; user edits block overwrite. No bidirectional sync."""
import json
import os
from pathlib import Path
from uuid import uuid4
from .intake_store import digest


def atomic_write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_suffix('.' + uuid4().hex + '.tmp')
    try:
        stage.write_bytes(raw)
        os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def publish_status(store, output):
    output = Path(output)
    items = store.items()
    artifacts = store.state('quant_catalog') or []
    export = {'schema': 1, 'items': items, 'artifacts': artifacts,
              'limits': 'Organization is not verification; no promotion, backtest, held-out access or trading.'}
    exported = json.dumps(export, indent=2, ensure_ascii=False).encode('utf-8')
    export_path = store.root / 'research/exports/research-catalog.json'
    if not export_path.exists() or export_path.read_bytes() != exported:
        atomic_write(export_path, exported)
    content = '# Research intake status\n\n<!-- managed: pdl-research-intake-v1 -->\n\n'
    content += 'Derived catalog snapshot, not Quant governance. Organized does not mean verified.\n\n'
    content += 'Scheduler is not activated by intake. Use `uv run pdl-intake schedule status` for live readback.\n\n'
    content += '| Note | Processing | Evidence | Versions | Next action |\n|---|---|---|---:|---|\n'
    for item in items:
        title = item['metadata'].get('title', item['path']).replace('|', '/').replace('\n', ' ')
        content += f"| {title} | {item['status']} | {item['evidence_status']} | {item['version_count']} | Review original and linked development metadata; no execution authorized |\n"
    content += '\n## Explicit development references\n\n'
    content += 'Historical documents can lag repository HEAD. Reference checksums and inspected revisions are provenance only; no latest approved strategy is inferred. Quant remains authoritative.\n\n'
    for artifact in artifacts:
        content += f"- {artifact['id']}: `{artifact['path']}` — {artifact.get('source_verdict') or 'unknown'}; status {artifact.get('status', 'unknown')}; inspected revision `{artifact.get('revision', 'unknown')}`; sha256 `{artifact.get('checksum') or 'unavailable'}`\n"
    content += '\n## Boundaries and recovery\n\nOnly saved direct-child UTF-8 Markdown in Research Inbox is captured. Other vault notes and Automation outputs are excluded. Stable saved versions, not every keystroke, are retained. Sources and URLs are never fetched from notes.\n\nRun `uv run pdl-intake run-once --notes-only` twice after saving (stability observation then capture). Inspect `uv run pdl-intake status`; fix a rejected input then `uv run pdl-intake retry ITEM_ID_OR_FILENAME`. See [[Automation/README|automation guide]].\n'
    body_hash = digest(content.encode('utf-8'))
    previous = store.state('managed_status')
    if output.exists():
        actual = digest(output.read_bytes())
        if not previous or actual != previous.get('file_hash'):
            store.event('status_conflict', 'Managed page edited/unowned. Preserve it; review and move aside before regeneration.')
            return {'status': 'conflict', 'path': str(output)}
        if previous.get('body_hash') == body_hash:
            return {'status': 'unchanged', 'path': str(output)}
    prior = previous.get('file_hash', 'none') if previous else 'none'
    raw = (content + f'\n<!-- prior checksum: {prior} -->\n').encode('utf-8')
    atomic_write(output, raw)
    store.state('managed_status', {'body_hash': body_hash, 'file_hash': digest(raw)})
    return {'status': 'written', 'path': str(output), 'checksum': digest(raw)}
