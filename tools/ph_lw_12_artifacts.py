"""Publish and freeze exact unpacked PH-LW-12 runtime artifacts; no ZIPs."""
import argparse,hashlib,json,shutil,struct,sys
from package_acceptance import ROOT,ENGINE,DOCS,files
sys.path.insert(0,str(ENGINE/'src'))
from project_harness.windows_package import verify_bundle

parser=argparse.ArgumentParser();parser.add_argument('--build',default='build-delivery');parser.add_argument('--preserve',default='')
args=parser.parse_args()
OUT=ROOT/'_workspace/PH_LW_12';scratch=ROOT/'_scratch/ph_lw_12';build=scratch/args.build
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ENGINE/'src/project_harness'
source_hashes={p.relative_to(source).as_posix():sha(p) for p in files(source)}
result=json.loads((build/'BUILD_RESULT.json').read_text('utf-8'))
assert source_hashes==result['source_files']
suffix='-'+args.preserve if args.preserve else ''
target=(ENGINE/'windows/Harness').resolve();archive=(scratch/('input-frozen'+suffix)).resolve()
assert target==ENGINE.resolve()/'windows/Harness' and target.is_relative_to(ENGINE.resolve()/'windows')
assert archive.is_relative_to(scratch.resolve()) and not archive.exists()
assert not target.is_symlink() and not target.is_junction()
shutil.copy2(ENGINE/'windows/Harness-Setup-win-x64.exe',scratch/('input-Harness-Setup'+suffix+'.exe'))
shutil.copy2(ENGINE/'windows/BUILD_RESULT.json',scratch/('INPUT_BUILD_RESULT'+suffix+'.json'))
target.rename(archive)
shutil.copytree(build/'frozen/Harness',target)
for name in ('BUILD_RESULT.json','Harness-Setup-win-x64.exe'):shutil.copy2(build/name,ENGINE/'windows'/name)
verify_bundle(target)
assert {p.relative_to(source).as_posix():sha(p) for p in files(source)}=={
    p.relative_to(target/'_internal/project_harness').as_posix():sha(p) for p in files(target/'_internal/project_harness')}
assert {p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)}=={
    p.relative_to(target/'_internal/documentation').as_posix():sha(p) for p in files(target/'_internal/documentation')}
def pe(path):
    data=path.read_bytes();off=struct.unpack_from('<I',data,0x3c)[0]
    assert data[:2]==b'MZ' and data[off:off+4]==b'PE\0\0'
    return hex(struct.unpack_from('<H',data,off+4)[0])
assert pe(target/'Harness.exe')=='0x8664'
value={'source_hashes':source_hashes,'documentation_hashes':{p.relative_to(DOCS).as_posix():sha(p) for p in files(DOCS)},
    'engine_build_digest':result['source_digest'],'build_id':result['build_id'],
    'wheel_sha256':sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
    'installer_sha256':sha(ENGINE/'windows/Harness-Setup-win-x64.exe'),
    'package_manifest_sha256':sha(target/'PACKAGE_FILES.json'),
    'architecture':{'payload_Harness_exe':pe(target/'Harness.exe'),
        'setup_bootstrap':pe(ENGINE/'windows/Harness-Setup-win-x64.exe'),
        'target':'Inno Setup ArchitecturesAllowed=x64compatible; Windows 11 x64 acceptance'},
    'signing':'UNSIGNED','zip_created':False,'runtime_changes_after_freeze_allowed':False}
(OUT/'RUNTIME_FREEZE.json').write_text(json.dumps(value,indent=2)+'\n','utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in ('source_hashes','documentation_hashes')},indent=2))
