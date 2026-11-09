"""Observe the unchanged PH-LW-07 browser regression; never alter timeouts."""
import argparse,json,time,unittest
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import Browser
from package_acceptance import ROOT,ENGINE
import sys
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
parser=argparse.ArgumentParser();parser.add_argument('--output',default='approval-diagnostic');parser.add_argument('--repeat',type=int,default=1);args=parser.parse_args()
out=ROOT/'_scratch/ph_lw_10'/args.output;out.mkdir(exist_ok=False)
events=[];states=[];started=time.monotonic();original=Browser.new_context;original_close=Browser.close
def new_context(self,*args,**kwargs):
    context=original(self,*args,**kwargs)
    def record(kind,request,status=None):
        path=urlsplit(request.url).path
        if not path.startswith('/api/'):return
        events.append({'elapsed':round(time.monotonic()-started,3),'event':kind,'method':request.method,'path':path,'status':status})
    context.on('request',lambda r:record('request',r))
    def response(r):
        record('response',r.request,r.status)
        if r.status>=400 and urlsplit(r.url).path.startswith('/api/'):
            try:events[-1]['error']=r.json().get('error')
            except Exception:pass
    context.on('response',response)
    return context
def close(self,*a,**kw):
    for context in self.contexts:
        for page in context.pages:
            try:
                states.append(page.evaluate('''() => ({notice:document.getElementById('notice')?.textContent,status:document.getElementById('approvals-status')?.textContent,busy:state.requestBusy})'''))
                page.screenshot(path=str(out/f'last-{len(states)}.png'),full_page=True)
            except Exception as e:states.append({'capture_error':type(e).__name__})
    return original_close(self,*a,**kw)
Browser.new_context=new_context
Browser.close=close
passed=True
for i in range(args.repeat):
    suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_ph_lw_07_http.ApprovalBrowserTests')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    passed=passed and result.wasSuccessful() and not result.skipped
(out/'REQUEST_TIMING.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n','utf-8')
(out/'LAST_UI_STATE.json').write_text(json.dumps(states,ensure_ascii=False,indent=2)+'\n','utf-8')
raise SystemExit(0 if passed else 1)
