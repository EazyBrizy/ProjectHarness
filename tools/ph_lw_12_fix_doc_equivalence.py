"""Prove exact unit-test inputs unchanged by the documentation-only rebuild."""
import json,hashlib
from package_acceptance import ROOT,ENGINE
W=ROOT/'_workspace/PH_LW_12_FIX'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=read(W/'RUNTIME_FREEZE_CANDIDATE_03.json');new=read(W/'RUNTIME_FREEZE.json')
assert old['source_hashes']==new['source_hashes']
assert old['wheel_sha256']==new['wheel_sha256']
assert old['engine_build_digest']==new['engine_build_digest']
for row in read(W/'DISCOVERY.json')['methods']:
    assert row['test_file_sha256']==sha(ENGINE/(row['module'].replace('.','/')+'.py'))
changed=[name for name in sorted(set(old['documentation_hashes'])|set(new['documentation_hashes']))
    if old['documentation_hashes'].get(name)!=new['documentation_hashes'].get(name)]
assert set(changed)=={'13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md',
    'FILE_INDEX.md','MANIFEST.sha256'},changed
old_chapter=ROOT/'_scratch/ph_lw_12_fix/input-frozen-candidate-03/_internal/documentation/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md'
chapter=ROOT/'Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/23_PH_LW_12_Blocker_Fixes.md'
assert chapter.read_text('utf-8').replace('**Дата:** 2026-10-25 (база документации v0.5.1)  \n','')==old_chapter.read_text('utf-8')
proof={'status':'PASS','scope':'Only source/wheel tests may use previous freeze. All actual installer/EXE runs repeated.',
    'previous_freeze_sha256':sha(W/'RUNTIME_FREEZE_CANDIDATE_03.json'),
    'current_freeze_sha256':sha(W/'RUNTIME_FREEZE.json'),'source_hashes_equal':True,'wheel_sha256_equal':True,
    'engine_build_digest_equal':True,'documentation_changes':changed,
    'runtime_code_changed':False,'tests_changed':False,'chapter_body_unchanged':True,
    'reason':'Required addendum base date only; generated index/manifest follow. Full aggregate unchanged.'}
(W/'RUNTIME_EQUIVALENCE.json').write_text(json.dumps(proof,indent=2)+'\n','utf-8')
(W/'FINAL04_TEST_FREEZE_READY.json').write_text(json.dumps({'status':'READY',
    'freeze':new['engine_build_digest'],'runtime_mutation_allowed':False},indent=2)+'\n','utf-8')
print('Source, wheel, tests unchanged; final04 installer requires fresh acceptance')
