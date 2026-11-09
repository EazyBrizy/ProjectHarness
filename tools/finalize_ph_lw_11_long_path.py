"""Publish the separate PH-LW-11 long-path remediation; retain original NO-GO."""
from collections import Counter
import hashlib,json,re,sys
from pathlib import Path
from package_acceptance import ROOT,ENGINE,files
from finalize_evidence import sanitize
S=ROOT/'_scratch/ph_lw_11_long_path';W=ROOT/'_workspace/PH_LW_11_LONG_PATH';O=ENGINE/'PH_LW_11_LONG_PATH_LOGS'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(sanitize(json.dumps(v,ensure_ascii=False,indent=2))+'\n','utf-8')
def outcomes(path):
 text=path.read_text('utf-8-sig');starts=list(re.finditer(r'^test\S+ \((tests\.[^)]+)\)(?: \.\.\.)?[ \t]*',text,re.M));rows={}
 for i,m in enumerate(starts):
  chunk=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
  chunk=re.split(r'^={20,}|^-{20,}',chunk,maxsplit=1,flags=re.M)[0]
  found=next((status for status,pattern in [('ERROR',r'(?:^|\.\.\. )ERROR\s*$'),('FAIL',r'(?:^|\.\.\. )FAIL\s*$'),('SKIP',r'(?:^|\.\.\. )skipped '),('PASS',r'(?:^|\.\.\. )ok\s*$')] if re.search(pattern,chunk,re.M)),None)
  if found:rows[m.group(1)]={'status':found,'evidence':path.relative_to(S).as_posix()}
 return rows
def main():
 frozen=read(S/'FINAL_BUILD_FREEZE.json');src=ENGINE/'src/project_harness'
 assert frozen['source_hashes']=={p.relative_to(src).as_posix():sha(p) for p in files(src)}
 assert frozen['test_hashes']=={p.relative_to(ENGINE).as_posix():sha(p) for d in (ENGINE/'tests',ENGINE/'local_web') for p in files(d)}
 assert frozen['wheel_sha256']==sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')
 assert frozen['installer_sha256']==sha(ENGINE/'windows/Harness-Setup-win-x64.exe')
 adapter=read(S/'PRE_LONG_ADAPTER_FREEZE.json')
 assert all(adapter[k]==frozen[k] for k in ('source_hashes','wheel_sha256','installer_sha256','package_manifest_sha256'))
 changed=[p for p,h in adapter['test_hashes'].items() if frozen['test_hashes'].get(p)!=h]
 assert changed==['local_web/windows/long_path_acceptance.py'],changed
 save(S/'TEST_ADAPTER_DELTA.json',{'changed_files':changed,'artifact_inputs_unchanged':True,
  'scope':'Test fixture startup: long USERPROFILE/projects, separate short app-data; snapshots read all deep files and real app-data. No product assertion or timeout changed.'})
 core=read(S/'regressions/MATRIX.json');assert len(core)==18
 assert all(r['status'] in {'PASS','PASS_WITH_SKIPS'} for r in core),[(r['module'],r['status']) for r in core]
 current={}
 for row in core:current.update(outcomes(S/'regressions'/row['log']))
 runs=['installed-nonbrowser','installed-browser']
 run_counts={}
 for name in runs:
  assert read(S/'runs'/f'{name}.run.json')['status']=='PASS'
  log=S/'runs'/f'{name}.log';found=outcomes(log)
  assert all(r['status']=='PASS' for r in found.values()) and '"source_import": false' in log.read_text('utf-8')
  current.update(found);run_counts[name]=len(found)
 public=read(S/'public-recheck/RESULT.json');assert public['status']=='PASS' and public['leaf_length']>=277
 exe=read(S/'installed-long-final/RESULT.json');assert exe['status']=='PASS'
 assert exe['long_path']['maximum_retained_project_file_path_length']>260
 assert exe['long_path']['long_paths_enabled_before']==exe['long_path']['long_paths_enabled_after']==0
 recovery=read(S/'installer-recovery/RESULT.json');assert recovery['status']=='PASS'
 before=read(W/'INPUT_FILE_HASHES.json');prefix=ENGINE.name+'/src/project_harness/'
 delta=[p for p,v in frozen['source_hashes'].items() if before.get(prefix+p)!=v]
 verdict={'long_path_preparation':'PASS','PH-LW-11':'NO-GO','LOCAL_WEB_MANUAL':'NO-GO; PH-LW-12 not started',
  'AUTOMATIC_EXECUTOR':'NO-GO; disabled','v0.5.1':'NO-GO / NOT RELEASED','system_settings_changed':False,
  'mandatory_not_run':['Clean Windows without developer runtimes','Actual Unicode Windows username','Physical offline','Real volume/quota disk-full'],
  'additional_blockers':['Separate long app-data ZIP import: native WinError 206 creating quarantine materialized directory; not changed in preparation-only scope'],
  'core_scopes':len(core),'core_methods':sum(r['ran'] for r in core),'core_skips':[s for r in core for s in r['skips']],
  'installed_wheel':run_counts,'fresh_unique_methods':len(current),'method_statuses':dict(Counter(r['status'] for r in current.values())),
  'installed_exe_tests':exe['tests'],'maximum_project_file_path_length':exe['long_path']['maximum_retained_project_file_path_length'],
  'installer_recovery':recovery,'zip_created':False,
  'scope_note':'Fresh scoped regressions; prior full matrix retained as history. Automatic/upper-level full matrices not rerun or promoted to PASS.'}
 assert not any(v['status'] in {'FAIL','ERROR'} for v in current.values())
 O.mkdir(exist_ok=False);index=[]
 selected=[*S.glob('*.json'),*(S/'runs').glob('*.log'),*(S/'runs').glob('*.json'),
           *(S/'regressions').glob('*.log'),*(S/'regressions').glob('*.json'),S/'build/BUILD_RESULT.json',S/'public-recheck/RESULT.json']
 for folder in ('installed-long','installed-long-verified','installed-long-final','installer-recovery'):
  selected += [p for p in (S/folder).iterdir() if p.is_file() and p.suffix in {'.json','.log','.png'}]
  selected += [p for p in (S/folder/'screenshots').glob('*.png')]
 for p in sorted(set(selected)):
  rel=p.relative_to(S);target=O/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if p.suffix=='.png':target.write_bytes(p.read_bytes())
  else:target.write_text(sanitize(p.read_text('utf-8-sig',errors='replace')),'utf-8')
  index.append({'raw_source':p.relative_to(ROOT).as_posix(),'file':rel.as_posix(),'raw_sha256':sha(p),'published_sha256':sha(target)})
 save(O/'EVIDENCE_INDEX.json',index);save(O/'METHOD_RESULTS.json',{'scope':'Fresh runs only','methods':current})
 save(O/'VERDICTS.json',verdict)
 save(O/'BUILD_PROVENANCE.json',{'build_id':'PH-LW-11-LONGPATH-20261108',**{k:frozen[k] for k in ('engine_build_digest','wheel_sha256','installer_sha256','package_manifest_sha256')},
  'changed_source_files':delta,'baseline':read(W/'INPUT_BASELINE.json'),'signing':'UNSIGNED','zip_created':False})
 print(json.dumps({'verdict':verdict,'evidence_files':len(index),'source_delta':delta},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
