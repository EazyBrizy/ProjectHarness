"""Record presentation-only completion, hashes and navigation; no further tests."""
import difflib
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((OUT/'INPUT_BASELINE.json').read_text('utf-8'))
freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
for name in ('VISUAL_RESULT.json','INTEGRITY.json','OPERATOR_UPGRADE.json'):
    assert json.loads((OUT/name).read_text('utf-8'))['status']=='PASS',name
for name in ('docs-validator.run.json','frozen-build.run.json'):
    assert json.loads((OUT/name).read_text('utf-8'))['exit_code']==0,name
changes={n:{'before':baseline['source'][n],'after':h} for n,h in freeze['source_hashes'].items() if baseline['source'][n]!=h}
parts=[]
for name in changes:
    parts.extend(difflib.unified_diff((OUT/'before/src/project_harness'/name).read_text('utf-8').splitlines(True),
        (ENGINE/'src/project_harness'/name).read_text('utf-8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
(OUT/'SOURCE_DIFF.patch').write_text(''.join(parts),'utf-8')
(OUT/'CHANGED_FILE_HASHES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n','utf-8')
current=ROOT/'_workspace/CURRENT_TASK.md';text=current.read_text('utf-8');point=text.index('\n\n')+2
entry='''2026-11-10. По заданию пользователя рабочая область «Опрос и GPT» занимает всю доступную ширину; кнопки CLI в одной строке, основная — «Анализировать через CLI». После подключения кнопка показывает «Подключено» с зелёной галочкой, инструкция скрыта. Пустая стартовая подсказка убрана, реальные job statuses сохранены; внизу карточки мелким серым шрифтом «На выполнение расходуются токены агента.». Изменены только HTML/CSS/interview.js presentation и metadata. Backend/CLI invocation/core/schemas/tests не менялись. Build `CLI-CARD-PRESENTATION-20261110` установлен, обычный ярлык обновлён, данные и previous version сохранены. Один целевой real TCP/headless Edge run из independent installed wheel: ширина и кнопки на 1920/1360/1024/390 pixels, disconnected→connected→reload→failed recheck PASS; явный FixtureCli только для connection probes, analysis/model requests 0, JS errors/dialogs 0. Полный движок/core/PH-LW matrix и model analysis NOT RUN. Docs/mirrors/manifests/wheel/frozen payload включая .pyd/installed package/doctor PASS. [Отчёт](CLI_CARD_PRESENTATION_2026-11-10/REPORT.md), [freeze](CLI_CARD_PRESENTATION_2026-11-10/RUNTIME_FREEZE.json), [глава 32](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/32_CLI_Card_Presentation.md). Actual installed-EXE browser reacceptance NOT RUN, прежние GO в своих exact-byte границах. Automatic Task executor disabled / прежний NO-GO; full v0.5.1 NOT RELEASED; ZIP не создавались. Следующий шаг — открыть Harness через прежний ярлык. Другие этапы и широкие прогоны не выполнять.

'''
assert 'CLI-CARD-PRESENTATION-20261110' not in text
current.write_text(text[:point]+entry+text[point:],'utf-8')
report='''# Рабочая область и карточка CLI

Дата: 2026-11-10. Выполнены все изменения представления из задания пользователя:

- «Опрос и GPT» занимает всю доступную ширину с сохранением навигации и обычных отступов; max-width других разделов не меняется.
- Кнопки CLI находятся в одной строке. Основная кнопка — «Анализировать через CLI».
- Подключённый CLI: кнопка «Подключено» с зелёной галочкой, инструкция подключения скрыта. Повторная проверка по нажатию сохранена. При ошибке показаны реальные сообщение/состояние, снова доступна инструкция.
- Удалена пустая стартовая подсказка «После запуска результат анализа появится здесь, без скачивания пакета и копирования JSON.». Реальные сообщения активного/завершённого анализа и ошибок сохранены.
- Внизу карточки текст «На выполнение расходуются токены агента.» серым шрифтом 12px.

Build `{build_id}` установлен по стандартному пути, обычный desktop shortcut обновлён. Данные и предыдущая версия сохранены. Новых подтверждений и local login нет.

## Scope и изменения

Только index.html, app.css, renderCliState в interview.js и build metadata: [baseline/allowed changes](INPUT_BASELINE.json), [diff](SOURCE_DIFF.patch), [input/output hashes](CHANGED_FILE_HASHES.json). До изменений проверены source/docs/manifests и полный frozen payload включая .pyd. Backend/CLI process logic, HTTP/API, packs, schemas/registries/core и test files не менялись. Чужие изменения сохранены. Добавлена [глава 32](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/32_CLI_Card_Presentation.md), прежние docs/reports сохранены.

## Только целевая проверка

Один presentation run в настоящем headless Edge/TCP, final installed wheel из независимой venv вне source tree, пустой PYTHONPATH. Windows 11 x64 / CPython 3.14.10, Flask 3.1.3 / Waitress 3.0.2 / Playwright 1.64.1. Package inventory совпал с final source. [Команда/interpreter/exit/log hash](visual-check.run.json), [среда/geometry/states](VISUAL_RESULT.json), [log](visual-check.log).

1920/1360/1024/390 CSS pixels: рабочая область заполняет main, main занимает всю доступную ширину после sidebar, кнопки остаются в одной строке и внутри карточек, horizontal overflow отсутствует. На 1920 ширина main 1665px, panel 1555px после стандартных отступов. Проверены disconnected label/help, hidden idle status, exact note; затем connected label/green check/hidden help, reload без новых probes, failed recheck с восстановлением инструкции. JS errors/dialogs 0. **PASS.** В connection шагах использован явно обозначенный FixtureCli; настоящий CLI/провайдер не запускались, analysis/model requests 0. Новые formal regression tests не добавлялись, прежние workflow suites повторно не запускались.

Снимки просмотрены визуально: [подключённый CLI, 1920](output/playwright/connected-1920.png), [до подключения, 1360](output/playwright/disconnected-1360.png), [узкий экран](output/playwright/disconnected-390.png). Рабочие сообщения анализа не заменены пустым placeholder: сообщение выводится при наличии job_id, скрывается только пустое состояние.

Docs validator PASS / 0 errors, ожидаемый WARN без ZIP: [log](docs-validator.log). Source/build/wheel/frozen bytes, CRC wheel, docs mirrors/manifests, весь frozen payload включая .pyd и allowed scope / unchanged tests — PASS: [integrity](INTEGRITY.json). Frozen/UNSIGNED installer собраны из canonical src: [build result](BUILD_RESULT.json), [build run](frozen-build.run.json).

Приложение остановлено штатным public POST, без force kill: [stop](STOP_FOR_UPDATE.json). Operator upgrade PASS, hashes app-data/project roots до/после одинаковы; предыдущая версия сохранена; --check-package и --doctor exit 0: [upgrade](OPERATOR_UPGRADE.json), [native installer log](installer-native.log), [ярлыки](SHORTCUTS.json). Видимый браузер не открывался.

## Exact bytes и ограничения

Source digest `{digest}`. Wheel SHA-256 `{wheel}`. UNSIGNED installer SHA-256 `{installer}`. Полные source/docs inventories — [freeze](RUNTIME_FREEZE.json), hashes evidence — [index](EVIDENCE_INDEX.json).

Full engine/core regression, полная PH-LW matrix, повторный CLI/model analysis и actual installed-EXE browser reacceptance **NOT RUN**: scope этой правки только представление. Installed EXE подтверждён по bytes/package/doctor, browser evidence — final installed wheel. Старые PH-LW/LOCAL_WEB_MANUAL verdicts остаются в своих exact-byte границах. Automatic Task executor disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. ZIP не создавались, другие этапы не включались.

Следующий разрешённый шаг: открыть Harness через прежний ярлык → «Опрос и GPT». Другие этапы и широкие проверки не выполнять.
'''.format(build_id=freeze['build_id'],digest=freeze['engine_build_digest'],wheel=freeze['wheel_sha256'],installer=freeze['installer_sha256'])
(OUT/'REPORT.md').write_text(report,'utf-8')
attestation={'status':'COMPLETE','build_id':freeze['build_id'],'presentation':'PASS: four widths and connection states',
    'full_engine_tests':'NOT RUN — presentation-only scope','model_requests':0,'zip_created':False,
    'report_sha256':sha(OUT/'REPORT.md'),'current_task_sha256':sha(current),
    'engine_manifest_sha256':sha(ENGINE/'MANIFEST.sha256')}
(OUT/'FINAL_ATTESTATION.json').write_text(json.dumps(attestation,ensure_ascii=False,indent=2)+'\n','utf-8')
index={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts}
(OUT/'EVIDENCE_INDEX.json').write_text(json.dumps({'files':index,'self_hash_omitted':True},ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(attestation,ensure_ascii=False,indent=2))
