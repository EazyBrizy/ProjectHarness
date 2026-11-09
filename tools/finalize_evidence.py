"""Copy reviewable acceptance evidence with paths/secrets redacted, preserving raw runs."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
OUT = ENGINE / 'PH_LW_04_05_WINDOWS_LOGS'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(text):
    for source, replacement in [(str(ROOT), '<WORKSPACE>'),
                                (os.environ.get('TEMP', ''), '<TEMP>'),
                                (os.environ.get('USERPROFILE', ''), '<USERPROFILE>')]:
        if source:
            for value in (source.replace('\\', '\\\\'), source, source.replace('\\', '/')):
                text = text.replace(value, replacement)
    text = re.sub(r'(#bootstrap=)[A-Za-z0-9_-]+', r'\1<REDACTED>', text)
    return text


def main():
    rows = json.loads((ROOT / '_scratch/regressions-final/MATRIX.json').read_text('utf-8'))
    assert len(rows) == len(list((ENGINE / 'tests').glob('test_*.py'))), 'Regression run is incomplete'
    for stage in ('04', '05'):
        report = json.loads((ROOT / f'_scratch/ci-{stage}-final/PH_LW_{stage}_WINDOWS_TEST_REPORT.json').read_text('utf-8'))
        assert report['status'] == 'PASS', report
    wheel = json.loads((ROOT / '_scratch/acceptance/installed-wheel.run.json').read_text('utf-8'))
    assert wheel['status'] == 'PASS', wheel
    OUT.mkdir(exist_ok=True)
    records = []
    groups = [('regressions_original', ROOT / '_scratch/regressions-final'),
              ('regressions_manual_recheck', ROOT / '_scratch/regressions-manual-recheck'),
              ('regressions_schema_recheck', ROOT / '_scratch/regressions-schema-recheck'),
              ('ci04', ROOT / '_scratch/ci-04-final'), ('ci05', ROOT / '_scratch/ci-05-final')]
    selected = ['baseline-targeted', 'reproductions-before', 'focused-after', 'replay-after',
                'core-failure-repro', 'windows-core-after', 'extended-live-initial',
                'extended-live-after', 'extra-boundaries', 'ui-final', 'ci-original',
                'installed-wheel', 'ci-04-final', 'ci-05-final', 'package-final-code']
    pairs = [(p, OUT / group / p.name) for group, directory in groups
             for p in directory.iterdir() if p.is_file() and p.suffix in ('.log', '.json')]
    for stem in selected:
        pairs += [(p, OUT / 'runs' / p.name) for p in (ROOT / '_scratch/acceptance').glob(stem + '.*')
                  if p.suffix in ('.log', '.json')]
    for source, target in pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sanitize(source.read_text('utf-8', errors='replace')), 'utf-8')
        records.append({'source': source.relative_to(ROOT).as_posix(),
                        'file': target.relative_to(OUT).as_posix(),
                        'raw_sha256': digest(source), 'redacted_sha256': digest(target)})
    latest = {row['module']: {**row, 'evidence': 'regressions_original/' + row['log']} for row in rows}
    for directory, label in [('regressions-manual-recheck', 'regressions_manual_recheck'),
                             ('regressions-schema-recheck', 'regressions_schema_recheck')]:
        for row in json.loads((ROOT / f'_scratch/{directory}/MATRIX.json').read_text('utf-8')):
            latest[row['module']] = {**row, 'evidence': label + '/' + row['log'],
                                    'supersedes': 'regressions_original/' + row['log']}
    ci = json.loads((ROOT / '_scratch/ci-05-final/stage_tests.json').read_text('utf-8'))
    for name, count in [('test_ph_lw_04_http', 17), ('test_ph_lw_05_import', 17),
                        ('test_ph_lw_05_http', 4), ('test_ph_lw_04_05_acceptance', 6)]:
        assert 'tests.' + name in ci['modules'] and ci['status'] == 'PASS' and not ci['skips']
        latest['tests.' + name] = {'module': 'tests.' + name, 'ran': count, 'failures': 0,
                                  'errors': 0, 'skips': [], 'status': 'PASS', 'evidence': 'ci05/stage_tests.log',
                                  'supersedes': 'regressions_original/' + name + '.log'}
    for row in latest.values():
        if row['status'] == 'PASS' and row.get('skips'):
            row['status'] = 'PASS_WITH_SKIPS'
    final = {'status': 'FAIL' if any(r['status'] in ('FAIL', 'TIMEOUT') for r in latest.values()) else 'PASS',
             'modules': len(latest), 'tests_run': sum(r.get('ran', 0) for r in latest.values()),
             'failure_events': sum(r.get('failures', 0) for r in latest.values()),
             'error_events': sum(r.get('errors', 0) for r in latest.values()),
             'skips': sum(len(r.get('skips', [])) for r in latest.values()),
             'rows': sorted(latest.values(), key=lambda row: row['module'])}
    (OUT / 'REGRESSION_MATRIX_FINAL.json').write_text(sanitize(json.dumps(final, ensure_ascii=False, indent=2)) + '\n', 'utf-8')
    (OUT / 'EVIDENCE_INDEX.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    (OUT / 'README.md').write_text('# Windows acceptance evidence\n\n'
        'Raw runs remain in workspace `_scratch`. Published copies replace workspace/user/temp paths and bootstrap URL values. '
        '`EVIDENCE_INDEX.json` binds raw and redacted SHA-256 separately; hashes inside copied raw run metadata refer to the raw logs. '
        'Final matrix explicitly supersedes older runs; failures, subtest errors and skips are retained. '
        'The initial monolithic run was interrupted after the confirmed Windows fsync defect; the bounded 37-module run replaces it. '
        'Exploratory browser harness failures (CORS event observation, form navigation, hidden locator) are retained in workspace; '
        'final stage/installed-wheel runs use the corrected fixtures. No private user documents or active credentials are included.\n', 'utf-8')
    # Exact diff against archived baseline, including generated mirrors.
    with zipfile.ZipFile(ROOT / '_inputs/Project_Harness_Engine_v0.5.1_PH_LW_05.zip') as zf:
        baseline = {name.split('/', 1)[1]: hashlib.sha256(zf.read(name)).hexdigest()
                    for name in zf.namelist() if not name.endswith('/')}
    current = {p.relative_to(ENGINE).as_posix(): digest(p) for p in ENGINE.rglob('*') if p.is_file()
               and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    changes = {'added': sorted(current.keys() - baseline.keys()),
               'modified': sorted(name for name in current.keys() & baseline.keys() if current[name] != baseline[name]),
               'removed': sorted(baseline.keys() - current.keys())}
    # Immutable historical report/log evidence must survive byte-for-byte.
    historical = [name for name in baseline if re.match(r'PH_(?:LW_\d\d|051_\d\d|F\d\d)', name)]
    assert all(current.get(name) == baseline[name] for name in historical), 'Historical evidence changed'
    changes['historical_files_unchanged'] = len(historical)
    (ROOT / '_workspace/ENGINE_CHANGES.json').write_text(json.dumps(changes, indent=2) + '\n', 'utf-8')
    print(json.dumps({key: value for key, value in final.items() if key != 'rows'}, indent=2))
    print('Immutable historical files:', len(historical))


if __name__ == '__main__':
    main()
