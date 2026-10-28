"""Manual acceptance driver using a separate headless browser, no user profile."""
import json
import os
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1100}, accept_downloads=True)
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(os.environ.get('PDL_BROWSER_URL','http://127.0.0.1:8501'), wait_until='networkidle')
    page.get_by_role('heading', name='The economic snapshot', exact=True).wait_for()
    page.locator('.js-plotly-plot').nth(2).wait_for()
    assert page.locator('.js-plotly-plot').count()==3
    assert page.get_by_text('CPI inflation · YoY', exact=True).count()==1
    page.screenshot(path=str(ROOT/'reports/dashboard-snapshot.png'), full_page=True)
    page.get_by_text('Library & explore', exact=True).click()
    page.get_by_text('Download selected cleaned CSV', exact=True).wait_for()
    page.get_by_role('textbox', name='Search name, topic or source').fill('UNRATE')
    page.get_by_role('textbox', name='Search name, topic or source').press('Enter')
    page.get_by_text('1 of 3 datasets', exact=False).wait_for()
    page.wait_for_function("document.querySelector('a[href=\"https://fred.stlouisfed.org/series/UNRATE\"]') !== null")
    for label, values in [('From', [('year','2020'),('month','01'),('day','01')]), ('Through', [('day','28'),('month','12'),('year','2020')])]:
        for segment, value in values:
            control=page.get_by_role('spinbutton', name=f'{segment}, {label}', exact=True)
            page.keyboard.press('Escape')
            control.click()
            control.press('Control+a')
            control.press_sequentially(value)
            control.press('Tab')
            page.wait_for_timeout(800)
    page.keyboard.press('Escape')
    page.get_by_role('textbox', name='Search name, topic or source').click()
    page.wait_for_function("document.querySelector('[data-testid=\"stDownloadButton\"]') !== null")
    page.wait_for_timeout(1500)
    with page.expect_download() as info:
        page.get_by_text('Download selected cleaned CSV', exact=True).click()
    download=info.value
    exported=ROOT/'reports/browser-selected-UNRATE.csv'
    download.save_as(str(exported))
    df=pd.read_csv(exported)
    assert len(df)==12, (len(df),df.to_dict())
    assert df['date'].min().startswith('2020-01-01')
    assert df['date'].max().startswith('2020-12-01')
    link=page.get_by_role('link',name='Official series, notes & citation')
    assert link.get_attribute('href')=='https://fred.stlouisfed.org/series/UNRATE'
    point=page.locator('.scatterlayer .point').nth(3)
    point.scroll_into_view_if_needed()
    box=point.bounding_box()
    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
    page.locator('.hoverlayer').get_by_text('14.8', exact=False).wait_for()
    page.screenshot(path=str(ROOT/'reports/dashboard-library.png'), full_page=True)
    search=page.get_by_role('textbox',name='Search name, topic or source')
    search.fill('zzzz-no-results'); search.press('Enter')
    page.get_by_text('No datasets match your search and filters.').wait_for()
    assert not errors, errors
    report={'browser':'Headless Microsoft Edge via Playwright','three_charts':True,'search_filter':True,'date_filter':'2020-01-01 through 2020-12-28','csv_rows':len(df),'source_link':True,'no_match_state':True,'browser_errors':errors}
    (ROOT/'reports/browser-acceptance.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    browser.close()
