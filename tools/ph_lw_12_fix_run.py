"""Bounded Windows-only reruns with immutable per-attempt logs and inputs."""
import argparse,hashlib,json,os,platform,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from package_acceptance import ROOT,ENGINE,files

OUT=ROOT/'_scratch/ph_lw_12_fix';W=ROOT/'_workspace/PH_LW_12_FIX'
OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run(name,command,*,cwd=ROOT,extra=None,timeout=1800):
    assert sys.platform=='win32'
    log=OUT/(name+'.log');assert not log.exists(),name
    env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'',
         'PH_LW_04_BROWSER_CHANNEL':'msedge',**(extra or {})}
    row={'command':list(map(str,command)),'cwd':str(cwd),'started_utc':datetime.now(timezone.utc).isoformat(),
         'platform':platform.platform(),'source_hashes':{p.relative_to(ENGINE/'src').as_posix():sha(p) for p in files(ENGINE/'src')},
         'test_hashes':{p.relative_to(ENGINE).as_posix():sha(p) for p in [*files(ENGINE/'tests'),*files(ENGINE/'local_web')]},
         'runtime_freeze_sha256':sha(W/'RUNTIME_FREEZE.json') if (W/'RUNTIME_FREEZE.json').exists() else None}
    started=time.monotonic()
    with log.open('wb') as stream:
        child=subprocess.Popen(list(map(str,command)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:
            code=child.wait(timeout=timeout);row.update(exit=code,status='PASS' if code==0 else 'FAIL')
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,timeout=20)
            child.wait(timeout=20);row.update(exit=None,status='TIMEOUT')
    row.update(elapsed_seconds=round(time.monotonic()-started,3),log_sha256=sha(log))
    log.with_suffix('.run.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(name,row['status'],row['elapsed_seconds'],flush=True)
    return row

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('name');parser.add_argument('cases',nargs='+');parser.add_argument('--timeout',type=int,default=900)
    args=parser.parse_args()
    row=run(args.name,[ROOT/'.venv/Scripts/python.exe','-B',ROOT/'tools/ph_lw_12_diagnostic.py',*args.cases],timeout=args.timeout)
    raise SystemExit(row['status']!='PASS')
