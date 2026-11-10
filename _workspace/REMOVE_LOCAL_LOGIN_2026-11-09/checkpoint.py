"""Current no-login artifacts and isolated acceptance; historical runs stay immutable."""
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
SCRATCH=ROOT/'_scratch/remove_local_login_20261109'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def inventory(base):
    return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def save(name,data):
    p=OUT/name
    assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')

def publish():
    build=SCRATCH/'build-final';bundle=build/'frozen/Harness'
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
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None
        for name,digest in source.items():
            assert hashlib.sha256(z.read('project_harness/'+name)).hexdigest()==digest
    for base in (ENGINE,DOCS):
        expected={name:digest for digest,name in (line.split('  ',1) for line in (base/'MANIFEST.sha256').read_text('utf-8').splitlines())}
        actual=inventory(base);actual.pop('MANIFEST.sha256')
        assert actual==expected,'Manifest mismatch: '+str(base)
    baseline=json.loads((OUT/'INPUT_BASELINE.json').read_text('utf-8'))
    changed=[name for name,digest in baseline['source'].items() if source.get(name)!=digest]
    allowed={'cli.py','local_web_http.py','local_web_launcher.py','local_web_instance.py','windows_package.py',
             'resources/local_web/metadata_v1.json','resources/local_web/assets/index.html'}
    allowed|={'resources/local_web/assets/'+n+'.js' for n in ('app','approvals','interview','lifecycle','preparation','tasks')}
    assert set(changed)<=allowed,changed
    tests=inventory(ENGINE/'tests')
    test_changes={n for n,h in baseline['tests'].items() if tests.get(n)!=h}
    allowed_tests={'test_document_upload_feedback.py','test_ph_lw_04_05_acceptance.py','test_ph_lw_04_http.py',
        'test_ph_lw_05_http.py','test_ph_lw_06_http.py','test_ph_lw_07_http.py','test_ph_lw_08_http.py',
        'test_ph_lw_09_http.py','test_ph_lw_09_manual_evidence.py','test_ph_lw_10_http.py',
        'test_ph_lw_11_desktop.py','test_ph_lw_12_acceptance.py','test_ph_lw_12_blockers.py'}
    assert test_changes<=allowed_tests,test_changes
    assert {n for n,h in baseline['documentation'].items() if docs.get(n)!=h}=={'FILE_INDEX.md','MANIFEST.sha256'}
    value={'status':'PASS','source_build_wheel_frozen':'PASS','full_frozen_payload_including_pyd':'PASS',
        'documentation_mirrors':'PASS','manifests':'PASS','only_allowed_runtime_changes':changed,
        'historical_documentation_preserved':True,'unrelated_original_tests_preserved':True,
        'build_id':freeze['build_id'],'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256'),
        'docs_manifest_sha256':sha(DOCS/'MANIFEST.sha256'),'zip_created':False}
    if not (OUT/'INTEGRITY.json').exists():save('INTEGRITY.json',value)
    print(json.dumps(value,ensure_ascii=False,indent=2))

def wheel_tests():
    import project_harness
    package=Path(project_harness.__file__).resolve().parent
    assert package.is_relative_to(Path(sys.prefix).resolve()) and not package.is_relative_to(ENGINE)
    assert inventory(package)==inventory(ENGINE/'src/project_harness')
    print(json.dumps({'interpreter':sys.executable,'python':sys.version,'package':str(package),
        'cwd':str(Path.cwd()),'source_import':False,'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')}},ensure_ascii=False),flush=True)
    sys.path.insert(0,str(ENGINE)) # tests only, never src
    modules=['tests.test_ph_lw_04_http.LocalHttpDependencyIndependent.test_local_login_implementation_removed',
        'tests.test_ph_lw_04_http.FlaskAppSecurityTests.test_direct_reads_without_login_and_removed_login_routes',
        'tests.test_ph_lw_04_http.FlaskAppSecurityTests.test_no_login_mutation_exact_json_and_transport_headers',
        'tests.test_ph_lw_04_http.FlaskAppSecurityTests.test_exact_host_origin_null_port_and_proxy_rejected',
        'tests.test_ph_lw_11_desktop.DesktopContractTests.test_stop_without_login_preserves_origin_and_field_validation',
        'tests.test_ph_lw_11_desktop.NativeLauncherTests.test_native_mutex_subprocess',
        'tests.test_ph_lw_11_desktop.NativeLauncherTests.test_plain_instance_record_discovery_cleanup_and_invalid_records']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    label='WHEEL_RESULTS'+('_02' if '--retry' in sys.argv else '')+'.json'
    save(label,{'ran':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),
        'skips':len(result.skipped),'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL'})
    raise SystemExit(not result.wasSuccessful() or bool(result.skipped))

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
    {'publish':publish,'verify':verify,'wheel-tests':wheel_tests,'upgrade':upgrade}[sys.argv[1]]()
