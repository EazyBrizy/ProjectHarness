"""Publish PH-LW-06 logs only after all frozen-code acceptance runs finish."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from finalize_evidence import sanitize

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
SCRATCH = ROOT / '_scratch/ph_lw_06'
OUT = ENGINE / 'PH_LW_06_LOGS'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8'))


def save(path, value):
    path.write_text(sanitize(json.dumps(value, ensure_ascii=False, indent=2)) + '\n', 'utf-8')


def summary(rows):
    return {'modules': len(rows), 'test_methods': sum(r['ran'] for r in rows),
            'module_statuses': dict(Counter(r['status'] for r in rows)),
            'failure_events': sum(r.get('failures', 0) for r in rows),
            'error_events': sum(r.get('errors', 0) for r in rows),
            'skips': sum(len(r.get('skips', [])) for r in rows)}


def main():
    rows = read(SCRATCH / 'regressions-final/MATRIX.json')
    assert len(rows) == len(list((ENGINE / 'tests').glob('test_*.py'))) == 40
    assert len({r['module'] for r in rows}) == len(rows)
    native = read(SCRATCH / 'native-final/PH_LW_06_WINDOWS_TEST_REPORT.json')
    installed = read(SCRATCH / 'runs/installed-wheel-final.run.json')
    assert installed['status'] == 'PASS'
    assert all(c['status'] == 'PASS' for c in native['checks'] if c.get('name') != 'documentation')
    assert read(SCRATCH / 'docs-corrected/DOC_VALIDATION.json')['status'] == 'PASS'
    assert 'Ran 62 tests' in (SCRATCH / 'runs/installed-wheel-final.log').read_text('utf-8')
    previous = read(ENGINE / 'PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/REGRESSION_MATRIX_COMBINED.json')
    previous_rows = {r['module']: r for r in previous['rows']}
    expected_failures = {r['module'] for r in previous['rows'] if r['status'] == 'FAIL'}
    assert {r['module'] for r in rows if r['status'] == 'FAIL'} == expected_failures
    assert not any(r['status'] not in {'PASS', 'PASS_WITH_SKIPS', 'FAIL'} for r in rows)
    comparison = []
    for row in rows:
        if row['module'] not in previous_rows:
            continue
        old = previous_rows[row['module']]
        fields = ('status', 'ran', 'failures', 'errors')
        delta = {k: {'previous': old.get(k), 'current': row.get(k)} for k in fields if old.get(k) != row.get(k)}
        if len(old['skips']) != len(row['skips']):
            delta['skip_count'] = {'previous': len(old['skips']), 'current': len(row['skips'])}
        comparison.append({'module': row['module'], 'differences': delta})
    assert not any(row['differences'] for row in comparison), comparison
    OUT.mkdir(exist_ok=True)
    groups = ('baseline', 'target-initial', 'target-second', 'target-third', 'target-fourth',
              'target-fifth', 'target-sixth', 'regressions-final', 'native-final', 'docs-corrected', 'runs')
    pairs = [(p, OUT / group / p.name) for group in groups for p in sorted((SCRATCH / group).iterdir())
             if p.is_file() and p.suffix in {'.json', '.log'}]
    pairs += [(SCRATCH / name, OUT / name) for name in ('INPUT_BASELINE.json', 'WHEEL_ENVIRONMENT.json')]
    pairs += [(p, OUT / 'browser-visual' / p.name) for p in sorted((SCRATCH / 'browser').glob('*.png'))]
    index = []
    for source, target in pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.png':
            target.write_bytes(source.read_bytes())
        else:
            target.write_text(sanitize(source.read_text('utf-8', errors='replace')), 'utf-8')
        index.append({'raw_source': source.relative_to(ROOT).as_posix(),
                      'file': target.relative_to(OUT).as_posix(),
                      'raw_sha256': digest(source), 'published_sha256': digest(target)})
    save(OUT / 'EVIDENCE_INDEX.json', index)
    save(OUT / 'RUN_ENVIRONMENTS.json', {
        'source_groups': list(groups), 'source_environment': 'INPUT_BASELINE.json',
        'source_python': str(ROOT / '.venv/Scripts/python.exe'),
        'source_pythonpath': [str(ENGINE / 'src'), str(ENGINE)],
        'browser_channel': 'msedge', 'native_platform_check': 'native-final/PH_LW_06_WINDOWS_TEST_REPORT.json',
        'wheel_runs': ['runs/installed-wheel-final.run.json'], 'wheel_environment': 'WHEEL_ENVIRONMENT.json',
        'wheel_pythonpath': '', 'note': 'Per-run command/interpreter paths are retained in MATRIX/run.json; dependency pins are common to these runs.'})
    save(OUT / 'NATIVE_SCOPE_VERDICT.json', {'status': 'PASS',
        'runtime': 'native-final/PH_LW_06_WINDOWS_TEST_REPORT.json',
        'runtime_result': '64 PASS / 0 SKIP; doctor PASS',
        'original_wrapper_status': native['status'],
        'original_docs': 'FAIL: new document metadata date and README NO-GO parsed as ID',
        'docs_retest': 'docs-corrected/DOC_VALIDATION.json',
        'docs_retest_status': 'PASS',
        'note': 'Separate docs-only retest; 64 runtime methods were not rerun for formatting fixes.'})
    save(OUT / 'REGRESSION_MATRIX_CURRENT.json', {
        'status': 'FAIL', 'provenance': 'ALL_MODULES_RERUN_THIS_TASK_ON_FINAL_CODE',
        **summary(rows), 'rows': rows})
    save(OUT / 'PREVIOUS_BASELINE_COMPARISON.json', {
        'status': 'UNCHANGED_RESULTS_FOR_ALL_38_PREVIOUS_MODULES',
        'reference': '../PH_LW_05_WINDOWS_MANUAL_REMEDIATION_LOGS/REGRESSION_MATRIX_COMBINED.json',
        'rows': comparison})
    meta = read(ENGINE / 'src/project_harness/resources/local_web/metadata_v1.json')
    save(OUT / 'BUILD_PROVENANCE.json', {
        'input': read(SCRATCH / 'INPUT_BASELINE.json'),
        'build_id': meta['local_web_build_id'], 'engine_build_digest': meta['engine_build_digest'],
        'wheel_sha256': digest(ENGINE / 'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
        'native_final': 'NATIVE_SCOPE_VERDICT.json',
        'installed_final': 'runs/installed-wheel-final.run.json',
        'final_tree_attestation': '../../_workspace/PH_LW_06/FINAL_WORKING_TREE_VERIFICATION.json',
        'zip_created': False})
    (OUT / 'README.md').write_text('''# PH-LW-06: фактические доказательства

`regressions-final` — все 40 модулей заново на финальном коде; прежние результаты не подставлены.
`native-final` — Windows/NTFS/non-admin/CPython 3.14, pinned Flask/Waitress, реальный TCP и Edge.
64 runtime tests и doctor PASS; общий wrapper FAIL из-за двух ошибок оформления docs.
`docs-corrected` — отдельный успешный retest после исправления docs; `NATIVE_SCOPE_VERDICT`
связывает эти два прогона, не переписывая исходный FAIL и не объявляя повтор 64 методов.
`runs/installed-wheel-final` — отдельная venv и Unicode CWD; импорт только из установленного wheel.
`target-sixth` — последний предварительный run (15 exchange + 4 HTTP methods); финальные native,
regression и installed-wheel runs включают дополнительный шестнадцатый exchange test.
Ранние FAIL, промежуточные wheel builds и диагностические browser runs сохранены, а не объявлены PASS.
`browser-visual` — проверенные снимки UI из предварительного успешного run, данные полностью синтетические.

Raw evidence остаётся в `_scratch/ph_lw_06`. В опубликованных текстах заменены пользовательские
пути/bootstrap values существующим sanitizer. EVIDENCE_INDEX различает raw и published SHA-256;
вложенные log hashes в скопированных run.json относятся к raw bytes. Ни uploads/auth,
ни временные projects, ни venv/wheelhouse в evidence не включены.

SKIP не является PASS; failure/error events включают subtests и не дают число успешных methods
простым вычитанием. Seven mixed Linux/automatic module FAIL сохранены в общей матрице.
Source tests, installed wheel и финальная проверка рабочих файлов — разные evidence runs.
ZIP-пара не создавалась по новому правилу пользователя; финальные hashes рабочих деревьев
находятся отдельно в `_workspace/PH_LW_06`, вне самих хешируемых деревьев.
''', 'utf-8')
    print(json.dumps({'status': 'PUBLISHED', 'files': len(index), **summary(rows)}, indent=2))


if __name__ == '__main__':
    main()
