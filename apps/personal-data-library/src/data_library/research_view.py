"""Content-only research catalog UI; the numerical workspace stays unchanged."""
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import streamlit as st
from .intake_store import IntakeStore


def obsidian_link(item, config):
    if not config.get('obsidian_vault') or not config.get('obsidian_inbox'):
        return None
    return 'obsidian://open?vault=' + quote(config['obsidian_vault'], safe='') + '&file=' + quote(config['obsidian_inbox'].rstrip('/') + '/' + item['path'], safe='')


def render():
    root = Path(os.environ.get('PDL_DATA_DIR', Path(__file__).resolve().parents[2] / 'data'))
    store = IntakeStore(root)
    st.subheader('Research library')
    if st.button('Process inbox now'):
        from .worker import load_config, run_once
        try:
            result = run_once(load_config(), notes_only=True)
            st.json(result)
        except (ValueError, OSError) as exc:
            st.error(f'Manual intake failed: {exc}. Inspect config and retry; original notes are unchanged.')
    st.info('Organized ≠ verified. This view cannot promote a strategy, execute notes, fetch sources, or run backtests. Quant remains authoritative.')
    search = st.text_input('Search research notes', placeholder='Question, strategy, title or source')
    columns = st.columns(4)
    process = columns[0].selectbox('Processing status', ['All', 'organized', 'needs_review', 'failed'])
    evidence = columns[1].selectbox('Evidence status', ['All', 'unverified', 'linked_to_existing_review', 'conflicting', 'unavailable'])
    strategy = columns[2].text_input('Strategy ID filter')
    research = columns[3].text_input('Research question filter')
    all_items = store.items(search)
    ctype, csource = st.columns(2)
    note_type = ctype.selectbox('Research type', ['All'] + sorted({i['metadata'].get('type', 'research_note') for i in all_items}))
    note_source = csource.selectbox('Research source', ['All'] + sorted({u for i in all_items for u in i['metadata'].get('source_urls', [])}))
    rows = [i for i in all_items if (note_type == 'All' or i['metadata'].get('type', 'research_note') == note_type)
            and (note_source == 'All' or note_source in i['metadata'].get('source_urls', [])) and (process == 'All' or i['status'] == process)
            and (evidence == 'All' or i['evidence_status'] == evidence)
            and strategy.casefold() in str(i['metadata'].get('strategy_id') or '').casefold()
            and research.casefold() in str(i['metadata'].get('research_id') or '').casefold()]
    artifacts = store.state('quant_catalog') or []
    if not rows:
        st.info('No research notes match. Save an opted-in Markdown note and process the inbox twice after saving.')
    else:
        item_id = st.selectbox('Research note', [i['id'] for i in rows], format_func=lambda v: next(i['metadata'].get('title', i['path']) for i in rows if i['id']==v))
        item = next(i for i in rows if i['id'] == item_id)
        st.caption(f"Processing: {item['status']} · Evidence: {item['evidence_status']} · {item['version_count']} retained versions · Source available: {bool(item['available'])}")
        st.text(f"Original source: {item['root']}/{item['path']}")
        from .worker import load_config
        try:
            source_link = obsidian_link(item, load_config())
        except (ValueError, OSError):
            source_link = None
        if source_link:
            st.link_button('Open original in Obsidian', source_link)
        versions = store.versions(item_id)
        index = st.selectbox('Retained note version', range(len(versions)), format_func=lambda n: f"Version {len(versions)-n} · {datetime.fromtimestamp(versions[n]['captured_at'], timezone.utc).isoformat()} · {versions[n]['checksum'][:12]}")
        selected = versions[index]
        st.caption('Capture time is local UTC, not publication time. Stable saved versions only, not every keystroke.')
        try:
            raw = store.read_version(selected)
            st.code(raw.decode('utf-8-sig', errors='replace'), language='markdown', wrap_lines=True, height=300)
            if selected['metadata'].get('error'):
                st.warning('Needs review: ' + selected['metadata']['error'] + '. Invalid UTF-8 is replaced only in this preview; downloads preserve exact bytes.')
            st.download_button('Download retained Markdown', raw, file_name=f"{item_id}-v{len(versions)-index}.md", mime='text/markdown')
        except (ValueError, OSError) as exc:
            st.error(f'Integrity/read failure: {exc}; preserve files and investigate before retry.')
        with st.expander('Selected version provenance'):
            st.json(selected)
        meta = selected['metadata']
        for url in meta.get('source_urls', []):
            st.link_button('Original source (not fetched or verified)', url)
        blocked = [a for a in artifacts if a.get('status') != 'indexed']
        if blocked:
            st.warning('Blocked development references: ' + '; '.join(f"{a['id']}: {a.get('error', 'review required')}" for a in blocked))
        linked = [a for a in artifacts if a.get('status') == 'indexed' and ((a.get('strategy_id') and a['strategy_id']==meta.get('strategy_id')) or (a.get('research_id') and a['research_id']==meta.get('research_id')))]
        if not linked and (meta.get('strategy_id') or meta.get('research_id')):
            st.warning('Unresolved research/strategy reference: no explicit approved development artifact matches. No production record was created.')
        if linked:
            st.markdown('#### Linked development references')
            for a in linked:
                st.text(f"{a['id']} · {a.get('kind','unknown')} · {a.get('classification','unknown')} · source-reported verdict: {a.get('source_verdict','unknown')}")
                st.text(f"quant/{a['path']} · sha256 {a.get('checksum','unavailable')}")
                with st.expander('Reference provenance · ' + a['id']):
                    st.json(a)
        st.warning('Needed next action: review the original question and source-reported development evidence; resolve cost/rule/data gaps in Quant under its existing freeze. Linking does not validate the note, authorize held-out reads, or establish prop suitability.')
    with st.expander('Automation health & activity', expanded=True):
        st.caption('Manual mode available. Scheduling requires separate activation confirmation; server connectivity does not mean current verified data.')
        try:
            from .scheduling import status
            st.json(status())
        except ImportError:
            st.caption('Scheduler adapter not yet available; no task created by this view.')
        health = store.health()
        pending, review, failed = st.columns(3)
        pending.metric('Pending intake', health['pending_count'])
        review.metric('Needs review', health['needs_review_count'])
        failed.metric('Failed inputs', health['failed_count'])
        st.json(health)
        st.json({'FRED refresh state': store.state('fred_due') or 'Not yet checked by worker'})
        retained = list((root / 'research/raw').glob('*.md')) if (root / 'research/raw').exists() else []
        st.caption(f"Retained blobs: {len(retained)} · {sum(p.stat().st_size for p in retained)} bytes. No automatic deletion; review storage growth manually.")
        st.code('uv run pdl-intake run-once --notes-only\nuv run pdl-intake status\nuv run pdl-intake retry ITEM_ID_OR_FILENAME', language='text')
