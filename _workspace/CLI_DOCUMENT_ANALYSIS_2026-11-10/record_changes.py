"""Record exact scoped edits against this task's own baseline, no history edits."""
import difflib
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(base):return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
baseline=json.loads((OUT/'INPUT_BASELINE.json').read_text('utf-8'))
records={};patches={}
for label,base,before in [('source',ENGINE/'src/project_harness',OUT/'before/src/project_harness'),
                          ('tests',ENGINE/'tests',OUT/'before/tests')]:
    now=inventory(base);original=baseline[label]
    changes={n:{'before':original.get(n),'after':now.get(n)} for n in sorted(set(now)|set(original)) if original.get(n)!=now.get(n)}
    records[label]=changes;parts=[]
    for name in changes:
        old=(before/name).read_text('utf-8').splitlines(True) if (before/name).is_file() else []
        new=(base/name).read_text('utf-8').splitlines(True) if (base/name).is_file() else []
        parts.extend(difflib.unified_diff(old,new,fromfile='before/'+label+'/'+name,tofile='after/'+label+'/'+name))
    patches[label]=''.join(parts)
for label,content in patches.items():(OUT/(label.upper()+'_DIFF.patch')).write_text(content,'utf-8')
docs=inventory(ROOT/'Project_Harness_Documentation_v0.5.1')
records['documentation']={n:{'before':baseline['documentation'].get(n),'after':docs.get(n)}
    for n in sorted(set(docs)|set(baseline['documentation'])) if baseline['documentation'].get(n)!=docs.get(n)}
records['navigation']={n:{'before':sha(OUT/'before'/n),'after':sha(ROOT/n)} for n in ('AGENTS.md','_workspace/CURRENT_TASK.md')}
records['additional_driver']={'local_web/windows/final_acceptance.py':{
    'after':sha(ENGINE/'local_web/windows/final_acceptance.py'),
    'before':'NOT RECORDED separately in this baseline',
    'scope':'Obsolete classification-selector interactions adapted; driver NOT RUN in this task'}}
(OUT/'CHANGED_FILE_HASHES.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n','utf-8')
freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
outputs={k:v for k,v in freeze.items() if k not in ('source_hashes','documentation_hashes')}
outputs['engine_manifest_sha256']=sha(ENGINE/'MANIFEST.sha256')
outputs['docs_manifest_sha256']=sha(ROOT/'Project_Harness_Documentation_v0.5.1/MANIFEST.sha256')
(OUT/'OUTPUT_HASHES.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'source_changes':len(records['source']),'test_changes':len(records['tests']),
                  'docs_changes':len(records['documentation']),'build_id':freeze['build_id']},ensure_ascii=False))
