"""Build and freeze snapshot-polling fix after deterministic before/after proof."""
import json,shutil,subprocess,sys
from ph_lw_12_fix_run import ROOT,OUT,W,ENGINE,run
from package_acceptance import DOCS
for name in ('RUNTIME_FREEZE','WHEEL_ENVIRONMENT','DISCOVERY','MATURITY_SETUP_CACHE'):
    target=W/(name+'_CANDIDATE_04.json');assert not target.exists()
    shutil.copy2(W/(name+'.json'),target)
previous=OUT/'candidate-04';previous.mkdir()
shutil.copy2(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl',previous)
meta=ENGINE/'src/project_harness/resources/local_web/metadata_v1.json'
data=json.loads(meta.read_text('utf-8'));data['local_web_build_id']='PH-LW-12-FIX5-20261108'
data['note']='Windows PH-LW-12 blocker and snapshot-polling fixes; pre-acceptance immutable build. Exact-hash verdict in PH_LW_12_FIX_TEST_REPORT.md; automatic executor disabled; full v0.5.1 NOT RELEASED.'
meta.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
current=ROOT/'_workspace/CURRENT_TASK.md'
current.write_text('PH-LW-12 FIX5 IN PROGRESS: найден и детерминированно исправлен snapshot-polling race. Прежние provisional GO не являются окончательной аттестацией. Требуются новая полная Windows matrix и actual installer acceptance. Automatic executor выключен; ZIP не создавать.\n\n'+current.read_text('utf-8'),'utf-8')
assert run('sync-build-wheel-05',[sys.executable,'-B',ROOT/'tools/sync_working_tree.py','--build-wheel'],timeout=180)['status']=='PASS'
assert run('docs-before-build-05',[sys.executable,'-B',DOCS/'tools/validate_documentation.py',DOCS,
    '--json',W/'DOC_VALIDATION_BEFORE_BUILD_05.json'],timeout=120)['status']=='PASS'
command=json.loads((OUT/'build-03.run.json').read_text('utf-8'))['command'];command[command.index('--output')+1]=str(OUT/'build-05')
assert run('build-05',command,timeout=900)['status']=='PASS'
subprocess.run([sys.executable,'-B',ROOT/'tools/ph_lw_12_fix_artifacts.py','--build','build-05','--preserve','candidate-04'],check=True)
wheel=OUT/'wheel-venv/Scripts/python.exe'
assert run('wheel-install-final05',[wheel,'-m','pip','install','--no-index','--no-deps','--force-reinstall',
    ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'],timeout=120)['status']=='PASS'
import ph_lw_12_acceptance as runner
runner.OUT=W;runner.RUNS=OUT;runner.discover()
subprocess.run([wheel,'-B',ROOT/'tools/ph_lw_12_fix_environment.py'],cwd=OUT/'Независимая папка wheel',check=True)
(W/'FINAL05_TEST_FREEZE_READY.json').write_text(json.dumps({'status':'READY',
    'freeze':json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))['engine_build_digest'],
    'runtime_mutation_allowed':False},indent=2)+'\n','utf-8')
print('Final05 source/wheel/frozen/installer ready; full exact-byte tests required',flush=True)
