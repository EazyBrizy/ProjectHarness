"""Publish the corrected immutable candidate after earlier EXE tests stop."""
import json,os,shutil,subprocess,sys,time
from ph_lw_12_fix_run import ROOT,OUT,W,ENGINE,run
deadline=time.monotonic()+3000
while not (OUT/'installed-extended.run.json').exists() or not (OUT/'build-02.run.json').exists():
    if time.monotonic()>deadline:raise RuntimeError('Previous frozen suite/build still active')
    time.sleep(1)
assert json.loads((OUT/'build-02.run.json').read_text('utf-8'))['status']=='PASS'
subprocess.run([sys.executable,'-B',str(ROOT/'tools/ph_lw_12_fix_artifacts.py'),'--build','build-02','--preserve','candidate-01'],check=True)
shutil.copy2(W/'WHEEL_ENVIRONMENT.json',W/'WHEEL_ENVIRONMENT_CANDIDATE_01.json')
wheel=OUT/'wheel-venv/Scripts/python.exe'
result=run('wheel-install-final',[wheel,'-m','pip','install','--no-index','--no-deps','--force-reinstall',
    ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'],timeout=120)
assert result['status']=='PASS'
import ph_lw_12_acceptance as runner
runner.OUT=W;runner.RUNS=OUT;runner.discover()
(W/'FINAL_TEST_FREEZE_READY.json').write_text(json.dumps({'status':'READY','freeze':json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))['engine_build_digest'],'runtime_mutation_allowed':False},indent=2)+'\n','utf-8')
print('Final runtime published; all subsequent acceptance must bind this freeze',flush=True)
