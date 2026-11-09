"""Rebuild the requested full ZIP pair; preserve original inputs and history."""
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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
DOCS = ROOT / 'Project_Harness_Documentation_v0.5.1'
OUTPUT = ROOT / '_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07'
CACHES = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and not CACHES.intersection(p.parts)
                  and p.suffix != '.pyc')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root):
    rows = [f'{digest(p)}  {p.relative_to(root).as_posix()}'
            for p in files(root) if p != root / 'MANIFEST.sha256']
    (root / 'MANIFEST.sha256').write_text('\n'.join(rows) + '\n', 'utf-8')


def remove_generated(path):
    target = path.resolve()
    if target not in {(ENGINE / name).resolve() for name in ('build', 'dist', 'local_web/windows_ci_logs')}:
        raise ValueError(f'Not an allowlisted generated target: {target}')
    if not target.is_relative_to(ENGINE.resolve()) or path.is_symlink() or path.is_junction():
        raise ValueError(f'Unsafe generated target: {target}')
    if target.exists():
        shutil.rmtree(target)


def archive(root, path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in files(root):
            rel = p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f'{root.name}/{rel}', (2026, 11, 7, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if rel == 'bin/project-harness' else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, p.read_bytes())
    with zipfile.ZipFile(path) as zf:
        assert zf.testzip() is None
        assert len(zf.namelist()) == len(files(root))
        for p in files(root):
            assert zf.read(f'{root.name}/{p.relative_to(root).as_posix()}') == p.read_bytes()
    return {'file': path.name, 'sha256': digest(path), 'files': len(files(root)), 'crc_tree': 'PASS'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-wheel', action='store_true', help='Keep already built unchanged wheel')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--hash-name', default='PH_LW_04_05_WINDOWS_ACCEPTANCE_SHA256.txt')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('documentation_validator', DOCS / 'tools/validate_documentation.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.build_aggregates(DOCS)
    manifest(DOCS)
    mirror = ENGINE / 'docs' / DOCS.name
    shutil.copytree(DOCS, mirror, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*CACHES, '*.pyc'))
    if {p.relative_to(DOCS) for p in files(DOCS)} != {p.relative_to(mirror) for p in files(mirror)}:
        raise ValueError('Unexpected extra embedded docs; investigate instead of deleting')
    for p in files(DOCS):
        assert p.read_bytes() == (mirror / p.relative_to(DOCS)).read_bytes()
    if not args.no_wheel:
        remove_generated(ENGINE / 'build')
        remove_generated(ENGINE / 'dist')
        (ENGINE / 'dist').mkdir()
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                        '--no-index', '--wheel-dir', 'dist', '.'], cwd=ENGINE, check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    # Old attempted CI logs were copied to _scratch/acceptance before removal.
    remove_generated(ENGINE / 'local_web/windows_ci_logs')
    manifest(ENGINE)
    result = [archive(root, output / f'{root.name}_PH_LW_05.zip') for root in (ENGINE, DOCS)]
    (output / args.hash_name).write_text(
        ''.join(f'{r["sha256"]}  {r["file"]}\n' for r in result), 'utf-8')
    (output / 'ARCHIVE_INTEGRITY.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
