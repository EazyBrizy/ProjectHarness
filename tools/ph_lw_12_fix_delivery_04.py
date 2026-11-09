"""Fresh exact-installer acceptance after documentation metadata correction."""
from ph_lw_12_fix_run import run,ROOT,OUT,W,ENGINE
assert (W/'FINAL04_TEST_FREEZE_READY.json').exists()
python=ROOT/'.venv/Scripts/python.exe';wheel=OUT/'wheel-venv/Scripts/python.exe'
setup=ENGINE/'windows/Harness-Setup-win-x64.exe';rows=[]
profile=ROOT/'_scratch'/('PH12UПрофиль-'+('x'*78))
rows.append(run('final04-installed-supported',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
    '--installer',setup,'--output',OUT/'final04-installed-supported','--runtime-root',profile,
    '--app-data-root',OUT/'final04-installed-supported/LocalAppData'],timeout=1500))
deep=OUT/('Длинный-'+('q'*110))
rows.append(run('final04-installed-deep',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
    '--installer',setup,'--output',OUT/'final04-installed-deep','--runtime-root',deep/'project-profile',
    '--app-data-root',deep/'app-data-profile'],timeout=1500))
rows.append(run('final04-installer-recovery',[python,'-B',ENGINE/'local_web/windows/installer_fault_acceptance.py',
    '--installer',setup,'--output',OUT/'final04-installer-recovery'],timeout=900))
rows.append(run('final04-installed-extended',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',setup,'--output',OUT/'final04-installed-extended','--advanced-fixtures',ROOT/'_scratch/ph_lw_12/advanced-fixtures'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=2400))
rows.append(run('final04-installed-deep-full',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',setup,'--output',OUT/'final04-installed-deep-full','--deep-full-flow',
    '--case','__main__.InstalledFullFlowTests.test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=900))
raise SystemExit(not all(row['status']=='PASS' for row in rows))
