"""Read-only verification of the documentation-only archive-policy change."""
import argparse
import hashlib
import json
from pathlib import Path
import re

EVIDENCE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--output', default='changes.json')
args = parser.parse_args()
ROOT = EVIDENCE.parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
DOCS = ROOT / 'Project_Harness_Documentation_v0.5.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


before = json.loads((EVIDENCE / 'before_hashes.json').read_text('utf-8'))
roots = [ENGINE.name, DOCS.name, '_inputs', '_deliverables',
         'Harness_Local_Web_Prompts_RU_r2',
         'Project_Harness_Implementation_Specifications_v0.4.1_to_v1.0']
tracked = [p for name in roots for p in files(ROOT / name).values()]
tracked += list(ROOT.glob('*.md')) + [p for p in (ROOT / '_workspace').iterdir() if p.is_file()]
after = {p.relative_to(ROOT).as_posix(): sha(p) for p in tracked}
doc_names = {'README.md', 'Project_Harness_Architecture_v0.5.0_FULL.md',
             'FILE_INDEX.md', 'MANIFEST.sha256'}
allowed = {'AGENTS.md', 'README.md', '_workspace/CURRENT_TASK.md', '_workspace/RUNBOOK.md',
           f'{ENGINE.name}/MANIFEST.sha256'}
allowed |= {f'{DOCS.name}/{name}' for name in doc_names}
allowed |= {f'{ENGINE.name}/docs/{DOCS.name}/{name}' for name in doc_names}
changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
errors = [f'Outside allowed file changes: {name}' for name in changed if name not in allowed]
counts = {}
for base in (DOCS, ENGINE):
    inventory = files(base)
    manifest = dict(row.split('  ', 1)[::-1] for row in (base / 'MANIFEST.sha256').read_text('utf-8').splitlines())
    if set(manifest) != set(inventory) - {'MANIFEST.sha256'}:
        errors.append(f'Manifest inventory mismatch: {base.name}')
    for rel, digest in manifest.items():
        if rel not in inventory or sha(inventory[rel]) != digest:
            errors.append(f'Manifest hash mismatch: {base.name}/{rel}')
    counts[base.name] = len(manifest)
a, b = files(DOCS), files(ENGINE / 'docs' / DOCS.name)
if set(a) != set(b) or any(a[name].read_bytes() != b[name].read_bytes() for name in a.keys() & b.keys()):
    errors.append('Documentation mirror mismatch')
link_count = 0
for path in [ROOT / 'AGENTS.md', ROOT / 'README.md', EVIDENCE / 'REPORT.md',
             *sorted((ROOT / '_workspace').glob('*.md'))]:
    if path.name == 'AGENTS.original.md':
        continue
    prose = re.sub(r'```.*?```', '', path.read_text('utf-8-sig'), flags=re.S)
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', prose):
        if re.match(r'^[a-zA-Z]+://', link) or link.startswith('#'):
            continue
        # run_logged writes these two files immediately after this child finishes.
        if path == EVIDENCE / 'REPORT.md' and link in {'verify_final.run.json', args.output}:
            continue
        link_count += 1
        if not (path.parent / link.split('#', 1)[0]).resolve().exists():
            errors.append(f'Broken link: {path.relative_to(ROOT)} -> {link}')
result = {'status': 'FAIL' if errors else 'PASS', 'manifest_entries': counts,
          'documentation_mirror_files': len(a), 'local_links': link_count,
          'tracked_files': len(after),
          'new_archives': sorted(name for name in after.keys() - before.keys() if name.endswith(('.zip', '.whl'))),
          'changed_files': [{'file': name, 'before_sha256': before.get(name), 'after_sha256': after.get(name)}
                            for name in changed], 'errors': errors}
(EVIDENCE / args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
