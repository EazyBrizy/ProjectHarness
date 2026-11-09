"""Finish independent delivery tests after the sequential backend rechecks."""
import subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'_scratch/ph_lw_12'
required=['maturity-final','exchange-http-final','lifecycle-http-final','lifecycle-service-final']
deadline=time.monotonic()+5400
while not all((S/(name+'.run.json')).exists() for name in required):
    if time.monotonic()>deadline:raise RuntimeError('Backend test pipeline did not finish; no result promotion')
    time.sleep(1)
results=[]
for mode in ('extended','wheel-browser','source'):
    code=subprocess.run([sys.executable,'-B',str(ROOT/'tools/ph_lw_12_final_runs.py'),mode],cwd=ROOT).returncode
    results.append({'mode':mode,'exit':code});print(mode,'exit',code,flush=True)
raise SystemExit(not all(row['exit']==0 for row in results))
