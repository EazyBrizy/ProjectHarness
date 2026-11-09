"""Publish fresh PH-LW-11 long app-data ZIP evidence, preserving prior failures."""
from collections import Counter
import json
from package_acceptance import ROOT,ENGINE,files
from finalize_ph_lw_11_long_path import outcomes as legacy_outcomes
from finalize_evidence import sanitize
import hashlib,re
S=ROOT/'_scratch/ph_lw_11_zip_path';W=ROOT/'_workspace/PH_LW_11_ZIP_PATH';O=ENGINE/'PH_LW_11_ZIP_PATH_LOGS'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(sanitize(json.dumps(v,ensure_ascii=False,indent=2))+'\n','utf-8')
def outcomes(path):
 # Reuse the immutable parser with this output root, not the old evidence root.
 import finalize_ph_lw_11_long_path as parser
 old=parser.S
 try:parser.S=S;return legacy_outcomes(path)
 finally:parser.S=old

def main():
 frozen=read(S/'FINAL_BUILD_FREEZE.json');src=ENGINE/'src/project_harness'
 assert frozen['source_hashes']=={p.relative_to(src).as_posix():sha(p) for p in files(src)}
 assert frozen['test_hashes']=={p.relative_to(ENGINE).as_posix():sha(p) for d in (ENGINE/'tests',ENGINE/'local_web') for p in files(d)}
 assert frozen['wheel_sha256']==sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')
 assert frozen['installer_sha256']==sha(ENGINE/'windows/Harness-Setup-win-x64.exe')
 assert read(S/'LOGIC_DELTA.json')['status']=='PASS'
 assert read(S/'TEST_ADAPTER_DELTA.json')['status']=='PASS'
 core=read(S/'regressions-final/MATRIX.json');assert len(core)==20
 assert all(r['status'] in {'PASS','PASS_WITH_SKIPS'} for r in core),[(r['module'],r['status']) for r in core]
 current={}
 for row in core:current.update(outcomes(S/'regressions-final'/row['log']))
 run_counts={}
 for label in ('nonbrowser','browser'):
  name='installed-final-'+label
  assert read(S/'runs'/f'{name}.run.json')['status']=='PASS'
  log=S/'runs'/f'{name}.log';found=outcomes(log)
  assert found and all(r['status']=='PASS' for r in found.values()) and '"source_import": false' in log.read_text('utf-8')
  current.update(found);run_counts['installed-'+label]=len(found)
 exe=read(S/'installed-long-verified/RESULT.json');assert exe['status']=='PASS'
 long=exe['long_path']
 assert long['maximum_retained_project_file_path_length']>260 and long['maximum_retained_app_data_file_path_length']>260
 assert long['retained_import_document_count']>0
 assert long['long_paths_enabled_before']==long['long_paths_enabled_after']==0
 recovery=read(S/'installer-recovery-final/RESULT.json');assert recovery['status']=='PASS'
 before=read(W/'INPUT_FILE_HASHES.json');prefix=ENGINE.name+'/src/project_harness/'
 delta=[p for p,v in frozen['source_hashes'].items() if before.get(prefix+p)!=v]
 verdict={'long_app_data_zip_import':'PASS','PH-LW-11':'NO-GO','LOCAL_WEB_MANUAL':'NO-GO; PH-LW-12 not started','AUTOMATIC_EXECUTOR':'NO-GO; disabled','v0.5.1':'NO-GO / NOT RELEASED','system_settings_changed':False,
  'mandatory_not_run':['Clean Windows without developer runtimes','Actual Unicode Windows username','Physical offline','Real volume/quota disk-full'],
  'additional_blockers':[], 'normal_second_launch_browser_fresh':'NOT RUN per explicit user prohibition of new visible browser windows; exact second --no-browser rejection exit 1 checked; historical normal-launch evidence preserved', 'core_scopes':len(core),'core_methods':sum(r['ran'] for r in core),'core_skips':[s for r in core for s in r['skips']],
  'installed_wheel':run_counts,'fresh_unique_methods':len(current),'method_statuses':dict(Counter(r['status'] for r in current.values())),
  'installed_exe_tests':exe['tests'],'long_path':long,'installer_recovery':recovery,'zip_created':False,
  'scope_note':'Fresh scoped regressions; historical full matrix preserved. Automatic/upper-level matrices not rerun or promoted. Existing unsigned status and unfinished visual walkthrough retained.'}
 assert not any(v['status'] in {'FAIL','ERROR'} for v in current.values())
 O.mkdir(exist_ok=False);index=[]
 selected=[*S.glob('*.json'),*(S/'runs').glob('*.log'),*(S/'runs').glob('*.json'),*(S/'regressions').glob('*.log'),*(S/'regressions').glob('*.json'),*(S/'regressions-final').glob('*.log'),*(S/'regressions-final').glob('*.json'),S/'build-final/BUILD_RESULT.json']
 for folder in ('installed-long','installed-long-final','installed-long-verified','installer-recovery','installer-recovery-final'):
  selected += [p for p in (S/folder).iterdir() if p.is_file() and p.suffix in {'.json','.log','.png'}]
  selected += list((S/folder/'screenshots').glob('*.png'))
 for p in sorted(set(selected)):
  rel=p.relative_to(S);target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if p.suffix=='.png':target.write_bytes(p.read_bytes())
  else:target.write_text(sanitize(p.read_text('utf-8-sig',errors='replace')),'utf-8')
  index.append({'raw_source':p.relative_to(ROOT).as_posix(),'file':rel.as_posix(),'raw_sha256':sha(p),'published_sha256':sha(target)})
 save(O/'EVIDENCE_INDEX.json',index);save(O/'METHOD_RESULTS.json',{'scope':'Fresh final runs only; diagnostic failures retained separately','methods':current})
 save(O/'VERDICTS.json',verdict)
 save(O/'BUILD_PROVENANCE.json',{'build_id':'PH-LW-11-ZIPPATH-20261108',**{k:frozen[k] for k in ('engine_build_digest','wheel_sha256','installer_sha256','package_manifest_sha256')},'changed_source_files':delta,'baseline':read(W/'INPUT_BASELINE.json'),'signing':'UNSIGNED','zip_created':False})
 print(json.dumps({'verdict':verdict,'evidence_files':len(index),'source_delta':delta},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
