"""Separate the external fixture's read from live browser polling."""
import hashlib,json,time
from ph_lw_12_final_runs import run,OUT,ROOT,ENGINE,wheel,W
deadline=time.monotonic()+900
while not (OUT/'installed-no-doc-final.run.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Prior frozen process not finished')
    time.sleep(1)
runner=ENGINE/'local_web/windows/final_acceptance.py'
(W/'RUNNER_MAINTENANCE_FINAL.py').write_bytes(runner.read_bytes())
(W/'MAINTENANCE_RUNNER_VERSION.json').write_text(json.dumps({
    'sha256':hashlib.sha256(runner.read_bytes()).hexdigest(),
    'reason':'Wait until UI reads finish; construct external fixture result before starting UI reads. No core assertions changed.'},indent=2)+'\n','utf-8')
row=run('installed-maintenance-final',[wheel,'-B',runner,
    '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installed-maintenance-final',
    '--advanced-fixtures',OUT/'advanced-fixtures',
    '--case','__main__.AdditionalLifecycleTests.test_maintenance_task_completion_through_browser'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=600)
raise SystemExit(row['status']!='PASS')
