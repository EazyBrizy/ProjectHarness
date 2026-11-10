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
assert read('UI_RESULTS.json')=={'ran':2,'failures':0,'errors':0,'skips':0,'status':'PASS'}
for name in ('INTEGRITY.json','DOCS_VALIDATION.json','OPERATOR_UPGRADE.json'):
    assert read(name)['status']=='PASS'
f=read('RUNTIME_FREEZE.json')

current=ROOT/'_workspace/CURRENT_TASK.md';first,rest=current.read_bytes().split(b'\r\n\r\n',1)
note=('2026-11-10. Улучшено представление вкладки «Опрос и GPT» по жалобе пользователя на hashes, известные ответы '
      'и смешанные английские термины. Вверху показан следующий шаг после ZIP; порядок: пакет для модели → ответ '
      'модели → оставшиеся вопросы. Хеши/refs/status codes и служебные JSON помещены в закрытые технические сведения. '
      'Автоматические настройки шаблона исключены из содержательных ответов; локальный черновик и предложения модели '
      'имеют понятные подписи происхождения. Подписи/option labels/история обмена по-русски, canonical значения/API '
      'payloads неизменны. Build `CLEAR-INTERVIEW-20261110` установлен, обычный ярлык обновлён; пользовательские '
      'данные сохранены. Только два изменённых interview UI сценария: **2 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, '
      'installed wheel вне source tree + real TCP/headless Edge; docs/mirrors/manifests/package PASS. '
      '[Отчёт](INTERVIEW_CLARITY_2026-11-10/REPORT.md), [freeze](INTERVIEW_CLARITY_2026-11-10/RUNTIME_FREEZE.json), '
      '[операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/29_Interview_Clarity.md). '
      'Core/API/schemas/states не менялись. Full engine/PH-LW matrix и actual installed-EXE browser reacceptance '
      'NOT RUN; UI bytes wheel/frozen/installed совпадают. Automatic executor disabled / прежний NO-GO; full v0.5.1 '
      'NOT RELEASED; ZIP не создавались. Dev server остановлен штатным public POST без force kill для обновления. '
      'Следующий шаг: открыть Harness заново через ярлык → «Опрос и GPT» → «Подготовить пакет для анализа». '
      'Другие этапы и широкие проверки не выполнять.')
current.write_bytes(first+b'\r\n\r\n'+note.encode('utf-8')+b'\r\n\r\n'+rest)

changes={};patch=[]
for group in ('src/project_harness','tests'):
    before=OUT/'before'/group;after=ENGINE/group
    names={p.relative_to(before).as_posix() for p in before.rglob('*') if p.is_file()}
    names|={p.relative_to(after).as_posix() for p in after.rglob('*') if p.is_file()}
    for name in sorted(names):
        if '__pycache__' in name or name.endswith('.pyc'):continue
        a=before/name;b=after/name;av=a.read_bytes() if a.exists() else b'';bv=b.read_bytes() if b.exists() else b''
        if av==bv:continue
        key=group+'/'+name;changes[key]={'before':sha(a) if a.exists() else None,'after':sha(b) if b.exists() else None}
        try:patch.extend(difflib.unified_diff(av.decode('utf-8').splitlines(keepends=True),bv.decode('utf-8').splitlines(keepends=True),fromfile='before/'+key,tofile='after/'+key))
        except UnicodeDecodeError:pass
for name in ('AGENTS.md','_workspace/CURRENT_TASK.md'):
    changes[name]={'before':sha(OUT/'before'/name),'after':sha(ROOT/name)}
save('CHANGED_FILE_HASHES.json',changes)
(OUT/'CODE_AND_TEST_DIFF.patch').write_text(''.join(patch),'utf-8')
report=f'''# Понятный экран анализа документации

Дата: 2026-11-10. Build `{f['build_id']}` установлен в стандартный пользовательский каталог; обычный desktop shortcut обновлён.

## Причина и результат

`get_interview` возвращает все непустые mutable draft fields. При начальной подготовке это включает настройки шаблона: `implementation.claimed_current_level`, `project.ambiguity_mode`, `skills.resolutions`. Старый renderer показывал их с canonical path, raw JSON и техническим provenance, как будто это уже известные ответы о пользовательском проекте. Хеши/revisions/statuses также попадали в основной текст. Эти значения не были результатами анализа загруженного ZIP.

Изменён только presentation layer:

- Вверху — понятный статус документов и следующий шаг «Подготовить пакет для анализа». Шаги расположены в порядке работы: подготовить пакет → вернуть ответ модели → уточнить вопросы.
- «Сохранённые сведения о проекте» показывают содержательные заполненные поля. Служебные template fields скрыты из этой группы; пустая группа прямо сообщает, что содержательных сведений ещё нет.
- Локальные значения имеют подпись «Сохранено в черновике проекта», без недоказанного утверждения, что их лично ввёл пользователь. GPT values имеют подпись «Предложено моделью» и читаемые имена источников; stale-source review warning сохранён.
- Названия полей, варианты выбора, статусы экрана, история пакетов/ответов, preview и сообщения сохранения показаны по-русски. Canonical option values и network payloads не меняются.
- Хеши, exact refs, status codes и полный технический view доступны в закрытых «Технических сведениях». Полная инструкция модели — отдельный раскрываемый блок с кнопкой копирования. В основной истории файлов нет digests/идентификаторов обмена.
- Общий banner «GET не запускает…» заменён на «Состояние обновлено».

API, provenance computation, schemas/registries, state transitions, sources, export/reply binding и содержимое пакета не изменены. UI не анализирует ZIP автоматически и не отправляет материалы модели. Local login, consent dialogs/checkboxes и automatic executor не возвращены.

## Как продолжить пользователю

Открыть Harness заново через ярлык → выбрать проект → «Опрос и GPT» → «Подготовить пакет для анализа» → выбрать категории данных → «Создать пакет для анализа». Скачать все файлы и передать их ChatGPT или Codex CLI с инструкцией из пакета. Полученный JSON вставить на шаге 2; посмотреть предложения и сохранить. При необходимости уточнить вопросы на шаге 3.

## Только целевые проверки

**2 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, один run без повторов. [Results](UI_RESULTS.json), [command/env/exit](targeted-ui.run.json), [raw log](targeted-ui.log).

1. Новый проект с ZIP из четырёх synthetic MD: next-action button виден до questionnaire; в видимом основном тексте отсутствуют hashes/internal refs/English status/provenance. Template facts не выданы за ответы. Закрытый technical block сохраняет original values/hashes. Общий banner понятный.
2. Сохранение ручного ответа → понятная local-draft provenance → создание/скачивание точного пакета → synthetic model reply с сохранением binding → preview с русскими labels → commit → понятная model provenance и история. Это declared fixture reply, не реальный вызов GPT/provider.

Проверки выполнены в независимой venv с установленным wheel вне source tree, CPython 3.14.10, Flask 3.1.3, Waitress 3.0.2, Playwright 1.64.1, Windows 11 x64/NTFS, real TCP/headless Edge. [Первый экран](screenshots/01-next-step.png), [сохранённое предложение модели](screenshots/02-saved-model-proposal.png); первый снимок визуально просмотрен. Синтаксис двух изменённых JS PASS.

Старые browser label expectations в PH-LW-06/08/12 адаптированы к русским надписям; их полные сценарии не запускались. Core tests и API expectations не ослаблялись. Full engine/core/PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN согласно правилу проверять только изменённое.

## Поставка и сохранность

[Documentation validator](DOCS_VALIDATION.json) PASS, ожидаемый ZIP-not-supplied warning. [Integrity](INTEGRITY.json): src/build/wheel/frozen UI bytes совпадают, все .pyd/payload files проверены, embedded mirror и manifests совпадают. [Build command](frozen-build.run.json), [BUILD_RESULT](BUILD_RESULT.json), [freeze](RUNTIME_FREEZE.json).

Запущенный dev server остановлен штатным public POST в idle состоянии, без force kill: [stop](STOP_FOR_UPDATE.json). [User upgrade](OPERATOR_UPGRADE.json) PASS: aggregate hashes/counts пользовательских app-data/projects до/после одинаковы; прежняя версия сохранена, package/doctor exit 0. [Ярлыки](SHORTCUTS.json). Visible browser windows не открывались; для применения открыть привычный ярлык заново.

В затронутом UI scope blockers нет. PH-LW-04/05: только затронутый presentation path PASS, новые полные verdicts не назначены. LOCAL_WEB_MANUAL full reacceptance NOT RUN; исторические GO сохраняют exact-byte границы. AUTOMATIC_EXECUTOR disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. Engine/Documentation ZIP не создавались; следующие этапы не выполнялись.

## Hashes и scope

- Source digest: `{f['engine_build_digest']}`.
- Wheel SHA-256: `{f['wheel_sha256']}`.
- Installer SHA-256: `{f['installer_sha256']}`.
- PACKAGE_FILES SHA-256: `{f['package_manifest_sha256']}`.
- [Input baseline / allowed file changes](INPUT_BASELINE.json), [changed hashes](CHANGED_FILE_HASHES.json), [diff](CODE_AND_TEST_DIFF.patch).

Runtime diff ограничен `interview.js`, interview HTML, shared notice/description text в `app.js` и build metadata. Остальной backend/core и историческая документация сохранены по input hashes. Чужие изменения не отменялись. Правило понятных пользовательских подписей записано в AGENTS.md и [главе 29](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/29_Interview_Clarity.md).
'''
(OUT/'REPORT.md').write_text(report,'utf-8')
(OUT/'GIT_STATUS.after.txt').write_bytes(subprocess.check_output(['git','status','--short'],cwd=ROOT))
save('OUTPUT_HASHES.json',{'source_digest':f['engine_build_digest'],'wheel_sha256':f['wheel_sha256'],'installer_sha256':f['installer_sha256'],
    'report':sha(OUT/'REPORT.md'),'runtime_freeze':sha(OUT/'RUNTIME_FREEZE.json'),
    'root_files':{n:sha(ROOT/n) for n in ('AGENTS.md','_workspace/CURRENT_TASK.md')},
    'engine_manifest':sha(ENGINE/'MANIFEST.sha256'),'documentation_manifest':sha(ROOT/'Project_Harness_Documentation_v0.5.1/MANIFEST.sha256')})
save('EVIDENCE_INDEX.json',{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and 'before' not in p.relative_to(OUT).parts and '__pycache__' not in p.parts})
print('Report and CURRENT_TASK updated. No additional product tests run.')
