import json
from package_acceptance import ROOT,ENGINE
p=ENGINE/'src/project_harness/resources/local_web/metadata_v1.json'
v=json.loads(p.read_text('utf-8'));base=json.loads((ROOT/'_workspace/PH_LW_10/INPUT_BASELINE.json').read_text('utf-8'))
v['local_web_build_id']='PH-LW-10-20261107'
v['note']='PH-LW-10 manual Stage lifecycle forms/adapters; automatic executor disabled; PH-LW-11 not started; full v0.5.1 remains NO-GO.'
v['ph_lw_10']={'report':'PH_LW_10_TEST_REPORT.md',
 'input_engine_manifest_sha256':base['trees'][ENGINE.name]['manifest_sha256'],
 'input_documentation_manifest_sha256':base['trees']['Project_Harness_Documentation_v0.5.1']['manifest_sha256'],
 'input_wheel_sha256':base['wheel_sha256'],'artifact_policy':'Unpacked working files; no Engine/Documentation ZIP requested'}
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
