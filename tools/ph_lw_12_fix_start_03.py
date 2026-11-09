"""Freeze the fully diagnosed Windows IO candidate and install exact wheel."""
import json,shutil,subprocess,sys,time
from ph_lw_12_fix_run import ROOT,OUT,W,ENGINE,run
while not (OUT/'build-03.run.json').exists():time.sleep(1)
assert json.loads((OUT/'build-03.run.json').read_text('utf-8'))['status']=='PASS'
assert (OUT/'final-installed-extended.run.json').exists() # previous frozen process stopped
subprocess.run([sys.executable,'-B',str(ROOT/'tools/ph_lw_12_fix_artifacts.py'),'--build','build-03','--preserve','candidate-02'],check=True)
shutil.copy2(W/'WHEEL_ENVIRONMENT.json',W/'WHEEL_ENVIRONMENT_CANDIDATE_02.json')
wheel=OUT/'wheel-venv/Scripts/python.exe'
result=run('wheel-install-final03',[wheel,'-m','pip','install','--no-index','--no-deps','--force-reinstall',
    ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'],timeout=120)
assert result['status']=='PASS'
import ph_lw_12_acceptance as runner
runner.OUT=W;runner.RUNS=OUT;runner.discover()
subprocess.run([str(wheel),'-B',str(ROOT/'tools/ph_lw_12_fix_environment.py')],cwd=OUT/'Независимая папка wheel',check=True)
(W/'FINAL03_TEST_FREEZE_READY.json').write_text(json.dumps({'status':'READY',
    'freeze':json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))['engine_build_digest'],
    'runtime_mutation_allowed':False},indent=2)+'\n','utf-8')
print('Final03 runtime frozen and installed',flush=True)
