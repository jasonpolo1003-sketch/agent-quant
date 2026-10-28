"""Opt-in prop-research usefulness acceptance; requires local SC-FUT-0008 note."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from data_library.intake_store import IntakeStore

ROOT = Path(__file__).resolve().parents[1]
store = IntakeStore(os.environ.get('PDL_DATA_DIR', ROOT / 'data'))
items = store.items('SC-FUT-0008')
assert len(items) == 1, 'Explicitly opt in the prop research question note first'
version = store.versions(items[0]['id'])[0]
artifacts = [a for a in store.state('quant_catalog') if a.get('strategy_id') == 'SC-FUT-0008']
assert len(artifacts) == 2
assert all(a['status'] == 'indexed' for a in artifacts)
assert any(a.get('definition_status') == 'frozen' for a in artifacts)
assert any('FAILED' in (a.get('source_verdict') or '') for a in artifacts)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1100}, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(os.environ.get('PDL_BROWSER_URL','http://127.0.0.1:8501'), wait_until='networkidle')
    page.get_by_text('Research library', exact=True).first.click()
    search = page.get_by_role('textbox', name='Search research notes', exact=True)
    search.fill('SC-FUT-0008'); search.press('Enter')
    page.get_by_text('Linked development references', exact=True).wait_for()
    page.get_by_text('SC-FUT-0008-practice-review', exact=False).first.wait_for()
    text = page.locator('body').inner_text()
    assert 'frozen' in text and 'FAILED' in text and 'Evidence: unverified' in text
    assert 'prop cash-gate' in text
    with page.expect_download() as pending:
        page.get_by_text('Download retained Markdown', exact=True).click()
    path = ROOT/'reports/prop-research-retained.md'
    pending.value.save_as(str(path))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == version['checksum']
    page.get_by_role('heading',name='Research library',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(ROOT/'reports/prop-research-usefulness.png'),full_page=True)
    assert not errors, errors
    report = {'ok':True,'strategy':'SC-FUT-0008','definition_status':'frozen','source_reported_practice_outcome':'FAILED','note_evidence_status':'unverified','linked_references':[a['id'] for a in artifacts],'download_matches_retained_version':True,'new_backtest_executed':False,'page_errors':errors}
    (ROOT/'reports/prop-research-usefulness.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    browser.close()
