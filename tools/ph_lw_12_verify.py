"""Final immutable-byte/documentary attestation; verdicts remain independent."""
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,sys,zipfile
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from verify_ph_lw_06_working_tree import verify_manifest

W=ROOT/'_workspace/PH_LW_12';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def run(name,command):
    log=W/(name+'.log')
    attempt=1
    while log.exists():
        log=W/(name+'-attempt-'+str(attempt)+'.log');attempt+=1
    with log.open('wb') as stream:
        p=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=240,
            env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
    row={'command':list(map(str,command)),'cwd':str(ROOT),'exit':p.returncode,
         'status':'PASS' if p.returncode==0 else 'FAIL','log':log.name,'log_sha256':sha(log)}
    save(log.with_suffix('.run.json'),row)
    assert p.returncode==0,row
    return row

def main():
    freeze=json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))
    source=ENGINE/'src/project_harness'
    assert freeze['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
    assert freeze['documentation_hashes']=={p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)}
    before=json.loads((W/'INPUT_FILE_HASHES.json').read_text('utf-8'))
    history=[];tests=[]
    for name,digest in before.items():
        path=ROOT/name
        protected=(name.startswith(('_inputs/','Harness_Local_Web_Prompts_RU_r2/',
                    'Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/')) or
                   (name.startswith(ENGINE.name+'/PH_') and not name.startswith(ENGINE.name+'/PH_LW_12')) or
                   (name.startswith('_workspace/PH_') and not name.startswith('_workspace/PH_LW_12/')))
        if protected:assert path.is_file() and sha(path)==digest,name;history.append(name)
        if name.startswith(ENGINE.name+'/tests/'):
            assert path.is_file() and sha(path)==digest,name;tests.append(name)
    old=ROOT/'_scratch/ph_lw_12/input-frozen/_internal/project_harness/local_web_service.py'
    text=old.read_text('utf-8')
    text=text.replace('Доступно в следующем этапе Local Web; сейчас операция не реализована.',
                      'В текущем Local Web интерфейсе эта операция не реализована.')
    assert text==(source/'local_web_service.py').read_text('utf-8')
    save(W/'SERVICE_TEXT_ONLY_DELTA.json',{'status':'PASS','before_sha256':sha(old),
        'after_sha256':sha(source/'local_web_service.py'),'only_disabled_reason_string_changed':True})
    # Create the final link destination before checking local links. This file
    # lives outside the immutable delivery tree; PASS is written only at end.
    save(W/'FINAL_WORKING_TREE_VERIFICATION.json',{'status':'IN PROGRESS','artifact_checks_only':True})
    if not (W/'SHA256.txt').exists():
        (W/'SHA256.txt').write_text('# IN PROGRESS: final output hashes follow successful artifact checks.\n','utf-8')
    if not (W/'CHANGED_FILE_HASHES.json').exists():save(W/'CHANGED_FILE_HASHES.json',[])
    commands=[run('workspace-final',[sys.executable,'-B',ROOT/'tools/check_workspace.py']),
        run('documentation-final',[sys.executable,'-B',DOCS/'tools/validate_documentation.py',DOCS,
             '--json',W/'DOC_VALIDATION.json']),
        run('doctor-final',[sys.executable,'-B',ENGINE/'project-harness.py','doctor']),
        run('integrity-final',[sys.executable,'-B',ROOT/'tools/ph_lw_12_integrity.py'])]
    link_count=0
    for path in [ENGINE/'PH_LW_12_TEST_REPORT.md',ENGINE/'PH_LW_12_CHANGED_FILES.md']:
        md=re.sub(r'(?ms)^```[^\n]*\n.*?^```[^\n]*$','',path.read_text('utf-8'))
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',md):
            if re.match(r'^[a-zA-Z]+://',link) or link.startswith('#'):continue
            assert (path.parent/link.split('#',1)[0]).resolve().exists(),(path,link)
            link_count+=1
    trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
    archives=[]
    for name,digest in json.loads((W/'PRESERVED_ARCHIVES.json').read_text('utf-8')).items():
        path=ROOT/name;assert sha(path)==digest,name
        with zipfile.ZipFile(path) as z:assert z.testzip() is None,name
        archives.append({'file':name,'sha256':digest,'crc':'PASS','unchanged':True})
    verdict=json.loads((ENGINE/'PH_LW_12_LOGS/VERDICTS.json').read_text('utf-8'))
    result={'status':'PASS','scope':'Working-tree integrity and factual report linkage; not a release GO',
        'verified_utc':datetime.now(timezone.utc).isoformat(),'trees':trees,'commands':commands,
        'source_digest':freeze['engine_build_digest'],'wheel_sha256':freeze['wheel_sha256'],
        'installer_sha256':freeze['installer_sha256'],'runtime_freeze_unchanged':True,
        'historical_files_preserved':len(history),'old_test_files_unchanged':len(tests),
        'new_report_links_checked':link_count,'archives':archives,'zip_created':False,
        'verdicts':{k:verdict[k] for k in ['PH-LW-04','PH-LW-05','PH-LW-12','LOCAL_WEB_MANUAL','AUTOMATIC_EXECUTOR','v0.5.1']},
        'accepted_not_run':verdict['accepted_not_run'],'open_blockers':verdict['new_unaccepted_blockers'],
        'workspace_files':{p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'README.md',ROOT/'_workspace/CURRENT_TASK.md',ROOT/'_workspace/PROJECT_MAP.md',ROOT/'_workspace/RUNBOOK.md']}}
    # Workspace validation updates its own mutable JSON result. Capture output
    # hashes after the checks, so the inventory binds final working bytes.
    changed=[]
    current_paths=[*files(ENGINE),*files(DOCS),*files(ROOT/'tools'),ROOT/'README.md',ROOT/'AGENTS.md',
                   *[p for p in (ROOT/'_workspace').glob('*.md')]]
    now={p.relative_to(ROOT).as_posix():sha(p) for p in current_paths}
    for name in sorted(set(before)|set(now)):
        after=now.get(name)
        if name not in now and (ROOT/name).is_file():after=sha(ROOT/name)
        if before.get(name)!=after:changed.append({'file':name,'before_sha256':before.get(name),'after_sha256':after})
    save(W/'CHANGED_FILE_HASHES.json',changed)
    save(W/'FINAL_WORKING_TREE_VERIFICATION.json',result)
    hash_paths=[ENGINE/'MANIFEST.sha256',DOCS/'MANIFEST.sha256',ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl',
        ENGINE/'windows/Harness-Setup-win-x64.exe',ENGINE/'PH_LW_12_TEST_REPORT.md',ENGINE/'PH_LW_12_CHANGED_FILES.md',
        W/'INPUT_BASELINE.json',W/'INPUT_FILE_HASHES.json',W/'RUNTIME_FREEZE.json',W/'CHANGED_FILE_HASHES.json',W/'FINAL_WORKING_TREE_VERIFICATION.json']
    (W/'SHA256.txt').write_text(''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in hash_paths),'utf-8')
    print(json.dumps({k:result[k] for k in ['status','trees','runtime_freeze_unchanged','historical_files_preserved','old_test_files_unchanged','verdicts','zip_created']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
