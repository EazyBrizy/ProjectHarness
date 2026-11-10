"""Record the small layout update without rerunning any engine functionality."""
import difflib
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((OUT/'INPUT_BASELINE.json').read_text('utf-8'))
freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
for file in ('VISUAL_RESULT.json','INTEGRITY.json','OPERATOR_UPGRADE.json'):
    assert json.loads((OUT/file).read_text('utf-8'))['status']=='PASS',file
for file in ('docs-validator.run.json','frozen-build.run.json'):
    assert json.loads((OUT/file).read_text('utf-8'))['exit_code']==0,file
changes={n:{'before':baseline['source'][n],'after':h} for n,h in freeze['source_hashes'].items() if baseline['source'][n]!=h}
parts=[]
for n in changes:
    parts.extend(difflib.unified_diff((OUT/'before/src/project_harness'/n).read_text('utf-8').splitlines(True),
        (ENGINE/'src/project_harness'/n).read_text('utf-8').splitlines(True),fromfile='before/'+n,tofile='after/'+n))
(OUT/'SOURCE_DIFF.patch').write_text(''.join(parts),'utf-8')
(OUT/'CHANGED_FILE_HASHES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n','utf-8')
current=ROOT/'_workspace/CURRENT_TASK.md'
text=current.read_text('utf-8');point=text.index('\n\n')+2
entry='''2026-11-10. По заданию пользователя карточки «Автоматически через Codex CLI» и «Вручную через ChatGPT или Codex» в шаге 1 размещены рядом в одной строке; при ширине экрана ≤760 CSS pixels переходят в одну колонку. Только HTML/CSS и build metadata; JS/backend/CLI/packages exchange logic/core/tests не менялись. Build `ANALYSIS-OPTIONS-ROW-20261110` установлен, обычный ярлык обновлён, данные и previous version сохранены. Один visual-check из independent installed wheel в real TCP/headless Edge: 1360/1024/390 pixels PASS, кнопки внутри карточек, нет горизонтальной прокрутки/JS ошибок/dialogs. Полные tests и повторный анализ модели NOT RUN — не нужны для этой правки. Docs/mirrors/manifests/wheel/frozen payload включая .pyd/installed package/doctor PASS. [Отчёт](ANALYSIS_OPTIONS_ROW_2026-11-10/REPORT.md), [freeze](ANALYSIS_OPTIONS_ROW_2026-11-10/RUNTIME_FREEZE.json), [глава 31](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/31_Analysis_Options_Row.md). Actual installed-EXE browser reacceptance NOT RUN; прежние GO остаются в своих exact-byte границах. Automatic Task executor disabled / прежний NO-GO; full v0.5.1 NOT RELEASED; ZIP не создавались. Следующий шаг — открыть Harness через прежний ярлык. Другие этапы и широкие проверки не выполнять.

'''
assert 'ANALYSIS-OPTIONS-ROW-20261110' not in text
current.write_text(text[:point]+entry+text[point:],'utf-8')
report='''# Два способа анализа в одной строке

Дата: 2026-11-10. Задание пользователя — разместить «Автоматически через Codex CLI» и «Вручную через ChatGPT или Codex» рядом в блоке «1. Выберите способ анализа документов».

Готово: две равные колонки с общим заголовком. На экранах ≤760 CSS pixels — одна колонка; кнопки и текст переносятся внутри карточки. Проверка снимков выполнена визуально. [Широкий экран](output/playwright/1360.png), [промежуточный](output/playwright/1024.png), [узкий](output/playwright/390.png).

Изменены только wrapper в index.html, четыре CSS rules для этой группы и build metadata. JavaScript, CLI connection/analysis, содержимое пакетов, API, schemas/registries, core и tests не менялись. [Baseline и разрешённые файлы](INPUT_BASELINE.json), [diff](SOURCE_DIFF.patch), [input/output hashes](CHANGED_FILE_HASHES.json). Входные source/docs/manifests и полный frozen payload включая .pyd проверены до изменений; чужие изменения и старые отчёты сохранены.

## Проверено только изменённое

Один visual-check, 3 viewport: 1360/1024 — карточки рядом с общей верхней границей; 390 — одна колонка. Все кнопки внутри карточек, horizontal overflow отсутствует, page errors/dialogs — 0. Настоящий TCP/headless установленный Edge, независимый installed wheel вне source tree с пустым PYTHONPATH; package inventory совпал с final source. Команда, среда, зависимости и geometry: [run](visual-check.run.json), [log](visual-check.log), [результат](VISUAL_RESULT.json). Формальные regression tests для этой малой правки не добавлялись и не запускались; model/CLI analysis повторно не вызывался.

Docs validator — PASS, 0 errors, ожидаемый WARN без ZIP: [log](docs-validator.log). Standalone/embedded/frozen docs побайтово совпали, manifests/wheel CRC/source-build-frozen equality/package payload including .pyd — PASS: [integrity](INTEGRITY.json). Проверка scope подтверждает изменение только трёх разрешённых source files, unchanged tests и сохранение старой документации; добавлена [глава 31](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/31_Analysis_Options_Row.md).

Frozen/UNSIGNED installer собраны из canonical src: [build result](BUILD_RESULT.json), [команда](frozen-build.run.json). Приложение завершено штатным public POST без force kill: [stop](STOP_FOR_UPDATE.json). Новая версия установлена по стандартному пользовательскому пути; данные и предыдущая версия сохранены; --check-package/--doctor exit 0, видимый браузер не запускался: [upgrade](OPERATOR_UPGRADE.json), [native installer log](installer-native.log), [ярлыки](SHORTCUTS.json).

## Exact bytes и границы результата

Build `{build_id}`. Source digest `{digest}`. Wheel SHA-256 `{wheel}`. UNSIGNED installer SHA-256 `{installer}`. Полные source/docs inventories — [freeze](RUNTIME_FREEZE.json); evidence hashes — [index](EVIDENCE_INDEX.json).

Full engine/core regression, CLI workflow tests, model analysis, полная PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN: scope только размещение карточек. Installed EXE проверен по bytes/package/doctor; визуальное evidence — final installed wheel. Это не новый полный PH-LW или LOCAL_WEB_MANUAL verdict. Их прежние GO сохраняют exact-byte границы. Automatic Task executor disabled / прежний NO-GO, full v0.5.1 NOT RELEASED. ZIP не создавались.

Следующий разрешённый шаг: открыть Harness через прежний ярлык → «Опрос и GPT»; карточки способов анализа находятся рядом. Другие этапы и широкие проверки не выполнять.
'''.format(build_id=freeze['build_id'],digest=freeze['engine_build_digest'],wheel=freeze['wheel_sha256'],installer=freeze['installer_sha256'])
(OUT/'REPORT.md').write_text(report,'utf-8')
attestation={'status':'COMPLETE','build_id':freeze['build_id'],'layout':'PASS at 1360/1024/390',
    'full_engine_tests':'NOT RUN — layout-only scope','model_requests':0,'zip_created':False,
    'report_sha256':sha(OUT/'REPORT.md'),'current_task_sha256':sha(current),
    'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256')}
(OUT/'FINAL_ATTESTATION.json').write_text(json.dumps(attestation,ensure_ascii=False,indent=2)+'\n','utf-8')
index={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts}
(OUT/'EVIDENCE_INDEX.json').write_text(json.dumps({'files':index,'self_hash_omitted':True},ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(attestation,ensure_ascii=False,indent=2))
