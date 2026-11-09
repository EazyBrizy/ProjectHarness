"""Correct the new no-doc driver's expect timeout; retain prior attempts."""
import hashlib,json,time
from datetime import datetime,timezone
from ph_lw_12_final_runs import run,OUT,ROOT,ENGINE,wheel,W
deadline=time.monotonic()+1500
while not (OUT/'installed-extended-focus3.run.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Previous frozen suite incomplete')
    time.sleep(1)
inputs=[ENGINE/'local_web/windows/final_acceptance.py',ROOT/'tools/ph_lw_12_final_runs.py',ROOT/'tools/ph_lw_12_no_docs_recheck.py']
(W/'FINAL_ACCEPTANCE_RUNNER_VERSION.json').write_text(json.dumps({
    'captured_utc':datetime.now(timezone.utc).isoformat(),
    'reason':'New driver: inherit 30s browser expect setting; preserve state before owned cleanup; accepted MVP cache is validated initial state only.',
    'hashes':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},ensure_ascii=False,indent=2)+'\n','utf-8')
row=run('installed-no-doc-final',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installed-no-doc-final',
    '--case','__main__.InstalledFullFlowTests.test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=600)
raise SystemExit(row['status']!='PASS')
