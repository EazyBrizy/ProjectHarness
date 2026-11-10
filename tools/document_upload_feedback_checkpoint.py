"""Evidence runner for the 2026-11-09 document upload UI correction."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import unittest
import zipfile

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
OUT = ROOT / '_workspace/DOCUMENT_UPLOAD_FEEDBACK_2026-11-09'
DOCS = ROOT / 'Project_Harness_Documentation_v0.5.1'
SCRATCH = ROOT / '_scratch/document_upload_feedback_20261109'

def inventory(base):
    return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')

def baseline():
    OUT.mkdir(exist_ok=False)
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    save(OUT/'INPUT_HASHES.json', {name: sha(ROOT/name) for name in paths if name and (ROOT/name).is_file()})
    (OUT/'CURRENT_TASK.before.md').write_bytes((ROOT/'_workspace/CURRENT_TASK.md').read_bytes())
    (OUT/'GIT_STATUS.before.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
    save(OUT/'BASELINE.json', {'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        'allowed_file_changes':['resources/local_web/assets/{app.js,index.html,app.css}',
            'resources/local_web/metadata_v1.json (build identity only)',
            'tests/test_document_upload_feedback.py', 'local_web/windows/document_upload_feedback_acceptance.py',
            'documentation operator chapter 24 and generated indexes/mirror',
            'generated build/wheel/frozen/installer/manifests',
            'tools/document_upload_feedback_checkpoint.py', '_workspace/CURRENT_TASK.md', str(OUT.relative_to(ROOT))],
        'preserve_dirty_files':['_workspace/CURRENT_TASK.md existing content', '_workspace/OPENDESIGN_LOCAL_WEB_DESIGN_PROMPT_RU.txt'],
        'automatic_executor_enabled':False, 'zip_requested':False})

def publish():
    source=ENGINE/'src/project_harness';build=SCRATCH/'build-final'
    result=json.loads((build/'BUILD_RESULT.json').read_text('utf-8'))
    assert inventory(source)==result['source_files']
    assert inventory(source)==inventory(build/'frozen/Harness/_internal/project_harness')
    assert inventory(DOCS)==inventory(build/'frozen/Harness/_internal/documentation')
    previous=SCRATCH/'before-publication';previous.mkdir(exist_ok=False)
    target=(ENGINE/'windows/Harness').resolve()
    destination=(previous/'Harness').resolve()
    assert target==ENGINE.resolve()/'windows/Harness' and destination.is_relative_to(SCRATCH.resolve())
    assert not target.is_junction() and not target.is_symlink()
    for name in ('BUILD_RESULT.json','Harness-Setup-win-x64.exe'):
        shutil.copy2(ENGINE/'windows'/name,previous/name)
    oldwheel='Project_Harness_Engine_v0.5.1/dist/project_harness_engine-0.5.1-py3-none-any.whl'
    (previous/'project_harness_engine-0.5.1-py3-none-any.whl').write_bytes(
        subprocess.check_output(['git','show','HEAD:'+oldwheel],cwd=ROOT))
    target.rename(destination)
    shutil.copytree(build/'frozen/Harness',target)
    for name in ('BUILD_RESULT.json','Harness-Setup-win-x64.exe'):
        shutil.copy2(build/name,ENGINE/'windows'/name)
    shutil.copy2(build/'BUILD_RESULT.json',OUT/'BUILD_RESULT.json')
    freeze={'source_hashes':inventory(source),'documentation_hashes':inventory(DOCS),
        'engine_build_digest':result['source_digest'],'build_id':result['build_id'],
        'wheel_sha256':sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
        'installer_sha256':sha(ENGINE/'windows/Harness-Setup-win-x64.exe'),
        'package_manifest_sha256':sha(target/'PACKAGE_FILES.json'),'zip_created':False,
        'scope':'Document upload UI correction; targeted acceptance, not full PH-LW-12 rerun'}
    save(OUT/'RUNTIME_FREEZE.json',freeze)

def verify():
    sys.path.insert(0,str(ENGINE/'src'))
    from project_harness.windows_package import verify_bundle
    f=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
    source=ENGINE/'src/project_harness';bundle=ENGINE/'windows/Harness'
    assert inventory(source)==f['source_hashes']==inventory(ENGINE/'build/lib/project_harness')==inventory(bundle/'_internal/project_harness')
    assert inventory(DOCS)==f['documentation_hashes']==inventory(ENGINE/'docs'/DOCS.name)==inventory(bundle/'_internal/documentation')
    verify_bundle(bundle)
    assert sha(bundle/'PACKAGE_FILES.json')==f['package_manifest_sha256']
    assert sha(ENGINE/'windows/Harness-Setup-win-x64.exe')==f['installer_sha256']
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    assert sha(wheel)==f['wheel_sha256']
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None
        for name,digest in f['source_hashes'].items():
            assert hashlib.sha256(z.read('project_harness/'+name)).hexdigest()==digest
    for base in (ENGINE,DOCS):
        actual=inventory(base);actual.pop('MANIFEST.sha256')
        expected={name:digest for digest,name in (line.split('  ',1) for line in (base/'MANIFEST.sha256').read_text('utf-8').splitlines())}
        assert actual==expected, 'Manifest mismatch: '+str(base)
    before=json.loads((OUT/'INPUT_HASHES.json').read_text('utf-8'));changed={}
    for name,digest in before.items():
        p=ROOT/name
        if not p.exists() or sha(p)!=digest:
            changed[name]={'before':digest,'after':sha(p) if p.exists() else None}
    engine_prefix=ENGINE.name+'/'
    allowed={engine_prefix+'src/project_harness/resources/local_web/assets/'+name for name in ('app.js','app.css','index.html')}
    allowed|={engine_prefix+'src/project_harness/resources/local_web/metadata_v1.json','_workspace/CURRENT_TASK.md',engine_prefix+'MANIFEST.sha256'}
    for prefix in (DOCS.name+'/',engine_prefix+'docs/'+DOCS.name+'/'):
        allowed|={prefix+name for name in ('MANIFEST.sha256','FILE_INDEX.md')}
    unexpected=[name for name in changed if name not in allowed and not name.startswith((engine_prefix+'windows/',engine_prefix+'dist/'))]
    assert not unexpected,unexpected
    save(OUT/'CHANGED_INPUT_HASHES.json',changed)
    (OUT/'CODE_DIFF.patch').write_bytes(subprocess.check_output(['git','diff','--',str(source.relative_to(ROOT))],cwd=ROOT))
    result={'status':'PASS','source_build_wheel_frozen_byte_equality':'PASS','documentation_mirrors':'PASS',
            'full_frozen_payload_including_pyd':'PASS','wheel_crc_and_source_hashes':'PASS','manifests':'PASS',
            'unrelated_tracked_input_files_preserved':True,'build_id':f['build_id'],
            'wheel_sha256':f['wheel_sha256'],'installer_sha256':f['installer_sha256'],
            'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256'),'docs_manifest_sha256':sha(DOCS/'MANIFEST.sha256'),
            'automatic_executor_enabled':False,'zip_created':False}
    save(OUT/'INTEGRITY.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))

def wheel_tests():
    import project_harness
    package=Path(project_harness.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
    freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
    assert inventory(package)==freeze['source_hashes']
    print(json.dumps({'installed_package':str(package),'python':sys.version,'cwd':str(Path.cwd()),
        'source_import':False,'installed_source_hashes':'PASS','launcher_mutex_test':'separate recorded run'},ensure_ascii=False),flush=True)
    sys.path.insert(0,str(ENGINE))  # tests only, never engine/src
    modules=['tests.test_document_upload_feedback','tests.test_ph_lw_05_import','tests.test_ph_lw_05_http',
             'tests.test_ph_lw_04_05_acceptance.BrowserImportAcceptance','tests.test_ph_lw_04_http','tests.test_ph_lw_06_http']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    save(OUT/'WHEEL_TEST_RESULTS.json',{'ran':result.testsRun,'failures':len(result.failures),
         'errors':len(result.errors),'skips':len(result.skipped),'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL'})
    raise SystemExit(not result.wasSuccessful() or bool(result.skipped))

def upgrade_user():
    sys.path.insert(0,str(ENGINE/'src'))
    from project_harness.windows_package import verify_bundle
    install=Path(os.environ['LOCALAPPDATA'])/'Programs/ProjectHarness'
    before_id=json.loads((install/'current.json').read_text('utf-8'))['build_id']
    roots=[Path(os.environ['LOCALAPPDATA'])/'ProjectHarness',Path.home()/'HarnessProjects',
           Path(os.environ['LOCALAPPDATA'])/'ProjectHarness-workspaces']
    def private_digest():
        rows=[]
        for base in roots:
            values=inventory(base) if base.exists() else {}
            # Only aggregate hashes/counts leave the private operator roots.
            rows.append({'root_label':base.name,'files':len(values),
                'digest':hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()})
        return rows
    before=private_digest()
    command=[str(ENGINE/'windows/Harness-Setup-win-x64.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
             '/DIR='+str(install),'/LOG='+str(SCRATCH/'operator-upgrade.log')]
    result=subprocess.run(command,timeout=180)
    if result.returncode:
        save(OUT/'OPERATOR_UPGRADE.json',{'status':'FAIL','exit':result.returncode,'before_build_id':before_id})
        raise RuntimeError('Operator upgrade failed')
    freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
    after_id=json.loads((install/'current.json').read_text('utf-8'))['build_id']
    assert after_id==freeze['build_id']
    bundle=install/'versions'/after_id
    verify_bundle(bundle)
    assert inventory(bundle/'_internal/project_harness')==freeze['source_hashes']
    assert before==private_digest(),'Operator data changed during installation'
    assert (install/'versions'/before_id/'Harness.exe').exists(),'Previous version missing'
    checks={}
    for arg in ('--check-package','--doctor'):
        code=subprocess.run([str(bundle/'Harness.exe'),arg],timeout=60).returncode
        checks[arg]=code
        assert code==0
    value={'status':'PASS','exit':0,'before_build_id':before_id,'after_build_id':after_id,
        'installer_sha256':freeze['installer_sha256'],'checks':checks,'operator_data_preserved':True,
        'private_roots_aggregate_hashes':before,'previous_version_preserved':True,'browser_launched':False}
    save(OUT/'OPERATOR_UPGRADE.json',value);print(json.dumps(value,ensure_ascii=False,indent=2))

def run(label, command, cwd, timeout, source):
    cwd=cwd.resolve()
    log=OUT/(label+'.log')
    if log.exists():
        raise FileExistsError(log)
    env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','PH_LW_04_BROWSER_CHANNEL':'msedge',
         'PYTHONPATH':str(ENGINE/'src')+';'+str(ENGINE) if source else ''}
    row={'command':command,'cwd':str(cwd),'platform':platform.platform(),'python':sys.version,
         'started_utc':datetime.now(timezone.utc).isoformat(),'source_layout':source,
         'dependencies':{name:version(name) for name in ('Flask','Waitress','playwright')}}
    started=time.monotonic()
    with log.open('wb') as stream:
        child=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:
            code=child.wait(timeout=timeout)
            row.update(exit=code,status='PASS' if code==0 else 'FAIL')
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,timeout=20)
            child.wait(timeout=20)
            row.update(exit=None,status='TIMEOUT')
    row.update(elapsed_seconds=round(time.monotonic()-started,3),log_sha256=sha(log))
    save(log.with_suffix('.run.json'),row)
    print(json.dumps(row,ensure_ascii=False,indent=2))
    print(log.read_text('utf-8',errors='replace')[-7000:])
    return row['status']=='PASS'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--cwd',type=Path,default=ROOT)
    p.add_argument('--timeout',type=int,default=600);p.add_argument('--source',action='store_true')
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.label=='baseline':
        baseline()
    elif a.label=='publish':
        publish()
    elif a.label=='verify':
        verify()
    elif a.label=='wheel-tests':
        wheel_tests()
    elif a.label=='upgrade-user':
        upgrade_user()
    else:
        command=a.command[1:] if a.command[:1]==['--'] else a.command
        raise SystemExit(not run(a.label,command,a.cwd,a.timeout,a.source))
