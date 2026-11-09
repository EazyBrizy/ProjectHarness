"""Sequential diagnostic rerun after the final native-launcher suite."""
import time
from ph_lw_12_final_runs import run,OUT,ROOT,ENGINE,wheel
deadline=time.monotonic()+2400
while not (OUT/'source-final-regressions.run.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Prior suite incomplete; no overlapping frozen launch')
    time.sleep(1)
command=[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installed-extended-focus3',
    '--advanced-fixtures',OUT/'advanced-fixtures']
for name in ('InstalledFullFlowTests.test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete',
             'AdditionalLifecycleTests.test_accepted_mvp_to_release_form_preserves_history',
             'AdditionalLifecycleTests.test_maintenance_task_completion_through_browser',
             'transport.ProductionHttpAcceptance.test_production_wsgi_declared_and_chunked_body_header_and_idle_limits'):
    # The transport class is an imported module, exposed explicitly below by
    # the runner. Local classes resolve through __main__.
    command+=['--case','__main__.'+name]
row=run('installed-extended-focus3',command,extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=1200)
raise SystemExit(row['status']!='PASS')
