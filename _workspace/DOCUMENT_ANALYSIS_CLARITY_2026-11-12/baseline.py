import hashlib, json, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ENGINE = ROOT/'Project_Harness_Engine_v0.5.1'
SOURCE = ENGINE/'src/project_harness'
def inventory(base):
    return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
if __name__ == '__main__':
    assert not (OUT/'INPUT_BASELINE.json').exists()
    freeze=json.loads((ROOT/'_workspace/MANUAL_ANALYSIS_ARCHIVE_2026-11-10/RUNTIME_FREEZE.json').read_text('utf-8'))
    assert inventory(SOURCE)==freeze['source_hashes']
    for base in (ENGINE,ROOT/'Project_Harness_Documentation_v0.5.1'):
        for line in (base/'MANIFEST.sha256').read_text('utf-8').splitlines():
            sha,relative=line.split('  ',1)
            assert hashlib.sha256((base/relative).read_bytes()).hexdigest()==sha,relative
    scope=['local_web_analysis.py','local_web_exchange.py','local_web_exchange_contract.py','local_web_cli.py',
        'local_web_cli_analysis.py','local_web_service.py','local_web_http.py','resources/local_web/GPT_PREPARATION.md',
        'resources/local_web/gpt_exchange_reply_v3.schema.json','resources/local_web/assets/interview.js',
        'resources/local_web/assets/index.html','resources/local_web/assets/app.css','resources/local_web/metadata_v1.json']
    (OUT/'INPUT_BASELINE.json').write_text(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'source':inventory(SOURCE),
        'docs':inventory(ROOT/'Project_Harness_Documentation_v0.5.1'),'tests':inventory(ENGINE/'tests'),
        'allowed_source':scope},ensure_ascii=False,indent=2)+'\n','utf-8')
    before=ROOT/'_scratch/document_analysis_clarity_20261112/before/source'
    for name in scope:
        file=SOURCE/name
        if file.exists():
            target=before/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
    print('PASS: source freeze and input manifests; baseline saved')
