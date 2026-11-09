"""Correct addendum metadata, validate first, rebuild only frozen delivery."""
import json,shutil,subprocess,sys
from ph_lw_12_fix_run import ROOT,OUT,W,ENGINE,run,sha
from package_acceptance import DOCS,files

old=json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))
assert not (W/'RUNTIME_FREEZE_CANDIDATE_03.json').exists()
shutil.copy2(W/'RUNTIME_FREEZE.json',W/'RUNTIME_FREEZE_CANDIDATE_03.json')
shutil.copy2(W/'DOC_VALIDATION.json',W/'DOC_VALIDATION_METADATA_FAIL.json')
snapshot=W/'candidate-03-before-doc-metadata';snapshot.mkdir()
for p in [ENGINE/'PH_LW_12_FIX_TEST_REPORT.md',ENGINE/'PH_LW_12_FIX_CHANGED_FILES.md',
          ENGINE/'PH_LW_12_FIX_LOGS/VERDICTS.json',ENGINE/'PH_LW_12_FIX_LOGS/EVIDENCE_INDEX.json']:
    shutil.copy2(p,snapshot/p.name)
(W/'FINALIZATION_ATTEMPT_03.json').write_text(json.dumps({'status':'FAIL',
    'reason':'New chapter missing required **Дата:** 2026-10-25 addendum base metadata',
    'source_and_wheel_tests':'459 PASS / 2 known capability SKIP; exact bytes unchanged',
    'acceptance_not_finalized':True,'evidence':'documentation-final.log; DOC_VALIDATION_METADATA_FAIL.json'},indent=2)+'\n','utf-8')
current=ROOT/'_workspace/CURRENT_TASK.md'
current.write_text('PH-LW-12 finalization IN PROGRESS: docs validator rejected missing addendum base date; correcting docs and repeating exact installer acceptance. Previous provisional summary below is not a completed attestation.\n\n'+current.read_text('utf-8'),'utf-8')
chapter=DOCS/'13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md'
text=chapter.read_text('utf-8');assert '**Дата:**' not in text
chapter.write_text(text.replace('**Дата дополнения:**','**Дата:** 2026-10-25 (база документации v0.5.1)  \n**Дата дополнения:**',1),'utf-8')
subprocess.run([sys.executable,'-B',ROOT/'tools/sync_working_tree.py'],check=True)
assert run('docs-metadata-fixed-before-build',[sys.executable,'-B',DOCS/'tools/validate_documentation.py',DOCS,
    '--json',W/'DOC_VALIDATION_FIXED_BEFORE_BUILD.json'],timeout=120)['status']=='PASS'
command=json.loads((OUT/'build-03.run.json').read_text('utf-8'))['command']
command[command.index('--output')+1]=str(OUT/'build-04')
assert run('build-04',command,timeout=900)['status']=='PASS'
subprocess.run([sys.executable,'-B',ROOT/'tools/ph_lw_12_fix_artifacts.py','--build','build-04','--preserve','candidate-03'],check=True)
new=json.loads((W/'RUNTIME_FREEZE.json').read_text('utf-8'))
assert old['source_hashes']==new['source_hashes']
assert old['wheel_sha256']==new['wheel_sha256']
assert old['engine_build_digest']==new['engine_build_digest']
changed=[name for name in sorted(set(old['documentation_hashes'])|set(new['documentation_hashes']))
    if old['documentation_hashes'].get(name)!=new['documentation_hashes'].get(name)]
assert set(changed)=={'13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md',
    'FILE_INDEX.md','MANIFEST.sha256'},changed
proof={'status':'PASS','scope':'Only source/wheel tests may use the previous freeze. All actual installer/EXE runs repeated.',
    'previous_freeze_sha256':sha(W/'RUNTIME_FREEZE_CANDIDATE_03.json'),
    'current_freeze_sha256':sha(W/'RUNTIME_FREEZE.json'),'source_hashes_equal':True,'wheel_sha256_equal':True,
    'engine_build_digest_equal':True,'documentation_changes':changed,
    'runtime_code_changed':False,'tests_changed':False,'reason':'Required addendum base date only; generated aggregate/index/manifest follow.'}
(W/'RUNTIME_EQUIVALENCE.json').write_text(json.dumps(proof,indent=2)+'\n','utf-8')
(W/'FINAL04_TEST_FREEZE_READY.json').write_text(json.dumps({'status':'READY',
    'freeze':new['engine_build_digest'],'runtime_mutation_allowed':False},indent=2)+'\n','utf-8')
print('Docs-only delivery rebuilt; source/wheel exact original tested bytes retained',flush=True)
