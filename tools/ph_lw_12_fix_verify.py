"""Attest exact final working files; historical evidence is immutable."""
import ast,hashlib,json,os,re,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from verify_ph_lw_06_working_tree import verify_manifest

W=ROOT/'_workspace/PH_LW_12_FIX';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text('utf-8-sig'))
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def run(name,command):
    p=W/(name+'.log');index=1
    while p.exists():p=W/(name+'-'+str(index)+'.log');index+=1
    with p.open('wb') as stream:
        result=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=240,
            env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
    row={'command':list(map(str,command)),'cwd':str(ROOT),'exit':result.returncode,
        'status':'PASS' if result.returncode==0 else 'FAIL','log':p.name,'log_sha256':sha(p)}
    save(p.with_suffix('.run.json'),row);assert result.returncode==0,row
    return row

def assertions(text):
    found=[]
    for node in ast.walk(ast.parse(text)):
        if isinstance(node,ast.Assert):found.append(ast.dump(node,include_attributes=False))
        elif isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
            if node.func.attr.startswith('assert') or 'expect(' in ast.unparse(node.func.value):
                found.append(ast.dump(node,include_attributes=False))
    return sorted(found)

def main():
    freeze=read(W/'RUNTIME_FREEZE.json');before=read(W/'INPUT_FILE_HASHES.json')
    source=ENGINE/'src/project_harness'
    assert freeze['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
    assert freeze['documentation_hashes']=={p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)}
    discovery=read(W/'DISCOVERY.json')
    for row in discovery['methods']:
        assert sha(ENGINE/(row['module'].replace('.','/')+'.py'))==row['test_file_sha256'],row['module']
    protected=[];old_tests=[];sync_test='Project_Harness_Engine_v0.5.1/tests/test_ph_lw_12_acceptance.py'
    for name,digest in before.items():
        path=ROOT/name
        immutable=(name.startswith(('_inputs/','Harness_Local_Web_Prompts_RU_r2/','Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0/')) or
            (name.startswith(ENGINE.name+'/PH_') and not name.startswith(ENGINE.name+'/PH_LW_12_FIX')) or
            (name.startswith('_workspace/PH_') and not name.startswith('_workspace/PH_LW_12_FIX/')))
        if immutable:assert path.is_file() and sha(path)==digest,name;protected.append(name)
        if name.startswith(ENGINE.name+'/tests/') and name!=sync_test:
            assert path.is_file() and sha(path)==digest,name;old_tests.append(name)
    old=W/'input-tests/test_ph_lw_12_acceptance.py';current=ROOT/sync_test
    assert sha(old)==before[sync_test]
    assert assertions(old.read_text('utf-8'))==assertions(current.read_text('utf-8'))
    save(W/'TEST_ASSERTION_PRESERVATION.json',{'status':'PASS','unchanged_test_files':len(old_tests),
        'synchronization_only_test':sync_test,'before_sha256':sha(old),'after_sha256':sha(current),
        'all_assert_and_expect_ASTs_unchanged':True})
    save(W/'FINAL_WORKING_TREE_VERIFICATION.json',{'status':'IN PROGRESS','artifact_checks_only':True})
    if not (W/'CHANGED_FILE_HASHES.json').exists():save(W/'CHANGED_FILE_HASHES.json',[])
    if not (W/'SHA256.txt').exists():(W/'SHA256.txt').write_text('# IN PROGRESS\n','utf-8')
    commands=[run('workspace-final',[sys.executable,'-B',ROOT/'tools/check_workspace.py']),
        run('documentation-final',[sys.executable,'-B',DOCS/'tools/validate_documentation.py',DOCS,'--json',W/'DOC_VALIDATION.json']),
        run('doctor-final',[sys.executable,'-B',ENGINE/'project-harness.py','doctor']),
        run('integrity-final',[sys.executable,'-B',ROOT/'tools/ph_lw_12_fix_integrity.py'])]
    trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
    links=0
    for path in [ENGINE/'PH_LW_12_FIX_TEST_REPORT.md',ENGINE/'PH_LW_12_FIX_CHANGED_FILES.md']:
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text('utf-8')):
            if re.match(r'^[a-zA-Z]+://',link) or link.startswith('#'):continue
            assert (path.parent/link.split('#',1)[0]).resolve().exists(),(path,link);links+=1
    archives=[]
    for name,digest in read(W/'PRESERVED_ARCHIVES.json').items():
        path=ROOT/name;assert sha(path)==digest,name
        with zipfile.ZipFile(path) as z:assert z.testzip() is None,name
        archives.append({'file':name,'sha256':digest,'crc':'PASS','unchanged':True})
    verdict=read(ENGINE/'PH_LW_12_FIX_LOGS/VERDICTS.json')
    self_referential={'CHANGED_FILE_HASHES.json','FINAL_WORKING_TREE_VERIFICATION.json','SHA256.txt'}
    paths=[*files(ENGINE),*files(DOCS),*files(ROOT/'tools'),ROOT/'README.md',ROOT/'AGENTS.md',
        *[p for p in (ROOT/'_workspace').glob('*.md')],
        *[p for p in files(W) if p.name not in self_referential]]
    now={p.relative_to(ROOT).as_posix():sha(p) for p in paths};changed=[]
    for name in sorted(set(before)|set(now)):
        after=now.get(name)
        if name not in now and (ROOT/name).is_file():after=sha(ROOT/name)
        if before.get(name)!=after:changed.append({'file':name,'before_sha256':before.get(name),'after_sha256':after})
    save(W/'CHANGED_FILE_HASHES.json',changed)
    result={'status':'PASS','scope':'Artifact integrity, preservation and exact-hash factual linkage; acceptance verdict separate',
        'verified_utc':datetime.now(timezone.utc).isoformat(),'trees':trees,'commands':commands,
        'source_digest':freeze['engine_build_digest'],'wheel_sha256':freeze['wheel_sha256'],'installer_sha256':freeze['installer_sha256'],
        'runtime_freeze_unchanged':True,'historical_files_preserved':len(protected),'unchanged_old_tests':len(old_tests),
        'discovery_test_file_hashes_unchanged':True,
        'changed_inventory_excluded_self_referential':sorted(self_referential),
        'synchronization_test_assertions_unchanged':True,'new_report_links_checked':links,'archives':archives,
        'verdicts':{key:verdict[key] for key in ('PH-LW-04','PH-LW-05','PH-LW-12','LOCAL_WEB_MANUAL','AUTOMATIC_EXECUTOR','v0.5.1')},
        'accepted_not_run':verdict['accepted_not_run'],'zip_created':False,
        'workspace_files':{p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/'README.md',ROOT/'_workspace/CURRENT_TASK.md',ROOT/'_workspace/PROJECT_MAP.md',ROOT/'_workspace/RUNBOOK.md']}}
    save(W/'FINAL_WORKING_TREE_VERIFICATION.json',result)
    outputs=[ENGINE/'MANIFEST.sha256',DOCS/'MANIFEST.sha256',ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl',
        ENGINE/'windows/Harness-Setup-win-x64.exe',ENGINE/'PH_LW_12_FIX_TEST_REPORT.md',ENGINE/'PH_LW_12_FIX_CHANGED_FILES.md',
        W/'INPUT_BASELINE.json',W/'INPUT_FILE_HASHES.json',W/'RUNTIME_FREEZE.json',W/'CHANGED_FILE_HASHES.json',W/'FINAL_WORKING_TREE_VERIFICATION.json']
    (W/'SHA256.txt').write_text(''.join(sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in outputs),'utf-8')
    print(json.dumps({key:result[key] for key in ('status','trees','runtime_freeze_unchanged','historical_files_preserved','unchanged_old_tests','verdicts','zip_created')},ensure_ascii=False))

if __name__=='__main__':main()
