"""Research UI acceptance against real opted-in retained versions, isolated Edge."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from data_library.intake_store import IntakeStore

ROOT=Path(__file__).resolve().parents[1]
store=IntakeStore(os.environ.get('PDL_DATA_DIR',ROOT/'data'))
items=store.items('RQ-INTEGRATION-WORKFLOW')
assert len(items)==1, 'Run the real opt-in manual intake before browser acceptance'
item=items[0]
versions=store.versions(item['id'])
assert len(versions)>=2, 'Real saved edit/version acceptance is required'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(os.environ.get('PDL_BROWSER_URL','http://127.0.0.1:8501'),wait_until='networkidle')
    page.get_by_text('Research library',exact=True).first.click()
    page.get_by_role('heading',name='Research library',exact=True).wait_for()
    search=page.get_by_role('textbox',name='Search research notes',exact=True)
    search.fill('RQ-INTEGRATION-WORKFLOW');search.press('Enter')
    page.get_by_text('Linked development references',exact=True).wait_for()
    page.get_by_text('Evidence: unverified',exact=False).wait_for()
    assert page.get_by_role('link',name='Original source (not fetched or verified)').get_attribute('href').startswith('https://chartschool.stockcharts.com/')
    assert page.get_by_role('link',name='Open original in Obsidian').get_attribute('href').startswith('obsidian://open')
    # Strategy filter and no-match state are real browser interactions.
    strategy=page.get_by_role('textbox',name='Strategy ID filter',exact=True)
    strategy.fill('NO-SUCH-STRATEGY');strategy.press('Enter')
    page.get_by_text('No research notes match.',exact=False).wait_for()
    strategy.fill('SC-0002');strategy.press('Enter')
    page.get_by_text('Download retained Markdown',exact=True).wait_for()
    for label, no_match in [('Processing status', 'needs_review'), ('Evidence status', 'conflicting')]:
        page.get_by_role('combobox',name=label,exact=True).click()
        page.get_by_role('option',name=no_match,exact=True).click()
        page.get_by_text('No research notes match.',exact=False).wait_for()
        page.get_by_role('combobox',name=label,exact=True).click()
        page.get_by_role('option',name='All',exact=True).click()
        page.get_by_text('Download retained Markdown',exact=True).wait_for()
    downloaded=[]
    for n,version in enumerate(versions):
        # Streamlit download/filter clicks can schedule a rerun after the visible
        # control returns; allow that rerun to settle before opening its menu.
        page.wait_for_timeout(1200)
        control=page.get_by_role('combobox',name='Retained note version',exact=True)
        control.click()
        page.get_by_role('option').filter(has_text=f'Version {len(versions)-n} ·').click()
        page.wait_for_timeout(800)
        with page.expect_download() as download_info:
            page.get_by_text('Download retained Markdown',exact=True).click()
        download=download_info.value
        target=ROOT/'reports'/f'browser-retained-v{len(versions)-n}.md'
        download.save_as(str(target))
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual==version['checksum'],(actual,version['checksum'])
        downloaded.append({'version':len(versions)-n,'checksum':actual,'file':str(target)})
    page.get_by_text('Automation health & activity',exact=True).wait_for()
    page.screenshot(path=str(ROOT/'reports/intake-research-library.png'),full_page=True)
    page.get_by_role('heading',name='Research library',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(ROOT/'reports/intake-research-top.png'))
    search.fill('NO-MATCH-RESEARCH');search.press('Enter')
    page.get_by_text('No research notes match.',exact=False).wait_for()
    page.screenshot(path=str(ROOT/'reports/intake-empty-state.png'),full_page=True)
    assert not errors,errors
    report={'browser':'isolated headless Edge','real_item_id':item['id'],'downloads':downloaded,'search':True,'strategy_filter':True,'source_links':True,'unverified_visible':True,'activity_visible':True,'empty_state':True,'errors':errors}
    (ROOT/'reports/intake-browser-acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    browser.close()
