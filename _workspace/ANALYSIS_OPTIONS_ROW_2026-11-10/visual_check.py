"""One-off layout observation in installed wheel; no workflow/model regression."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
import project_harness
package=Path(project_harness.__file__).resolve().parent
assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
def inventory(base):return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert inventory(package)==inventory(ENGINE/'src/project_harness')
sys.path.insert(0,str(ENGINE))
from tests.test_ph_lw_04_05_acceptance import LiveServer
from playwright.sync_api import sync_playwright,expect
screens=OUT/'output/playwright';screens.mkdir(parents=True,exist_ok=True)
report={'python':sys.version,'platform':platform.platform(),'package':str(package),'cwd':str(Path.cwd()),
    'source_import':False,'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},
    'scope':'Observe only option-card layout at 1360/1024/390 CSS pixels; no model calls or CLI connection',
    'viewports':[],'page_errors':[],'dialogs':[]}
with tempfile.TemporaryDirectory(prefix='analysis-options-layout-') as folder:
    live=LiveServer(folder)
    try:
        pid=live.create('analysis-options-layout-001')
        live.upload(pid,[('Layout.md',b'# Synthetic layout observation only')])
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='msedge',headless=True)
            try:
                report['edge_version']=browser.version
                page=browser.new_page(viewport={'width':1360,'height':1100})
                page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
                page.on('dialog',lambda dialog:(report['dialogs'].append(dialog.message),dialog.dismiss()))
                page.goto(live.origin+'/');expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                page.locator('.project-button').filter(has_text=pid).click()
                page.locator('[data-screen="interview"]').click()
                expect(page.locator('#analysis-options')).to_be_visible()
                for width in (1360,1024,390):
                    page.set_viewport_size({'width':width,'height':1100 if width>760 else 844})
                    cards=page.locator('#analysis-options > .question')
                    expect(cards).to_have_count(2)
                    metrics=page.locator('#analysis-options').evaluate('''node=>({
                        columns:getComputedStyle(node).gridTemplateColumns,
                        cards:[...node.children].map(child=>{const r=child.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}}),
                        buttons:[...node.querySelectorAll('button')].filter(b=>getComputedStyle(b).display!=='none').map(b=>{const r=b.getBoundingClientRect(),c=b.closest('.question').getBoundingClientRect();return {text:b.textContent,inside:r.left>=c.left && r.right<=c.right}}),
                        no_horizontal_overflow:document.documentElement.scrollWidth<=document.documentElement.clientWidth
                    })''')
                    a,b=metrics['cards']
                    metrics['width']=width
                    metrics['row_matches_request']=(abs(a['y']-b['y'])<1 and a['x']+a['width']<=b['x']) if width>760 else a['y']+a['height']<=b['y']
                    report['viewports'].append(metrics)
                    page.locator('#analysis-options').screenshot(path=str(screens/(str(width)+'.png')))
            finally:browser.close()
    finally:live.close()
report['status']='PASS' if not report['page_errors'] and not report['dialogs'] and all(
    v['row_matches_request'] and v['no_horizontal_overflow'] and all(b['inside'] for b in v['buttons']) for v in report['viewports']) else 'FAIL'
(OUT/'VISUAL_RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(report['status']!='PASS')
