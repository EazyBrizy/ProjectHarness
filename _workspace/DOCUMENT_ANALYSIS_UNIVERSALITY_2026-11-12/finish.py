import ast,hashlib,json,platform,sys
from pathlib import Path
from importlib.metadata import version
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((OUT/name).read_text('utf-8'))
def save(name,value):
    p=OUT/name;assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def inventory(base):return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
freeze=load('RUNTIME_FREEZE.json');baseline=load('INPUT_BASELINE.json')
for name in ('PROBE_RESULTS.json','WHEEL_FOCUSED_RESULTS.json','NATIVE_CASES.json','DOC_VALIDATION.json','INTEGRITY.json','OPERATOR_UPGRADE.json'):
    assert load(name)['status']=='PASS',name
assert load('WHEEL_RESULTS.json')['ran']==4 and len(load('WHEEL_RESULTS.json')['failures'])==1
assert not load('WHEEL_RESULTS.json')['errors']
save('RESULTS.json',{'status':'PASS','unique_targeted_methods':7,'remaining_failures':0,
    'source_probe':'3 PASS; corpus 4 domains, 1/2/3/6 documents, normalization and generic UI',
    'wheel_initial':'3 PASS, 1 FAIL — fixture used positional fields after schema-driven editor',
    'wheel_focused':'1 PASS — only failed case, input by labels; semantic assertions unchanged',
    'runtime_bytes_unchanged_for_focused_retry':True,'native_model_requests':2,
    'native_cases':load('NATIVE_CASES.json')['results'],'full_engine_tests':'NOT RUN',
    'full_core_regression':'NOT RUN','full_ph_lw_matrix':'NOT RUN','automatic_executor_enabled':False})
bindings={}
for file in (ROOT/'_scratch/document_analysis_universality_20261112/native').glob('*/interview.json'):
    value=json.loads(file.read_text('utf-8'))
    bindings[file.parent.name]={'exports':[{'sha256':e['export_sha256'],'files':e['files']} for e in value['exports']],
        'sources':[{'name':d['source_relative_path'],'sha256':d['sha256']} for d in value['documents']]}
save('NATIVE_PACKET_BINDINGS.json',bindings)
changes={}
for label,base in [('source',ENGINE/'src/project_harness'),('tests',ENGINE/'tests')]:
    now=inventory(base);old=baseline[label]
    changes[label]={n:{'before':old.get(n),'after':now.get(n)} for n in sorted(set(old)|set(now)) if old.get(n)!=now.get(n)}
    for name in changes[label]:
        if name.endswith('.py'):ast.parse((base/name).read_text('utf-8'),filename=name)
save('CHANGED_FILE_HASHES.json',changes)
paths=[p for p in (ENGINE/'src/project_harness').glob('local_web*.py')]
paths+=list((ENGINE/'src/project_harness/resources/local_web').rglob('*'))
paths=[p for p in paths if p.is_file() and p.suffix in {'.py','.js','.json','.html','.css','.md'}]
specific=['MIN_ANDROID_VERSION','Flutter','SQLite','питание.zip','01_Концепция_проекта.md','LWP-AAA9F15BA8B5F6F2BDB5']
hits=[{'file':p.relative_to(ENGINE).as_posix(),'text':term} for p in paths for term in specific if term in p.read_text('utf-8')]
assert not hits,hits
save('RUNTIME_LITERAL_SCAN.json',{'status':'PASS','files_reviewed':len(paths),'specific_literals':specific,'hits':hits,
    'scope':'Current local-web Python/assets/prompt; normative enums/refs/limits remain contracts, examples only in tests',
    'not_a_proof_of_model_behavior':True})
save('ENVIRONMENT.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
    'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},'browser':'real TCP / headless Edge',
    'wheel_interpreter':str(ROOT/'_scratch/document_upload_feedback_20261109/wheel-venv/Scripts/python.exe'),
    'native_cli':'0.154.0','native_selection':'Chosen from actual CLI catalog; request recorded per job',
    'final_source_digest':freeze['engine_build_digest']})
current=ROOT/'_workspace/CURRENT_TASK.md';text=current.read_text('utf-8');point=text.index('\n\n')+2
entry='''2026-11-12. По новому заданию проверена и исправлена универсальность работы с документацией. Убраны Android-specific example/предположение о прототипе и тематические правила «всегда потом» из prompt. Формы и enum теперь строятся по readonly canonical schema, без частного template технологий. Нормализация сохраняет C/C++/C#, регистр единиц и математические обозначения; пустой roadmap явно показан, произвольные API/build identifiers не переводятся вне контекста уровня. Importer/exchange не зависят от названий, числа 4 или исходного продукта. 7 unique targeted methods PASS по scoped runs: 3 source cases (4 domains, 1/2/3/6 MD), 3 initial wheel PASS + 1 fixture-order FAIL, затем только failed case с input by labels — PASS без runtime/semantic-assert изменений. Два actual CLI synthetic cases PASS: действующий Go/PostgreSQL service сохранил текущую миграцию и payment callback; непрограммная заявка не получила выдуманный стек/план. Данные рабочего проекта не анализировались повторно. Build `DOC-ANALYSIS-UNIVERSAL-20261112` установлен, данные/previous version сохранены, shortcut обновлён. [Отчёт](DOCUMENT_ANALYSIS_UNIVERSALITY_2026-11-12/REPORT.md), [результаты](DOCUMENT_ANALYSIS_UNIVERSALITY_2026-11-12/RESULTS.json), [freeze](DOCUMENT_ANALYSIS_UNIVERSALITY_2026-11-12/RUNTIME_FREEZE.json), [глава 35](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/35_Project_Independent_Document_Analysis.md). Docs/mirrors/manifests/wheel/full frozen payload including .pyd/package/doctor PASS. Универсальность относится к содержанию в поддерживаемых UTF-8 MD/ZIP и прежних limits/policy, не заявляет PDF/DOCX/OCR. Core contracts, accepted history и предыдущая uncommitted работа сохранены; Task executor disabled / прежний NO-GO, full v0.5.1 NOT RELEASED. Full engine/core/PH-LW matrix, installed-EXE browser reacceptance, Engine/Documentation ZIP и commit/push NOT RUN. Следующий шаг — открыть прежний ярлык и использовать анализ для своего проекта; для обновлённого результата повторить анализ. Новые этапы не выполнять самостоятельно.

'''
assert freeze['build_id'] not in text
current.write_text(text[:point]+entry+text[point:],'utf-8')
report=f'''# Универсальность работы с документацией

Дата: 2026-11-12. Build `{freeze['build_id']}` установлен, обычный desktop
shortcut обновлён. Данные и предыдущая версия сохранены. Найденные привязки
исправлены; это проверка текущего документального пути, не гарантия результата
модели на любом возможном входе.

| Область | Результат проверки и изменение |
|---|---|
| Импорт/ZIP/exact payload | Фиксированных четырёх файлов, имён исходного архива или ролей документов нет. Тексты и refs передаются по inventory. Проверены 1/2/3/6 документов, BOM, вложенность, произвольные Unicode names и обратный порядок ZIP entries. |
| Инструкция | Убраны пример Android-specific topic ID, привязка к прототипу и автоматическое отнесение тематических работ к будущему. Область, стек, зрелость, темы и план определяются источниками. Есть правила для действующих систем, миграции, исследований, непрограммных и неполных описаний, конфликтов и отсутствующего плана. |
| Обработка | Ключ текста больше не стирает значимые знаки/регистр: C/C++/C#, MB/Mb, x²/x2 и Unicode различаются. Повтор одной темы по stable id/тексту объединяется без потери разных решений. Похожие формулировки с разными id автоматически семантически не угадываются. |
| Ответы/UI | Структуры и enum берутся из canonical schema в read-only interview, без отдельного hardcoded technology template. Поддержаны refs, варианты string/object, списки/вложенные объекты, bool, number и null; значения не выбираются автоматически. Отсутствующий план явно показан. Перевод названий уровней ограничен соответствующим полем, literal API/build identifiers сохраняются. |
| Общие правила | Canonical fields/enums/refs/digests, bounded exchange, source/secret/policy/Host/Origin guards, mutable whitelist и readonly tools policy — общие контракты, не факты о предметной области. Они сохранены. |

Изменены только пять разрешённых source files: [scope](SCOPE.md),
[before/after hashes](CHANGED_FILE_HASHES.json). [Scan](RUNTIME_LITERAL_SCAN.json)
не нашёл исходных продуктовых имён/стека/ID в текущем local-web пути; сам поиск
литералов не заменяет семантические проверки. Исторические specs/prompts/reports
и legacy full-manual template сохранены. Последний не используется текущим
Local Web/CLI document packet; его общие engine contracts не переписаны.

## Целевая проверка

**7 уникальных методов PASS по scoped runs.** [Результаты](RESULTS.json),
[source probe](source-probe.run.json), [installed wheel](wheel-targeted.run.json),
[один focused retry](wheel-focused.run.json), [среда](ENVIRONMENT.json).
Первый source run: 3 PASS, включая 4 предметные области и реальный Edge/TCP.
Wheel run: 3 PASS / 1 FAIL — прежняя fixture заполняла поля по позиции; schema
передаётся JSON object и порядок ключей не является контрактом. Fixture переведена
на labels, semantic asserts технологии/версии сохранены. Runtime bytes не менялись;
повторён только этот failed case — PASS. Полный движок/core/PH-LW matrix не запускался.

Проверены exact texts/payload hashes, разные filenames/counts/порядок, изоляция
проектов, строгий preview без canonical commit, сохранение неизвестного target
и отсутствие подставленного стека, точные поля schema. В UI проверены создание
пользователя/компонента/критерия/технологии через общий editor, сохранение вложенных
значений, null/неизменённых списков, отсутствующий roadmap, enum из schema,
literal RELEASE в неподходящем для перевода контексте, inert HTML, отсутствие
JS errors/dialogs. Устаревший v2 unknowns/UNSURE/pending-approvals guard PASS.

## Реальный CLI отдельно от fixtures

Два синтетических входа, выбранная из native CLI catalog модель gpt-6-astra / low:

- Действующий сервис Go/PostgreSQL, 3 документа: 5 ответов, 2 этапа. CURRENT —
  миграция R7 с обязательным платёжным callback, FUTURE — дизайн R8. Подготовка
  intake не превратила существующую систему в разработку прототипа.
- Непрограммная заявка на выставку, 1 документ: 4 ответа, roadmap пустой.
  Фактический этап обозначен неизвестным, уточнение условий — рекомендация;
  программный стек не навязан.

[CLI results](NATIVE_CASES.json), [команда/log](native-cases.run.json),
[exact packet/source bindings](NATIVE_PACKET_BINDINGS.json). Runtime source и
prompt соответствуют финальным bytes; native runs выполнялись в source layout
до регенерации build metadata. Final metadata отличается как metadata сборки.
Raw JSON/inputs/result находятся в `_scratch/document_analysis_universality_20261112/`.
Это 2 model requests, не повторный разбор пользовательского проекта. Canonical
draft каждого case до/после одинаков, сохранено только PREVIEW; product writes,
Task executor и команды из документов не запускались.

## Артефакты и пределы

Docs validator PASS / 0 errors, ожидаемый WARN без delivery ZIP:
[результат](DOC_VALIDATION.json). Source/build/wheel/frozen equality, docs mirrors,
manifests, весь frozen payload включая .pyd, сохранение core/history и предыдущих
изменений: [integrity](INTEGRITY.json). Установка/данные/previous version,
--check-package/--doctor exit 0: [upgrade](OPERATOR_UPGRADE.json),
[shortcut](SHORTCUTS.json). Visible browser не открывался.

Source digest `{freeze['engine_build_digest']}`.
Wheel SHA-256 `{freeze['wheel_sha256']}`.
UNSIGNED installer SHA-256 `{freeze['installer_sha256']}`.
[Полный freeze](RUNTIME_FREEZE.json).

Универсальность касается содержания поддерживаемых **UTF-8 Markdown и ZIP с MD**.
PDF/DOCX/OCR, nested ZIP и снятие прежних limits/policy не добавлялись. Некоторое
описание может быть недостаточным или неприменимым для формального software
handoff Harness; это не основание придумывать детали. Формальная подготовка,
stage assignment, approvals и фактическая зрелость остаются отдельными.

Actual installed-EXE browser reacceptance NOT RUN; browser evidence — source и
independent installed wheel, installed EXE — byte equality/package/doctor.
Старые release verdicts сохраняют прежние exact-byte границы. AUTOMATIC_EXECUTOR
disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. Engine/Documentation ZIP,
commit/push и Git-index equality check незакоммиченной работы NOT RUN. Новая
working packaging anchor подготовлена для следующей публикации; предыдущая
uncommitted работа сохранена.

Следующий разрешённый шаг — открыть Harness прежним ярлыком и использовать
анализ для своего проекта; для нового результата повторить анализ. Другие этапы
и полную matrix самостоятельно не запускать.
'''
(OUT/'REPORT.md').write_text(report,'utf-8')
save('FINAL_ATTESTATION.json',{'status':'COMPLETE','build_id':freeze['build_id'],'unique_targeted_methods_passed':7,
    'native_requests':2,'full_engine_tests':'NOT RUN','delivery_zip_created':False,'commit_push':'NOT RUN',
    'report_sha256':sha(OUT/'REPORT.md'),'current_task_sha256':sha(current),
    'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256')})
save('EVIDENCE_INDEX.json',{'self_hash_omitted':True,'files':{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts}})
print(json.dumps(load('FINAL_ATTESTATION.json'),ensure_ascii=False,indent=2))
