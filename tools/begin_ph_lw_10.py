"""Capture PH-LW-10 input without modifying historical attestations."""
import hashlib, json, shutil, sys
from datetime import datetime, timezone
from package_acceptance import ROOT, ENGINE, DOCS, files
from verify_ph_lw_06_working_tree import verify_manifest

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / '_workspace/PH_LW_10'
out.mkdir(exist_ok=False)
prior = json.loads((ROOT/'_workspace/PH_LW_09_MANUAL_EVIDENCE/FINAL_WORKING_TREE_VERIFICATION.json').read_text('utf-8'))
trees = {p.relative_to(ROOT).as_posix(): verify_manifest(p) for p in (ENGINE, DOCS, ENGINE/'docs'/DOCS.name)}
assert trees == prior['trees']
wheel = ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'
assert sha(wheel) == prior['wheel_sha256']
for name, digest in prior['workspace_files'].items(): assert sha(ROOT/name) == digest, name
before = {p.relative_to(ROOT).as_posix():sha(p) for folder in (ENGINE, DOCS, ROOT/'_inputs', ROOT/'Harness_Local_Web_Prompts_RU_r2', ROOT/'Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0') for p in files(folder)}
archives = {p.relative_to(ROOT).as_posix():sha(p) for p in list((ROOT/'_deliverables').rglob('*.zip'))+list(ROOT.glob('*.zip'))}
for name, data in [('INPUT_FILE_HASHES.json',before),('PRESERVED_ARCHIVES.json',archives),('INPUT_BASELINE.json',{'status':'PASS','captured_utc':datetime.now(timezone.utc).isoformat(),'source_checkpoint':'PH-LW-09 MANUAL EVIDENCE PASS with explicit rechecks','trees':trees,'wheel_sha256':sha(wheel),'workspace_files':prior['workspace_files'],'drift':[]})]:
    (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
shutil.copy2(ROOT/'_workspace/CURRENT_TASK.md',out/'CURRENT_TASK.before.md')
print(json.dumps({'status':'PASS','files':len(before),'trees':trees,'wheel_sha256':sha(wheel)},indent=2))


