"""Record this local UI change; do not run broader suites."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text('utf-8'))
def save(name,data):
    p=OUT/name;assert not p.exists(),p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')

assert read('UI_RESULTS.json')=={'ran':3,'failures':0,'errors':1,'skips':0,'status':'FAIL'}
assert read('UI_FOCUSED_RESULTS.json')=={'ran':1,'failures':0,'errors':0,'skips':0,'status':'PASS'}
assert read('INTEGRITY.json')['status']=='PASS'
assert read('DOCS_VALIDATION.json')['status']=='PASS'
assert read('OPERATOR_UPGRADE.json')['status']=='PASS'
f=read('RUNTIME_FREEZE.json')
save('METHOD_RESULTS.json',{
 'tests.test_single_action_ui.SingleActionUiTests.test_create_upload_replace_error_export_and_stop_without_confirmations':{'status':'PASS','log':'targeted-ui.log'},
 'tests.test_single_action_ui.SingleActionUiTests.test_decisions_and_folder_action_need_no_extra_checkbox':{'status':'PASS','log':'focused-ui.log'},
 'tests.test_single_action_ui.SingleActionUiTests.test_task_and_lifecycle_clicks_submit_current_intent_without_checkbox':{'status':'PASS','log':'targeted-ui.log'},
})

current=ROOT/'_workspace/CURRENT_TASK.md';first,rest=current.read_bytes().split(b'\r\n\r\n',1)
note=('2026-11-09. По прямому указанию пользователя удалены все modal confirm dialogs и дополнительные обязательные '
      'consent checkboxes во всём UI. Одно нажатие конкретной кнопки достаточно; CLI verify/manual evidence также '
      'не требуют дополнительного флага. Данные/ошибки показываются в форме; API intent-поля передаёт сам адаптер '
      'нажатия, без автоматических решений при GET/GPT import. Build `SINGLE-ACTION-UI-20261109` установлен, обычный '
      'desktop shortcut обновлён; данные сохранены. Проверены только изменённые UI paths: **3 уникальных метода PASS** '
      '(первый run: 2 PASS / 1 ERROR из-за имени селектора в новом fixture; исправлен селектор и повторён только этот '
      'метод — PASS). Docs/mirrors/manifests/package PASS; full engine/core/PH-LW matrix NOT RUN. '
      '[Отчёт и ограничения](NO_EXTRA_CONFIRMATIONS_2026-11-09/REPORT.md), '
      '[freeze](NO_EXTRA_CONFIRMATIONS_2026-11-09/RUNTIME_FREEZE.json), '
      '[правило интерфейса](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/28_Single_Action_Interface.md). '
      'Запущенный dev server остановлен штатным POST только после проверки отсутствия активной работы, force kill не '
      'использовался. Для применения открыть Harness заново через ярлык. Automatic executor disabled / прежний NO-GO; '
      'full v0.5.1 NOT RELEASED; ZIP не создавались. Других этапов и широких прогонов не выполнять.')
current.write_bytes(first+b'\r\n\r\n'+note.encode('utf-8')+b'\r\n\r\n'+rest)

changed={};patch=[]
for group in ('src/project_harness','tests','local_web'):
    before=OUT/'before'/group;after=ENGINE/group
    names={p.relative_to(before).as_posix() for p in before.rglob('*') if p.is_file()}
    names|={p.relative_to(after).as_posix() for p in after.rglob('*') if p.is_file()}
    for name in sorted(names):
        if '__pycache__' in name or name.endswith('.pyc'):continue
        a=before/name;b=after/name;av=a.read_bytes() if a.exists() else b'';bv=b.read_bytes() if b.exists() else b''
        if av==bv:continue
        key=group+'/'+name;changed[key]={'before':sha(a) if a.exists() else None,'after':sha(b) if b.exists() else None}
        try:patch.extend(difflib.unified_diff(av.decode('utf-8').splitlines(keepends=True),bv.decode('utf-8').splitlines(keepends=True),fromfile='before/'+key,tofile='after/'+key))
        except UnicodeDecodeError:pass
for name in ('AGENTS.md','_workspace/CURRENT_TASK.md'):
    changed[name]={'before':sha(OUT/'before'/name),'after':sha(ROOT/name)}
save('CHANGED_FILE_HASHES.json',changed)
(OUT/'CODE_AND_TEST_DIFF.patch').write_text(''.join(patch),'utf-8')

report=f'''# Действия без повторных подтверждений

Дата: 2026-11-09. Build `{f['build_id']}` установлен в стандартный `%LOCALAPPDATA%/Programs/ProjectHarness`.

## Что изменено

Во всех разделах Local Web удалены `window.confirm` и дополнительные обязательные галочки «подтверждаю / разрешаю / я прочитал». Создание проекта, загрузка/замена ZIP, ответ «Документации нет», остановка, создание GPT pack, применение решений, размещение папки, manual evidence, Task verification и lifecycle actions выполняются конкретной кнопкой без второго вопроса. При отсутствии данных либо ошибке показывается сообщение в форме.

Удалены DOM controls и все обращения к ним; обработчики отправляют существующие `confirm`/`confirmed`/`consent` поля по одному явному нажатию. Статусы проекта, binding/replay checks, источники и результаты не назначаются самим UI. Formal decisions остаются смыслом конкретной кнопки действия, без дополнительной галочки. GET/polling и GPT import не создают решений автоматически. Automatic executor не включался.

CLI `verify` принимает саму команду как намерение выполнить её declared verification plan; `record-task-manual-evidence` принимает саму команду как намерение сохранить переданные наблюдения. Дополнительные confirmation switches больше не обязательны и убраны из help; старые явные switches принимаются для совместимости. Product commands в этой проверке не запускались. Это явное изменение прежнего UX-контракта закреплено в AGENTS.md и [главе 28](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/28_Single_Action_Interface.md); исторические описания не переписывались.

## Только целевые проверки

Три уникальных метода проверяют изменённые UI paths; весь движок и полная PH-LW matrix не запускались.

| Проверка | Итог | Evidence |
|---|---|---|
| Создание проекта, missing fields inline, upload/replace ZIP, rejected ZIP без потери источников, local export, no-doc action и stop — без dialogs | PASS | [targeted log](targeted-ui.log) |
| Отдельные решения без checkbox, размещение папки одним действием | PASS | [focused log](focused-ui.log) |
| Task verify/manual evidence и lifecycle action отправляют current intent без удалённых DOM controls | PASS, typed UI fixtures + captured HTTP requests; business worker не запускался | [targeted log](targeted-ui.log) |
| Независимый installed wheel, исходники совпадают побайтово | PASS | [command/env](targeted-ui.run.json) |
| CLI help без confirmation switches | PASS; без исполнения product commands | [result](CLI_HELP.json) |
| Документация / embedded mirror / manifests / wheel CRC / frozen payload, включая .pyd | PASS | [docs](DOCS_VALIDATION.json), [integrity](INTEGRITY.json) |
| Обновление пользовательской установки, package/doctor и сохранность данных | PASS | [upgrade](OPERATOR_UPGRADE.json), [shortcuts](SHORTCUTS.json) |

Первый UI run: 2 PASS / 1 ERROR. Ошибка была в новом test selector: карточки показывают project ID, а fixture искал название. Исправлен только selector; повторён только этот метод, PASS. Уже прошедшие методы не повторялись. [Поимённые итоги](METHOD_RESULTS.json), [focused command](focused-ui.run.json). Это не исправление runtime через ослабление ожиданий: отсутствие dialogs/checkboxes, exact request count и обязательные API intent checks сохранены.

Windows 11 x64/NTFS/non-admin, CPython 3.14.10, Flask 3.1.3, Waitress 3.0.2, Playwright 1.64.1, headless Edge с реальным TCP. Реальный upload/export/decision путь проверен через public APIs; folder target и Task/lifecycle event checks останавливают mutation на HTTP fixture boundary, не заявляют проверку compiler/worker/core state machines. [Снимок формы](screenshots/documents-without-confirmations.png). Дополнительно проверен синтаксис изменённых JS и Python; run-wide business tests не запускались.

## Обновление и ограничения

Работавший dev server остановлен штатным public POST в idle состоянии, без force kill; [evidence](STOP_FOR_UPDATE.json). Установлен новый build, обычный ярлык обновлён; ярлык «разработка» использует текущий src. Aggregate hashes пользовательских app-data/projects до/после установки совпадают; прежняя версия сохранена. Откройте Harness заново через привычный ярлык, чтобы заменить старую страницу с загруженным JavaScript.

Actual installed-EXE browser/full workflow reacceptance NOT RUN: UI проверен из installed wheel, совпадение UI bytes с frozen/installed bundle доказано отдельно. Full core/PH-LW matrix NOT RUN согласно прямому правилу пользователя. Исторические GO не переносятся на новую сборку как full verdict. PH-LW-04/05: затронутый UI path PASS; LOCAL_WEB_MANUAL full reacceptance NOT RUN. AUTOMATIC_EXECUTOR disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. Engine/Documentation ZIP не создавались. В выполненном scope blockers нет; соседние этапы не запускались.

## Exact bytes

- Source digest: `{f['engine_build_digest']}`.
- Wheel SHA-256: `{f['wheel_sha256']}`.
- Installer SHA-256: `{f['installer_sha256']}`.
- PACKAGE_FILES SHA-256: `{f['package_manifest_sha256']}`.
- [Input baseline / allowed changes](INPUT_BASELINE.json), [output freeze](RUNTIME_FREEZE.json), [changed hashes](CHANGED_FILE_HASHES.json), [diff](CODE_AND_TEST_DIFF.patch).

Runtime изменён только в шести UI scripts, HTML, CLI adapter и build metadata. Соседние core modules, schemas/registries и прежняя документация сохранены по baseline hashes. Старые UI tests адаптированы только к удалённым controls/изменённым надписям; новые целевые методы перечислены выше. Чужие изменения не отменялись.
'''
(OUT/'REPORT.md').write_text(report,'utf-8')
(OUT/'GIT_STATUS.after.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
save('OUTPUT_HASHES.json',{'source_digest':f['engine_build_digest'],'wheel_sha256':f['wheel_sha256'],
    'installer_sha256':f['installer_sha256'],'report':sha(OUT/'REPORT.md'),'runtime_freeze':sha(OUT/'RUNTIME_FREEZE.json'),
    'root_files':{name:sha(ROOT/name) for name in ('AGENTS.md','_workspace/CURRENT_TASK.md')},
    'engine_manifest':sha(ENGINE/'MANIFEST.sha256'),'docs_manifest':sha(ROOT/'Project_Harness_Documentation_v0.5.1/MANIFEST.sha256')})
save('EVIDENCE_INDEX.json',{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
    if p.is_file() and 'before' not in p.relative_to(OUT).parts and '__pycache__' not in p.parts})
print('Final report and CURRENT_TASK written. No broader tests run.')
