"""Capture the final PH-LW-11 source/wheel/installer build under test."""
import argparse,hashlib,json,platform,sys
from importlib.metadata import version
from package_acceptance import ROOT,ENGINE,files
out=ROOT/'_scratch/ph_lw_11'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--build',required=True);parser.add_argument('--name',default='FINAL_BUILD_FREEZE.json')
args=parser.parse_args()
source=ENGINE/'src/project_harness';build=out/args.build
value={'source_hashes':{p.relative_to(source).as_posix():sha(p) for p in files(source)},
 'test_hashes':{p.relative_to(ENGINE).as_posix():sha(p) for folder in (ENGINE/'tests',ENGINE/'local_web') for p in files(folder)},
 'engine_build_digest':json.loads((source/'resources/local_web/metadata_v1.json').read_text('utf-8'))['engine_build_digest'],
 'wheel_sha256':sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
 'installer_sha256':sha(build/'Harness-Setup-win-x64.exe'),
 'package_manifest_sha256':sha(build/'frozen/Harness/PACKAGE_FILES.json')}
assert value['source_hashes']==json.loads((build/'BUILD_RESULT.json').read_text('utf-8'))['source_files']
(out/args.name).write_text(json.dumps(value,indent=2)+'\n','utf-8')
(out/'SOURCE_ENVIRONMENT.json').write_text(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
 'dependencies':{x:version(x) for x in ['flask','waitress','playwright','PyYAML','jsonschema','setuptools','wheel']}},indent=2)+'\n','utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in ('source_hashes','test_hashes')},indent=2))
