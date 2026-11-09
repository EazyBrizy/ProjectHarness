"""Actual Windows delivery checks; frozen launcher suites remain sequential."""
from ph_lw_12_fix_run import run,ROOT,OUT,ENGINE
python=ROOT/'.venv/Scripts/python.exe';wheel=OUT/'wheel-venv/Scripts/python.exe'
setup=ENGINE/'windows/Harness-Setup-win-x64.exe';rows=[]
profile=ROOT/'_scratch'/('PH12FПрофиль-'+('x'*78))
rows.append(run('installed-supported',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
    '--installer',setup,'--output',OUT/'installed-supported','--runtime-root',profile,
    '--app-data-root',OUT/'installed-supported/LocalAppData'],timeout=1500))
deep=OUT/('Длинный-'+('x'*110))
rows.append(run('installed-deep',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
    '--installer',setup,'--output',OUT/'installed-deep','--runtime-root',deep/'project-profile',
    '--app-data-root',deep/'app-data-profile'],timeout=1500))
rows.append(run('installer-recovery',[python,'-B',ENGINE/'local_web/windows/installer_fault_acceptance.py',
    '--installer',setup,'--output',OUT/'installer-recovery'],timeout=900))
rows.append(run('installed-extended',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
    '--installer',setup,'--output',OUT/'installed-extended','--advanced-fixtures',ROOT/'_scratch/ph_lw_12/advanced-fixtures'],
    extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=2400))
raise SystemExit(not all(row['status']=='PASS' for row in rows))
