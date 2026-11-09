from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import time

root=Path(__file__).resolve().parents[1]
logdir=root/'PH_LW_02_LOGS'/'REGRESSION_MODULES'
logdir.mkdir(parents=True,exist_ok=True)
modules=sorted('tests.'+p.stem for p in (root/'tests').glob('test_*.py'))
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'src')+os.pathsep+str(root)}

def execute(module):
    start=time.monotonic()
    try:
        p=subprocess.run([sys.executable,'-B','-m','unittest','-v',module],cwd=root,env=env,
                         text=True,capture_output=True,timeout=450)
        output=p.stdout+p.stderr
        status='PASS' if p.returncode == 0 else 'FAIL'
        code=p.returncode
    except subprocess.TimeoutExpired as e:
        output=(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else (e.stdout or '')
        output+='\nTIMEOUT 450 seconds'
        status='TIMEOUT';code=124
    (logdir/(module.replace('.','_')+'.log')).write_text(output,encoding='utf-8')
    m=re.search(r'Ran (\d+) tests?',output)
    count=int(m.group(1)) if m else None
    skip=re.search(r'OK \(skipped=(\d+)\)',output)
    return dict(module=module, status=status,exit_code=code,tests=count,skipped=int(skip.group(1)) if skip else 0,
                duration_s=round(time.monotonic()-start,2),log=f'REGRESSION_MODULES/{module.replace(".","_")}.log')

start=time.monotonic()
results=[]
with ThreadPoolExecutor(max_workers=5) as pool:
    futures=[pool.submit(execute,m) for m in modules]
    for fut in as_completed(futures):
        r=fut.result();results.append(r)
        print(r['status'],r['module'],r['tests'],'skip',r['skipped'],'sec',r['duration_s'],flush=True)
results.sort(key=lambda r:r['module'])
summary={'platform':sys.platform,'python':sys.version.split()[0],'modules':len(modules),
         'tests':sum(r['tests'] or 0 for r in results),'skipped':sum(r['skipped'] for r in results),
         'failures':[r for r in results if r['status']!='PASS'],
         'duration_s':round(time.monotonic()-start,2),'results':results}
(root/'PH_LW_02_LOGS'/'REGRESSION_MATRIX.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print('SUMMARY',summary['tests'],'tests',summary['skipped'],'skips',len(summary['failures']),'failed modules',flush=True)
sys.exit(0 if not summary['failures'] else 1)
