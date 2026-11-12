import ast,hashlib,json,platform,sys
from importlib.metadata import version
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((OUT/name).read_text('utf-8'))
def save(name,value):
    p=OUT/name;assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def inventory(base):return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
freeze=load('RUNTIME_FREEZE.json');baseline=load('INPUT_BASELINE.json')
for n in ['SOURCE_RESULTS.json','SOURCE_CONTEXT_RESULTS.json','SOURCE_TARGET_CHOICE_RESULTS.json','UI_PROBE_RETRY_RESULTS.json',
          'WHEEL_RESULTS.json','NATIVE_CASE.json','DOC_VALIDATION.json','INTEGRITY.json','OPERATOR_UPGRADE.json']:
    assert load(n)['status']=='PASS',n
assert len(load('UI_PROBE_RESULTS.json')['errors'])==1
methods=set(load('SOURCE_RESULTS.json')['methods'])|set(load('WHEEL_RESULTS.json')['methods'])
assert len(methods)==11
save('RESULTS.json',{'status':'PASS','unique_targeted_methods':11,'methods':sorted(methods),
    'source':'5 PASS; context and explicit target guard rechecked only after their changes',
    'ui_probe':'Initial fixture direct service read raced browser GET and correctly hit operation guard; public queued read retry PASS',
    'wheel':'6 PASS / 0 FAIL / 0 ERROR, outside source tree / real TCP / Edge',
    'native':load('NATIVE_CASE.json'),'full_engine_tests':'NOT RUN','full_core_regression':'NOT RUN','full_ph_lw_matrix':'NOT RUN',
    'automatic_executor_enabled':False})
changes={}
for label,base in [('source',ENGINE/'src/project_harness'),('tests',ENGINE/'tests')]:
    now=inventory(base);old=baseline[label]
    changes[label]={n:{'before':old.get(n),'after':now.get(n)} for n in sorted(set(old)|set(now)) if old.get(n)!=now.get(n)}
    for name in changes[label]:
        if name.endswith('.py'):ast.parse((base/name).read_text('utf-8'),filename=name)
save('CHANGED_FILE_HASHES.json',changes)
save('ENVIRONMENT.json',{'python':sys.version,'platform':platform.platform(),'executable':sys.executable,
    'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},'browser':'headless msedge / real TCP',
    'wheel_interpreter':str(ROOT/'_scratch/document_upload_feedback_20261109/wheel-venv/Scripts/python.exe'),
    'native_cli':'0.154.0','native_selection':load('NATIVE_CASE.json')['selection']})
current=ROOT/'_workspace/CURRENT_TASK.md';text=current.read_text('utf-8');point=text.index('\n\n')+2
entry='''2026-11-12. По новому заданию вопросы документального анализа получили 2–3 готовых варианта, объяснение, ограничения и рекомендацию. Local-web v4 сохраняет v2/v3/history; новые варианты обязательны, не выбираются автоматически, существующие вопросы привязаны индексом без дубля. Один click выбирает вариант через public draft API с typed validation, SET-stale/APPEND preservation, revision/replay/source checks и existing durable recovery. KEEP_OPEN сохраняет подход, не закрывая неизвестный факт. Свой ответ/typed form доступны; пользовательские ответы сохраняются, показываются с provenance и передаются следующему анализу, superseded values помечены. Target не назначается в v4 main import до выбора пользователя. 11 unique targeted methods PASS по scoped runs; начальный UI probe столкнул прямой fixture GET с browser queue, guard сохранён, исправлено только чтение fixture через public queued API — PASS. Independent installed wheel / Windows 11 / Python 3.14 / real TCP / Edge: 6 PASS. Actual native CLI synthetic case PASS: 1 существующий вопрос, 2 содержательных варианта, рекомендованный выбран/сохранён, без approvals/Task execution и без model call при выборе. Build `DOC-DECISION-OPTIONS-20261112` установлен, данные/previous version/shortcut сохранены. [Отчёт](DOCUMENT_DECISION_OPTIONS_2026-11-12/REPORT.md), [результаты](DOCUMENT_DECISION_OPTIONS_2026-11-12/RESULTS.json), [freeze](DOCUMENT_DECISION_OPTIONS_2026-11-12/RUNTIME_FREEZE.json), [глава 36](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/36_Question_Decision_Options.md). Docs/mirrors/manifests/wheel/full frozen including .pyd/package/doctor PASS. Core schemas/registries и previous uncommitted work сохранены. Full engine/core/PH-LW matrix, actual installed-EXE browser reacceptance, Engine/Documentation ZIP и commit/push NOT RUN. Automatic executor disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. Следующий шаг — открыть прежний ярлык, повторить анализ для вариантов нового формата, сохранить предложения и выбирать готовые решения. Другие этапы не выполнять самостоятельно.

'''
assert freeze['build_id'] not in text
current.write_text(text[:point]+entry+text[point:],'utf-8')
report=f'''# Готовые варианты решения вопросов

Дата: 2026-11-12. Build `{freeze['build_id']}` установлен, ярлык обновлён,
данные и предыдущая версия сохранены.

Вопросы нового анализа содержат 2–3 варианта с описанием подхода, tradeoffs и
обоснованной рекомендацией. Они определяются документами конкретного проекта;
производственного списка универсальных «ответов на всё» нет. Вариант не выбран
автоматически. До сохранения анализа предложения видны read-only, затем одна
кнопка «Выбрать этот вариант» сохраняет ответ без дополнительного confirmation.
«Свой вариант» поддерживает текст и обычный typed editor. Вопросы будущих этапов
тоже получают варианты, оставаясь необязательными для текущей работы.

Для неизвестных фактов предлагается способ получения данных или явно обозначенное
допущение. Если resolves_question=false, сохраняется подход и прежний blocking,
а не выдуманный готовый факт. Выбранные ответы переживают reload, имеют provenance
USER_ANSWER и входят в следующий пакет как INPUT. Позднее отредактированные поля
помечаются superseded_fields, актуальный draft имеет приоритет. Для массивов
APPEND сохраняет другие ответы; SET защищён от перезаписи изменённых данных.

## Данные и границы

Новый local-web envelope v4 содержит choices/recommendation/existing_unknown_index.
V2/V3 и принятая история не переписаны; core schemas/registries не менялись.
Варианты проходят строгую проверку типа/семантики/refs до показа. Выбор передаёт
только server-issued IDs: произвольный patch готового варианта не принимается.
Недоступны execution/approvals/identity/Stage/Task/JIT/skills/work_packages и прямое
изменение unknowns. Последние меняет сервер для конкретного явно отвеченного
пункта. Основной v4 import не назначает target: для него нужен явный выбор.

Новый POST использует existing public draft update/commit и durable intent/recovery.
Source/input/revision/fingerprint/Origin/replay checks сохранены. GET/polling не
выбирают варианты. Выбор не запускает CLI/model request, команды или product writes.
Максимум v4 — 50 вопросов в прежнем bounded exchange; старому анализу без вариантов
нужен новый разбор. Сам выбор ответа не является formal approval или evidence.

## Только целевые проверки

**11 уникальных методов PASS**, [matrix](RESULTS.json), [среда](ENVIRONMENT.json).
[Source: 5 PASS](source-tests.run.json), [контекст после редактирования](source-context.run.json),
[явный target](source-target-choice.run.json), [final installed wheel: 6 PASS](wheel-targeted.run.json).
Windows 11 / CPython 3.14.10 / pinned Flask/Waitress/Playwright, real TCP/headless Edge,
independent installed wheel вне source tree; package inventory совпал с source.

Проверены обязательные options/recommendation, typed values и запрет protected
изменений, v2/v3 envelopes, привязка существующего вопроса без дубля/снятия blocking,
отсутствие автоподстановки target, SET/APPEND, KEEP_OPEN, custom reply, следующий
pack с ответами, источники/Origin/stale/replay/tamper, no extra model invocation,
existing recovery до/после atomic update. В UI — рекомендации без автоселекции,
один click, свой ответ, будущие вопросы, reload, сохранение typed структуры,
ручной ZIP/strict preview и совместимость текущего CLI пути, без JS errors/dialogs.

Первый [UI probe](ui-probe.run.json) дал ERROR в fixture: прямой service GET
конкурировал с собственными browser reads и правильно встретил operation guard.
Переведено только чтение fixture на существующий serialized public API;
[retry](ui-probe-retry.run.json) PASS, semantic assertions/guard не ослаблялись.
Уже прошедшие проверки повторялись только после изменения прямой зависимости
или для проверки финального distribution boundary. Полный движок не запускался.

## Реальный модельный ответ

Один synthetic CLI case, gpt-6-astra / low (выбран из actual CLI catalog):
существующий вопрос об учёте порядка JSON-массивов получил два содержательных
варианта: позиционное сравнение либо позиционное сравнение с отдельной отметкой
перестановок. Модель объяснила ограничения, рекомендовала простой подход для
прототипа. Рекомендуемый вариант явно выбран в тесте, typed architecture decision
сохранён, approvals false, Task execution отсутствует. Model requests **1**;
при выборе повторного вызова модели нет. [Native result](NATIVE_CASE.json),
[команда/log](native-case.run.json). Raw input/reply/snapshots — приватно в
`_scratch/document_decision_options_20261112/native/`; пользовательский проект
не анализировался повторно и его ответы не выбирались тестом.

Native run проверял source layout до финальной регенерации build metadata и
добавления flags устаревшего answer context/явного target guard. Для этого case
target уже выбран и старых answers нет; обе новые ветки проверены отдельно.
Actual installed-EXE browser reacceptance NOT RUN: UI evidence — final wheel,
EXE — полная byte equality/package/doctor. [Снимок вариантов](../../_scratch/document_decision_options_20261112/playwright/ready-options.png).

## Артефакты

Docs validator PASS / 0 errors / ожидаемый WARN без delivery ZIP:
[результат](DOC_VALIDATION.json). [Integrity](INTEGRITY.json) проверяет source,
build/lib, wheel, frozen including .pyd, mirrors/manifests, allowed changes и
сохранение предыдущей работы. [Upgrade](OPERATOR_UPGRADE.json), [shortcut](SHORTCUTS.json).
Source digest `{freeze['engine_build_digest']}`.
Wheel SHA-256 `{freeze['wheel_sha256']}`.
UNSIGNED installer SHA-256 `{freeze['installer_sha256']}`.
[Freeze](RUNTIME_FREEZE.json), [before/after](CHANGED_FILE_HASHES.json).

Full engine/core regression/PH-LW matrix NOT RUN. Старые verdicts не расширяются
на новые bytes; AUTOMATIC_EXECUTOR disabled / прежний NO-GO, full v0.5.1 NOT RELEASED.
Engine/Documentation ZIP, commit/push и Git-index equality check незакоммиченной
работы NOT RUN. История и все предыдущие uncommitted изменения сохранены.

Следующий шаг: открыть Harness прежним ярлыком, повторить анализ, сохранить
предложения; выбрать вариант на шаге 3. Другие этапы самостоятельно не выполнять.
'''
(OUT/'REPORT.md').write_text(report,'utf-8')
save('FINAL_ATTESTATION.json',{'status':'COMPLETE','build_id':freeze['build_id'],'unique_targeted_methods_passed':11,
    'native_requests':1,'full_engine_tests':'NOT RUN','delivery_zip_created':False,'commit_push':'NOT RUN',
    'report_sha256':sha(OUT/'REPORT.md'),'current_task_sha256':sha(current),
    'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256')})
save('EVIDENCE_INDEX.json',{'self_hash_omitted':True,'files':{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts}})
print(json.dumps(load('FINAL_ATTESTATION.json'),ensure_ascii=False,indent=2))
