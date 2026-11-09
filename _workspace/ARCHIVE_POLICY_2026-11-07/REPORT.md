# Правило архивирования — 2026-11-07

По явному указанию пользователя обязательная сборка Engine/Documentation ZIP после каждого этапа отменена. Все рабочие файлы проекта хранятся в распакованных каталогах; архивы создаются только по явному запросу пользователя для передачи в ChatGPT на анализ, когда это требуется. Старые архивы, inputs, планы/prompts и отчёты сохранены как исторические источники.

В рамках этого задания изменены `AGENTS.md`, корневой README, `_workspace/RUNBOOK.md`, `_workspace/CURRENT_TASK.md`, README Documentation, производные aggregate/index/manifests и побайтовое зеркало docs внутри Engine. Код и входные файлы wheel этим заданием не изменялись. Новые ZIP и wheel не собирались.

## Проверки

Среда: Windows 11, CPython 3.14.10 x64 из `.venv`, PyYAML 6.0.3. [Preflight](preflight.json) содержит interpreter/platform/deps и результат проверки исходных manifests и hashes последней ZIP-пары. В workspace нет Git; состояние до правки зафиксировано в [before_hashes.json](before_hashes.json), исходные версии редактируемых файлов сохранены в `before/`.

| Проверка | Результат | Команда, exit и log |
|---|---|---|
| Синхронизация aggregates/index/manifests и docs mirror без упаковки | PASS, exit 0 | [run](sync.run.json), [log](sync.log) |
| Documentation validator по распакованному каталогу | PASS, exit 0; 35 PASS, 1 WARN | [run](docs_validation.run.json), [log](docs_validation.log), [JSON](docs_validation.json) |
| Оригинальные inputs: CRC/manifests | PASS, exit 0 | [run](inputs.run.json), [log](inputs.log), [JSON](inputs.json) |
| Первая сверка workspace | FAIL, exit 1: параллельная правка кода и ложное распознавание Python-кода как Markdown-ссылки в проверочном скрипте | [run](verify.run.json), [log](verify.log), [hashes](changes.json) |
| Итоговая сверка workspace после исправления разбора Markdown | FAIL, exit 1: параллельные изменения 5 файлов кода/build/resources вне scope и несовпадение с Engine manifest; docs manifest/mirror, реальные ссылки и сохранность архивов — PASS | [run](verify_final.run.json), [log](verify_final.log), [точные input/output hashes](changes_final.json) |
| Core/Windows/browser regressions, wheel build/acceptance | NOT RUN — это задание меняет только документацию; параллельная правка кода не проверяется здесь | Не являются новой runtime acceptance |
| Создание и проверка новой финальной ZIP-пары | NOT RUN — пользователь не запрашивал архивы | Согласно новому правилу |

Единственное предупреждение validator: `ZIP archive: zip path not supplied`. Оно означает, что архив не проверялся; свежий PASS относится к рабочим файлам документации. Исторические `VALIDATION_REPORT.md` и архивные отчёты не переписаны. Точные входные и выходные hashes изменённых файлов перечислены в `changes_final.json`; исходная точка сверки — `before_hashes.json`.

Во время выполнения задания отдельно изменились `pyproject.toml`, `src/project_harness/project_input.py` и добавились `src/project_harness/local_web_exchange_contract.py`, `src/project_harness/resources/local_web/GPT_PREPARATION.md`, `src/project_harness/resources/local_web/gpt_exchange_reply_v2.schema.json` внутри Engine. Эти чужие правки сохранены, не откатывались и не включались в документационную работу; общий workspace PASS не заявляется. Engine manifest обновлён для документации, но проверка параллельного кода и его синхронизация с manifest/build/wheel относятся к заданию, в котором этот код меняется. Это снимок на момент `verify_final.run.json`, а не наблюдение за завершением параллельной работы.

Блокеров для этой правки нет. Прежние verdicts PH-LW-04/05, `LOCAL_WEB_MANUAL`, `AUTOMATIC_EXECUTOR` и полной v0.5.1 не пересматривались. Следующий разрешённый шаг — новое задание пользователя; PH-LW-06 не начинался, automatic executor не включался. Архивы собираются только по отдельному явному запросу пользователя.
