"""Reproduce the manual long-path blocker with exact command/build provenance."""
import hashlib,json,platform,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
from tests.ph_f06_fixtures import prepared
from project_harness.compiler import prepare_handoff
out=ROOT/'_scratch/ph_lw_11/long-path-final';out.mkdir(exist_ok=False)
fixture=ROOT/'_scratch/Л11long';fixture.mkdir(exist_ok=False)
prepared(fixture/'fixture',target='PROTOTYPE')
keep=fixture/('Длинный-'+('x'*116))/'project'
metadata=json.loads((ENGINE/'src/project_harness/resources/local_web/metadata_v1.json').read_text('utf-8'))
record={'platform':platform.platform(),'python':sys.version,'engine_build_digest':metadata['engine_build_digest'],
 'public_api':'prepare_handoff','workspace':str(fixture/'fixture/intake'),'keep_directory':str(keep),
 'leaf_length':len(str(keep/'.harness/engine/project_harness/resources/schemas/maintenance_cancel_approval.schema.json')),
 'security_settings_changed':False}
try:
 result=prepare_handoff(fixture/'fixture/intake',out/'diagnostic-handoff.zip',keep_directory=keep)
 record.update(status='PASS',result=result)
except Exception as exc:
 record.update(status='FAIL',exception=type(exc).__name__,message=str(exc))
 (out/'ERROR.txt').write_text(traceback.format_exc(),'utf-8');traceback.print_exc()
(out/'RESULT.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
raise SystemExit(0 if record['status']=='PASS' else 1)
