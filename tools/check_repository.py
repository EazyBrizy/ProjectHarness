"""Read-only Windows Git-checkout integrity; no private workspace inputs needed."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import subprocess
import sys


def io(path: Path) -> Path:
    return Path('\\\\?\\' + os.path.abspath(path))


def sha(path: Path) -> str:
    return hashlib.sha256(io(path).read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(io(path).read_text('utf-8-sig'))


def inventory(base: Path, *, caches: bool = False) -> set[str]:
    result = set()
    private = io(base)
    for current, directories, names in os.walk(private, followlinks=False):
        if not caches:
            directories[:] = [name for name in directories if name not in {'__pycache__', '.pytest_cache'}]
        for name in directories + names:
            path = Path(current) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Reparse point in checked tree: ' + str(path))
        for name in names:
            if caches or not name.endswith(('.pyc', '.pyo')):
                result.add((Path(current) / name).relative_to(private).as_posix())
    return result


def check(root: Path) -> dict:
    engine = root / 'Project_Harness_Engine_v0.5.1'
    docs = root / 'Project_Harness_Documentation_v0.5.1'
    evidence = root / '_workspace/DOCUMENT_DECISION_OPTIONS_2026-11-12'
    freeze = read(evidence / 'RUNTIME_FREEZE.json')
    integrity = read(evidence / 'INTEGRITY.json')
    tracked = {}
    for entry in subprocess.check_output(['git', '-C', str(root), 'ls-files', '--stage', '-z'], timeout=30).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, oid, stage = metadata.decode('ascii').split()
        if stage != '0' or mode not in {'100644', '100755'}:
            raise ValueError('Resolve unsupported/conflicted Git entries first')
        tracked[name.decode('utf-8')] = oid
    object_format = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-object-format'], text=True, timeout=30).strip()
    checks = {}
    errors = []

    def compare(label, base, expected, *, exact=False, caches=False):
        missing = []; changed = []; untracked = []; blob_changed = []
        for name, digest in expected.items():
            if (not isinstance(name, str) or PureWindowsPath(name).drive or PureWindowsPath(name).root
                    or '\\' in name or any(part in {'', '.', '..'} for part in name.split('/'))):
                raise ValueError('Unsafe manifest path')
            full = base / name
            relative = full.relative_to(root).as_posix()
            if not io(full).is_file():
                missing.append(relative)
            else:
                content = io(full).read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    changed.append(relative)
                git_digest = hashlib.new(object_format, b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
                if relative in tracked and tracked[relative] != git_digest:
                    blob_changed.append(relative)
            if relative not in tracked:
                untracked.append(relative)
        extra = sorted(inventory(base, caches=caches) - set(expected)) if exact else []
        row = {'status': 'FAIL' if missing or changed or untracked or extra or blob_changed else 'PASS',
               'required': len(expected), 'missing': missing, 'changed': changed,
               'not_in_git': untracked, 'git_blob_mismatch': blob_changed, 'unexpected': extra}
        checks[label] = row
        if row['status'] != 'PASS':
            errors.append(label)

    compare('source', engine / 'src/project_harness', freeze['source_hashes'], exact=True)
    for label, base in [('documentation', docs), ('embedded_documentation', engine / 'docs' / docs.name)]:
        compare(label, base, freeze['documentation_hashes'], exact=True)
    compare('artifacts', engine, {
        'dist/project_harness_engine-0.5.1-py3-none-any.whl': freeze['wheel_sha256'],
        'windows/Harness-Setup-win-x64.exe': freeze['installer_sha256'],
        'windows/Harness/PACKAGE_FILES.json': freeze['package_manifest_sha256']})
    bundle = engine / 'windows/Harness'
    package = read(bundle / 'PACKAGE_FILES.json')
    if (set(package) != {'format', 'build_id', 'files'} or package['format'] != 1
            or package['build_id'] != freeze['build_id'] or not isinstance(package['files'], dict)):
        raise ValueError('Invalid frozen package manifest')
    compare('frozen_bundle', bundle, {**package['files'], 'PACKAGE_FILES.json': freeze['package_manifest_sha256']}, exact=True, caches=True)

    # Full acceptance manifests also include reproducible build metadata. Keep
    # that historical evidence unchanged and verify only versioned payload here.
    manifest = engine / 'MANIFEST.sha256'
    expected_manifest = integrity['engine_manifest_sha256']
    compare('working_manifest_anchor', engine, {'MANIFEST.sha256': expected_manifest})
    payload = {}; generated = []
    for line in io(manifest).read_text('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        if name.startswith(('build/', 'src/project_harness_engine.egg-info/')):
            generated.append(name)
        else:
            payload[name] = digest
    compare('versioned_acceptance_payload', engine, payload)
    return {'status': 'FAIL' if errors else 'PASS', 'root': str(root), 'build_id': freeze['build_id'],
            'scope': 'Versioned Git payload, source/docs/artifact hashes and complete frozen package; not a new runtime acceptance.',
            'git_index_files': len(tracked), 'checks': checks, 'failed_checks': errors,
            'local_generated_entries_not_required': len(generated),
            'local_directories_not_required': ['_inputs', '_deliverables', '_scratch', '_tools', '.venv'],
            'runtime_tests': 'NOT RUN; existing acceptance unchanged', 'automatic_executor_enabled': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This repository workflow is Windows-only')
    root = Path(os.path.abspath(args.root))
    if not re.fullmatch(r'[A-Za-z]:', PureWindowsPath(root).drive) or str(root).startswith(('\\\\', '//')):
        parser.error('Use an ordinary absolute local drive path')
    try:
        result = check(root)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result = {'status': 'FAIL', 'root': str(root), 'error': str(error)}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
