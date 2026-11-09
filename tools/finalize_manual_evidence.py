"""Publish this task's evidence without altering prior acceptance reports/runs."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

from finalize_evidence import sanitize

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
SCRATCH = ROOT / '_scratch/manual-remediation'
PREFIX = 'PH_LW_05_WINDOWS_MANUAL_REMEDIATION'
OUT = ENGINE / (PREFIX + '_LOGS')
BASE = ROOT / '_deliverables/PH_LW_04_05_WINDOWS_RETEST_2026-11-07'
INPUTS = {
    'Project_Harness_Engine_v0.5.1_PH_LW_05.zip': 'd48a47b43957df5fd3e4e57db98f0b4e2e73c668893489a528e9c739200cb6ef',
    'Project_Harness_Documentation_v0.5.1_PH_LW_05.zip': '5d610858306dc91e1b125711e30dc84e7f4aed046d4d72c20f0ff401f05f9b8b',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8'))


def save(path, value):
    path.write_text(sanitize(json.dumps(value, ensure_ascii=False, indent=2)) + '\n', 'utf-8')


def summary(rows):
    return {'modules': len(rows), 'tests_run': sum(r['ran'] for r in rows),
            'failure_events': sum(r.get('failures', 0) for r in rows),
            'error_events': sum(r.get('errors', 0) for r in rows),
            'skips': sum(len(r.get('skips', [])) for r in rows),
            'module_statuses': dict(Counter(r['status'] for r in rows))}


def main():
    for name, expected in INPUTS.items():
        assert digest(BASE / name) == expected, 'Prior ZIP changed: ' + name
    rows = read(SCRATCH / 'regressions-final/MATRIX.json')
    assert len(rows) == 18 and sum(r['ran'] for r in rows) == 294
    installed = read(SCRATCH / 'installed-wheel-final.run.json')
    assert installed['status'] == 'PASS'
    assert read(SCRATCH / 'docs-validation.json')['status'] == 'PASS'
    installed_text = (SCRATCH / 'installed-wheel-final.log').read_text('utf-8')
    assert 'Ran 42 tests' in installed_text and '"skips": 0' in installed_text
    OUT.mkdir(exist_ok=True)
    records = []
    pairs = []
    for group in ('regressions-final', 'native-extra-initial', 'migration-final'):
        pairs.extend((p, OUT / group / p.name) for p in (SCRATCH / group).iterdir()
                     if p.is_file() and p.suffix in {'.json', '.log'})
    stems = ('migration-before', 'migration-after-fsync', 'partial-copy-before',
             'capability-check', 'installed-wheel', 'installed-wheel-final', 'build', 'build-final')
    for stem in stems:
        pairs.extend((p, OUT / 'runs' / p.name) for p in SCRATCH.glob(stem + '.*')
                     if p.suffix in {'.json', '.log'})
    pairs.append((SCRATCH / 'docs-validation.json', OUT / 'docs-validation.json'))
    for source, target in pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sanitize(source.read_text('utf-8', errors='replace')), 'utf-8')
        records.append({'source': source.relative_to(ROOT).as_posix(),
                        'file': target.relative_to(OUT).as_posix(),
                        'raw_sha256': digest(source), 'published_sha256': digest(target)})
    old = read(ENGINE / 'PH_LW_04_05_WINDOWS_LOGS/REGRESSION_MATRIX_FINAL.json')
    latest = {r['module']: {**r, 'provenance': 'CARRIED_FORWARD_NOT_RERUN_THIS_TASK',
              'evidence': '../PH_LW_04_05_WINDOWS_LOGS/' + r['evidence']} for r in old['rows']}
    fresh = [{**r, 'provenance': 'RERUN_THIS_TASK', 'evidence': 'regressions-final/' + r['log']} for r in rows]
    for row in fresh:
        latest[row['module']] = row
    merged = sorted(latest.values(), key=lambda r: r['module'])
    assert len(merged) == 38 and sum(r['ran'] for r in merged) == 436
    save(OUT / 'REGRESSION_MATRIX_CURRENT.json', {'status': 'FAIL', **summary(fresh), 'rows': fresh})
    save(OUT / 'REGRESSION_MATRIX_COMBINED.json', {
        'status': 'FAIL', 'note': '18 modules rerun; 20 unchanged modules carry prior evidence, NOT a fresh 38-module run.',
        **summary(merged), 'rows': merged})
    save(OUT / 'EVIDENCE_INDEX.json', records)
    save(OUT / 'BUILD_PROVENANCE.json', {
        'input_archives': INPUTS, 'wheel_sha256': digest(ENGINE / 'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
        'source_sha256': digest(ENGINE / 'src/project_harness/migration.py'),
        'installed_final_run': 'runs/installed-wheel-final.run.json',
        'earlier_installed_run': 'runs/installed-wheel.run.json (41 tests, earlier candidate wheel; superseded)',
        'final_zip_attestation': 'External FINAL_VERIFICATION/FINAL_ARCHIVE_VERIFICATION.json binds final ZIP hashes; no self-hash cycle.'})
    (OUT / 'README.md').write_text(
        '# Windows manual remediation evidence\n\n'
        'Исходные runs сохранены в workspace `_scratch/manual-remediation`. Здесь заменены пути пользователя, '
        'workspace/temp и bootstrap values; EVIDENCE_INDEX хранит raw/published hashes отдельно. '
        'Хеши внутри скопированных run.json относятся к исходным raw logs.\n\n'
        'REGRESSION_MATRIX_CURRENT — свежие 18 модулей; COMBINED — 38 модулей с явной provenance: '
        '20 прежних результатов не прогонялись заново. Failure/error events могут быть subtests, '
        'поэтому их сумма не равна числу отдельных test methods. SKIP не считается PASS. '
        'Ранние воспроизведения дефектов и промежуточные builds сохранены; final installed-wheel run заменяет candidate run. '
        'Полная финальная пара проверяется отдельно после упаковки, attestations лежат рядом с ZIP.\n', 'utf-8')

    triage = [
        ('test_contract_hardening', 'Fixture prerequisite', 'Единственный прежний ERROR — WinError 1314 при создании file symlink. Helper пропускает только этот фактический OS отказ; остальные 30 cases проходят. Symlink rejection этим run не доказан.'),
        ('test_ph_051_02_executor_protocol', 'Fixture prerequisite', 'WinError 1314 отделён в самостоятельный symlink case. Malformed, missing и oversized result cases выполняются; теперь 25 tests. Продуктовые ожидания не ослаблены.'),
        ('test_ph_051_03_rootless_podman', 'Linux/Podman path + fixture', 'os.geteuid/getegid отсутствуют, symlink fixture требует привилегии; Windows refusal/validation срабатывает раньше Linux output-limit/doctor ожиданий. Реальный rootless Podman не проверен.'),
        ('test_ph_051_04_disposable_roots', 'Linux automatic implementation', 'safety.safe_disposable_baseline_revision открывает directory fd; Windows даёт PermissionError. Также недоступны Unix/symlink fixtures. Этот disposable root не используется manual handoff.'),
        ('test_ph_051_05_codex_adapter', 'Смешанный, manual subset PASS', 'Отдельный hardlink test теперь выполняется и PASS; file symlink SKIP. Остались os.geteuid mock и 3 PreparedJit directory-fd errors. Manual mode cannot activate и проверки exact profiles проходят.'),
        ('test_ph_051_06_result_channel', 'Linux private automatic output', 'Exact /output channel требует UID/mode/dir_fd; ошибки os.geteuid и disposable baseline. Manual Agent Result проходит другой public complete путь; его проверяет новый end-to-end migration case.'),
        ('test_ph_051_08_atomic_apply', 'Linux automatic product apply', '31 subtest error на подготовке disposable baseline с POSIX directory fd. Даже manual-optout cases этого модуля сначала готовят automatic candidate. Это не доказательство поломки manual complete.'),
        ('test_ph_051_09_automatic_runtime', 'Windows refusal vs Linux expectations', 'Native Windows возвращает BLOCKED/SANDBOX_UNAVAILABLE до fake automatic pipeline. Не добавлялись mock bypass или host fallback; новый native test подтверждает отсутствие Popen и любых изменений project bytes.'),
        ('test_ph_051_10_migration_recovery', 'Исправленный manual + Linux recovery', 'Все 5 V051MigrationTests PASS. Оставшиеся 4 failures/7 errors: automatic Windows guard, os.geteuid, недоступный conditional-import mock target finalize_execution_root и symlink privilege; mixed module остаётся FAIL.'),
    ]
    by_name = {r['module'].removeprefix('tests.'): r for r in fresh}
    table = '\n'.join(f'| [{name}]({PREFIX}_LOGS/regressions-final/{name}.log) | {by_name[name]["status"]}; {by_name[name]["ran"]}/{by_name[name]["failures"]}/{by_name[name]["errors"]}/{len(by_name[name]["skips"])} | {kind}. {reason} |'
                      for name, kind, reason in triage)
    wheel_hash = digest(ENGINE / 'dist/project_harness_engine-0.5.1-py3-none-any.whl')
    report = f'''# Windows manual remediation: фактический отчёт

Дата: 2026-11-07. Build `PH-LW-05-WINDOWS-MANUAL-REMEDIATION-20261107`, v0.5.1-WIP / NOT RELEASED.

Исправлена применимая Windows-миграция v0.5.0→v0.5.1 и два дефекта очистки staging. Проверены все 9 прежних FAIL-модулей: 2 стали PASS_WITH_SKIPS, 7 остаются FAIL в Linux/automatic частях. Manual migration subset проходит полностью. Automatic executor не включался; PH-LW-06 не выполнялся.

## База и область изменения

Входные Engine/Documentation ZIP: `d48a47b43957df5fd3e4e57db98f0b4e2e73c668893489a528e9c739200cb6ef` / `5d610858306dc91e1b125711e30dc84e7f4aed046d4d72c20f0ff401f05f9b8b`. Это предыдущая проверенная поставка, не исходный архив из browser chat. Preflight hashes/mirrors/doctor PASS; прежние архивы, normative specs, планы и исторические reports/logs сохранены побайтово.

Разрешённая область: `migration.py`, доказанные manual regressions, platform test fixtures, документация, evidence и производные build/wheel/manifests. Из production Python изменён только migration module; metadata обновлена для traceability. [Список изменений]({PREFIX}_CHANGED_FILES.md), [инварианты]({PREFIX}_PRESERVED_INVARIANTS.md).

## Дефекты и исправления

1. **Windows staged fsync:** 4 из 5 исходных migration cases падали с `OSError: [Errno 9] Bad file descriptor`. Windows `_commit` требует write-capable file descriptor. Staged files открываются с `O_RDWR` только на Windows; POSIX остаётся `O_RDONLY`. Flush выполняется до journal/первого canonical rename, ошибка не подавляется. [До]({PREFIX}_LOGS/runs/migration-before.log), [после]({PREFIX}_LOGS/runs/migration-after-fsync.log).
2. **Частичный copy:** copytree раньше стоял вне cleanup try; PermissionError оставлял staging. Copy включён в тот же блок восстановления, исходный проект остаётся неизменным. [Воспроизведение]({PREFIX}_LOGS/runs/partial-copy-before.log).
3. **Read-only cleanup:** copied NTFS read-only файлы мешали удалить private staging после отказа миграции. Cleanup проверяет native path, parent и точное UUID-имя migration sibling; read-only снимается только с обычного single-link файла этого storage. Canonical source и внешний hardlink не меняются. ACL/sharing ошибки не подавляются. [Первичный failure]({PREFIX}_LOGS/native-extra-initial/test_windows_manual_migration.log).

Readonly source не объявляется поддержанным успешным сценарием: миграция отказывает до swap, сохраняет bytes/attributes источника и удаляет свой staging. Это подтверждённый безопасный отказ. Не заявляется Windows power-loss durability: `os._exit` проверяет остановку процесса, не обесточивание диска.

## Результаты

| Проверка | Фактический результат |
|---|---|
| Новые native migration/cleanup cases | 10 PASS, 0 SKIP: CLI Unicode/spaces; replay; manual next→verify→complete; copy/fsync/rename failure; real process exit с обеих сторон swap; открытый Windows handle; read-only; чужой sibling/hardlink; запрет automatic dispatch |
| Прежние V051MigrationTests | 5 PASS, 0 SKIP; включены также в mixed PH-051-10 run |
| Свежий regression run | 18 модулей, 294 tests; 8 PASS / 3 PASS_WITH_SKIPS / 7 FAIL; 24 failure events, 88 error events, 7 SKIP; 0 TIMEOUT |
| Установленный финальный wheel, другая CWD/venv | 42 PASS, 0 SKIP: 27 HTTP/import/реальный Edge + 15 migration/cleanup; actual console launcher и loopback health PASS; импорт из site-packages |
| Documentation validator | 36 checks PASS, 0 errors/warnings; 146 files, 928 local links |
| Объединённая матрица с историей | 38 модулей, 436 tests; 28 PASS / 3 PASS_WITH_SKIPS / 7 FAIL. **20 модулей взяты из предыдущей приёмки, не запускались заново в этой задаче** |

Два разделённых составных tests и 10 новых увеличили число с 424 до 436. Error count снижен с 95 до 88: устранены 4 migration errors, 3 недоступных file-symlink fixtures стали явными SKIP. 24 failure events остались; subtest events нельзя вычитать из testsRun для вычисления числа успешных methods.

[Свежая матрица]({PREFIX}_LOGS/REGRESSION_MATRIX_CURRENT.json), [объединённая provenance]({PREFIX}_LOGS/REGRESSION_MATRIX_COMBINED.json), [installed wheel log]({PREFIX}_LOGS/runs/installed-wheel-final.log), [индекс raw/published hashes]({PREFIX}_LOGS/EVIDENCE_INDEX.json).

## Разбор девяти прежних FAIL

В числовой колонке: tests / failures / errors / skips. Статусы относятся к целому модулю; PASS subset не заменяет FAIL смешанного модуля.

| Модуль | Повторный результат | Причина и решение |
|---|---|---|
{table}

Вне этого списка также проходит повторная проверка PH-LW-02 (с прежним NTFS case-sensitive SKIP), PH-LW-03 service, всех 44 HTTP/import/browser cases, 13 maturity lifecycle и 15 stage-transaction recovery cases. Дополнительных применимых manual дефектов эти прогоны не выявили.

Семь skips: 3 file-symlink WinError 1314, 2 real Podman prerequisites, 1 Unix FIFO, 1 NTFS case-sensitive fixture. Старый report неточно называл четыре прежних skips «3 Podman + 1 NTFS»; правильные raw logs сохранены. SKIP не закрывает соответствующий gate; системные привилегии не повышались.

## Среда, воспроизведение и поставка

Native Windows 11 Pro build 26200 x64, NTFS C:, non-admin; portable CPython 3.14.10 x64, Flask 3.1.3 и Waitress 3.0.2 по hash lock; Playwright 1.64.1 с установленным Edge 157.0.4341.42. jsonschema установлен в основной dev venv; wheel-run использует отдельную venv и импорт site-packages. Это не clean-machine installer acceptance.

Команды, UTC start, exit и durations записаны в MATRIX/run.json. Из корня workspace: `.venv/Scripts/python.exe tools/run_regressions.py --output <новый каталог> --jobs 3 --timeout 900 <modules из свежей матрицы>`. Только migration: `tests.test_windows_manual_migration tests.test_ph_051_10_migration_recovery.V051MigrationTests`. Для wheel: независимый Python запускает `tools/verify_installed.py --engine <Engine> --manual-migration` из другой CWD с пустым PYTHONPATH. Raw paths редактированы только в опубликованных копиях logs; raw hashes сохранены отдельно.

Финальный wheel SHA-256: `{wheel_hash}`. Engine/Documentation ZIP hashes находятся рядом с архивами в `{PREFIX}_SHA256.txt`. После упаковки точная пара распаковывается в отдельный каталог; выполняются CRC/exact tree/all manifests, 44 HTTP/import/browser tests, doctor/docs и 15 migration/cleanup tests. Фактический результат этого последнего шага — **внешняя аттестация** `FINAL_VERIFICATION/FINAL_ARCHIVE_VERIFICATION.json` рядом с ZIP, привязанная к их SHA-256; она намеренно не включена обратно в архив, чтобы не создавать цикл self-hash. Отсутствие PASS в этой аттестации означает незавершённую проверку поставки.

## Verdict и открытые gates

PH-LW-04/05 Windows HTTP/security regression — **PASS в проверенном scope**, прежняя приёмка сохранена. Windows v0.5.0→v0.5.1 manual migration remediation — **PASS** по source и final installed wheel. Общая regression matrix — **FAIL**, 7 модулей подробно классифицированы выше.

`LOCAL_WEB_MANUAL: NO-GO` до полного набора PH-LW gates, включая PH-LW-12. `AUTOMATIC_EXECUTOR: NO-GO`; real rootless Podman, positive governed per-Run egress и Linux automatic recovery этим Windows run не подтверждены. Полная v0.5.1 — **NO-GO / NOT RELEASED**. Automatic и PH-LW-06 не разрешены этим заданием.
'''
    (ENGINE / (PREFIX + '_TEST_REPORT.md')).write_text(report, 'utf-8')
    invariants = '''# Сохранённые инварианты — Windows manual remediation

- MANUAL_HANDOFF / network_mode NONE / null adapter and sandbox refs / EXPLICIT_AFTER_VERIFICATION сохраняются миграцией и проверяются tests.
- Accepted input, Stage/Run history и replay bytes неизменны; только kernel migration metadata обновляется штатным public API.
- Failed flush/copy до journal не меняет canonical root. Second rename failure возвращает старое дерево; real process exit до/после swap восстанавливается через public migrate-project.
- Read-only атрибут источника и внешнего hardlink не меняется cleanup. Удаляются только принадлежащие migration UUID siblings после native-path проверки.
- Public executor-doctor/execute-current на Windows BLOCKED; тест запрещает Popen и проверяет полный snapshot без mutation. No host Codex fallback, Podman install, policy/privilege changes.
- HTTP/service/import implementation и auth/CSRF/revision/replay contracts не менялись; повторные real TCP/Edge проверки проходят.
- Schemas, registries, templates, skills, нормативные specs и все прежние отчёты/logs сохранены. Зеркала docs/build/wheel проверяются отдельно; generated artifacts получены из canonical source.
- SKIP не означает security PASS; mixed automatic модули остаются FAIL. PH-LW-06 и полный manual release gate не объявлены выполненными.
'''
    (ENGINE / (PREFIX + '_PRESERVED_INVARIANTS.md')).write_text(invariants, 'utf-8')

    with zipfile.ZipFile(BASE / 'Project_Harness_Engine_v0.5.1_PH_LW_05.zip') as zf:
        baseline = {n.split('/', 1)[1]: hashlib.sha256(zf.read(n)).hexdigest()
                    for n in zf.namelist() if not n.endswith('/')}
    current = {p.relative_to(ENGINE).as_posix(): digest(p) for p in ENGINE.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    planned = {PREFIX + '_CHANGED_FILES.md', PREFIX + '_CHANGED_FILES.json'}
    added = (current.keys() - baseline.keys()) | planned
    changed = sorted(n for n in current.keys() & baseline.keys() if current[n] != baseline[n])
    historical = [n for n in baseline if re.match(r'PH_(?:LW_\d\d|051_\d\d|F\d\d)', n)]
    assert all(current.get(n) == baseline[n] for n in historical), 'Historical evidence changed'
    assert not (baseline.keys() - current.keys()), 'Unexpected removed baseline file'
    allowed_code = {'src/project_harness/migration.py', 'src/project_harness/resources/local_web/metadata_v1.json'}
    assert {n for n in changed if n.startswith('src/project_harness/')} <= allowed_code
    changes = {'input_archives': INPUTS, 'added': sorted(added), 'modified': changed, 'removed': [],
               'historical_files_unchanged': len(historical),
               'note': 'Generated docs aggregates/mirror and MANIFEST may be refreshed after this report; final ZIP verifier checks all bytes.'}
    save(ENGINE / (PREFIX + '_CHANGED_FILES.json'), changes)
    (ENGINE / (PREFIX + '_CHANGED_FILES.md')).write_text(
        '# Изменения относительно предыдущей Windows HTTP поставки\n\n'
        f'Исторические reports/logs: **{len(historical)} файлов побайтово неизменны**. Удалённых файлов нет. '
        f'Полный список: [{PREFIX}_CHANGED_FILES.json]({PREFIX}_CHANGED_FILES.json).\n\n'
        'Production: только `src/project_harness/migration.py` (Windows file flush и cleanup) и build metadata. '
        'Tests: platform-capability helper, 3 существующих fixture modules, новый native migration module. '
        'Docs: новый manual-migration chapter, README/CHANGELOG и generated aggregates/mirror. '
        'Build: source mirror, egg-info/SOURCES, wheel, manifests. Новые reports/logs не заменяют исторические.\n\n'
        'Workspace отдельно: актуализированы AGENTS/current task/map/runbook и tools для адресной упаковки, '
        'установленного wheel, точного extracted rerun и отчёта с provenance. Эти development files не входят в Engine wheel.\n', 'utf-8')
    print(json.dumps({'current': summary(fresh), 'combined': summary(merged),
                      'historical_files_unchanged': len(historical)}, indent=2))


if __name__ == '__main__':
    main()
