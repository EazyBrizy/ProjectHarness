"""Record explicit user acceptance exceptions; preserve runtime and old evidence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from package_acceptance import ENGINE, DOCS, files, manifest
from verify_ph_lw_06_working_tree import verify_manifest

W = Path(__file__).resolve().parent
OLD = ROOT / '_workspace/PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json'
DOCUMENT = ENGINE / 'PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md'
NAV = {'README.md', '_workspace/CURRENT_TASK.md', '_workspace/PROJECT_MAP.md', '_workspace/RUNBOOK.md'}
ALLOWED = NAV | {ENGINE.name + '/MANIFEST.sha256', '_workspace/WORKSPACE_VALIDATION.json'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def snapshot():
    paths = [p for folder in (ENGINE, DOCS, ROOT / '_workspace') for p in files(folder)
             if not p.is_relative_to(W)]
    paths += [ROOT / 'README.md', ROOT / 'AGENTS.md']
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(paths))}


def main():
    assert not (W / 'INPUT_FILE_HASHES.json').exists(), 'Keep this decision record immutable; use a new output for another update'
    old = json.loads(OLD.read_text('utf-8'))
    assert old['status'] == 'PASS'
    for folder in (ENGINE, DOCS, ENGINE / 'docs' / DOCS.name):
        checked = verify_manifest(folder)
        assert checked['manifest_sha256'] == old['trees'][folder.relative_to(ROOT).as_posix()]['manifest_sha256']
    for name, digest in old['workspace_files'].items():
        assert sha(ROOT / name) == digest, 'Unexpected workspace drift: ' + name
    wheel = ENGINE / 'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    installer = ENGINE / 'windows/Harness-Setup-win-x64.exe'
    assert sha(wheel) == old['wheel_sha256'] and sha(installer) == old['installer_sha256']
    assert not DOCUMENT.exists()
    before = snapshot()
    save(W / 'INPUT_FILE_HASHES.json', before)
    save(W / 'INPUT_BASELINE.json', {
        'status': 'PASS', 'captured_utc': datetime.now(timezone.utc).isoformat(),
        'previous_attestation': str(OLD.relative_to(ROOT)), 'previous_attestation_sha256': sha(OLD),
        'wheel_sha256': sha(wheel), 'installer_sha256': sha(installer),
        'engine_build_digest': old['engine_build_digest'],
        'allowed_existing_changes': sorted(ALLOWED),
        'allowed_new_files': [DOCUMENT.relative_to(ROOT).as_posix(), W.relative_to(ROOT).as_posix() + '/*'],
        'purpose': 'Explicitly accepted limitations; no code, test, runtime package or historical evidence changes',
    })
    (W / 'CURRENT_TASK.before.md').write_bytes((ROOT / '_workspace/CURRENT_TASK.md').read_bytes())
    cases = [
        ('clean_machine_windows', 'Чистая Windows без инструментов разработчика', 'Среда недоступна; отдельную чистую Windows не требовать'),
        ('physical_offline', 'Физически отключённый интернет', 'Пользователь отменил обязательный прогон'),
        ('real_disk_full', 'Реально заполненный диск/том', 'Пользователь отменил обязательный прогон'),
        ('actual_unicode_windows_username', 'Настоящая учётная запись Windows с кириллицей', 'Отдельно подтверждено пользователем: тоже не блокирует'),
    ]
    decision = {
        'date': '2026-11-08', 'authority': 'Explicit user instruction in this chat',
        'confirmation': ['Да, НЕ являются блокерами', 'Windows с кириллицей тоже не должна блокировать!'],
        'scope': 'Current PH-LW-11 acceptance only; runtime requirements/core contracts unchanged',
        'checks': [{'id': key, 'description': label, 'result': 'NOT RUN',
                    'disposition': 'ACCEPTED_LIMITATION', 'blocks_ph_lw_11': False,
                    'mandatory_future_run': False, 'reason': reason} for key, label, reason in cases],
        'effective_verdicts': {'PH-LW-11': 'GO', 'qualifier': 'С принятыми пользователем ограничениями',
            'LOCAL_WEB_MANUAL': 'NO-GO; PH-LW-12 not started',
            'AUTOMATIC_EXECUTOR': 'NO-GO; disabled', 'v0.5.1': 'NO-GO / NOT RELEASED'},
        'runtime_tests_rerun': False, 'zip_created': False,
        'basis': 'Previously verified long-path fix, 240 source PASS/2 SKIP, installed wheel 49+33 PASS, EXE 4 PASS, installer recovery 4 PASS; not rerun for this documentary update',
    }
    save(W / 'DECISION.json', decision)
    DOCUMENT.write_text('''# PH-LW-11 — решение пользователя об условиях приёмки

**Дата:** 2026-11-08  
**Текущий verdict PH-LW-11:** **GO с принятыми пользователем ограничениями**.

## Принятые ограничения

По прямому решению пользователя следующие четыре проверки **не являются блокерами PH-LW-11**. Они остаются фактически **NOT RUN**; результат PASS им не назначается.

| Проверка | Фактический результат | Влияние на приёмку |
| --- | --- | --- |
| Чистая Windows без инструментов разработчика | NOT RUN | Принятое ограничение; отдельную среду не требовать |
| Работа с физически отключённым интернетом | NOT RUN | Принятое ограничение; обязательный прогон отменён |
| Реально заполненный диск/том | NOT RUN | Принятое ограничение; обязательный прогон отменён |
| Настоящая учётная запись Windows с кириллицей | NOT RUN | Принятое ограничение; отдельный прогон не требуется |

Эти проверки не назначать повторно как prerequisite приёмки или продолжения работы. Вернуться к ним можно по новому явному заданию пользователя. Unicode paths, sanitized PATH, no-external-request checks и ENOSPC injection остаются ранее полученным evidence; они не переименовываются в прогоны перечисленных четырёх условий.

## Основание и изменение прежней нормы

Пользователь подтвердил: «Да, НЕ являются блокерами», затем отдельно уточнил: «Windows с кириллицей тоже не должна блокировать!». Это явное изменение условий пользовательской приёмки данного PH-LW-11.

В [полном prompt r2](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_11.md) раздел «Реальная приёмка» требует эти проверки; [предыдущий отчёт](PH_LW_11_ZIP_PATH_TEST_REPORT.md) считал их mandatory NOT RUN и основанием NO-GO. Новое решение пользователя снимает именно блокирующий характер и обязательность этих четырёх прогонов. Исходный prompt, исторические NO-GO, raw test results, manifests и аттестации прежних checkpoints не переписываются. Настоящий документ и [машиночитаемое решение](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/DECISION.json) задают текущую политику поверх сохранённой истории.

Требования к self-contained installer, локальным assets, запрету CDN/provider calls, целостности и recovery не ослабляются; runtime-код и core contracts этим решением не меняются.

## Текущий статус и границы

Long-path ZIP-import и последующее чтение sources исправлены и ранее проверены на native Windows без изменения системных настроек. Проверенная база: PH-LW-11-ZIPPATH-20261108; source digest sha256:5f0d5ac595d8a052bfa456140f2d42c5d571c53ab38aff3c8831d4ebbe309bbf. Сохраняются результаты: source 240 PASS/2 SKIP, installed wheel 49+33 PASS, installed EXE 4 PASS, installer recovery 4 PASS. [Полный evidence](PH_LW_11_ZIP_PATH_LOGS/VERDICTS.json) отражает факты и прежнюю оценку до этого решения.

- **PH-LW-11: GO в согласованном пользователем объёме**, с четырьмя явно принятыми NOT RUN ограничениями.
- **LOCAL_WEB_MANUAL: NO-GO** до отдельного завершения PH-LW-12. Сам PH-LW-12 не начат и этим решением не разрешён.
- **AUTOMATIC_EXECUTOR: NO-GO**, выключен; Podman/positive governed per-Run egress не закрыты.
- Полная v0.5.1: **NO-GO / NOT RELEASED**. Подпись не добавлялась: installer UNSIGNED. Два прежних core SKIP и незавершённый visual walkthrough не объявляются PASS.

По отдельному указанию пользователя новые видимые browser windows не открывать; ручной UI выполнять в уже открытом авторизованном окне. Прежний fresh normal browser-opening second launch остаётся NOT RUN; подтверждённый historical normal launch и свежий точный отказ второго --no-browser launch (exit 1) сохраняются.

## Проверка документального обновления

Код, tests, standalone/embedded runtime docs, wheel, frozen bundle и installer не меняются. Решение хранится отдельным документом приёмки вне runtime package; пересборка и повтор runtime tests для этого изменения не требуются. Предыдущая [аттестация](../_workspace/PH_LW_11_ZIP_PATH/FINAL_WORKING_TREE_VERIFICATION.json) сохраняется как snapshot до принятия исключений. Текущие hashes, проверка связности, manifests и byte preservation: [новая проверка](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json), [before/after](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/CHANGED_FILE_HASHES.json), [SHA-256](../_workspace/PH_LW_11_ACCEPTANCE_SCOPE/SHA256.txt).

Следующий этап — только по отдельному заданию пользователя. Automatic executor не включать, к PH-LW-12 самостоятельно не переходить, Engine/Documentation ZIP не собирать.
''', 'utf-8')
    current = (ROOT / '_workspace/CURRENT_TASK.md').read_text('utf-8')
    current = current.replace('PH-LW-11 acceptance: NO-GO.', 'PH-LW-11 acceptance: GO с принятыми пользователем ограничениями.')
    previous = 'ZIP-import blocker закрыт. PH-LW-11 NO-GO из-за mandatory NOT RUN: clean-machine Windows, actual Unicode username, physical offline, real disk-full.'
    assert previous in current
    current = current.replace(previous, 'ZIP-import blocker закрыт. PH-LW-11: GO в согласованном пользователем объёме. Clean-machine Windows, actual Unicode username, physical offline и real disk-full остаются NOT RUN как принятые ограничения; все четыре не блокируют приёмку и не требуют обязательного будущего прогона по явному решению пользователя от 2026-11-08.')
    current = current.replace('Следующий разрешённый шаг — отдельное задание пользователя на оставшиеся acceptance environments.', 'PH-LW-11 закрыт в согласованном объёме с принятыми ограничениями. Следующий этап — только по отдельному заданию пользователя; четыре снятых прогона не назначать как prerequisite.')
    notice = '''
## Решение пользователя от 2026-11-08

[Условия приёмки](../Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md), [decision JSON](PH_LW_11_ACCEPTANCE_SCOPE/DECISION.json), [новая проверка](PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json). Четыре ранее блокировавших NOT RUN приняты как ограничения; текущий PH-LW-11 GO относится только к согласованному объёму. Прежние отчёты/вердикты и аттестации ниже — история до этого решения. Runtime artifacts, source digest, wheel и installer hashes не менялись. LOCAL_WEB_MANUAL и полный релиз не объявляются GO.
'''
    position = current.index('\n[Новый отчёт]')
    current = current[:position] + notice + current[position:]
    (ROOT / '_workspace/CURRENT_TASK.md').write_text(current, 'utf-8')
    for path, prefix in [
        (ROOT / 'README.md', 'Текущий PH-LW-11: **GO с принятыми пользователем ограничениями**. [Решение об условиях приёмки](Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md), [CURRENT_TASK](_workspace/CURRENT_TASK.md). Ниже сохранены прежние checkpoints. LOCAL_WEB_MANUAL/automatic/full v0.5.1 не повышены до GO; PH-LW-12 не начат.'),
        (ROOT / '_workspace/PROJECT_MAP.md', 'Актуальные условия PH-LW-11: [решение пользователя](../Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md). Четыре NOT RUN не блокируют этап; текущий PH-LW-11 GO с принятыми ограничениями. [CURRENT_TASK](CURRENT_TASK.md); ниже — история прежних checkpoints.'),
    ]:
        path.write_text(prefix + '\n\n' + path.read_text('utf-8'), 'utf-8')
    with (ROOT / '_workspace/RUNBOOK.md').open('a', encoding='utf-8') as stream:
        stream.write('''
## PH-LW-11 — принятые пользователем ограничения приёмки, 2026-11-08

[Решение](../Project_Harness_Engine_v0.5.1/PH_LW_11_ACCEPTANCE_SCOPE_DECISION.md), [decision JSON](PH_LW_11_ACCEPTANCE_SCOPE/DECISION.json), [проверка](PH_LW_11_ACCEPTANCE_SCOPE/VERIFICATION.json). Clean-machine Windows, physical offline, real disk-full и actual Unicode Windows username: фактически NOT RUN, но не блокируют PH-LW-11 и не являются обязательными будущими прогонами. Не требовать их как prerequisite без нового явного задания пользователя. Текущий PH-LW-11 GO — в согласованном объёме с принятыми ограничениями. Старые prompt/NO-GO/evidence не переписывать, NOT RUN не превращать в PASS.

Решение вынесено за runtime package: source/tests/docs mirrors/wheel/frozen/installer неизменны, runtime tests повторно не запускались. Проверяются ссылки, документационная связность, manifests, before/after hashes и сохранность старых evidence. LOCAL_WEB_MANUAL NO-GO до отдельно разрешённого PH-LW-12; automatic executor выключен, полная v0.5.1 NO-GO. Не открывать новые видимые browser windows; использовать открытое авторизованное окно для ручного UI. Engine/Documentation ZIP не собирать без явного запроса.
''')
    save(W / 'VERIFICATION.json', {'status': 'VERIFYING'})
    save(W / 'CHANGED_FILE_HASHES.json', [])
    (W / 'SHA256.txt').write_text('Verification in progress.\n', 'utf-8')
    manifest(ENGINE)
    commands = []
    for label, command in [
        ('workspace', [sys.executable, '-B', str(ROOT / 'tools/check_workspace.py')]),
        ('docs', [sys.executable, '-B', str(DOCS / 'tools/validate_documentation.py'), str(DOCS), '--json', str(W / 'DOC_VALIDATION.json')]),
    ]:
        log = W / (label + '.log')
        with log.open('wb') as stream:
            run = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=120,
                                 env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        commands.append({'command': command, 'cwd': str(ROOT), 'exit': run.returncode,
                         'status': 'PASS' if run.returncode == 0 else 'FAIL', 'log': log.name, 'log_sha256': sha(log)})
        assert run.returncode == 0, commands[-1]
    after = snapshot()
    changes = [{'file': name, 'before_sha256': before.get(name), 'after_sha256': after.get(name)}
               for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)]
    assert {name for name in after if name not in before} == {DOCUMENT.relative_to(ROOT).as_posix()}
    for row in changes:
        assert row['file'] in ALLOWED or row['file'] == DOCUMENT.relative_to(ROOT).as_posix(), row
    assert sha(OLD) == json.loads((W / 'INPUT_BASELINE.json').read_text('utf-8'))['previous_attestation_sha256']
    assert sha(wheel) == old['wheel_sha256'] and sha(installer) == old['installer_sha256']
    trees = {folder.relative_to(ROOT).as_posix(): verify_manifest(folder)
             for folder in (ENGINE, DOCS, ENGINE / 'docs' / DOCS.name)}
    save(W / 'CHANGED_FILE_HASHES.json', changes)
    save(W / 'VERIFICATION.json', {
        'status': 'PASS', 'verified_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Documentary acceptance decision only; no runtime or historical evidence changes',
        'effective_verdicts': decision['effective_verdicts'], 'accepted_not_run_count': len(cases),
        'source_tests_docs_wheel_frozen_installer_unchanged': True,
        'previous_attestation_unchanged': True, 'protected_existing_files_verified': len(before) - len([r for r in changes if r['before_sha256']]),
        'wheel_sha256': sha(wheel), 'installer_sha256': sha(installer),
        'document_sha256': sha(DOCUMENT), 'decision_sha256': sha(W / 'DECISION.json'),
        'input_file_hashes_sha256': sha(W / 'INPUT_FILE_HASHES.json'),
        'changed_file_hashes_sha256': sha(W / 'CHANGED_FILE_HASHES.json'),
        'script_sha256': sha(Path(__file__)), 'commands': commands, 'trees': trees,
        'python': sys.version, 'interpreter': sys.executable, 'platform': platform.platform(),
        'runtime_tests': 'NOT RUN; inputs unchanged, prior validated results retained',
        'zip_created': False, 'system_settings_changed': False, 'PH-LW-12_started': False,
        'workspace_files': {name: sha(ROOT / name) for name in sorted(NAV)},
    })
    output = [DOCUMENT, ENGINE / 'MANIFEST.sha256', DOCS / 'MANIFEST.sha256', wheel, installer,
              *sorted(p for p in W.iterdir() if p.is_file() and p.name != 'SHA256.txt')]
    (W / 'SHA256.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}' for p in output) + '\n', 'utf-8')
    print(json.dumps({'status': 'PASS', 'PH-LW-11': 'GO with user-accepted limitations',
                      'accepted_NOT_RUN': len(cases), 'runtime_unchanged': True,
                      'changed_files': [r['file'] for r in changes], 'zip_created': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
