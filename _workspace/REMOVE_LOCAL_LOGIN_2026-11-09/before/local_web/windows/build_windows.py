"""Pinned native PyInstaller onedir + Inno Setup; no end-user downloads.

Run with a dedicated developer venv installed from both hash locks. Output
must be new. No ZIP artifacts or security-setting modifications are performed.
"""
from __future__ import annotations
import argparse
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ENGINE = Path(__file__).resolve().parents[2]
PACKAGES = ['PyInstaller', 'pyinstaller-hooks-contrib', 'altgraph', 'pefile', 'pywin32-ctypes',
            'packaging', 'setuptools', 'Flask', 'Waitress', 'PyYAML', 'Werkzeug', 'Jinja2',
            'MarkupSafe', 'click', 'blinker', 'itsdangerous', 'colorama']
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', 'utf-8')
def run(command, cwd=None):
    print(json.dumps(list(map(str, command)), ensure_ascii=False), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--iscc', required=True, type=Path)
    args = parser.parse_args()
    if os.name != 'nt' or platform.machine().upper() not in {'AMD64', 'X86_64'} or platform.python_version() != '3.14.10':
        raise RuntimeError('Requires native Windows x64 CPython 3.14.10')
    if version('PyInstaller') != '6.22.3': raise RuntimeError('Pinned PyInstaller unavailable')
    pins = json.loads((Path(__file__).parent/'build_tools.json').read_text('utf-8'))
    if sha(args.iscc) != pins['iscc_sha256']: raise RuntimeError('Pinned Inno Setup compiler mismatch')
    for name, expected in pins['packages'].items():
        if version(name) != expected: raise RuntimeError('Build dependency mismatch: '+name)
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    meta = json.loads((ENGINE/'src/project_harness/resources/local_web/metadata_v1.json').read_text('utf-8'))
    build_id = meta['local_web_build_id']
    spec = out/'spec'; spec.mkdir()
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
        '--windowed', '--name', 'Harness', '--distpath', out/'frozen', '--workpath', out/'work',
        '--specpath', spec, '--paths', ENGINE/'src', '--collect-submodules', 'project_harness',
        '--manifest', ENGINE/'local_web/windows/Harness.manifest',
        '--collect-submodules', 'yaml', '--collect-all', 'flask', '--collect-all', 'waitress',
        '--add-data', str(ENGINE/'src/project_harness')+';project_harness',
        '--add-data', str(ENGINE/'docs/Project_Harness_Documentation_v0.5.1')+';documentation',
        '--exclude-module', 'tkinter', '--exclude-module', 'playwright',
        ENGINE/'local_web/windows/frozen_entry.py']
    run(command, ENGINE)
    bundle = out/'frozen/Harness'
    for cache in list(bundle.rglob('__pycache__')):
        # Only generated cache children of this newly created output.
        assert out in cache.resolve().parents
        shutil.rmtree(cache)
    notices = bundle/'THIRD_PARTY_LICENSES'; notices.mkdir()
    inventory = []
    for name in PACKAGES:
        dist = distribution(name)
        license_files = []
        for entry in dist.files or []:
            if any(word in entry.name.lower() for word in ('license', 'copying', 'notice')) and '.dist-info/' in str(entry):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    target = notices/(name+'-'+entry.name)
                    target.write_bytes(source.read_bytes()); license_files.append(target.name)
        inventory.append({'name': name, 'version': dist.version,
            'license': dist.metadata.get('License-Expression') or dist.metadata.get('License'),
            'license_files': license_files})
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if not python_license.exists(): raise RuntimeError('Python license required')
    shutil.copy2(python_license, notices/'Python-LICENSE.txt')
    shutil.copy2(args.iscc.resolve().parent/'License.txt', notices/'InnoSetup-LICENSE.txt')
    save(notices/'DEPENDENCIES.json', inventory)
    save(bundle/'PACKAGE_FILES.json', {'format':1, 'build_id':build_id, 'files':{
        p.relative_to(bundle).as_posix():sha(p) for p in sorted(bundle.rglob('*')) if p.is_file()}})
    run([bundle/'Harness.exe', '--check-package'], out)
    # Inno verifies compiled SHA-256 values BEFORE executing the frozen helper.
    checks = []
    deletes = []
    for path in sorted(bundle.rglob('*')):
        if not path.is_file(): continue
        rel = str(path.relative_to(bundle))
        checks.append("  if GetSHA256OfFile(ExpandConstant('{tmp}\\payload\\"+rel+"')) <> '"+sha(path)+"' then RaiseException('Payload integrity failure');")
        deletes.append('Type: files; Name: "{app}\\versions\\'+build_id+'\\'+rel+'"')
    for path in sorted([p for p in bundle.rglob('*') if p.is_dir()], key=lambda p:len(p.parts), reverse=True):
        deletes.append('Type: dirifempty; Name: "{app}\\versions\\'+build_id+'\\'+str(path.relative_to(bundle))+'"')
    deletes.append('Type: dirifempty; Name: "{app}\\versions\\'+build_id+'"')
    (out/'payload_checks.iss').write_text('\n'.join(checks)+'\n','utf-8-sig')
    (out/'payload_uninstall.iss').write_text('\n'.join(deletes)+'\n','utf-8-sig')
    script = (Path(__file__).parent/'Harness.iss').read_text('utf-8-sig')
    script = script.replace('@BUILD_ID@',build_id).replace('@BUNDLE@',str(bundle)).replace('@OUTPUT@',str(out))
    (out/'Harness.iss').write_text(script,'utf-8-sig')
    run([args.iscc, out/'Harness.iss'])
    save(out/'BUILD_RESULT.json', {'status':'BUILT_NOT_ACCEPTED', 'build_id':build_id,
        'python':sys.version,'platform':platform.platform(), 'signing':'UNSIGNED',
        'source_digest':meta['engine_build_digest'], 'iscc_sha256':sha(args.iscc),
        'installer_sha256':sha(out/'Harness-Setup-win-x64.exe'),
        'package_manifest_sha256':sha(bundle/'PACKAGE_FILES.json'), 'zip_created':False,
        'source_files':{p.relative_to(ENGINE/'src/project_harness').as_posix():sha(p)
            for p in sorted((ENGINE/'src/project_harness').rglob('*')) if p.is_file() and '__pycache__' not in p.parts},
        'dependencies':inventory})

if __name__ == '__main__': main()
