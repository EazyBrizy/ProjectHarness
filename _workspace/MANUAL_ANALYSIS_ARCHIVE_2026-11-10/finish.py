"""Exact evidence and navigation for the manual ZIP change; no suite reruns."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda n:json.loads((OUT/n).read_text('utf-8'))
def save(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
baseline=load('INPUT_BASELINE.json');freeze=load('RUNTIME_FREEZE.json')
assert load('WHEEL_FOCUSED_RESULTS.json')['status']=='PASS'
assert load('WHEEL_RESULTS.json')=={'ran':5,'failures':1,'errors':1,'skips':0,'status':'FAIL'}
for n in ('INTEGRITY.json','OPERATOR_UPGRADE.json'):assert load(n)['status']=='PASS'
for n in ('docs-validator.run.json','frozen-build.run.json'):assert load(n)['exit_code']==0
method_names=['test_single_archive_content_exact_binding_read_only_and_replay',
    'test_real_multipart_recombined_without_truncation_and_tamper_rejected',
    'test_stale_and_foreign_origin_rejected_without_download_or_mutation',
    'test_one_click_zip_download_without_history_and_reply_still_previews',
    'test_download_error_and_wrong_mime_are_inline_without_extra_download']
save('FINAL_RESULTS.json',{'unique_methods':5,'passed':5,'failures_remaining':0,'model_requests':0,
    'same_runtime_bytes_in_both_runs':True,'wheel_sha256':freeze['wheel_sha256'],
    'methods':{n:{'status':'PASS','log':'wheel-focused.log' if n==method_names[-1] else 'wheel-tests.log'} for n in method_names},
    'initial_failure':'Playwright route fixture accepted Request as default status argument; cleanup error same case. Fixed callback signature only; runtime and expectations unchanged. Retried only that method.'})
records={};diffs={}
for label,base,old in [('source',ENGINE/'src/project_harness',baseline['source']),('tests',ENGINE/'tests',baseline['tests'])]:
    now={p.relative_to(base).as_posix():sha(p) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    changed={n:{'before':old.get(n),'after':now.get(n)} for n in sorted(set(old)|set(now)) if old.get(n)!=now.get(n)}
    records[label]=changed;parts=[]
    for name in changed:
        before=OUT/'before'/('src/project_harness' if label=='source' else 'tests')/name
        a=before.read_text('utf-8').splitlines(True) if before.exists() else []
        b=(base/name).read_text('utf-8').splitlines(True)
        parts.extend(difflib.unified_diff(a,b,fromfile='before/'+label+'/'+name,tofile='after/'+label+'/'+name))
    (OUT/(label.upper()+'_DIFF.patch')).write_text(''.join(parts),'utf-8')
driver='local_web/windows/final_acceptance.py'
records['additional_driver']={driver:{'before':baseline['additional_driver'][driver],'after':sha(ENGINE/driver)}}
(OUT/'DRIVER_DIFF.patch').write_text(''.join(difflib.unified_diff((OUT/'before'/driver).read_text('utf-8').splitlines(True),
    (ENGINE/driver).read_text('utf-8').splitlines(True),fromfile='before/'+driver,tofile='after/'+driver)),'utf-8')
for name in records['tests']:ast.parse((ENGINE/'tests'/name).read_text('utf-8'),filename=name)
ast.parse((ENGINE/driver).read_text('utf-8'),filename=driver)
save('ADAPTER_SYNTAX.json',{'status':'PASS','files':list(records['tests'])+[driver],'scope':'AST parse only; old broad workflows NOT RUN'})
save('CHANGED_FILE_HASHES.json',records)
sample=OUT/'output/playwright/harness-analysis.zip'
with ZipFile(sample) as z:save('ZIP_SAMPLE.json',{'archive_sha256':sha(sample),'bytes':sample.stat().st_size,
    'members':{i.filename:{'bytes':i.file_size,'sha256':hashlib.sha256(z.read(i.filename)).hexdigest()} for i in z.infolist()},
    'unpacked_files_also_saved':True,'synthetic_sources_only':True})
current=ROOT/'_workspace/CURRENT_TASK.md';text=current.read_text('utf-8');point=text.index('\n\n')+2
entry='''2026-11-10. По заданию пользователя удалён блок истории пакета/отдельных ссылок/копирования инструкции. «Сформировать пакет вручную» одним нажатием создаёт export и сразу скачивает `harness-analysis.zip` с двумя MD: `ИНСТРУКЦИЯ.md` и полным `pack.md`. Части большого пакета проверяются и объединяются без обрезки; exact payload/binding и старый parts API сохранены. ZIP GET read-only, stale/tamper отказ, binary GET в существующей browser queue; JSON ошибки не скачивается как ZIP. Build `MANUAL-ANALYSIS-ZIP-20261110` установлен, ярлык обновлён, данные и previous version сохранены. Только 5 новых целевых методов: 5 unique PASS across scoped runs (первый: 4 PASS, 1 FAIL + cleanup ERROR той же fixture; исправлена только route callback signature, повторён один failed метод — PASS). Independent installed wheel / real TCP/headless Edge, model requests 0. Docs/mirrors/manifests/wheel/frozen payload включая .pyd/installed package/doctor PASS. [Отчёт](MANUAL_ANALYSIS_ARCHIVE_2026-11-10/REPORT.md), [freeze](MANUAL_ANALYSIS_ARCHIVE_2026-11-10/RUNTIME_FREEZE.json), [глава 33](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/33_Manual_Analysis_Archive.md). Full engine/core/PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN; прежние verdicts сохраняют exact-byte границы. Automatic Task executor disabled / прежний NO-GO; full v0.5.1 NOT RELEASED. Engine/Documentation ZIP не собирались; ручной handoff ZIP — явно запрошенная feature. Следующий шаг — открыть Harness через прежний ярлык → «Опрос и GPT» → «Сформировать пакет вручную», прикрепить скачанный ZIP к GPT/Codex. Другие этапы и широкие проверки не выполнять.

'''
assert freeze['build_id'] not in text
current.write_text(text[:point]+entry+text[point:],'utf-8')
report='''# Один ZIP для ручного анализа

Дата: 2026-11-10. Build `{build}` установлен по стандартному пути, обычный desktop shortcut обновлён, данные и предыдущая версия сохранены.

Кнопка «Сформировать пакет вручную» готовит export и сразу скачивает `harness-analysis.zip`. Внутри только `ИНСТРУКЦИЯ.md` по-русски и полный `pack.md` с документами, правилами, схемами и return skeleton. Блок истории/отдельных ссылок/копирования инструкции удалён. Пользователь прикрепляет архив к GPT/Codex и возвращает JSON на шаге 2. Модель не вызывается самой ручной кнопкой; отдельный автоматический CLI-анализ сохранён.

## Scope и exact data

[Baseline и разрешённые файлы](INPUT_BASELINE.json) проверены до изменений: source/docs/manifests и полный frozen payload включая .pyd. Изменены local_web_exchange/service/http для фиксированного read-only archive GET, serialized transport app.js только для ZIP responseType, interview.js/index.html для одного скачивания и удаления блока, build metadata. Core/schemas/registries/Task executors/CLI analysis не менялись. [Hashes](CHANGED_FILE_HASHES.json), [runtime diff](SOURCE_DIFF.patch), [test diff](TESTS_DIFF.patch), [driver diff](DRIVER_DIFF.patch). Старые test/browser drivers адаптированы только к новому download/ZIP, их широкие workflows не запускались; AST parse PASS. Чужие изменения и исторические документы/отчёты сохранены. Добавлена [глава 33](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/33_Manual_Analysis_Archive.md).

ZIP собирается в памяти из существующих verified export files под project operation guard. GET ничего не записывает и не запускает. При single/multipart удалены только presentation headers частей и старая краткая ссылка-инструкция; Exact payload / return skeleton побайтово сохраняют данные и bindings. Части соединяются в исходном UTF-8 порядке без обрезки; ограничение 20 MiB остаётся. Проверяются index и все parts hashes, exact current binding. В ZIP два фиксированных инертных MD, без путей/имён из документов, execute bit отсутствует. Secret/restricted policy и старый MD/parts API сохранены. Browser POST не повторяется автоматически, binary GET использует существующую очередь и разбирает JSON-ошибки в форму; неправильный MIME отвергается.

## Только целевые проверки

**5 уникальных новых методов PASS** по одному final runtime/wheel, без повторения уже прошедших методов: [итоговая matrix](FINAL_RESULTS.json), [первая команда/log](wheel-tests.run.json), [исправленный один метод](wheel-focused.run.json), [среда](WHEEL_ENVIRONMENT.json). Independent installed wheel вне source tree, пустой PYTHONPATH, Windows 11 x64/CPython 3.14.10, Flask 3.1.3/Waitress 3.0.2/Playwright 1.64.1, настоящий TCP и headless Edge. Package inventory совпал с final source.

Проверены ZIP/CRC/два фиксированных файла, полный exact payload и skeleton, GET read-only/replay, настоящий multipart с большим русским документом без потерь UTF-8, tamper/stale/foreign Origin отказ, одно нажатие → одно скачивание, отсутствие старого блока/copy buttons/dialogs/JS errors, JSON из архива → strict PREVIEW без commit. Для ошибок ZIP GET и неправильного MIME проверены inline notice, доступная кнопка, отсутствие ложного скачивания и автоматического replay POST. Model/CLI calls 0; reply для проверки preview — объявленный synthetic fixture. [Снимок](output/playwright/one-click-manual-card.png), [sample ZIP hashes](ZIP_SAMPLE.json); синтетические instruction/pack также сохранены распакованными рядом.

Первый run: 4 PASS; один error-path browser case дал FAIL и cleanup ERROR из-за подписи тестового Playwright callback: Request попал в status default argument. Исправлена только callback signature, ожидания и runtime bytes не менялись; повторён только этот метод — PASS. Raw [log первого run](wheel-tests.log) и [focused log](wheel-focused.log) сохранены. В первом log также есть Waitress socket diagnostic при закрытии fixture после stale test; сам stale/read-only метод PASS, runtime из-за этого не менялся.

Docs validator PASS / 0 errors, ожидаемый WARN без архива поставки: [log](docs-validator.log). Source/build/wheel/frozen equality, CRC wheel, docs mirrors/manifests, весь frozen payload включая .pyd и allowed scope — PASS: [integrity](INTEGRITY.json). [Build result](BUILD_RESULT.json), [build command/log](frozen-build.run.json). Существующие project state machines/approvals не менялись.

Для обновления сначала дождались завершения текущей работы: stop helper после 30 секунд получил busy, force stop не использовался. Последующий public stop вернул 200 STOPPING: [diagnostic](STOP_DIAGNOSTIC.json); к установке процесс уже остановлен: [stop](STOP_FOR_UPDATE.json). [Operator upgrade](OPERATOR_UPGRADE.json) PASS, aggregate hashes данных до/после одинаковы, previous version сохранена, --check-package/--doctor exit 0. [Native installer log](installer-native.log), [ярлыки](SHORTCUTS.json). Видимых окон не открывали.

## Артефакты и ограничения

Source digest `{digest}`. Wheel SHA-256 `{wheel}`. UNSIGNED installer SHA-256 `{installer}`. Полные source/docs inventories — [freeze](RUNTIME_FREEZE.json); [evidence index](EVIDENCE_INDEX.json).

Full engine/core regression, вся PH-LW matrix, повторный provider/model analysis, actual installed-EXE browser reacceptance и старые широкие workflows NOT RUN: scope — только ручной архив и его прямые зависимости. Installed EXE проверен по bytes/package/doctor; browser — final installed wheel. Прежние PH-LW/LOCAL_WEB_MANUAL verdicts сохранены в их exact-byte границах. Automatic Task executor disabled / прежний NO-GO, полная v0.5.1 NOT RELEASED. Engine/Documentation delivery ZIP не собирались; `zip_created:false` в build freeze относится к ним. Синтетический manual handoff ZIP создан именно для проверки запрошенной feature, распакованные файлы сохранены.

Следующий разрешённый шаг: открыть Harness через прежний ярлык → «Опрос и GPT» → «Сформировать пакет вручную». Прикрепить ZIP к GPT/Codex. Другие этапы и широкие проверки не выполнять.
'''.format(build=freeze['build_id'],digest=freeze['engine_build_digest'],wheel=freeze['wheel_sha256'],installer=freeze['installer_sha256'])
(OUT/'REPORT.md').write_text(report,'utf-8')
save('FINAL_ATTESTATION.json',{'status':'COMPLETE','build_id':freeze['build_id'],'unique_targeted_methods_passed':5,
    'full_engine_tests':'NOT RUN — manual ZIP scope','model_requests':0,'distribution_zip_created':False,
    'synthetic_manual_zip_created':True,'report_sha256':sha(OUT/'REPORT.md'),'current_task_sha256':sha(current),
    'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256')})
index={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts}
save('EVIDENCE_INDEX.json',{'files':index,'self_hash_omitted':True})
print(json.dumps(load('FINAL_ATTESTATION.json'),ensure_ascii=False,indent=2))
