"""Real dashboard interaction during a separate-process official FRED refresh."""
import json
import os
from pathlib import Path
import subprocess
import sys
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('PDL_DATA_DIR', ROOT/'data'))
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100})
    page.goto(os.environ.get('PDL_BROWSER_URL','http://127.0.0.1:8501'),wait_until='networkidle')
    page.locator('.js-plotly-plot').nth(2).wait_for()
    child=subprocess.Popen([sys.executable,'-m','data_library.refresh','--data-dir',str(DATA)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        page.get_by_text('Library & explore',exact=True).click()
        page.get_by_role('textbox',name='Search name, topic or source').fill('UNRATE')
        page.get_by_role('textbox',name='Search name, topic or source').press('Enter')
        page.get_by_text('Download selected cleaned CSV',exact=True).wait_for()
        assert page.locator('[data-testid="stException"]').count()==0
        out,err=child.communicate(timeout=90)
        assert child.returncode==0,(out,err)
        results=[json.loads(line) for line in out.splitlines() if line.strip()]
        assert len(results)==3 and all(r['ok'] for r in results)
        page.get_by_text('Economic snapshot',exact=True).click()
        page.locator('.js-plotly-plot').nth(2).wait_for()
        assert page.locator('[data-testid="stException"]').count()==0
        page.screenshot(path=str(ROOT/'reports/intake-concurrent-refresh.png'),full_page=True)
        report={'real_cli_refresh':results,'dashboard_usable':True,'numerical_store_shared':str(DATA),'stderr':err}
        (ROOT/'reports/intake-concurrent-refresh.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
    finally:
        if child.poll() is None: child.kill();child.wait()
        browser.close()
