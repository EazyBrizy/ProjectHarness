"""Offline, hash-locked independent PH-LW-10 wheel acceptance environment."""
from pathlib import Path
import json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_scratch/ph_lw_10'
ENV=OUT/'wheel-venv'
assert not ENV.exists(), 'Use a new environment; do not replace an existing acceptance run'
def run(command):
    print(json.dumps(list(map(str,command)),ensure_ascii=False),flush=True)
    subprocess.run(list(map(str,command)),check=True,env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
run([ROOT/'_tools/Python314/python.exe','-m','venv',ENV])
python=ENV/'Scripts/python.exe'
for lock,house in [('Project_Harness_Engine_v0.5.1/local_web/requirements-web-win_amd64-cp314.lock','_tools/wheelhouse'),('_workspace/requirements-dev-win_amd64-cp314.lock','_tools/devwheelhouse')]:
    run([python,'-m','pip','install','--no-index','--find-links',ROOT/house,'--require-hashes','-r',ROOT/lock])
run([python,'-m','pip','install','--no-deps','--no-index',ROOT/'Project_Harness_Engine_v0.5.1/dist/project_harness_engine-0.5.1-py3-none-any.whl'])
cwd=OUT/'Независимая папка wheel';cwd.mkdir()
code="import sys,json,platform;from importlib.metadata import version;import project_harness;print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'package':project_harness.__file__,'dependencies':{x:version(x) for x in ['flask','waitress','playwright','PyYAML','jsonschema']}},indent=2))"
result=subprocess.run([str(python),'-B','-c',code],cwd=cwd,env={**os.environ,'PYTHONPATH':'','PYTHONUTF8':'1'},capture_output=True,text=True,check=True)
(OUT/'WHEEL_ENVIRONMENT.json').write_text(result.stdout,'utf-8')
print(result.stdout,flush=True)

