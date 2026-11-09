from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess, sys, os, time, pathlib
modules=['tests.test_ph_f01_planner_regression','tests.test_ph_f03_active_stage_planning','tests.test_ph_f04_runtime_reachability']
base=pathlib.Path('PH_LW_02_LOGS/RERUN_EXEC_MODE_FAILURES')
def run(mod):
 t=time.monotonic(); p=subprocess.run([sys.executable,'-B','-m','unittest','-v',mod],env={**os.environ,'PYTHONPATH':'src:.','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=400); (base/(mod.replace('.','_')+'.log')).write_text(p.stdout+p.stderr,encoding='utf8'); return mod,p.returncode,round(time.monotonic()-t,1)
with ThreadPoolExecutor(max_workers=3) as ex:
 for f in as_completed([ex.submit(run,mod) for mod in modules]):
  print(f.result(),flush=True)
