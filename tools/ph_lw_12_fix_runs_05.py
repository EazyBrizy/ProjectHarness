"""Launch final05 acceptance modes after exact wheel/frozen publication."""
import argparse,json,time
from ph_lw_12_fix_run import ROOT,OUT,W,ENGINE,run
p=argparse.ArgumentParser();p.add_argument('mode',choices=('maturity','delivery'));a=p.parse_args()
deadline=time.monotonic()+1200
while not (W/'FINAL05_TEST_FREEZE_READY.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Final05 not frozen')
    time.sleep(1)
python=ROOT/'.venv/Scripts/python.exe';wheel=OUT/'wheel-venv/Scripts/python.exe'
if a.mode=='maturity':
    row=run('maturity-final05',[wheel,'-B',ROOT/'tools/ph_lw_12_fix_maturity_driver_05.py',
        '--engine',ENGINE,'--case','tests.test_ph_f06_maturity_lifecycle'],
        cwd=OUT/'Независимая папка wheel',timeout=2700)
    raise SystemExit(row['status']!='PASS')
setup=ENGINE/'windows/Harness-Setup-win-x64.exe';rows=[]
profile=ROOT/'_scratch'/('PH12VПрофиль-'+('x'*78))
rows.append(run('final05-installed-supported',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
    '--installer',setup,'--output',OUT/'final05-installed-supported','--runtime-root',profile,
    '--app-data-root',OUT/'final05-installed-supported/LocalAppData'],timeout=1500))
deep=OUT/('Длинный-'+('r'*110))
rows.append(run('final05-installed-deep',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
    '--installer',setup,'--output',OUT/'final05-installed-deep','--runtime-root',deep/'project-profile',
    '--app-data-root',deep/'app-data-profile'],timeout=1500))
rows.append(run('final05-installer-recovery',[python,'-B',ENGINE/'local_web/windows/installer_fault_acceptance.py',
    '--installer',setup,'--output',OUT/'final05-installer-recovery'],timeout=900))
rows.append(run('final05-installed-extended',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',setup,'--output',OUT/'final05-installed-extended','--advanced-fixtures',ROOT/'_scratch/ph_lw_12/advanced-fixtures'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=2400))
rows.append(run('final05-installed-deep-full',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',setup,'--output',OUT/'final05-installed-deep-full','--deep-full-flow',
    '--case','__main__.InstalledFullFlowTests.test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=900))
raise SystemExit(not all(row['status']=='PASS' for row in rows))
