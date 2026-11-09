"""Verify supplied archives without trusting member paths; optionally extract once."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    'Project_Harness_Engine_v0.5.1_PH_LW_05.zip',
    'Project_Harness_Documentation_v0.5.1_PH_LW_05.zip',
    'Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0 (1).zip',
    'Project_Harness_Windows_Local_Web_Implementation_Prompts_RU_r2 (1).zip',
]
LOOSE = {
    'AGENTS.md': 'AGENTS.original.md',
    'Project_Harness_v0.5.0_Remediation_Plan_RU (1).md': 'Project_Harness_v0.5.0_Remediation_Plan_RU.md',
    'Project_Harness_v0.5.1_Implementation_Plan_RU (1).md': 'Project_Harness_v0.5.1_Implementation_Plan_RU.md',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect_archive(path):
    with zipfile.ZipFile(path) as archive:
        seen = set()
        for info in archive.infolist():
            name = info.filename
            parts = PurePosixPath(name).parts
            if ('\\' in name or not parts or name.startswith('/')
                    or any(p in ('.', '..') or ':' in p or p.endswith((' ', '.')) for p in parts)
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError(f'Unsafe member: {name}')
            if name.casefold() in seen:
                raise ValueError(f'Duplicate member: {name}')
            seen.add(name.casefold())
        bad = archive.testzip()
        if bad:
            raise ValueError(f'CRC failure: {bad}')
        manifests = []
        for name in archive.namelist():
            if not name.endswith('/MANIFEST.sha256'):
                continue
            prefix = name.rsplit('/', 1)[0] + '/'
            count = 0
            listed = set()
            for line in archive.read(name).decode('utf-8-sig').splitlines():
                if not line.strip() or line.startswith('#'):
                    continue
                match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?(.+)', line)
                if not match:
                    raise ValueError(f'Invalid manifest line: {name}: {line}')
                digest, relative = match.groups()
                member = prefix + relative
                if member in listed or sha(archive.read(member)) != digest.lower():
                    raise ValueError(f'Manifest mismatch/duplicate: {member}')
                listed.add(member)
                count += 1
            unlisted = [n for n in archive.namelist()
                        if n.startswith(prefix) and not n.endswith('/')
                        and n != name and n not in listed]
            manifests.append({'path': name, 'verified': count, 'unlisted': unlisted})
        return {'file': path.name, 'sha256': sha(path.read_bytes()),
                'bytes': path.stat().st_size, 'members': len(archive.infolist()),
                'crc': 'PASS', 'manifests': manifests,
                'roots': sorted({n.split('/')[0] for n in archive.namelist()})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / '_inputs')
    parser.add_argument('--extract', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / '_workspace' / 'PREFLIGHT_INPUTS.json')
    args = parser.parse_args()
    results = [inspect_archive(args.source / name) for name in INPUTS]
    if args.extract:
        for result in results:
            for root in result['roots']:
                if (ROOT / root).exists():
                    raise FileExistsError(f'Refusing to overwrite {ROOT / root}')
        (ROOT / '_inputs').mkdir(exist_ok=True)
        for name in INPUTS:
            source = args.source / name
            destination = ROOT / '_inputs' / name
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            with zipfile.ZipFile(source) as archive:
                for info in archive.infolist():
                    dest = ROOT.joinpath(*PurePosixPath(info.filename).parts)
                    if info.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(info) as src, dest.open('xb') as out:
                            shutil.copyfileobj(src, out)
        for name, dest_name in LOOSE.items():
            source = args.source / name
            shutil.copy2(source, ROOT / '_inputs' / name)
            dest = ROOT / ('_workspace' if name == 'AGENTS.md' else '') / dest_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                raise FileExistsError(dest)
            shutil.copy2(source, dest)
    data = {'status': 'PASS', 'external_expected_hashes': 'NOT PROVIDED; observed digests are provenance, not independent authenticity proof',
            'archives': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
