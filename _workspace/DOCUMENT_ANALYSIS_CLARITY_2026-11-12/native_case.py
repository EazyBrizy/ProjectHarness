"""One real CLI analysis of the original four documents in a private workspace."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1';OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ENGINE/'src'));sys.path.insert(0,str(ENGINE))
from tests.test_ph_lw_04_05_acceptance import LiveServer
from project_harness.local_web_cli_analysis import _load
ATTEMPT=sys.argv[sys.argv.index('--attempt')+1] if '--attempt' in sys.argv else '01'
BASE=ROOT/('_scratch/document_analysis_clarity_20261112/native'+('' if ATTEMPT=='01' else ATTEMPT))
BASE.mkdir(parents=True,exist_ok=True)
assert not (BASE/'appdata').exists(),'Never overwrite an earlier run'
live=LiveServer(str(BASE))
try:
    pid=live.create('actual-four-document-case-20261112')
    documents=sorted((ROOT/'_scratch/document_analysis_audit_20261112/documents').glob('*.md'))
    assert len(documents)==4
    assert live.upload(pid,[(p.name,p.read_bytes()) for p in documents])[0]==200
    connection=live.service.connect_cli()
    model=next(m for m in connection['models'] if m['id']=='gpt-6-astra')
    live.service.select_cli_model(model=model['id'],reasoning_effort='medium')
    before=live.service.get_interview(pid)
    job=live.service.start_cli_analysis(pid,expected_fingerprint=before['fingerprint'],idempotency_key='actual-four-document-analysis-20261112')
    print(json.dumps({'state':job['state'],'selection':job['selection'],'documents':len(documents)},ensure_ascii=False),flush=True)
    live.service._futures[job['job_id']].result(timeout=340)
    result=live.service.get_cli_analysis(pid);after=live.service.get_interview(pid)
    (BASE/'interview.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),'utf-8')
    (BASE/'job.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    assert after['draft']==before['draft'],'Native analysis must not commit'
    preview=after['imports'][-1] if after['imports'] else None
    a=preview.get('analysis') if preview else None
    summary={'state':result['state'],'error_code':result.get('error_code'),'message_ru':result['message_ru'],
        'selection':result['selection'],'documents':len(documents),'canonical_draft_unchanged':True,
        'answers':len(a['answers']) if a else 0,'roadmap_stages':len(a['roadmap']) if a else 0,
        'current_questions':len([q for q in a['questions'] if q['stage']=='CURRENT']) if a else 0,
        'future_questions':len([q for q in a['questions'] if q['stage']=='FUTURE']) if a else 0,
        'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in documents}}
    (OUT/('NATIVE_CASE'+('' if ATTEMPT=='01' else ATTEMPT)+'.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'},ensure_ascii=False),flush=True)
    assert result['state']=='SUCCEEDED',result
finally:live.close()
