"""Repeat the original public prepare_handoff failure on a new owned fixture."""
import json,platform,sys,winreg
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
from tests.ph_f06_fixtures import prepared
from project_harness.compiler import prepare_handoff
from project_harness.validation import validate_handoff,validate_project_directory
out=ROOT/'_scratch/ph_lw_11_long_path/public-recheck';out.mkdir(exist_ok=False)
fixture=ROOT/'_scratch/Л11long-fix';fixture.mkdir(exist_ok=False)
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
 before=winreg.QueryValueEx(key,'LongPathsEnabled')[0]
prepared(fixture/'fixture',target='PROTOTYPE')
keep=fixture/('Длинный-'+('x'*116))/'project'
result=prepare_handoff(fixture/'fixture/intake',out/'diagnostic-handoff.zip',keep_directory=keep)
directory=validate_handoff(keep);mutable=validate_project_directory(keep)
assert directory['status']==mutable['status']=='PASS'
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
 after=winreg.QueryValueEx(key,'LongPathsEnabled')[0]
assert before==after==0
value={'status':'PASS','public_api':'prepare_handoff','python':sys.version,'platform':platform.platform(),
 'leaf_length':len(str(keep/'.harness/engine/project_harness/resources/schemas/maintenance_cancel_approval.schema.json')),
 'long_paths_enabled_before':before,'long_paths_enabled_after':after,'system_settings_changed':False,
 'build_digest':json.loads((ENGINE/'src/project_harness/resources/local_web/metadata_v1.json').read_text('utf-8'))['engine_build_digest'],
 'directory_validation':directory['status'],'mutable_validation':mutable['status'],'result':result}
(out/'RESULT.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(value,ensure_ascii=False,indent=2))
