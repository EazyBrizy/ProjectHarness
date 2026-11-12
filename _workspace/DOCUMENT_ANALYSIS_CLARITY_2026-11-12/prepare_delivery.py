"""Create current-task packaging helpers without rewriting historical evidence."""
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
old=(ROOT/'_workspace/MANUAL_ANALYSIS_ARCHIVE_2026-11-10/checkpoint.py').read_text('utf-8')
prefix=old[:old.index('def verify():')]
prefix=prefix.replace('Analysis option layout artifacts; only visual placement is observed.','Current document-analysis clarity artifacts; no full runtime regression.')
prefix=prefix.replace('_scratch/manual_analysis_archive_20261110','_scratch/document_analysis_clarity_20261112')
prefix=prefix.replace("build=SCRATCH/'build';", "build=SCRATCH/'build02';")
upgrade=old[old.index('def upgrade():'):old.index("if __name__=='__main__':")]
verify='''def verify():
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
    allowed=set(baseline['allowed_source'])-{'resources/local_web/assets/styles.css','resources/local_web/build_metadata.json'}
    allowed|={'resources/local_web/assets/app.css','resources/local_web/metadata_v1.json'}
    assert changed==allowed,changed^allowed
    tests=inventory(ENGINE/'tests')
    assert {n for n,h in baseline['tests'].items() if tests.get(n)!=h}=={'test_cli_document_analysis.py','test_manual_analysis_archive.py'}
    assert set(tests)-set(baseline['tests'])=={'test_document_analysis_clarity.py'}
    assert {n for n,h in baseline['docs'].items() if docs.get(n)!=h}=={'FILE_INDEX.md','MANIFEST.sha256'}
    assert set(docs)-set(baseline['docs'])=={'13_Local_Web_Manual_Companion/34_Document_Analysis_Results_and_Models.md'}
    value={'status':'PASS','build_id':freeze['build_id'],'source_build_wheel_frozen':'PASS','full_frozen_payload_including_pyd':'PASS',
        'documentation_mirrors':'PASS','manifests':'PASS','allowed_source_changes':sorted(changed),
        'core_contracts_and_historical_documentation_preserved':True,'unrelated_tests_preserved':True,
        'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256'),'docs_manifest_sha256':sha(DOCS/'MANIFEST.sha256'),'zip_created':False}
    save('INTEGRITY.json',value);print(json.dumps(value,ensure_ascii=False,indent=2))

'''
(OUT/'checkpoint.py').write_text(prefix+verify+upgrade+"if __name__=='__main__':\n    {'publish':publish,'verify':verify,'upgrade':upgrade}[sys.argv[1]]()\n",'utf-8')
stop=(ROOT/'_workspace/MANUAL_ANALYSIS_ARCHIVE_2026-11-10/stop_for_update.py').read_text('utf-8')
(OUT/'stop_for_update.py').write_text(stop,'utf-8')
print('Prepared task-local delivery helpers')
