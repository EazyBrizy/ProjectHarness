"""Current document-analysis clarity artifacts; no full runtime regression."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import zipfile

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
DOCS=ROOT/'Project_Harness_Documentation_v0.5.1'
SCRATCH=ROOT/'_scratch/document_analysis_universality_20261112'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def inventory(base):
    return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def save(name,data):
    p=OUT/name
    assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')

def publish():
    build=SCRATCH/'build';bundle=build/'frozen/Harness'
    result=json.loads((build/'BUILD_RESULT.json').read_text('utf-8'))
    assert result['source_files']==inventory(ENGINE/'src/project_harness')==inventory(bundle/'_internal/project_harness')
    assert inventory(DOCS)==inventory(bundle/'_internal/documentation')
    before=SCRATCH/'before';before.mkdir(exist_ok=True)
    target=(ENGINE/'windows/Harness').resolve();destination=(before/'Harness').resolve()
    assert target==ENGINE.resolve()/'windows/Harness' and destination.is_relative_to(SCRATCH.resolve())
    assert not target.is_junction() and not target.is_symlink() and not destination.exists()
    for name in ('BUILD_RESULT.json','Harness-Setup-win-x64.exe'):
        shutil.copy2(ENGINE/'windows'/name,before/name)
    target.rename(destination)
    shutil.copytree(bundle,target)
    for name in ('BUILD_RESULT.json','Harness-Setup-win-x64.exe'):
        shutil.copy2(build/name,ENGINE/'windows'/name)
    save('RUNTIME_FREEZE.json',{'build_id':result['build_id'],'engine_build_digest':result['source_digest'],
        'source_hashes':inventory(ENGINE/'src/project_harness'),'documentation_hashes':inventory(DOCS),
        'wheel_sha256':sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
        'installer_sha256':sha(ENGINE/'windows/Harness-Setup-win-x64.exe'),
        'package_manifest_sha256':sha(target/'PACKAGE_FILES.json'),'zip_created':False})
    shutil.copy2(build/'BUILD_RESULT.json',OUT/'BUILD_RESULT.json')

def verify():
    freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
    source=inventory(ENGINE/'src/project_harness');docs=inventory(DOCS)
    assert source==freeze['source_hashes']==inventory(ENGINE/'build/lib/project_harness')==inventory(ENGINE/'windows/Harness/_internal/project_harness')
    assert docs==freeze['documentation_hashes']==inventory(ENGINE/'docs'/DOCS.name)==inventory(ENGINE/'windows/Harness/_internal/documentation')
    sys.path.insert(0,str(ENGINE/'src'))
    from project_harness.windows_package import verify_bundle
    verify_bundle(ENGINE/'windows/Harness')
    assert sha(ENGINE/'windows/Harness/PACKAGE_FILES.json')==freeze['package_manifest_sha256']
    assert sha(ENGINE/'windows/Harness-Setup-win-x64.exe')==freeze['installer_sha256']
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    assert sha(wheel)==freeze['wheel_sha256']
    with zipfile.ZipFile(wheel) as archive:
        assert archive.testzip() is None
        for name,digest in source.items():assert hashlib.sha256(archive.read('project_harness/'+name)).hexdigest()==digest
    for base in (ENGINE,DOCS):
        expected={name:digest for digest,name in (line.split('  ',1) for line in (base/'MANIFEST.sha256').read_text('utf-8').splitlines())}
        actual=inventory(base);actual.pop('MANIFEST.sha256');assert actual==expected,str(base)
    baseline=json.loads((OUT/'INPUT_BASELINE.json').read_text('utf-8'))
    changed={n for n in set(baseline['source'])|set(source) if source.get(n)!=baseline['source'].get(n)}
    assert changed==set(baseline['allowed_source']),changed^set(baseline['allowed_source'])
    tests=inventory(ENGINE/'tests')
    assert {n for n,h in baseline['tests'].items() if tests.get(n)!=h}=={'test_document_analysis_clarity.py'}
    assert set(tests)-set(baseline['tests'])=={'test_document_analysis_universality.py'}
    assert {n for n,h in baseline['docs'].items() if docs.get(n)!=h}=={'FILE_INDEX.md','MANIFEST.sha256'}
    assert set(docs)-set(baseline['docs'])=={'13_Local_Web_Manual_Companion/35_Project_Independent_Document_Analysis.md'}
    value={'status':'PASS','build_id':freeze['build_id'],'source_build_wheel_frozen':'PASS','full_frozen_payload_including_pyd':'PASS',
        'documentation_mirrors':'PASS','manifests':'PASS','allowed_source_changes':sorted(changed),
        'core_contracts_and_historical_documentation_preserved':True,'unrelated_tests_preserved':True,
        'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256'),'docs_manifest_sha256':sha(DOCS/'MANIFEST.sha256'),'zip_created':False}
    save('INTEGRITY.json',value);print(json.dumps(value,ensure_ascii=False,indent=2))

def upgrade():
    sys.path.insert(0,str(ENGINE/'src'))
    from project_harness.windows_package import verify_bundle
    install=Path(os.environ['LOCALAPPDATA'])/'Programs/ProjectHarness'
    previous=json.loads((install/'current.json').read_text('utf-8'))['build_id']
    roots=[Path(os.environ['LOCALAPPDATA'])/'ProjectHarness',Path.home()/'HarnessProjects',
           Path(os.environ['LOCALAPPDATA'])/'ProjectHarness-workspaces']
    def private_digest():
        return [{'label':p.name,'files':len(values),'digest':hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()}
                for p in roots for values in [inventory(p)]]
    before=private_digest()
    command=[str(ENGINE/'windows/Harness-Setup-win-x64.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
             '/DIR='+str(install),'/LOG='+str(SCRATCH/'operator-upgrade.log')]
    code=subprocess.run(command,timeout=180).returncode
    assert code==0,code
    freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
    current=json.loads((install/'current.json').read_text('utf-8'))['build_id']
    assert current==freeze['build_id']
    bundle=install/'versions'/current;verify_bundle(bundle)
    assert inventory(bundle/'_internal/project_harness')==freeze['source_hashes']
    assert private_digest()==before,'Operator data changed during upgrade'
    assert (install/'versions'/previous/'Harness.exe').exists()
    checks={arg:subprocess.run([str(bundle/'Harness.exe'),arg],timeout=60).returncode
            for arg in ('--check-package','--doctor')}
    assert all(code==0 for code in checks.values()),checks
    save('OPERATOR_UPGRADE.json',{'status':'PASS','command':command,'exit':code,'before_build_id':previous,
        'after_build_id':current,'operator_data_preserved':True,'private_roots_aggregate_hashes':before,
        'previous_version_preserved':True,'checks':checks,'browser_launched':False})

if __name__=='__main__':
    {'publish':publish,'verify':verify,'upgrade':upgrade}[sys.argv[1]]()
