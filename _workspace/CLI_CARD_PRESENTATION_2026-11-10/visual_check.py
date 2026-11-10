"""Only changed card presentation on real TCP/Edge; declared connection fixture."""
from contextlib import ExitStack
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
import tempfile
from unittest.mock import patch

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
import project_harness
package=Path(project_harness.__file__).resolve().parent
assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
def inventory(base):return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert inventory(package)==inventory(ENGINE/'src/project_harness')
sys.path.insert(0,str(ENGINE))
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_cli_document_analysis import FixtureCli
from playwright.sync_api import sync_playwright,expect
screens=OUT/'output/playwright';screens.mkdir(parents=True,exist_ok=True)
report={'python':sys.version,'platform':platform.platform(),'package':str(package),'cwd':str(Path.cwd()),
    'source_import':False,'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},
    'scope':'Full width, buttons row/labels, token note, idle hidden, connection/reload/recheck-failure presentation only',
    'provider':'Declared FixtureCli probes only; no actual CLI/model analysis',
    'viewports':[],'states':[],'page_errors':[],'dialogs':[]}
with tempfile.TemporaryDirectory(prefix='cli-card-presentation-') as folder, ExitStack() as stack:
    fake=FixtureCli();executable=Path(folder)/'codex.exe';executable.write_bytes(b'MZ declared fixture, never executed')
    stack.enter_context(patch('project_harness.local_web_cli.find_cli',lambda:executable))
    stack.enter_context(patch('project_harness.local_web_cli.invoke',fake))
    live=LiveServer(folder);stack.callback(live.close)
    pid=live.create('cli-card-presentation-001')
    live.upload(pid,[('Layout.md',b'# Synthetic presentation observation only')])
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='msedge',headless=True)
        try:
            report['edge_version']=browser.version
            page=browser.new_page(viewport={'width':1920,'height':1100})
            page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
            page.on('dialog',lambda dialog:(report['dialogs'].append(dialog.message),dialog.dismiss()))
            page.goto(live.origin+'/');expect(page.locator('#connection-state')).to_have_text('Сервер готов')
            page.locator('.project-button').filter(has_text=pid).click()
            page.locator('[data-screen="interview"]').click()
            expect(page.locator('#cli-connection-status')).to_contain_text('Подключите установленный')
            expect(page.locator('#cli-connect-label')).to_have_text('Подключить CLI')
            expect(page.locator('#cli-analyze')).to_have_text('Анализировать через CLI')
            expect(page.locator('#cli-connection-help')).to_be_visible()
            expect(page.locator('#cli-analysis-status')).to_be_hidden()
            expect(page.locator('#cli-token-note')).to_have_text('На выполнение расходуются токены агента.')
            assert not fake.calls
            report['states'].append('disconnected: label/help/idle/note PASS; no process from GET')
            for width in (1920,1360,1024,390):
                page.set_viewport_size({'width':width,'height':1100 if width>760 else 844})
                metrics=page.locator('#analysis-options').evaluate('''node=>{
                    const main=document.querySelector('main'),p=document.querySelector('#interview-panel'),m=main.getBoundingClientRect(),s=getComputedStyle(main),r=p.getBoundingClientRect();
                    const buttons=[...node.querySelectorAll('.cli-actions button')].filter(b=>getComputedStyle(b).display!=='none').map(b=>{const x=b.getBoundingClientRect(),c=b.closest('.question').getBoundingClientRect();return {text:b.textContent,x:x.x,y:x.y,width:x.width,height:x.height,inside:x.left>=c.left && x.right<=c.right}});
                    const n=getComputedStyle(document.querySelector('#cli-token-note'));
                    return {main_right:m.right,main_width:m.width,panel_width:r.width,
                        fills_main:Math.abs(r.width-(m.width-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)))<1,
                        buttons,one_button_row:buttons.every(b=>Math.abs(b.y+b.height/2-(buttons[0].y+buttons[0].height/2))<1),
                        note:{font_size:n.fontSize,color:n.color},
                        no_horizontal_overflow:document.documentElement.scrollWidth<=document.documentElement.clientWidth};
                }''')
                metrics['width']=width
                assert metrics['fills_main'] and abs(metrics['main_right']-width)<1,metrics
                assert metrics['one_button_row'] and metrics['no_horizontal_overflow'] and all(b['inside'] for b in metrics['buttons']),metrics
                report['viewports'].append(metrics)
                page.locator('#analysis-options').screenshot(path=str(screens/('disconnected-'+str(width)+'.png')))
            page.set_viewport_size({'width':1920,'height':1100})
            page.locator('#cli-connect').click()
            expect(page.locator('#cli-connect-label')).to_have_text('Подключено')
            expect(page.locator('#cli-connect-check')).to_be_visible()
            expect(page.locator('#cli-connect-check')).to_have_css('color','rgb(22, 132, 66)')
            expect(page.locator('#cli-connection-help')).to_be_hidden()
            expect(page.locator('#cli-connect')).to_be_enabled()
            assert len(fake.calls)==3
            report['states'].append('connected: label/green check/hidden help/enabled recheck PASS')
            page.locator('#analysis-options').screenshot(path=str(screens/'connected-1920.png'))
            page.reload()
            expect(page.locator('#cli-connect-label')).to_have_text('Подключено')
            expect(page.locator('#cli-connection-help')).to_be_hidden()
            expect(page.locator('#cli-analysis-status')).to_be_hidden()
            assert len(fake.calls)==3
            report['states'].append('reload: connected presentation persists; no new CLI probes PASS')
            fake.mode='logged-out';page.locator('#cli-connect').click()
            expect(page.locator('#notice')).to_contain_text('codex login')
            expect(page.locator('#cli-connect-label')).to_have_text('Подключить CLI')
            expect(page.locator('#cli-connect-check')).to_be_hidden()
            expect(page.locator('#cli-connection-help')).to_be_visible()
            expect(page.locator('#cli-analyze')).to_be_enabled()
            report['states'].append('failed recheck: honest disconnected label/help restored PASS')
            report['analysis_calls']=sum('--output-last-message' in call for call in fake.calls)
            assert report['analysis_calls']==0
        finally:browser.close()
report['status']='PASS' if not report['page_errors'] and not report['dialogs'] else 'FAIL'
(OUT/'VISUAL_RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(report['status']!='PASS')
