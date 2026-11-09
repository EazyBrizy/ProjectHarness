"""Recheck public compilation of copied UI-approved input to a deep output."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path.insert(0,str(E/'src'))
from project_harness.platform_fs import _native_io_path,ensure_native_path
from project_harness.serialization import load_data
from project_harness.compiler import prepare_handoff
from project_harness.materialization import inspect_initial_handoff
S=ROOT/'_scratch/ph_lw_12_fix'
app=S/('Длинный-'+('x'*110))/'app-data-profile/ProjectHarness'
catalog=load_data(app/'catalog.json')
source=Path(next(x['root'] for x in catalog['projects'].values() if x['kind']=='workspace'))
assert source.is_relative_to(S) and source.name=='intake'
base=S/(sys.argv[1] if len(sys.argv)>1 else 'compile-deep-source');assert not base.exists()
root=base/'intake';ensure_native_path(source,tree=True)
shutil.copytree(_native_io_path(source),_native_io_path(root))
parent=base/('publication-'+('x'*120))/('staging-'+('y'*70))
assert len(str(parent))>260
_native_io_path(parent).mkdir(parents=True)
result=prepare_handoff(root,parent/'handoff.zip',keep_directory=parent/'project')
assert result['status']=='READY_FOR_CODEX',result
initial=inspect_initial_handoff(parent/'project',parent/'handoff.zip')
assert initial['tree_digest']
print(json.dumps({'status':'PASS','output_parent_length':len(str(parent)),'source':'Copied actual UI-approved provisional fixture; no record editing','result':result},ensure_ascii=False))
