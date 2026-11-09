"""Observe the unchanged migration browser test with real directory swaps."""
import argparse,faulthandler,json,sys,threading,time,unittest
from pathlib import Path
from urllib.parse import urlsplit
from package_acceptance import ROOT,ENGINE
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
from playwright.sync_api import Browser
from project_harness import lifecycle_forms
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
out=ROOT/'_scratch/ph_lw_10'/args.output;out.mkdir(exist_ok=False)
events=[];original=Browser.new_page;close=Browser.close;sha=lifecycle_forms.sha256_file
def slow_snapshot(path):
    if '.ph05110-backup-' in str(path) and not threading.current_thread().name.startswith('local-web'):
        time.sleep(.02)
    return sha(path)
lifecycle_forms.sha256_file=slow_snapshot
def new_page(self,*a,**kw):
    page=original(self,*a,**kw)
    def response(r):
        if r.status>=400 and urlsplit(r.url).path.startswith('/api/'):
            try:body=json.loads(r.body())
            except Exception:body=None
            events.append({'status':r.status,'path':urlsplit(r.url).path,'body':body})
    page.on('response',response)
    return page
def closing(self,*a,**kw):
    for context in self.contexts:
        for page in context.pages:
            try:events.append({'ui':page.evaluate("() => ({notice:document.getElementById('notice')?.textContent,operation:document.getElementById('lifecycle-operation')?.textContent})")})
            except Exception:pass
    with (out/'THREADS.log').open('w') as f:faulthandler.dump_traceback(file=f)
    return close(self,*a,**kw)
Browser.new_page=new_page;Browser.close=closing
suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_ph_lw_10_http.LifecycleBrowserTests.test_edge_supported_migration_confirmation_and_restart_replay')
result=unittest.TextTestRunner(verbosity=2).run(suite)
(out/'POLLING.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n','utf-8')
raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
