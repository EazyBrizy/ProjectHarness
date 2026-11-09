"""Bind PH-LW-10 unpacked deliverables to preserved inputs and test build."""
from datetime import datetime, timezone
import hashlib,json,os,subprocess,sys
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from verify_ph_lw_06_working_tree import verify_manifest
OUT=ROOT/'_workspace/PH_LW_10'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
ALLOWED_SOURCE={'lifecycle_forms.py','local_web_lifecycle.py','local_web_selection.py','local_web_service.py','local_web_http.py',
 'resources/local_web/assets/app.js','resources/local_web/assets/approvals.js','resources/local_web/assets/tasks.js','resources/local_web/assets/lifecycle.js',
 'resources/local_web/assets/app.css','resources/local_web/assets/index.html','resources/local_web/metadata_v1.json'}
def main():
    final=OUT/'FINAL_WORKING_TREE_VERIFICATION.json'
    if final.exists() and read(final).get('status')=='PASS':raise RuntimeError('Completed attestation is immutable')
    before=read(OUT/'INPUT_FILE_HASHES.json');immutable=history=0;prefix=ENGINE.name+'/src/project_harness/'
    mutable_docs={'README.md','FILE_INDEX.md','MANIFEST.sha256','Project_Harness_Architecture_v0.5.0_FULL.md'}
    for name,digest in before.items():
        parts=Path(name).parts
        protected=parts[0] in {'_inputs','Harness_Local_Web_Prompts_RU_r2','Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0'}
        protected |= parts[0]==ENGINE.name and (parts[1].startswith('PH_') or parts[1] in {'schemas','registries','tests'})
        protected |= name.startswith(prefix) and name.removeprefix(prefix) not in ALLOWED_SOURCE
        protected |= parts[0]==DOCS.name and '/'.join(parts[1:]) not in mutable_docs
        if protected:
            assert sha(ROOT/name)==digest,'Immutable input changed: '+name
            immutable+=1;history+=int(parts[0]==ENGINE.name and parts[1].startswith('PH_'))
    baseline=read(OUT/'INPUT_BASELINE.json')
    mutable_workspace={'README.md','_workspace/CURRENT_TASK.md','_workspace/PROJECT_MAP.md','_workspace/RUNBOOK.md','tools/check_workspace.py','tools/verify_installed.py'}
    for name,digest in baseline['workspace_files'].items():
        if name not in mutable_workspace:assert sha(ROOT/name)==digest,name
    archives=read(OUT/'PRESERVED_ARCHIVES.json')
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'_deliverables').rglob('*.zip')}|{p.relative_to(ROOT).as_posix() for p in ROOT.glob('*.zip')}
    assert actual==set(archives)
    for name,digest in archives.items():assert sha(ROOT/name)==digest,name
    frozen=read(ROOT/'_scratch/ph_lw_10/FINAL_BUILD_FREEZE.json');source=ENGINE/'src/project_harness'
    assert {p.relative_to(source).as_posix():sha(p) for p in files(source)}==frozen['source_hashes']
    assert {p.relative_to(ENGINE).as_posix():sha(p) for folder in (ENGINE/'tests',ENGINE/'local_web') for p in files(folder)}==frozen['test_hashes']
    for p in files(source):
        if p.relative_to(ROOT).as_posix() not in before:assert p.relative_to(source).as_posix() in ALLOWED_SOURCE
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl';assert sha(wheel)==frozen['wheel_sha256']
    evidence=read(ENGINE/'PH_LW_10_LOGS/EVIDENCE_INDEX.json')
    for row in evidence:
        assert sha(ROOT/row['raw_source'])==row['raw_sha256']
        assert sha(ENGINE/'PH_LW_10_LOGS'/row['file'])==row['published_sha256']
    verdict=read(ENGINE/'PH_LW_10_LOGS/NATIVE_SCOPE_VERDICT.json');assert verdict['status']=='PASS'
    save(final,{'status':'VERIFYING'});save(OUT/'CHANGED_FILE_HASHES.json',[]);(OUT/'SHA256.txt').write_text('Verification in progress.\n','utf-8')
    commands=[]
    for name,command,cwd in [('workspace',[sys.executable,str(ROOT/'tools/check_workspace.py')],ROOT),
        ('doctor',[sys.executable,str(ENGINE/'project-harness.py'),'doctor'],ENGINE),
        ('docs',[sys.executable,str(DOCS/'tools/validate_documentation.py'),str(DOCS),'--json',str(OUT/'DOC_VALIDATION.json')],ROOT)]:
        log=OUT/(name+'.log');started=datetime.now(timezone.utc).isoformat()
        with log.open('wb') as stream:result=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=180,env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
        row={'command':command,'cwd':str(cwd),'started_utc':started,'exit':result.returncode,'status':'PASS' if result.returncode==0 else 'FAIL','log':log.name,'log_sha256':sha(log)}
        commands.append(row);assert result.returncode==0,row
    trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
    after={p.relative_to(ROOT).as_posix():sha(p) for folder in (ENGINE,DOCS) for p in files(folder)}
    names={x for x in before if x.startswith((ENGINE.name+'/',DOCS.name+'/'))}|set(after)
    changes=[{'file':x,'before_sha256':before.get(x),'after_sha256':after.get(x)} for x in sorted(names) if before.get(x)!=after.get(x)]
    save(OUT/'CHANGED_FILE_HASHES.json',changes)
    workspace=sorted(set(baseline['workspace_files'])|{p.relative_to(ROOT).as_posix() for p in (ROOT/'tools').glob('*ph_lw_10*.py')})
    save(final,{'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),'scope':'PH-LW-10 unpacked working pair, not full release',
        'trees':trees,'wheel_sha256':sha(wheel),'engine_build_digest':frozen['engine_build_digest'],'immutable_files_verified':immutable,
        'historical_engine_evidence_preserved':history,'archives_preserved':len(archives),'zip_created':False,
        'input_baseline_sha256':sha(OUT/'INPUT_BASELINE.json'),'input_file_hashes_sha256':sha(OUT/'INPUT_FILE_HASHES.json'),
        'changed_file_hashes_sha256':sha(OUT/'CHANGED_FILE_HASHES.json'),'evidence_files_verified':len(evidence),'commands':commands,
        'native_acceptance':verdict,'workspace_files':{x:sha(ROOT/x) for x in workspace},
        'verdicts':{**{f'PH-LW-{x:02d}':'PASS' for x in range(4,11)},'LOCAL_WEB_MANUAL':'NO-GO','AUTOMATIC_EXECUTOR':'NO-GO','v0.5.1':'NO-GO / NOT RELEASED'},
        'mandatory_not_run':[],'next_step':'Only a new user task; PH-LW-11 not started'})
    (OUT/'SHA256.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}' for p in [ENGINE/'MANIFEST.sha256',DOCS/'MANIFEST.sha256',wheel,final,OUT/'CHANGED_FILE_HASHES.json'])+'\n','utf-8')
    print(json.dumps({'integrity_status':'PASS','stage_verdict':'PASS','trees':trees,'history_preserved':history,'evidence':len(evidence)},indent=2))
if __name__=='__main__':main()
