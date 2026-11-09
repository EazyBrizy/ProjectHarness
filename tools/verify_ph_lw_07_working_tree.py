"""Final exact unpacked-tree attestation, immutable baseline and evidence checks."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from package_acceptance import ROOT, ENGINE, DOCS, files
from verify_ph_lw_06_working_tree import verify_manifest

OUT = ROOT / '_workspace/PH_LW_07'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8'))


def run(name, command, cwd):
    log = OUT / (name+'.log')
    started = datetime.now(timezone.utc).isoformat()
    with log.open('wb') as stream:
        result = subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=180,
            env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
    info={'command':command,'cwd':str(cwd),'started_utc':started,'exit':result.returncode,
          'status':'PASS' if result.returncode==0 else 'FAIL','log':log.name,'log_sha256':sha(log)}
    assert result.returncode==0,info
    return info


def main():
    assert '**COMPLETE' in (ROOT/'_workspace/CURRENT_TASK.md').read_text('utf-8')
    final_path = OUT/'FINAL_WORKING_TREE_VERIFICATION.json'
    if final_path.exists() and read(final_path).get('status')=='PASS':
        raise RuntimeError('Preserve completed historical attestation; use a new output for a new verification run')
    before=read(OUT/'INPUT_FILE_HASHES.json')
    allowed_source={'local_web_approval_core.py','local_web_approvals.py','local_web_exchange.py','local_web_http.py',
        'local_web_service.py','resources/local_web/assets/approvals.js','resources/local_web/assets/app.css',
        'resources/local_web/assets/app.js','resources/local_web/assets/index.html','resources/local_web/assets/interview.js',
        'resources/local_web/metadata_v1.json'}
    source_prefix=ENGINE.name+'/src/project_harness/'
    docs_mutable={'README.md','FILE_INDEX.md','MANIFEST.sha256','Project_Harness_Architecture_v0.5.0_FULL.md'}
    history=0; invariants=0
    for name,digest in before.items():
        rel=Path(name)
        immutable=(rel.parts[0] in {'_inputs','Harness_Local_Web_Prompts_RU_r2','Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0'}
            or (rel.parts[0]==ENGINE.name and (rel.parts[1].startswith('PH_') or rel.parts[1] in {'schemas','registries','tests'}))
            or (rel.parts[0]==DOCS.name and rel.parts[1].startswith('PH_')))
        immutable = immutable or (name.startswith(source_prefix) and name.removeprefix(source_prefix) not in allowed_source)
        immutable = immutable or (rel.parts[0]==DOCS.name and '/'.join(rel.parts[1:]) not in docs_mutable)
        if immutable:
            assert sha(ROOT/name)==digest,'Immutable input/history changed: '+name
            invariants+=1
            if rel.parts[0]==ENGINE.name and rel.parts[1].startswith('PH_'): history+=1
    archives=read(OUT/'PRESERVED_ARCHIVES.json')
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'_deliverables').rglob('*.zip')} | {p.relative_to(ROOT).as_posix() for p in ROOT.glob('*.zip')}
    assert actual==set(archives),'Deliverable ZIP set changed'
    for name,digest in archives.items():
        assert sha(ROOT/name)==digest
        with zipfile.ZipFile(ROOT/name) as zf: assert zf.testzip() is None
    evidence=read(ENGINE/'PH_LW_07_LOGS/EVIDENCE_INDEX.json')
    for item in evidence:
        assert sha(ROOT/item['raw_source'])==item['raw_sha256'],item['raw_source']
        assert sha(ENGINE/'PH_LW_07_LOGS'/item['file'])==item['published_sha256'],item['file']
    native=read(ENGINE/'PH_LW_07_LOGS/NATIVE_SCOPE_VERDICT.json')
    assert native['status']=='PASS' and not native['skips']
    # Link targets exist during the final check, but cannot claim PASS until
    # every check finishes. These are new checkpoint outputs, never old history.
    final_path.write_text('{"status":"VERIFYING"}\n','utf-8')
    (OUT/'CHANGED_FILE_HASHES.json').write_text('[]\n','utf-8')
    (OUT/'SHA256.txt').write_text('Verification in progress; no final hashes yet.\n','utf-8')
    commands=[run('workspace-check',[sys.executable,str(ROOT/'tools/check_workspace.py')],ROOT),
        run('doctor',[sys.executable,str(ENGINE/'project-harness.py'),'doctor'],ENGINE),
        run('documentation',[sys.executable,str(DOCS/'tools/validate_documentation.py'),str(DOCS),'--json',str(OUT/'DOC_VALIDATION.json')],ROOT)]
    trees={p.relative_to(ROOT).as_posix():verify_manifest(p) for p in (ENGINE,DOCS,ENGINE/'docs'/DOCS.name)}
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as zf: assert zf.testzip() is None
    meta=read(ENGINE/'src/project_harness/resources/local_web/metadata_v1.json')
    provenance=read(ENGINE/'PH_LW_07_LOGS/BUILD_PROVENANCE.json')
    assert sha(wheel)==provenance['wheel_sha256']
    source=ENGINE/'src/project_harness'
    for p in files(source):
        if p.relative_to(ROOT).as_posix() not in before:
            assert p.relative_to(source).as_posix() in allowed_source, p
    entries=[f'{sha(p)}  {p.relative_to(source).as_posix()}' for p in files(source) if p!=source/'resources/local_web/metadata_v1.json']
    assert 'sha256:'+hashlib.sha256(('\n'.join(entries)+'\n').encode()).hexdigest()==meta['engine_build_digest']==provenance['engine_build_digest']
    after={p.relative_to(ROOT).as_posix():sha(p) for tree in (ENGINE,DOCS) for p in files(tree)}
    names={name for name in before if name.startswith((ENGINE.name+'/',DOCS.name+'/'))}|set(after)
    changes=[{'file':name,'before_sha256':before.get(name),'after_sha256':after.get(name)} for name in sorted(names) if before.get(name)!=after.get(name)]
    (OUT/'CHANGED_FILE_HASHES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n','utf-8')
    workspace_paths=['AGENTS.md','README.md','_workspace/CURRENT_TASK.md','_workspace/PROJECT_MAP.md','_workspace/RUNBOOK.md',
        'tools/check_workspace.py','tools/verify_installed.py','tools/finalize_ph_lw_07_evidence.py','tools/verify_ph_lw_07_working_tree.py','tools/sync_working_tree.py']
    result={'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'PH-LW-07 exact unpacked pair, not full release', 'trees':trees,'wheel_sha256':sha(wheel),
        'engine_build_digest':meta['engine_build_digest'],'input_baseline_sha256':sha(OUT/'INPUT_BASELINE.json'),
        'input_file_hashes_sha256':sha(OUT/'INPUT_FILE_HASHES.json'),'historical_engine_evidence_preserved':history,
        'immutable_files_verified':invariants,'unchanged_deliverable_archives_crc_and_hash_checked':len(archives),
        'evidence_files_verified_against_raw_and_published_hashes':len(evidence),
        'changed_file_hashes_sha256':sha(OUT/'CHANGED_FILE_HASHES.json'),'commands':commands,
        'native_acceptance':native,'workspace_files':{p:sha(ROOT/p) for p in workspace_paths},
        'zip_created':False,'verdicts':{'PH-LW-04':'PASS','PH-LW-05':'PASS','PH-LW-06':'PASS','PH-LW-07':'PASS',
            'LOCAL_WEB_MANUAL':'NO-GO','AUTOMATIC_EXECUTOR':'NO-GO','v0.5.1':'NO-GO / NOT RELEASED'}}
    (OUT/'FINAL_WORKING_TREE_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
    paths=[ENGINE/'MANIFEST.sha256',DOCS/'MANIFEST.sha256',wheel,OUT/'FINAL_WORKING_TREE_VERIFICATION.json',OUT/'CHANGED_FILE_HASHES.json']
    (OUT/'SHA256.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}' for p in paths)+'\n','utf-8')
    print(json.dumps({'status':'PASS','trees':trees,'history':history,'evidence':len(evidence),'wheel_sha256':sha(wheel)},indent=2))


if __name__=='__main__':main()
