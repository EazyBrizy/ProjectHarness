from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
text=(OUT/'checkpoint.py').read_text('utf-8')
text=text.replace("build=SCRATCH/'build02'", "build=SCRATCH/'build03'")
text=text.replace("before=SCRATCH/'before'", "before=SCRATCH/'before-final'")
for old,new in [('RUNTIME_FREEZE.json','RUNTIME_FREEZE_FINAL.json'),('BUILD_RESULT.json','BUILD_RESULT_FINAL.json'),
                ('INTEGRITY.json','INTEGRITY_FINAL.json'),('OPERATOR_UPGRADE.json','OPERATOR_UPGRADE_FINAL.json')]:
    # BUILD_RESULT is the builder's immutable input name; only evidence copy is renamed.
    if old=='BUILD_RESULT.json':
        text=text.replace("OUT/'BUILD_RESULT.json'", "OUT/'BUILD_RESULT_FINAL.json'")
    else:text=text.replace(old,new)
(OUT/'final_checkpoint.py').write_text(text,'utf-8')
import json
meta=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness/resources/local_web/metadata_v1.json'
value=json.loads(meta.read_text('utf-8'));value['local_web_build_id']='DOC-ANALYSIS-CLARITY2-20261112'
meta.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
