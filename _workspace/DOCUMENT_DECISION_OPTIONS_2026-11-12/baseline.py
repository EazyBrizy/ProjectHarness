import hashlib,json,shutil,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
def inventory(base):
    return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
if __name__=='__main__':
    assert not (OUT/'INPUT_BASELINE.json').exists()
    source=ENGINE/'src/project_harness';docs=ROOT/'Project_Harness_Documentation_v0.5.1'
    freeze=json.loads((ROOT/'_workspace/DOCUMENT_ANALYSIS_UNIVERSALITY_2026-11-12/RUNTIME_FREEZE.json').read_text('utf-8'))
    assert inventory(source)==freeze['source_hashes']
    for base in (ENGINE,docs):
        for line in (base/'MANIFEST.sha256').read_text('utf-8').splitlines():
            sha,name=line.split('  ',1);assert hashlib.sha256((base/name).read_bytes()).hexdigest()==sha,name
    allowed=['local_web_analysis.py','local_web_answers.py','local_web_exchange.py','local_web_exchange_contract.py',
        'local_web_http.py','local_web_service.py','resources/local_web/GPT_PREPARATION.md',
        'resources/local_web/gpt_exchange_reply_v4.schema.json','resources/local_web/assets/interview.js',
        'resources/local_web/assets/app.css','resources/local_web/metadata_v1.json']
    (OUT/'INPUT_BASELINE.json').write_text(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'dirty_before':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'source':inventory(source),
        'docs':inventory(docs),'tests':inventory(ENGINE/'tests'),'allowed_source':allowed},ensure_ascii=False,indent=2)+'\n','utf-8')
    for name in allowed:
        if not (source/name).exists():continue
        target=ROOT/'_scratch/document_decision_options_20261112/before/source'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
    print('PASS: current freeze/manifests; previous work retained; baseline saved')
