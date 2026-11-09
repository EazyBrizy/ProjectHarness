"""Attest the final unpacked PH-LW-11 bundle without claiming acceptance GO."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from verify_ph_lw_06_working_tree import verify_manifest
OUT=ROOT/'_workspace/PH_LW_11'
ALLOWED_SOURCE={'local_web_desktop.py','local_web_instance.py','windows_package.py',
 'local_web_launcher.py','local_web_http.py','resources.py',
 'resources/local_web/assets/app.js','resources/local_web/assets/index.html','resources/local_web/metadata_v1.json'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')

def main():
    final=OUT/'FINAL_WORKING_TREE_VERIFICATION.json'
    if final.exists() and read(final).get('status')=='PASS':raise RuntimeError('Completed attestation is immutable')
    before=read(OUT/'INPUT_FILE_HASHES.json');immutable=history=0;prefix=ENGINE.name+'/src/project_harness/'
    mutable_docs={'README.md','FILE_INDEX.md','MANIFEST.sha256','Project_Harness_Architecture_v0.5.0_FULL.md'}
    for name,digest in before.items():
        parts=Path(name).parts
        protected=parts[0] in {'_inputs','Harness_Local_Web_Prompts_RU_r2','Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0'}
        protected|=parts[0]==ENGINE.name and (parts[1].startswith('PH_') or parts[1] in {'schemas','registries','tests'})
        protected|=name.startswith(prefix) and name.removeprefix(prefix) not in ALLOWED_SOURCE
        protected|=parts[0]==DOCS.name and '/'.join(parts[1:]) not in mutable_docs
        if protected:
            assert sha(ROOT/name)==digest,'Immutable input changed: '+name
            immutable+=1;history+=int(parts[0]==ENGINE.name and parts[1].startswith('PH_'))
    baseline=read(OUT/'INPUT_BASELINE.json')
    allowed_workspace={'README.md','_workspace/CURRENT_TASK.md','_workspace/PROJECT_MAP.md','_workspace/RUNBOOK.md','tools/check_workspace.py','tools/verify_installed.py'}
    for name,digest in baseline['workspace_files'].items():
        if name not in allowed_workspace:assert sha(ROOT/name)==digest,name
    archives=read(OUT/'PRESERVED_ARCHIVES.json')
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'_deliverables').rglob('*.zip')}|{p.relative_to(ROOT).as_posix() for p in ROOT.glob('*.zip')}
    assert actual==set(archives)
    for name,digest in archives.items():assert sha(ROOT/name)==digest,name
    frozen=read(ROOT/'_scratch/ph_lw_11/FINAL_BUILD_FREEZE.json');src=ENGINE/'src/project_harness'
    source_files={p.relative_to(src).as_posix():sha(p) for p in files(src)}
    assert source_files==frozen['source_hashes']
    assert {p.relative_to(ENGINE).as_posix():sha(p) for d in (ENGINE/'tests',ENGINE/'local_web') for p in files(d)}==frozen['test_hashes']
    for p in files(src):
        if p.relative_to(ROOT).as_posix() not in before:assert p.relative_to(src).as_posix() in ALLOWED_SOURCE
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl';installer=ENGINE/'windows/Harness-Setup-win-x64.exe'
    assert sha(wheel)==frozen['wheel_sha256'];assert sha(installer)==frozen['installer_sha256']
    build=read(ENGINE/'windows/BUILD_RESULT.json');assert build['source_files']==source_files and build['installer_sha256']==sha(installer)
    bundle=ENGINE/'windows/Harness'
    assert sha(bundle/'PACKAGE_FILES.json')==frozen['package_manifest_sha256']
    sys.path.insert(0,str(ENGINE/'src'))
    from project_harness.windows_package import verify_bundle
    inventory=verify_bundle(bundle)
    for name,digest in source_files.items():assert sha(bundle/'_internal/project_harness'/name)==digest,name
    docs_files={p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)}
    assert {p.relative_to(bundle/'_internal/documentation').as_posix():sha(p) for p in files(bundle/'_internal/documentation')}==docs_files
    evidence=read(ENGINE/'PH_LW_11_LOGS/EVIDENCE_INDEX.json')
    for row in evidence:
        assert sha(ROOT/row['raw_source'])==row['raw_sha256']
        assert sha(ENGINE/'PH_LW_11_LOGS'/row['file'])==row['published_sha256']
    verdict=read(ENGINE/'PH_LW_11_LOGS/NATIVE_SCOPE_VERDICT.json');assert verdict['status']=='NO-GO'
    save(final,{'status':'VERIFYING'});save(OUT/'CHANGED_FILE_HASHES.json',[]);(OUT/'SHA256.txt').write_text('Verification in progress.\n','utf-8')
    commands=[]
    for name,command,cwd in [('workspace',[sys.executable,str(ROOT/'tools/check_workspace.py')],ROOT),
        ('doctor',[sys.executable,str(ENGINE/'project-harness.py'),'doctor'],ENGINE),
        ('docs',[sys.executable,str(DOCS/'tools/validate_documentation.py'),str(DOCS),'--json',str(OUT/'DOC_VALIDATION.json')],ROOT),
        ('frozen-doctor',[str(bundle/'Harness.exe'),'--doctor'],ROOT),('frozen-integrity',[str(bundle/'Harness.exe'),'--check-package'],ROOT)]:
        log=OUT/(name+'.log');started=datetime.now(timezone.utc).isoformat()
        with log.open('wb') as stream:result=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=180,env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
        row={'command':command,'cwd':str(cwd),'started_utc':started,'exit':result.returncode,'status':'PASS' if result.returncode==0 else 'FAIL','log':log.name,'log_sha256':sha(log)}
        commands.append(row);assert result.returncode==0,row
    trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
    after={p.relative_to(ROOT).as_posix():sha(p) for folder in (ENGINE,DOCS) for p in files(folder)}
    names={x for x in before if x.startswith((ENGINE.name+'/',DOCS.name+'/'))}|set(after)
    changes=[{'file':x,'before_sha256':before.get(x),'after_sha256':after.get(x)} for x in sorted(names) if before.get(x)!=after.get(x)]
    save(OUT/'CHANGED_FILE_HASHES.json',changes)
    workspace=sorted(set(baseline['workspace_files'])|{p.relative_to(ROOT).as_posix() for p in (ROOT/'tools').glob('*ph_lw_11*.py')})
    save(final,{'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),'scope':'Artifact integrity only; PH-LW-11 acceptance NO-GO',
        'trees':trees,'wheel_sha256':sha(wheel),'installer_sha256':sha(installer),'frozen_files':len(inventory['files']),
        'engine_build_digest':frozen['engine_build_digest'],'immutable_files_verified':immutable,'historical_engine_evidence_preserved':history,
        'archives_preserved':len(archives),'zip_created':False,'input_baseline_sha256':sha(OUT/'INPUT_BASELINE.json'),
        'input_file_hashes_sha256':sha(OUT/'INPUT_FILE_HASHES.json'),'changed_file_hashes_sha256':sha(OUT/'CHANGED_FILE_HASHES.json'),
        'evidence_files_verified':len(evidence),'commands':commands,'native_acceptance':verdict,
        'workspace_files':{x:sha(ROOT/x) for x in workspace},
        'verdicts':{**{f'PH-LW-{x:02d}':'Prior accepted scope preserved; current completed/partial regressions in method matrix' for x in range(4,11)},
            'PH-LW-11':'NO-GO','LOCAL_WEB_MANUAL':'NO-GO','AUTOMATIC_EXECUTOR':'NO-GO','v0.5.1':'NO-GO / NOT RELEASED'},
        'mandatory_not_run':verdict['mandatory_not_run'],'next_step':'New user task to close PH-LW-11 blockers; PH-LW-12 not started'})
    (OUT/'SHA256.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}' for p in [ENGINE/'MANIFEST.sha256',DOCS/'MANIFEST.sha256',wheel,installer,bundle/'PACKAGE_FILES.json',final,OUT/'CHANGED_FILE_HASHES.json'])+'\n','utf-8')
    print(json.dumps({'integrity_status':'PASS','stage_verdict':'NO-GO','trees':trees,'history_preserved':history,'evidence':len(evidence)},indent=2))

if __name__=='__main__':main()
