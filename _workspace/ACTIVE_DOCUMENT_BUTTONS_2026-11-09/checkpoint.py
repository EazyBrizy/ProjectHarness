"""Immutable evidence for active document controls; no historical rewrites."""
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
SCRATCH=ROOT/'_scratch/active_document_buttons_20261109'
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
    before=SCRATCH/'before';before.mkdir(exist_ok=False)
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
    source=inventory(ENGINE/'src/project_harness')
    docs=inventory(DOCS)
    assert source==freeze['source_hashes']==inventory(ENGINE/'build/lib/project_harness')==inventory(ENGINE/'windows/Harness/_internal/project_harness')
    assert docs==freeze['documentation_hashes']==inventory(ENGINE/'docs'/DOCS.name)==inventory(ENGINE/'windows/Harness/_internal/documentation')
    sys.path.insert(0,str(ENGINE/'src'))
    from project_harness.windows_package import verify_bundle
    verify_bundle(ENGINE/'windows/Harness')
    assert sha(ENGINE/'windows/Harness/PACKAGE_FILES.json')==freeze['package_manifest_sha256']
    assert sha(ENGINE/'windows/Harness-Setup-win-x64.exe')==freeze['installer_sha256']
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    assert sha(wheel)==freeze['wheel_sha256']
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None
        for name,digest in source.items():
            assert hashlib.sha256(z.read('project_harness/'+name)).hexdigest()==digest
    for base in (ENGINE,DOCS):
        expected={name:digest for digest,name in (line.split('  ',1) for line in (base/'MANIFEST.sha256').read_text('utf-8').splitlines())}
        actual=inventory(base);actual.pop('MANIFEST.sha256')
        assert actual==expected
    before=json.loads((OUT/'INPUT_BASELINE.json').read_text('utf-8'))
    changed=[name for name,digest in before['source'].items() if source.get(name)!=digest]
    assert set(changed)=={'resources/local_web/assets/app.js','resources/local_web/assets/index.html','resources/local_web/metadata_v1.json'},changed
    tests=inventory(ENGINE/'tests')
    assert [name for name,digest in before['tests'].items() if tests.get(name)!=digest]==['test_document_upload_feedback.py']
    doc_changes=[name for name,digest in before['docs'].items() if docs.get(name)!=digest]
    assert set(doc_changes)=={'FILE_INDEX.md','MANIFEST.sha256'},doc_changes
    value={'status':'PASS','source_build_wheel_frozen':'PASS','full_frozen_payload_including_pyd':'PASS',
        'documentation_mirrors':'PASS','manifests':'PASS','backend_core_original_tests_preserved':True,
        'build_id':freeze['build_id'],'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256'),
        'docs_manifest_sha256':sha(DOCS/'MANIFEST.sha256'),'zip_created':False}
    if not (OUT/'INTEGRITY.json').exists():save('INTEGRITY.json',value)
    print(json.dumps(value,ensure_ascii=False,indent=2))

def wheel_tests():
    os.environ['PH_LW_04_BROWSER_CHANNEL']='msedge'
    import project_harness
    package=Path(project_harness.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
    assert inventory(package)==inventory(ENGINE/'src/project_harness')
    print(json.dumps({'interpreter':sys.executable,'python':sys.version,'package':str(package),
        'cwd':str(Path.cwd()),'source_import':False,'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')}},ensure_ascii=False),flush=True)
    sys.path.insert(0,str(ENGINE))
    modules=['tests.test_document_button_validation','tests.test_document_upload_feedback',
        'tests.test_ph_lw_05_import','tests.test_ph_lw_05_http','tests.test_ph_lw_04_05_acceptance.BrowserImportAcceptance',
        'tests.test_ph_lw_04_http','tests.test_ph_lw_06_http']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    suffix='_02' if '--retry' in sys.argv else ''
    save('WHEEL_RESULTS'+suffix+'.json',{'ran':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),
        'skips':len(result.skipped),'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL'})
    raise SystemExit(not result.wasSuccessful() or bool(result.skipped))

if __name__=='__main__':
    {'publish':publish,'verify':verify,'wheel-tests':wheel_tests}[sys.argv[1]]()
