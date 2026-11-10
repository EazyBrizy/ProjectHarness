"""Write final evidence once, without rerunning product tests."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text('utf-8'))
def save(name,value):
    path=OUT/name;assert not path.exists(),path
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')

freeze=read('RUNTIME_FREEZE.json');upgrade=read('OPERATOR_UPGRADE.json')
assert read('WHEEL_RESULTS.json')['status']=='PASS'
assert read('installed-exe/RESULT.json')['status']=='PASS'
assert upgrade['status']=='PASS' and read('INTEGRITY.json')['status']=='PASS'
assert read('DOCS_FINAL.json')['status']=='PASS'
assert read('LAUNCHER_SMOKE.json')['status']=='PASS'

current=ROOT/'_workspace/CURRENT_TASK.md'
first,rest=current.read_bytes().split(b'\r\n\r\n',1)
note=('2026-11-09. Локальный вход полностью удалён по явному решению пользователя: формы, bootstrap, '
      'auth sessions/cookies/CSRF, login/logout routes и DPAPI handshake. Build `NO-LOCAL-LOGIN-20261109` '
      'установлен в стандартный каталог; desktop shortcut обновлён, dev shortcut использует canonical src. '
      'Данные сохранены. Только целевые проверки финальных bytes: **7 PASS HTTP/instance + 12 PASS actual EXE/Edge**, '
      'source pythonw launch/relaunch/restart/stop PASS; docs/mirrors/manifests/package PASS. '
      '[Отчёт и ограничения](REMOVE_LOCAL_LOGIN_2026-11-09/REPORT.md), '
      '[freeze](REMOVE_LOCAL_LOGIN_2026-11-09/RUNTIME_FREEZE.json). Широкие pilot runs остановлены, '
      'не засчитаны финальной приёмкой; наблюдавшийся PH-LW-08 browser FAIL не расследован в суженном scope. '
      'Полная повторная PH-LW matrix / LOCAL_WEB_MANUAL нового build NOT RUN; прежние GO исторические. '
      'Automatic executor disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. ZIP не создавались. '
      'Следующий разрешённый шаг — открыть любой прежний ярлык и пользоваться интерфейсом без входа. '
      'Другие этапы не выполнять. Для следующих правок проверять только изменённое; полный прогон '
      'требует отдельного явного запроса пользователя.')
current.write_bytes(first+b'\r\n\r\n'+note.encode('utf-8')+b'\r\n\r\n'+rest)

rows={};patch=[]
for group in ('src/project_harness','tests','local_web'):
    before=OUT/'before'/group;after=ENGINE/group
    names={p.relative_to(before).as_posix() for p in before.rglob('*') if p.is_file()}
    names|={p.relative_to(after).as_posix() for p in after.rglob('*') if p.is_file()}
    for key in sorted(names):
        if '__pycache__' in key or key.endswith('.pyc'):continue
        a=before/key;b=after/key
        av=a.read_bytes() if a.exists() else b'';bv=b.read_bytes() if b.exists() else b''
        if av==bv:continue
        name=group+'/'+key
        rows[name]={'before':sha(a) if a.exists() else None,'after':sha(b) if b.exists() else None}
        try:patch.extend(difflib.unified_diff(av.decode('utf-8').splitlines(keepends=True),bv.decode('utf-8').splitlines(keepends=True),fromfile='before/'+name,tofile='after/'+name))
        except UnicodeDecodeError:pass
for name in ('AGENTS.md','_workspace/CURRENT_TASK.md','_workspace/RUNBOOK.md','tools/verify_installed.py'):
    rows[name]={'before':sha(OUT/'before'/name),'after':sha(ROOT/name)}
save('FINAL_CHANGED_FILE_HASHES.json',rows)
(OUT/'FINAL_CODE_AND_TEST_DIFF.patch').write_text(''.join(patch),'utf-8')

report=f'''# Локальный вход удалён; только целевые проверки

Дата: 2026-11-09. Build `{freeze['build_id']}` установлен в `%LOCALAPPDATA%/Programs/ProjectHarness`.

## Результат

Удалены формы входа/выхода, bootstrap-коды, LocalWebAuth, session store/TTL, auth cookies, CSRF headers/checks, session routes и DPAPI/challenge-response launcher channel. Обычный loopback URL сразу открывает интерфейс. `/api/session`, `/api/session/bootstrap`, `/api/session/logout` возвращают 404. Instance discovery хранит только PID/port; старый private record выводится из использования. Exact Host/Origin/port, loopback binding, operation guard, schemas, revision/replay и проектные approvals сохранены. Правило изменения auth-контракта явно записано в AGENTS.md и [главе 26](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/26_No_Local_Login.md); исторические нормы и отчёты сохранены.

Обычный desktop shortcut указывает на новую установленную сборку. «Project Harness — разработка» использует canonical src и не требует переустановки для последующих source changes. [Проверка ярлыков](SHORTCUTS.json). [Обновление пользователя](OPERATOR_UPGRADE.json): exit 0, прежняя версия сохранена, aggregate hashes app-data/projects до и после одинаковы; `--check-package` и `--doctor` exit 0. Проверочные серверы остановлены, видимых окон браузера не открывали. Для работы открыть привычный ярлык; коды и пароли не нужны.

## Правило проверок — прямое указание пользователя

**Проверяем только то, что меняем, и доказанные прямые зависимости. Весь движок раз за разом не проверяем. Полный прогон — только по отдельному явному запросу пользователя.** Уже прошедшие проверки без новых изменений или конкретной причины не повторяем. Зафиксировано в AGENTS.md, CURRENT_TASK.md, RUNBOOK.md и [главе 27](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/27_Targeted_Verification.md), включая embedded mirror. Это указание имеет приоритет над прежними широкими командами в исторических планах/prompts.

## Целевые проверки финальных bytes

| Проверка | Результат | Evidence |
|---|---|---|
| Изменённый HTTP contract и instance discovery, installed wheel вне source tree | 7 PASS, 0 FAIL/ERROR/SKIP | [log/command](targeted-wheel.run.json), [results](WHEEL_RESULTS.json) |
| Direct entry, ZIP import/feedback, active document controls, missing fields, cookie clear/reload/new tab, service restart | Actual installed EXE: 12 PASS, 0 FAIL/ERROR/SKIP | [results](installed-exe/RESULT.json), [browser log](installed-exe/browser.log), [command](installed-exe-tests.run.json) |
| Source pythonw launcher, second launch plain URL, restart, legacy record retirement, direct stop | PASS, isolated fixture | [results](LAUNCHER_SMOKE.json), [command](launcher-smoke.run.json) |
| Updated source/build/wheel/frozen bytes, full payload including .pyd, mirrors/manifests | PASS | [integrity](INTEGRITY.json), [freeze](RUNTIME_FREEZE.json) |
| Updated documentation, including targeted-verification rule | PASS; expected warning: ZIP not supplied | [result](DOCS_FINAL.json), [command](docs-final.run.json) |

Windows 11 x64/NTFS/non-admin; CPython 3.14.10; Flask 3.1.3; Waitress 3.0.2; headless Edge over real TCP. Build tools/pins/commands: [final build](frozen-build-final.run.json), [BUILD_RESULT](BUILD_RESULT.json). Browser tests used only synthetic documents, isolated roots and a sanitized installed-process PATH. [Screenshots](installed-exe/screenshots/direct-documents.png).

## Preliminary runs и ограничения

`initial-http-ui`: 37 PASS на предварительных bytes, не финальная приёмка. `source-local-web` и `wheel-tests` — широкие предварительные runs, остановлены; raw logs/exit сохранены. Их результаты не засчитаны финальной matrix. Obsolete CSRF-negative expectations заменены в связи с явным удалением auth-контракта; Host/Origin, schema, replay и business negatives сохранены. Выявленная ошибка instance record (`ensure_native_path` без `file_ok=True`) исправлена; [focused regression](instance-fixed.run.json), финальные wheel/EXE/launcher checks PASS. В широком candidate был PH-LW-08 browser FAIL без завершённого traceback/report; причина не исследована после сужения scope пользователем, не объявлена исправленной. Этот run не даёт нового full-manual verdict. [Решение о сужении scope](TARGETED_SCOPE_DECISION.json).

PH-LW-04: целевые проверки нового direct-access contract PASS, прежний auth contract отменён пользователем. PH-LW-05: затронутый upload/UI path PASS. Полная новая PH-LW matrix и LOCAL_WEB_MANUAL: NOT RUN; исторические GO относятся к прежним exact bytes. AUTOMATIC_EXECUTOR disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. Clean machine, physical offline, actual Unicode username, real disk-full, visible default-browser launch и EXE timing-latch injection не выполнялись. Engine/Documentation ZIP не создавались.

## Hashes и scope

- Source digest: `{freeze['engine_build_digest']}`.
- Wheel SHA-256: `{freeze['wheel_sha256']}`.
- Installer SHA-256: `{freeze['installer_sha256']}`.
- PACKAGE_FILES SHA-256: `{freeze['package_manifest_sha256']}`.
- [Input baseline](INPUT_BASELINE.json), [scope addendum](SCOPE_ADDENDUM.json), [final changed hashes](FINAL_CHANGED_FILE_HASHES.json), [diff относительно сохранённой базы](FINAL_CODE_AND_TEST_DIFF.patch).

Изменены только auth/entry runtime paths, связанные tests/drivers, инструкции/операторские главы и generated artifacts. Остальной runtime/core, прежние тесты вне auth-affected списка и историческая документация сохранены; это проверено по baseline hashes. Чужие исходные изменения не отменялись. Дальше — использовать приложение; другие этапы и широкие прогоны не запускать самостоятельно.
'''
(OUT/'REPORT.md').write_text(report,'utf-8')
(OUT/'GIT_STATUS.after.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
save('OUTPUT_HASHES.json',{'runtime_freeze':sha(OUT/'RUNTIME_FREEZE.json'),
    'report':sha(OUT/'REPORT.md'),'changed_hashes':sha(OUT/'FINAL_CHANGED_FILE_HASHES.json'),
    'root_files':{n:sha(ROOT/n) for n in ('AGENTS.md','_workspace/CURRENT_TASK.md','_workspace/RUNBOOK.md','tools/verify_installed.py')},
    'engine_manifest':sha(ENGINE/'MANIFEST.sha256'),'documentation_manifest':sha(ROOT/'Project_Harness_Documentation_v0.5.1/MANIFEST.sha256')})
save('EVIDENCE_INDEX.json',{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
    if p.is_file() and 'before' not in p.relative_to(OUT).parts and '__pycache__' not in p.parts})
print('Final report, current task and output hashes written; no tests rerun.')
