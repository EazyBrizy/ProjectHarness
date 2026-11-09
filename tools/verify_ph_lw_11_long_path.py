"""Attest the separately authorized long-path correction and preserved history."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,winreg
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from verify_ph_lw_06_working_tree import verify_manifest
W=ROOT/'_workspace/PH_LW_11_LONG_PATH';S=ROOT/'_scratch/ph_lw_11_long_path';O=ENGINE/'PH_LW_11_LONG_PATH_LOGS'
ALLOWED={'compiler.py','platform_fs.py','hashing.py','serialization.py','workspace.py','validation.py','stages.py','materialization.py','local_web_preparation.py','resources/local_web/metadata_v1.json'}
DOC_ALLOWED={'README.md','FILE_INDEX.md','MANIFEST.sha256','Project_Harness_Architecture_v0.5.0_FULL.md','13_Local_Web_Manual_Companion/19_PH_LW_11_Windows_Installation.md'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
def main():
 final=W/'FINAL_WORKING_TREE_VERIFICATION.json'
 if final.exists() and read(final).get('status')=='PASS':raise RuntimeError('Completed attestation is immutable')
 before=read(W/'INPUT_FILE_HASHES.json');protected=history=0
 for name,digest in before.items():
  allowed=False
  if name.startswith(ENGINE.name+'/'):
   rel=name[len(ENGINE.name)+1:]
   allowed=(rel in {'README.md','MANIFEST.sha256'} or rel.startswith(('build/','dist/','windows/','docs/','src/project_harness_engine.egg-info/')))
   if rel.startswith('src/project_harness/'):allowed=rel.removeprefix('src/project_harness/') in ALLOWED
  elif name.startswith(DOCS.name+'/'):allowed=name[len(DOCS.name)+1:] in DOC_ALLOWED
  if not allowed:
   assert sha(ROOT/name)==digest,'Immutable input changed: '+name
   protected+=1;history+=int(name.startswith(ENGINE.name+'/PH_'))
 base=read(W/'INPUT_BASELINE.json')
 for name,digest in base['workspace_files'].items():
  if name not in {'README.md','_workspace/CURRENT_TASK.md','_workspace/PROJECT_MAP.md','_workspace/RUNBOOK.md'}:assert sha(ROOT/name)==digest,name
 archives=read(W/'PRESERVED_ARCHIVES.json')
 actual={p.relative_to(ROOT).as_posix() for p in [*(ROOT/'_deliverables').rglob('*.zip'),*ROOT.glob('*.zip')]}
 assert actual==set(archives)
 for name,digest in archives.items():assert sha(ROOT/name)==digest,name
 freeze=read(S/'FINAL_BUILD_FREEZE.json');src=ENGINE/'src/project_harness'
 source={p.relative_to(src).as_posix():sha(p) for p in files(src)};assert source==freeze['source_hashes']
 assert {p.relative_to(ENGINE).as_posix():sha(p) for d in (ENGINE/'tests',ENGINE/'local_web') for p in files(d)}==freeze['test_hashes']
 wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl';exe=ENGINE/'windows/Harness-Setup-win-x64.exe';bundle=ENGINE/'windows/Harness'
 assert sha(wheel)==freeze['wheel_sha256'] and sha(exe)==freeze['installer_sha256']
 build=read(ENGINE/'windows/BUILD_RESULT.json')
 assert build['source_files']==source and build['installer_sha256']==sha(exe)
 assert sha(bundle/'PACKAGE_FILES.json')==freeze['package_manifest_sha256']
 sys.path.insert(0,str(ENGINE/'src'))
 from project_harness.windows_package import verify_bundle
 inventory=verify_bundle(bundle)
 for name,digest in source.items():assert sha(bundle/'_internal/project_harness'/name)==digest,name
 assert {p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)}=={p.relative_to(bundle/'_internal/documentation').as_posix():sha(p) for p in files(bundle/'_internal/documentation')}
 evidence=read(O/'EVIDENCE_INDEX.json')
 for row in evidence:
  assert sha(ROOT/row['raw_source'])==row['raw_sha256']
  assert sha(O/row['file'])==row['published_sha256']
 verdict=read(O/'VERDICTS.json');assert verdict['long_path_preparation']=='PASS' and verdict['PH-LW-11']=='NO-GO'
 with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:setting=winreg.QueryValueEx(key,'LongPathsEnabled')[0]
 assert setting==read(W/'SOURCE_ENVIRONMENT.json')['long_paths_enabled']==0
 save(final,{'status':'VERIFYING'});save(W/'CHANGED_FILE_HASHES.json',[]);(W/'SHA256.txt').write_text('Verification in progress.\n','utf-8')
 commands=[]
 for label,command,cwd in [('workspace',[sys.executable,str(ROOT/'tools/check_workspace.py')],ROOT),('doctor',[sys.executable,str(ENGINE/'project-harness.py'),'doctor'],ENGINE),
  ('docs',[sys.executable,str(DOCS/'tools/validate_documentation.py'),str(DOCS),'--json',str(W/'DOC_VALIDATION.json')],ROOT),
  ('frozen-doctor',[str(bundle/'Harness.exe'),'--doctor'],ROOT),('frozen-integrity',[str(bundle/'Harness.exe'),'--check-package'],ROOT)]:
  log=W/(label+'.log')
  with log.open('wb') as stream:run=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=180,env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
  row={'command':command,'cwd':str(cwd),'exit':run.returncode,'status':'PASS' if run.returncode==0 else 'FAIL','log':log.name,'log_sha256':sha(log)}
  commands.append(row);assert run.returncode==0,row
 trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
 after={p.relative_to(ROOT).as_posix():sha(p) for d in (ENGINE,DOCS) for p in files(d)}
 names={n for n in before if n.startswith((ENGINE.name+'/',DOCS.name+'/'))}|set(after)
 save(W/'CHANGED_FILE_HASHES.json',[{'file':n,'before_sha256':before.get(n),'after_sha256':after.get(n)} for n in sorted(names) if before.get(n)!=after.get(n)])
 save(final,{'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),'scope':'Artifact integrity; long-path remediation PASS; full PH-LW-11 acceptance NO-GO',
  'trees':trees,'wheel_sha256':sha(wheel),'installer_sha256':sha(exe),'engine_build_digest':freeze['engine_build_digest'],
  'source_delta':read(O/'BUILD_PROVENANCE.json')['changed_source_files'],'immutable_files_verified':protected,'historical_engine_evidence_preserved':history,
  'evidence_files_verified':len(evidence),'archives_preserved':len(archives),'zip_created':False,'long_paths_enabled':setting,'system_settings_changed':False,
  'input_baseline_sha256':sha(W/'INPUT_BASELINE.json'),'input_file_hashes_sha256':sha(W/'INPUT_FILE_HASHES.json'),
  'changed_file_hashes_sha256':sha(W/'CHANGED_FILE_HASHES.json'),'commands':commands,'verdicts':verdict,
  'workspace_files':{p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'README.md',ROOT/'_workspace/CURRENT_TASK.md',ROOT/'_workspace/PROJECT_MAP.md',ROOT/'_workspace/RUNBOOK.md',*(ROOT/'tools').glob('*ph_lw_11_long_path*.py')]}})
 (W/'SHA256.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}' for p in [ENGINE/'MANIFEST.sha256',DOCS/'MANIFEST.sha256',wheel,exe,bundle/'PACKAGE_FILES.json',final,W/'CHANGED_FILE_HASHES.json'])+'\n','utf-8')
 print(json.dumps({'integrity':'PASS','long_path':'PASS','PH-LW-11':'NO-GO','history_preserved':history,'trees':trees},indent=2))
if __name__=='__main__':main()
