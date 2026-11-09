"""Sequential Windows delivery acceptance; exact logs, no ZIPs/system changes."""
import argparse,hashlib,json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from package_acceptance import ROOT,ENGINE

OUT=ROOT/'_scratch/ph_lw_12';W=ROOT/'_workspace/PH_LW_12'
python=ROOT/'.venv/Scripts/python.exe';wheel=OUT/'wheel-venv/Scripts/python.exe'

def run(name,command,*,cwd=ROOT,extra=None,timeout=1800):
    log=OUT/(name+'.log');assert not log.exists(),name
    env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'',
         'PH_LW_04_BROWSER_CHANNEL':'msedge',**(extra or {})}
    for stage in ('06','07','08','09','10'):env['PH_LW_'+stage+'_SCREENSHOT_DIR']=str(OUT/'final-screenshots'/stage)
    started=time.monotonic();row={'command':list(map(str,command)),'cwd':str(cwd),
        'started_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':hashlib.sha256((W/'RUNTIME_FREEZE.json').read_bytes()).hexdigest()}
    with log.open('wb') as stream:
        child=subprocess.Popen(list(map(str,command)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:
            code=child.wait(timeout=timeout);row.update(exit=code,status='PASS' if code==0 else 'FAIL')
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,timeout=20)
            child.wait(timeout=20);row.update(exit=None,status='TIMEOUT')
    row.update(elapsed_seconds=round(time.monotonic()-started,3),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    log.with_suffix('.run.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(name,row['status'],row['elapsed_seconds'],flush=True)
    return row

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('basic','basic-supported','recovery','extended','wheel-browser','rechecks','source'))
    args=parser.parse_args();rows=[]
    if args.mode=='basic':
        long=OUT/('Длинный-'+('x'*110))
        rows.append(run('installed-basic-final',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
            '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installed-basic-final',
            '--runtime-root',long/'project-profile','--app-data-root',long/'app-data-profile'],timeout=1200))
    elif args.mode=='basic-supported':
        # Repeat the PH-LW-11 verified root geometry. The deliberately deeper
        # first stress attempt remains a separate FAIL, not a rewritten run.
        profile=ROOT/'_scratch'/('PH12Профиль-'+('x'*78))
        rows.append(run('installed-basic-supported',[python,'-B',ENGINE/'local_web/windows/zip_path_acceptance.py',
            '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installed-basic-supported',
            '--runtime-root',profile,'--app-data-root',OUT/'installed-basic-supported/LocalAppData'],timeout=1200))
    elif args.mode=='recovery':
        rows.append(run('installer-recovery-final',[python,'-B',ENGINE/'local_web/windows/installer_fault_acceptance.py',
            '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installer-recovery-final'],timeout=900))
    elif args.mode=='extended':
        rows.append(run('installed-extended-final',[wheel,'-B',ENGINE/'local_web/windows/final_acceptance.py',
            '--installer',ENGINE/'windows/Harness-Setup-win-x64.exe','--output',OUT/'installed-extended-final',
            '--advanced-fixtures',OUT/'advanced-fixtures'],extra={'PH_LW_12_INSTALLED_DRIVER':'1'},timeout=2400))
    elif args.mode=='wheel-browser':
        data=json.loads((W/'DISCOVERY.json').read_text('utf-8'))['methods']
        ids=[r['id'] for r in data if r['platform_status']=='SCHEDULED_WINDOWS' and any(x in r['id'] for x in ('Browser','Edge','NativeLauncherTests'))]
        command=[wheel,'-B',ROOT/'tools/verify_installed.py','--engine',ENGINE,'--case','tests.test_ph_lw_01_contract']
        for ident in ids:command+=['--case',ident]
        cwd=OUT/'Независимая папка wheel';cwd.mkdir(exist_ok=True)
        rows.append(run('wheel-browser-final',command,cwd=cwd,timeout=1800))
    elif args.mode=='rechecks':
        # Earlier setup/socket/time-limit errors are preserved. No deadline or
        # assertion in these unchanged tests is modified for the sequential run.
        groups=[('maturity-final','tests.test_ph_f06_maturity_lifecycle'),
                ('exchange-http-final','tests.test_ph_lw_06_http.ExchangeHttpTests'),
                ('lifecycle-http-final','tests.test_ph_lw_10_http.LifecycleHttpTests'),
                ('lifecycle-service-final','tests.test_ph_lw_10_lifecycle')]
        for name,module in groups:
            driver=('ph_lw_12_maturity_driver.py' if name=='maturity-final' else
                    'ph_lw_12_legacy_driver.py' if name.startswith('lifecycle-') else 'verify_installed.py')
            command=[wheel,'-B',ROOT/'tools'/driver,'--engine',ENGINE,'--case',module]
            rows.append(run(name,command,cwd=OUT/'Независимая папка wheel',timeout=2400))
    elif args.mode=='source':
        rows.append(run('source-final-regressions',[python,'-B',ROOT/'tools/ph_lw_12_diagnostic.py','tests.test_ph_lw_12_acceptance'],timeout=600))
    return not all(row['status']=='PASS' for row in rows)

if __name__=='__main__':raise SystemExit(main())
