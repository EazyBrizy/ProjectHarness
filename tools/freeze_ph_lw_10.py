import hashlib,json,platform,sys
from importlib.metadata import version
from package_acceptance import ROOT,ENGINE,files
out=ROOT/'_scratch/ph_lw_10'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ENGINE/'src/project_harness'
value={'source_hashes':{p.relative_to(source).as_posix():sha(p) for p in files(source)},
 'test_hashes':{p.relative_to(ENGINE).as_posix():sha(p) for folder in (ENGINE/'tests',ENGINE/'local_web') for p in files(folder)},
 'engine_build_digest':json.loads((source/'resources/local_web/metadata_v1.json').read_text('utf-8'))['engine_build_digest'],
 'wheel_sha256':sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')}
(out/'FINAL_BUILD_FREEZE.json').write_text(json.dumps(value,indent=2)+'\n','utf-8')
(out/'SOURCE_ENVIRONMENT.json').write_text(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
 'dependencies':{x:version(x) for x in ['flask','waitress','playwright','PyYAML','jsonschema','setuptools','wheel']}},indent=2)+'\n','utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in ('source_hashes','test_hashes')},indent=2))
