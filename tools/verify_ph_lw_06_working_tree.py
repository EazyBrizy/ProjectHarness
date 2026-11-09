"""Attest the exact unpacked PH-LW-06 pair, preserving archive/history provenance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from package_acceptance import ROOT, ENGINE, DOCS, files

OUT = ROOT / '_workspace/PH_LW_06'
BASE = ROOT / '_deliverables/PH_LW_05_WINDOWS_MANUAL_REMEDIATION_2026-11-07'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8'))


def verify_manifest(root):
    path = root / 'MANIFEST.sha256'
    rows = {}
    for line in path.read_text('utf-8').splitlines():
        digest, name = line.split('  ', 1)
        assert name not in rows and sha(root / name) == digest, name
        rows[name] = digest
    actual = {p.relative_to(root).as_posix() for p in files(root) if p != path}
    assert actual == set(rows), {'extra': sorted(actual-set(rows)), 'missing': sorted(set(rows)-actual)}
    return {'status': 'PASS', 'files': len(rows), 'manifest_sha256': sha(path)}


def run(name, command, cwd):
    log = OUT / (name + '.log')
    started = datetime.now(timezone.utc).isoformat()
    with log.open('wb') as stream:
        result = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=180,
            env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    info = {'command': command, 'cwd': str(cwd), 'started_utc': started,
            'exit': result.returncode, 'status': 'PASS' if result.returncode == 0 else 'FAIL',
            'log': log.name, 'log_sha256': sha(log)}
    assert result.returncode == 0, info
    return info


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    report = (ENGINE / 'PH_LW_06_TEST_REPORT.md').read_text('utf-8')
    assert 'IN PROGRESS' not in report and 'PENDING' not in report and 'RUNNING' not in report
    assert '**COMPLETE' in (ROOT / '_workspace/CURRENT_TASK.md').read_text('utf-8')
    baseline = read(ENGINE / 'PH_LW_06_LOGS/INPUT_BASELINE.json')
    evidence = read(ENGINE / 'PH_LW_06_LOGS/EVIDENCE_INDEX.json')
    for item in evidence:
        assert sha(ENGINE / 'PH_LW_06_LOGS' / item['file']) == item['published_sha256'], item['file']
        assert sha(ROOT / item['raw_source']) == item['raw_sha256'], item['raw_source']
    changes = []
    historical = []
    archives = []
    for row, root in zip(baseline['archives'], (ENGINE, DOCS), strict=True):
        archive = BASE / row['file']
        assert sha(archive) == row['sha256']
        with zipfile.ZipFile(archive) as zf:
            assert zf.testzip() is None
            before = {n.removeprefix(root.name + '/'): hashlib.sha256(zf.read(n)).hexdigest()
                      for n in zf.namelist() if not n.endswith('/')}
        after = {p.relative_to(root).as_posix(): sha(p) for p in files(root)}
        for name in sorted(set(before) | set(after)):
            if before.get(name) != after.get(name):
                changes.append({'tree': root.name, 'file': name, 'before_sha256': before.get(name),
                                'after_sha256': after.get(name)})
            if root == ENGINE and name in before and name.startswith('PH_'):
                assert before[name] == after.get(name), 'Historical evidence changed: ' + name
                historical.append(name)
        archives.append({'file': row['file'], 'sha256': sha(archive), 'crc': 'PASS'})
    commands = [run('workspace-check', [sys.executable, str(ROOT / 'tools/check_workspace.py')], ROOT),
        run('doctor', [sys.executable, str(ENGINE / 'project-harness.py'), 'doctor'], ENGINE),
        run('documentation', [sys.executable, str(DOCS / 'tools/validate_documentation.py'), str(DOCS),
            '--json', str(OUT / 'DOC_VALIDATION.json')], ROOT)]
    trees = {root.relative_to(ROOT).as_posix(): verify_manifest(root)
             for root in (ENGINE, DOCS, ENGINE / 'docs' / DOCS.name)}
    changes_path = OUT / 'CHANGED_FILE_HASHES.json'
    changes_path.write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    native = read(ENGINE / 'PH_LW_06_LOGS/NATIVE_SCOPE_VERDICT.json')
    installed = read(ENGINE / 'PH_LW_06_LOGS/runs/installed-wheel-final.run.json')
    assert native['status'] == installed['status'] == 'PASS'
    provenance = read(ENGINE / 'PH_LW_06_LOGS/BUILD_PROVENANCE.json')
    wheel = ENGINE / 'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    assert provenance['wheel_sha256'] == sha(wheel)
    meta = read(ENGINE / 'src/project_harness/resources/local_web/metadata_v1.json')
    assert provenance['engine_build_digest'] == meta['engine_build_digest']
    source = ENGINE / 'src/project_harness'
    entries = [f'{sha(p)}  {p.relative_to(source).as_posix()}' for p in files(source)
               if p != source / 'resources/local_web/metadata_v1.json']
    assert 'sha256:' + hashlib.sha256(('\n'.join(entries)+'\n').encode()).hexdigest() == meta['engine_build_digest']
    workspace_paths = ['AGENTS.md', 'README.md', '_workspace/CURRENT_TASK.md', '_workspace/PROJECT_MAP.md',
        '_workspace/RUNBOOK.md', '_workspace/ARCHIVE_POLICY_TASK_COMPLETED.md',
        '_workspace/ARCHIVE_POLICY_2026-11-07/REPORT.md', 'tools/sync_working_tree.py',
        'tools/check_workspace.py', 'tools/verify_installed.py',
        'tools/finalize_ph_lw_06_evidence.py', 'tools/verify_ph_lw_06_working_tree.py']
    result = {'status': 'PASS', 'verified_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Exact unpacked working pair; not a full v0.5.1 release verdict',
        'input_archives': archives, 'historical_engine_evidence_preserved': len(historical),
        'evidence_files_verified_against_raw_and_published_hashes': len(evidence),
        'trees': trees, 'wheel_sha256': sha(wheel), 'engine_build_digest': meta['engine_build_digest'],
        'changed_file_hashes_sha256': sha(changes_path), 'commands': commands,
        'native_acceptance': native['status'], 'installed_wheel_acceptance': installed['status'],
        'workspace_files': {p: sha(ROOT / p) for p in workspace_paths},
        'zip_created': False, 'zip_reason': 'Explicit user archive-policy override dated 2026-11-07',
        'verdicts': {'PH-LW-04': 'PASS', 'PH-LW-05': 'PASS', 'PH-LW-06': 'PASS',
            'LOCAL_WEB_MANUAL': 'NO-GO', 'AUTOMATIC_EXECUTOR': 'NO-GO', 'v0.5.1': 'NO-GO / NOT RELEASED'}}
    (OUT / 'FINAL_WORKING_TREE_VERIFICATION.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    lines = [f'{sha(ENGINE / "MANIFEST.sha256")}  {ENGINE.name}/MANIFEST.sha256',
             f'{sha(DOCS / "MANIFEST.sha256")}  {DOCS.name}/MANIFEST.sha256',
             f'{sha(wheel)}  {ENGINE.name}/dist/{wheel.name}',
             f'{sha(OUT / "FINAL_WORKING_TREE_VERIFICATION.json")}  _workspace/PH_LW_06/FINAL_WORKING_TREE_VERIFICATION.json']
    (OUT / 'SHA256.txt').write_text('\n'.join(lines)+'\n', 'utf-8')
    print(json.dumps({'status': 'PASS', 'trees': trees, 'history_preserved': len(historical),
                      'changes': len(changes), 'wheel_sha256': sha(wheel)}, indent=2))


if __name__ == '__main__':
    main()
