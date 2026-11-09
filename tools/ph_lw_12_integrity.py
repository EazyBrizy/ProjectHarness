"""Read-only final runtime/resources/architecture and bounded secret scan."""
import base64,csv,hashlib,io,json,re,sys,zipfile
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
sys.path.insert(0,str(ENGINE/'src'))
from project_harness.windows_package import verify_bundle

OUT=ROOT/'_workspace/PH_LW_12';freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ENGINE/'src/project_harness';frozen=ENGINE/'windows/Harness'
assert freeze['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
assert freeze['documentation_hashes']=={p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)}
assert freeze['wheel_sha256']==sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')
assert freeze['installer_sha256']==sha(ENGINE/'windows/Harness-Setup-win-x64.exe')
verify_bundle(frozen)
mirrors={}
for name in ('schemas','registries','templates','skills'):
    left={p.relative_to(ENGINE/name).as_posix():sha(p) for p in files(ENGINE/name)}
    right={p.relative_to(source/'resources'/name).as_posix():sha(p) for p in files(source/'resources'/name)}
    assert left==right,name;mirrors[name]={'status':'PASS','files':len(left)}
with zipfile.ZipFile(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl') as z:
    assert z.testzip() is None
    package={n.removeprefix('project_harness/'):hashlib.sha256(z.read(n)).hexdigest()
             for n in z.namelist() if n.startswith('project_harness/') and not n.endswith('/')}
    assert package==freeze['source_hashes']
    record=next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
    records=list(csv.reader(io.StringIO(z.read(record).decode())))
    for name,digest,size in records:
        if not digest:continue
        assert digest=='sha256='+base64.urlsafe_b64encode(hashlib.sha256(z.read(name)).digest()).rstrip(b'=').decode()
        assert len(z.read(name))==int(size)
private_names={'launcher-private.json','launcher-auth.bin','ui-resume.json','catalog.json'}
bad=[p.relative_to(ENGINE).as_posix() for p in files(ENGINE) if p.name in private_names or
     any(x in p.relative_to(ENGINE).parts for x in ('_scratch','_tools','.venv','__pycache__','uploads','quarantine'))]
assert not bad,bad
patterns={
 'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'openai_key_shape':re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}'),
 'live_bootstrap_url':re.compile(r'#bootstrap=[A-Za-z0-9_-]{24,}'),
 'github_token_shape':re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}')}
matches=[];count=0
for base in (source,DOCS):
 for p in files(base):
    if p.suffix not in {'.py','.md','.json','.yaml','.html','.js','.css'}:continue
    count+=1;text=p.read_text('utf-8',errors='replace')
    for name,pattern in patterns.items():
        if pattern.search(text):matches.append({'file':p.relative_to(ROOT).as_posix(),'pattern':name})
assert not matches,matches
archives=json.loads((OUT/'PRESERVED_ARCHIVES.json').read_text('utf-8'))
for name,digest in archives.items():assert sha(ROOT/name)==digest,name
result={'status':'PASS','runtime_freeze_unchanged':True,'wheel_crc_record_source':'PASS',
    'frozen_inventory':'PASS','resource_mirrors':mirrors,'private_runtime_files':bad,
    'secret_scan':{'status':'PASS','text_files':count,'patterns':list(patterns),'matches':matches,
        'limitations':'Bounded pattern scan of controlled runtime source/resources and documentation; no universal DLP or semantic/binary secret guarantee. Fixture and operator raw roots excluded from delivery.'},
    'architecture':freeze['architecture'],'preserved_archives':len(archives),'zip_created':False}
(OUT/'INTEGRITY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
