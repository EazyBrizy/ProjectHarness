"""Synchronize unpacked docs, build inputs, wheel and manifests; never create ZIPs."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from package_acceptance import ROOT, ENGINE, DOCS, CACHES, files, manifest, remove_generated


def main():
    # Importing the validator must not add cache files to its generated index.
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-wheel', action='store_true')
    args = parser.parse_args()
    meta = ENGINE / 'src/project_harness/resources/local_web/metadata_v1.json'
    source = ENGINE / 'src/project_harness'
    entries = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(source).as_posix()}'
               for p in files(source) if p != meta]
    build_digest = 'sha256:' + hashlib.sha256(('\n'.join(entries) + '\n').encode()).hexdigest()
    data = json.loads(meta.read_text('utf-8'))
    if data.get('engine_build_digest') != build_digest:
        if not args.build_wheel:
            raise ValueError('Source changed: --build-wheel required to update build metadata and wheel')
        data['engine_build_digest'] = build_digest
        meta.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    caches = [p for p in DOCS.rglob('*') if p.is_file() and
              (CACHES.intersection(p.parts) or p.suffix == '.pyc')]
    if caches:
        raise ValueError('Remove generated documentation caches before indexing: ' + ', '.join(map(str, caches)))
    spec = importlib.util.spec_from_file_location('documentation_validator', DOCS / 'tools/validate_documentation.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.build_aggregates(DOCS)
    manifest(DOCS)
    mirror = ENGINE / 'docs' / DOCS.name
    shutil.copytree(DOCS, mirror, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*CACHES, '*.pyc'))
    assert {p.relative_to(DOCS) for p in files(DOCS)} == {p.relative_to(mirror) for p in files(mirror)}
    assert all(p.read_bytes() == (mirror / p.relative_to(DOCS)).read_bytes() for p in files(DOCS))
    if args.build_wheel:
        remove_generated(ENGINE / 'build'); remove_generated(ENGINE / 'dist')
        (ENGINE / 'dist').mkdir()
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                        '--no-index', '--wheel-dir', 'dist', '.'], cwd=ENGINE, check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})
    manifest(ENGINE)
    print(json.dumps({'status':'PASS', 'engine_build_digest':build_digest, 'zip_created':False,
        'engine_manifest_sha256':hashlib.sha256((ENGINE/'MANIFEST.sha256').read_bytes()).hexdigest(),
        'docs_manifest_sha256':hashlib.sha256((DOCS/'MANIFEST.sha256').read_bytes()).hexdigest(),
        'wheel_sha256':hashlib.sha256((ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl').read_bytes()).hexdigest()},indent=2))


if __name__ == '__main__':
    main()
