"""Read-only linkage, immutable inputs, docs/resource mirror checks."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
DOCS = ROOT / 'Project_Harness_Documentation_v0.5.1'


def files(path):
    return {p.relative_to(path).as_posix(): p for p in path.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    errors = []
    checks = {}
    for label, left, right in [('documentation_mirror', DOCS, ENGINE / 'docs' / DOCS.name),
                             *[(f'{name}_mirror', ENGINE / name, ENGINE / 'src/project_harness/resources' / name)
                               for name in ('schemas', 'registries', 'templates', 'skills')]]:
        a, b = files(left), files(right)
        bad = sorted(set(a) ^ set(b)) + [name for name in sorted(set(a) & set(b))
                                       if a[name].read_bytes() != b[name].read_bytes()]
        checks[label] = {'files': len(a), 'mismatches': bad}
        errors.extend(f'{label}: {name}' for name in bad)
    link_count = 0
    for path in [ROOT / 'AGENTS.md', ROOT / 'README.md', *sorted((ROOT / '_workspace').glob('*.md')),
                 *sorted(ENGINE.glob('PH_LW_04_05_WINDOWS_ACCEPTANCE*.md')),
                 *sorted(ENGINE.glob('PH_LW_06*.md')),
                 *sorted(ENGINE.glob('PH_LW_07*.md')),
                 *sorted(ENGINE.glob('PH_LW_08*.md')),
                 *sorted(ENGINE.glob('PH_LW_09*.md')),
                 *sorted(ENGINE.glob('PH_LW_10*.md')),
                 *sorted(ENGINE.glob('PH_LW_11*.md')),
                 *sorted(ENGINE.glob('PH_LW_05_WINDOWS_MANUAL_REMEDIATION*.md'))]:
        if path.name == 'AGENTS.original.md':
            continue
        markdown = re.sub(r'(?ms)^```[^\n]*\n.*?^```[^\n]*$', '', path.read_text('utf-8-sig'))
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', markdown):
            if re.match(r'^[a-zA-Z]+://', link) or link.startswith('#'):
                continue
            target = (path.parent / link.split('#', 1)[0]).resolve()
            link_count += 1
            if not target.exists():
                errors.append(f'Broken link: {path.relative_to(ROOT)} -> {link}')
    checks['workspace_links'] = link_count
    source = files(ENGINE / 'src/project_harness')
    built = files(ENGINE / 'build/lib/project_harness')
    bad = sorted(set(source) ^ set(built)) + [name for name in source.keys() & built.keys()
                                            if source[name].read_bytes() != built[name].read_bytes()]
    errors.extend('Build mirror: ' + name for name in bad)
    checks['build_mirror'] = {'files': len(source), 'mismatches': bad}
    wheel = ENGINE / 'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as zf:
        packaged = {name.removeprefix('project_harness/'): name for name in zf.namelist()
                    if name.startswith('project_harness/') and not name.endswith('/')}
        bad = sorted(set(source) ^ set(packaged)) + [name for name in source.keys() & packaged.keys()
                                                   if source[name].read_bytes() != zf.read(packaged[name])]
    checks['wheel_source_mirror'] = {'files': len(packaged), 'mismatches': bad}
    errors.extend('Wheel source mirror: ' + name for name in bad)
    original = json.loads((ROOT / '_workspace/PREFLIGHT_INPUTS.json').read_text('utf-8'))
    for row in original['archives']:
        archive = ROOT / '_inputs' / row['file']
        if hashlib.sha256(archive.read_bytes()).hexdigest() != row['sha256']:
            errors.append(f'Original ZIP changed: {archive.name}')
        if 'Specifications' in archive.name or 'Prompts' in archive.name:
            with zipfile.ZipFile(archive) as zf:
                for member in zf.infolist():
                    if not member.is_dir() and (ROOT / member.filename).read_bytes() != zf.read(member):
                        errors.append(f'Immutable source changed: {member.filename}')
    for name in ('Project_Harness_v0.5.0_Remediation_Plan_RU', 'Project_Harness_v0.5.1_Implementation_Plan_RU'):
        if (ROOT / f'{name}.md').read_bytes() != (ROOT / '_inputs' / f'{name} (1).md').read_bytes():
            errors.append(f'Historical plan changed: {name}')
    loose = json.loads((ROOT / '_workspace/PREFLIGHT_LOOSE_INPUTS.json').read_text('utf-8'))
    for row in loose:
        if hashlib.sha256((ROOT / '_inputs' / row['file']).read_bytes()).hexdigest() != row['sha256']:
            errors.append('Original loose input changed: ' + row['file'])
    if (ROOT / '_inputs/AGENTS.md').read_bytes() != (ROOT / '_workspace/AGENTS.original.md').read_bytes():
        errors.append('Original AGENTS backup changed')
    result = {'status': 'FAIL' if errors else 'PASS', 'checks': checks, 'errors': errors}
    (ROOT / '_workspace/WORKSPACE_VALIDATION.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
