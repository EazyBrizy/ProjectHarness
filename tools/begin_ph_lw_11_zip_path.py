"""Capture the verified PH-LW-11 input for the separately authorized path fix."""
import hashlib,json,shutil
from datetime import datetime,timezone
from package_acceptance import ROOT,ENGINE,DOCS,files
from verify_ph_lw_06_working_tree import verify_manifest
out=ROOT/'_workspace/PH_LW_11_ZIP_PATH';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((ROOT/'_workspace/PH_LW_11_LONG_PATH/FINAL_WORKING_TREE_VERIFICATION.json').read_text('utf-8'))
trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
assert trees==prior['trees']
for name,value in prior['workspace_files'].items():assert sha(ROOT/name)==value,name
assert sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')==prior['wheel_sha256']
assert sha(ENGINE/'windows/Harness-Setup-win-x64.exe')==prior['installer_sha256']
before={p.relative_to(ROOT).as_posix():sha(p) for folder in (ENGINE,DOCS,ROOT/'_inputs',ROOT/'Harness_Local_Web_Prompts_RU_r2',ROOT/'Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0',ROOT/'_workspace/PH_LW_11',ROOT/'_workspace/PH_LW_11_LONG_PATH') for p in files(folder)}
archives={p.relative_to(ROOT).as_posix():sha(p) for p in [*(ROOT/'_deliverables').rglob('*.zip'),*ROOT.glob('*.zip')]}
for name,value in [('INPUT_FILE_HASHES.json',before),('PRESERVED_ARCHIVES.json',archives),('INPUT_BASELINE.json',{'status':'PASS','captured_utc':datetime.now(timezone.utc).isoformat(),'trees':trees,'wheel_sha256':prior['wheel_sha256'],'installer_sha256':prior['installer_sha256'],'workspace_files':prior['workspace_files'],'drift':[]})]:
 (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
shutil.copy2(ROOT/'_workspace/CURRENT_TASK.md',out/'CURRENT_TASK.before.md')
print(json.dumps({'status':'PASS','files':len(before),'trees':trees},indent=2))

