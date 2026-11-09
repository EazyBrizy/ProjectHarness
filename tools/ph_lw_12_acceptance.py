"""PH-LW-12 evidence: immutable input, current discovery, bounded native runs.

No ZIP creation, executor activation, environment installation or system changes.
"""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

from package_acceptance import ROOT, ENGINE, DOCS, files
from verify_ph_lw_06_working_tree import verify_manifest

OUT = ROOT / '_workspace/PH_LW_12'
RUNS = ROOT / '_scratch/ph_lw_12'
LINUX_MODULES = {
    'test_ph_051_02_executor_protocol', 'test_ph_051_03_rootless_podman',
    'test_ph_051_04_disposable_roots', 'test_ph_051_05_codex_adapter',
    'test_ph_051_06_result_channel', 'test_ph_051_07_sandbox_verification',
    'test_ph_051_08_atomic_apply', 'test_ph_051_09_automatic_runtime',
}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', 'utf-8')

def environment():
    return {'python':sys.version, 'executable':sys.executable,
            'platform':platform.platform(), 'machine':platform.machine(),
            'non_admin':not bool(ctypes.windll.shell32.IsUserAnAdmin()),
            'dependencies':{n:version(n) for n in ('Flask','Waitress','Playwright','PyYAML','jsonschema')},
            'zip_created':False, 'automatic_executor':'NO-GO; disabled'}

def begin():
    OUT.mkdir(exist_ok=False)
    prior=json.loads((ROOT/'_workspace/PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json').read_text('utf-8'))
    trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
    assert trees==prior['trees']
    for name,value in prior['workspace_files'].items(): assert sha(ROOT/name)==value,name
    assert sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')==prior['wheel_sha256']
    assert sha(ENGINE/'windows/Harness-Setup-win-x64.exe')==prior['installer_sha256']
    folders=(ENGINE,DOCS,ROOT/'_inputs',ROOT/'Harness_Local_Web_Prompts_RU_r2',
             ROOT/'Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0',ROOT/'_workspace')
    before={p.relative_to(ROOT).as_posix():sha(p) for folder in folders for p in files(folder)
            if not p.is_relative_to(OUT)}
    before.update({p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'README.md',ROOT/'AGENTS.md',*files(ROOT/'tools')]})
    save(OUT/'INPUT_FILE_HASHES.json',before)
    save(OUT/'INPUT_BASELINE.json',{'status':'PASS','captured_utc':datetime.now(timezone.utc).isoformat(),
        'trees':trees,'wheel_sha256':prior['wheel_sha256'],'installer_sha256':prior['installer_sha256'],
        'previous_attestation_sha256':sha(ROOT/'_workspace/PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json'),
        'accepted_limitations':['clean Windows','physical offline','real disk-full','actual Unicode username'],
        'git':'not a repository; complete file hash baseline', 'drift':[],
        'allowed_file_changes':['PH-LW-12 acceptance tests/runners/reports/matrices/logs',
            'current README/runbook/examples/operator documentation and mirror/generated manifests',
            'proven direct runtime regression fix and regenerated wheel/frozen/installer only if needed'],
        'environment':environment()})
    save(OUT/'PRESERVED_ARCHIVES.json',{p.relative_to(ROOT).as_posix():sha(p)
        for folder in (ROOT/'_deliverables',ROOT/'_inputs') for p in folder.rglob('*.zip')})
    shutil.copy2(ROOT/'_workspace/CURRENT_TASK.md',OUT/'CURRENT_TASK.before.md')
    print('Input PASS; hashed',len(before),'files',flush=True)

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite): yield from flatten(item)
        else: yield item

def discover():
    sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
    rows=[]
    for p in sorted((ENGINE/'tests').glob('test_*.py')):
        suite=unittest.defaultTestLoader.loadTestsFromName('tests.'+p.stem)
        for case in flatten(suite):
            ident=case.id()
            reason=None
            if p.stem in LINUX_MODULES: reason='Outside the user-authorized Windows-only platform; POSIX executor legacy tests are NOT RUN and are not prerequisites'
            if p.stem=='test_ph_051_10_migration_recovery' and '.V051MigrationTests.' not in ident:
                reason='Simulated POSIX automatic recovery outside the user-authorized Windows-only scope'
            rows.append({'id':ident,'module':'tests.'+p.stem,'platform_status':'NOT RUN' if reason else 'SCHEDULED_WINDOWS',
                         'reason':reason,'test_file_sha256':sha(p)})
    save(OUT/'DISCOVERY.json',{'current_modules':len({r['module'] for r in rows}),
        'current_methods':len(rows),'methods':rows,'environment':environment()})
    print('Discovered',len(rows),'methods in',len({r['module'] for r in rows}),'modules',flush=True)

def run_one(name, ids, *, python=None, wheel=False, timeout=900):
    python=Path(python or sys.executable).resolve()
    destination=RUNS/('wheel' if wheel else 'source');destination.mkdir(parents=True,exist_ok=True)
    cwd=RUNS/'Независимая папка wheel' if wheel else ENGINE
    cwd.mkdir(exist_ok=True,parents=True)
    log=destination/(name+'.log')
    if log.exists(): raise RuntimeError('Preserve previous run: '+str(log))
    code=('import sys,unittest,json;from pathlib import Path;'
          + ('import project_harness;assert Path(project_harness.__file__).resolve().is_relative_to(Path(sys.prefix).resolve());' if wheel else '')
          + 'sys.path.insert(0,sys.argv[1]);from local_web.run_windows_acceptance import run_suite;'
          + 'r=run_suite(sys.argv[3:],Path(sys.argv[2]),reject_skips=False);raise SystemExit(r["status"]!="PASS")')
    command=[str(python),'-B','-c',code,str(ENGINE),str(log),*ids]
    env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1',
         'PYTHONPATH':'' if wheel else str(ENGINE/'src')+os.pathsep+str(ENGINE),
         'PH_LW_04_BROWSER_CHANNEL':'msedge'}
    for stage in ('06','07','08','09','10'):
        env['PH_LW_'+stage+'_SCREENSHOT_DIR']=str(destination/'screenshots'/stage)
    started=time.monotonic()
    proc=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try:
        output=proc.communicate(timeout=timeout)[0];status='PASS' if proc.returncode==0 else 'FAIL'
    except subprocess.TimeoutExpired:
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=20)
        output=proc.communicate(timeout=20)[0];status='TIMEOUT'
    log.with_suffix('.process.log').write_bytes(output)
    row={'name':name,'command':command,'cwd':str(cwd),'exit':proc.returncode,'status':status,
         'elapsed_seconds':round(time.monotonic()-started,3),'environment_ref':'INPUT_BASELINE.json' if not wheel else 'WHEEL_ENVIRONMENT.json'}
    if log.with_suffix('.json').exists(): row.update(json.loads(log.with_suffix('.json').read_text('utf-8')))
    row['process_status']=status
    if log.exists():row['log_sha256']=sha(log)
    save(log.with_suffix('.run.json'),row)
    print(name,status,'ran',row.get('ran'),'skips',len(row.get('skips',[])),flush=True)
    return row

def suites(kind, python=None, jobs=2):
    rows=json.loads((OUT/'DISCOVERY.json').read_text('utf-8'))['methods']
    grouped={}
    for r in rows:
        if r['platform_status']!='SCHEDULED_WINDOWS':continue
        isbrowser=any(x in r['id'] for x in ('Browser','Edge','NativeLauncherTests'))
        if (kind=='browser')!=isbrowser:continue
        grouped.setdefault(r['module'],[]).append(r['id'])
    # Keep all browser sessions sequential to avoid Edge teardown contention.
    results=[]
    with ThreadPoolExecutor(max_workers=1 if kind=='browser' else jobs) as pool:
        pending=[pool.submit(run_one,module.removeprefix('tests.')+'-'+kind,ids,python=python,wheel=python is not None)
                 for module,ids in grouped.items()]
        for future in as_completed(pending):
            results.append(future.result())
            save(OUT/(('WHEEL_' if python else 'SOURCE_')+kind.upper()+'_MATRIX.json'),results)
    return not all(r.get('process_status')=='PASS' for r in results)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('begin','discover','nonbrowser','browser'))
    parser.add_argument('--python',type=Path);parser.add_argument('--jobs',type=int,default=2);args=parser.parse_args()
    if args.mode=='begin':begin()
    elif args.mode=='discover':discover()
    else:return suites(args.mode,args.python,args.jobs)
    return 0

if __name__=='__main__':raise SystemExit(main())
