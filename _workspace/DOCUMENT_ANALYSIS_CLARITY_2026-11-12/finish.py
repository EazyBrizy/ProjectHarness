"""Record exact targeted results, current navigation and artifact boundaries."""
import ast,difflib,hashlib,json,os,platform,sys
from pathlib import Path
from importlib.metadata import version
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
def read(name):return json.loads((OUT/name).read_text('utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    path=OUT/name;assert not path.exists(),path
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def inventory(base):return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
freeze=read('RUNTIME_FREEZE_FINAL.json');baseline=read('INPUT_BASELINE.json')
for name in ('WHEEL_RESULTS.json','WHEEL_FOCUSED_RESULTS.json','WHEEL_TECHNOLOGY_RESULTS.json','WHEEL_TYPED_FINAL_RESULTS.json',
             'WHEEL_LEGACY_V2_RESULTS.json','WHEEL_ARCHIVE_FINAL_RESULTS.json','NATIVE_UI.json','INTEGRITY_FINAL.json','OPERATOR_UPGRADE_FINAL.json'):
    assert read(name)['status']=='PASS',name
assert read('NATIVE_CASE02.json')['state']=='SUCCEEDED'
assert read('NATIVE_CASE.json')['error_code']=='DRAFT_VALIDATION_FAILED'
save('FINAL_RESULTS.json',{'status':'PASS','unique_targeted_unittest_methods':16,'full_engine_tests':'NOT RUN — scoped change only',
    'runtime_runs':[{'result':n,'ran':read(n)['ran']} for n in ['WHEEL_RESULTS.json','WHEEL_FOCUSED_RESULTS.json','WHEEL_TECHNOLOGY_RESULTS.json',
        'WHEEL_TYPED_FINAL_RESULTS.json','WHEEL_LEGACY_V2_RESULTS.json','WHEEL_ARCHIVE_FINAL_RESULTS.json']],
    'rerun_reasons':{'focused':'Exact profile refs added after failed real case; model cache recovery and typed UI changed.',
        'technology':'New typed technology/version answer and explicit question resolution.',
        'typed_final':'Shared typed-array editor changed for adding technology; rechecked object preservation.',
        'archive_final':'Instruction version now comes from exact skeleton, fixed stale v2 literal.'},
    'native_model_requests':2,'native_first':'FAIL — profile.ref lacked consumable exact refs in pack; guard correctly rejected.',
    'native_second':'PASS after exact allowed_refs added; same four private documents, no canonical commit.',
    'native_model':read('NATIVE_CASE02.json')['selection'],'answers':14,'roadmap_stages':8,'current_questions':2,'future_questions':13,
    'full_ph_lw_matrix':'NOT RUN','automatic_executor_enabled':False})
changes={}
for label,base in [('source',ENGINE/'src/project_harness'),('tests',ENGINE/'tests')]:
    now=inventory(base);old=baseline[label]
    changes[label]={n:{'before':old.get(n),'after':now.get(n)} for n in sorted(set(old)|set(now)) if old.get(n)!=now.get(n)}
    for name in changes[label]:
        if name.endswith('.py'):ast.parse((base/name).read_text('utf-8'),filename=name)
save('CHANGED_FILE_HASHES.json',changes)
save('ENVIRONMENT.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
    'targeted_wheel_interpreter':str(ROOT/'_scratch/document_upload_feedback_20261109/wheel-venv/Scripts/python.exe'),
    'wheel_cwd':str(ROOT/'_scratch/document_upload_feedback_20261109/Независимая папка wheel'),
    'dependencies':{n:version(n) for n in ('Flask','Waitress','playwright')},'browser':'headless msedge / real TCP',
    'native_cli':'codex-cli 0.154.0','source_build_digest':freeze['engine_build_digest']})
current=ROOT/'_workspace/CURRENT_TASK.md';text=current.read_text('utf-8');point=text.index('\n\n')+2
entry='''2026-11-12. По новому заданию исправлены prompt → strict v3 import → UI документационного анализа и добавлен явный выбор модели/глубины CLI. Новые вопросы имеют один канал и устойчивый id; текущие/будущие решения разделены, notes не становятся blockers. Показаны содержательные ответы с источниками, ближайший этап и roadmap из документов отдельно от формальных Tasks/readiness. Структура редактируемых объектов сохраняется; статусы PREVIEW/сохранено согласованы. Legacy v2/history сохранены; approvals и Task executor не автоматизированы. Build `DOC-ANALYSIS-CLARITY2-20261112` установлен, прежние версии и данные сохранены; обычный desktop shortcut обновлён. 16 unique targeted methods PASS по scoped runs, independent installed wheel / Windows 11 / Python 3.14 / real TCP / headless Edge. Actual CLI на четырёх пользовательских MD: первый ответ корректно отклонён из-за profile.ref; после exact allowed_refs повтор только этого case — PASS: 14 ответов, 8 этапов, 2 текущих и 13 будущих вопросов вместо прежних 39 OPEN. Рабочий проект пользователя не менялся; native проверка — приватный scratch PREVIEW. [Отчёт](DOCUMENT_ANALYSIS_CLARITY_2026-11-12/REPORT.md), [freeze](DOCUMENT_ANALYSIS_CLARITY_2026-11-12/RUNTIME_FREEZE_FINAL.json), [результаты](DOCUMENT_ANALYSIS_CLARITY_2026-11-12/FINAL_RESULTS.json), [глава 34](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/34_Document_Analysis_Results_and_Models.md). Docs/mirrors/manifests/wheel/frozen including .pyd/installed package/doctor PASS. Full engine/core/PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN; прежние exact-byte verdicts не расширяются. Automatic executor disabled / прежний NO-GO, full v0.5.1 NOT RELEASED; Engine/Documentation ZIP, commit/push не выполнялись. Следующий шаг — запустить прежний ярлык → «Опрос и GPT» → обновить подключение CLI, выбрать модель/глубину и повторить анализ, затем сохранить предложения. Новые этапы самостоятельно не выполнять.

'''
assert freeze['build_id'] not in text
current.write_text(text[:point]+entry+text[point:],'utf-8')
report=f'''# Результат анализа документов и явная модель CLI

Дата: 2026-11-12. Build `{freeze['build_id']}` установлен по стандартному пути;
обычный ярлык обновлён. Данные и предыдущие версии сохранены.

Исправлена причина прежних дублей: инструкция требовала одни вопросы в трёх
каналах, обработчик объединял их по точному тексту и делал любую строку blocker.
В новом local-web v3 один канал questions с устойчивыми id, field, объяснением,
источниками, текущим/будущим этапом. Дубли id/нормализованного текста объединяются;
противоречивые scope/blocking, notes вместо вопросов и future blockers отклоняются.
Существующие пользовательские unknowns сохраняются до явного решения пользователя.
Семантически разные формулировки с разными id не угадываются алгоритмом: за один
id независимой темы отвечает новая инструкция. История v2 не переписана.

Analysis хранит суть проекта, ответы с происхождением и статусом
описано/предложение/противоречие, ближайший рекомендуемый этап и roadmap с шагами
и критериями готовности. Будущие этапы/вопросы свёрнуты. Этот обзор не назначает
Stage и не выдаётся за утверждённые executable Tasks/JIT. Формальные пробелы
Harness показаны отдельно. Версии/цены/масштаб и утверждения не выдумываются.

PREVIEW больше не сопровождается старой пустой анкетой или ожиданием ответа.
Видно, что предложения ещё не сохранены; после сохранения показываются вопросы
с полным текстом и основанием. Структурированное редактирование сохраняет имя,
потребность, обоснование и другие поля; у технологий/версий есть обычная форма.
Разрешение вопроса — явное действие сохранения, без отдельного confirmation.
Raw refs/digests/JSON остаются в технических details, canonical values не меняются.

В карточке CLI есть выбор модели и глубины. Каталог получает явный connect POST
через native `codex debug models`; GET читает cache. Выбор проверяется по каталогу,
сохраняется и передаётся фиксированными `--model` / `model_reasoning_effort`.
Job хранит запрошенные параметры этого запуска. Новая настройка не меняет старый
job и не вызывает повторный запуск при replay. У исторических jobs модель честно
неизвестна; server-side alias resolution не заявляется измеренным. Фиксированный
read-only invocation, выключенные tools/apps/plugins/web, process limits,
strict preview/bindings/revisions/approvals и отсутствие product writes сохранены.
Каталог CLI experimental, проверен на native 0.154.0; доступ аккаунта не обещается.
Параметры сверены с [OpenAI Docs CLI reference](https://learn.chatgpt.com/docs/cli/reference)
и [config reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Проверка на исходном проблемном случае

Все четыре MD пользователя переданы целиком в отдельной scratch рабочей области.
Первый реальный ответ отклонён strict validator: включённый registry содержал key,
но не точный profile.ref. Добавлены exact allowed_refs из public registry API,
без изменения registry или ослабления validator. Повторён только неудачный case:
**PASS**, gpt-6-astra / medium, 14 содержательных ответов, 8 этапов, 2 текущих
решения и 13 будущих. Future blocking=false. Главные сведения о сценариях,
Flutter/Dart/SQLite, ограничениях, архитектуре и порядке модулей сохранены;
неизвестные версии не превращены в «стек неизвестен». Source business texts и
полные результаты остаются приватно в `_scratch/document_analysis_clarity_20261112/`.
Рабочий проект пользователя и его черновик не изменены этой проверкой.
[Первый результат](NATIVE_CASE.json), [повтор](NATIVE_CASE02.json),
[команда/log](native-case02.run.json), [UI actual result](NATIVE_UI.json).
Снимки реального ответа просмотрены; canonical inventory до/после UI одинаков.

## Только целевые проверки

**16 уникальных unittest methods PASS**, без полного движка/core/PH-LW matrix:
[matrix и причины focused повторов](FINAL_RESULTS.json), [первый run](WHEEL_RESULTS.json),
[focused](wheel-focused.run.json), [новая форма технологий](wheel-technology.run.json),
[структура объектов](wheel-typed-final.run.json), [v2 roundtrip](wheel-legacy-v2.run.json),
[ручной ZIP](wheel-archive-final.run.json). Среда — [ENVIRONMENT.json](ENVIRONMENT.json).
Первая matrix: 13 PASS; позднее повторялись только изменённые зависимости и новые
cases. Model requests 2 (первый rejected, второй PASS), не на каждом прогоне tests.

Проверены v3 dedupe/scope/notes/source refs/bindings/approval-forgery отказ,
PREVIEW без commit, commit/reload/provenance, сохранение пользовательских unknowns,
отсутствие блокировки future, model/effort/argv/snapshot/replay, cache recovery,
Origin/unknown fields, busy/cancel/stale/restart, ручной ZIP и структура ответа,
real TCP/headless Edge, понятные статусы, ввод/сохранение typed objects и версий,
отсутствие JS errors/dialogs. Существующий v2 documented/no-doc roundtrip PASS.

При финальной сверке исправлена старая v2 ссылка в отдельной ИНСТРУКЦИЯ.md
ручного ZIP: версия теперь берётся из exact skeleton. Повторён только archive
case. Первый candidate build/его проверка сохранены отдельно; итоговый build2
установлен новым version directory. Повторного model analysis для этой строки нет.

Docs validator: первый FAIL из-за отсутствующего metadata header новой главы;
исправлен только header, итог PASS / 0 errors / ожидаемый WARN без delivery ZIP:
[итог](DOC_VALIDATION_FINAL.json). Source/build/wheel/frozen equality,
полный frozen payload включая .pyd, docs mirrors/manifests, core/history preservation:
[integrity](INTEGRITY_FINAL.json). [Upgrade](OPERATOR_UPGRADE_FINAL.json),
[ярлыки](SHORTCUTS_FINAL.json). Старый процесс остановлен public stop без force kill;
данные до/после install одинаковы, previous version сохранена, package/doctor exit 0.

## Точные артефакты и границы

Source digest `{freeze['engine_build_digest']}`.
Wheel SHA-256 `{freeze['wheel_sha256']}`.
UNSIGNED installer SHA-256 `{freeze['installer_sha256']}`.
[Полный freeze](RUNTIME_FREEZE_FINAL.json), [изменённые hashes](CHANGED_FILE_HASHES.json).
В финале относительно успешного native case менялись только UI и версия инструкции
архива, не prompt/model argv/normalization. Побайтовые границы описаны в evidence.

Actual installed-EXE browser reacceptance, full engine/core/PH-LW matrix NOT RUN.
Браузерная проверка — independent installed wheel, installed EXE — package/doctor
и полная идентичность bytes. Старые verdicts не расширяются на новые bytes.
AUTOMATIC_EXECUTOR disabled / прежний NO-GO; full v0.5.1 NOT RELEASED.
Engine/Documentation delivery ZIP, commit/push не выполнялись. User documents,
auth/connection/jobs/caches не добавлены в Git. Git index equality check не запускался
как требование незакоммиченной правки; current packaging anchor обновлён для будущей
публикации. Лимит native analysis остаётся прежним 300 секунд; проверенный разбор
занял около 266 секунд. Более глубокие режимы могут потребовать ручного пакета.

Следующий разрешённый шаг: запустить обычный ярлык, открыть «Опрос и GPT», обновить
подключение (кнопка «Подключено»), выбрать модель/глубину и повторить анализ в рабочем
проекте. Затем «Сохранить предложения». Новые результаты не заменяют старые сами.
Другие этапы и Task executor не включать самостоятельно.
'''
(OUT/'REPORT.md').write_text(report,'utf-8')
save('FINAL_ATTESTATION.json',{'status':'COMPLETE','build_id':freeze['build_id'],'unique_targeted_methods_passed':16,
    'native_requests':2,'full_engine_tests':'NOT RUN','automatic_executor_enabled':False,
    'delivery_zip_created':False,'commit_push':'NOT RUN','report_sha256':sha(OUT/'REPORT.md'),
    'current_task_sha256':sha(current),'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256')})
save('EVIDENCE_INDEX.json',{'self_hash_omitted':True,'files':{p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
    if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts}})
print(json.dumps(read('FINAL_ATTESTATION.json'),ensure_ascii=False,indent=2))
