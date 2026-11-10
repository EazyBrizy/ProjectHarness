# Подключение CLI и упрощение анализа документации

Дата: 2026-11-10. Build `CLI-DOC-ANALYSIS-20261110` установлен в `%LOCALAPPDATA%/Programs/ProjectHarness`; обычный desktop shortcut обновлён. Пользовательские данные и предыдущий build сохранены. Архивы Engine/Documentation не создавались.

## Что изменилось для пользователя

После ZIP во вкладке «Опрос и GPT» доступны два способа:

- «Подключить CLI» → «Анализировать документы через CLI»: документы передаются установленному Codex CLI, прогресс и предложения модели появляются в браузере. Переносить JSON вручную не нужно. Неподключённый CLI проверяется и при прямом нажатии анализа. Есть отмена, восстановление отображения после reload и сообщения об ошибках.
- «Сформировать пакет вручную»: одно нажатие сразу создаёт пакет и ссылки для скачивания. Пользователь передаёт его GPT/Codex и возвращает JSON прежним способом.

Полей категорий каждого документа/черновика больше нет. Новых подтверждений, consent-галочек и локального входа нет. Предложения сначала показаны для просмотра; сохранение в черновик остаётся отдельным содержательным действием. Ответы не назначаются автоматически при загрузке, polling или import.

Подключение сохраняется для всего приложения. Сейчас используется только для документации; автоматизацию Task/Run и файлов создаваемого продукта пользователь явно отложил. Инструкция «если CLI ещё не установлен или требуется вход» раскрывается при необходимости. `codex login` относится к установленному Codex, собственного входа Harness нет.

## Область и архитектура

Входная база `CLEAR-INTERVIEW-20261110` и hashes проверены до редактирования: [baseline](INPUT_BASELINE.json), [plan](IMPLEMENTATION_PLAN.md), [уточнение scope](SCOPE_ADDITION.json), [Git status](GIT_STATUS.before.txt). До начала сохранены source/tests/AGENTS/CURRENT_TASK. Предыдущие изменения в dirty checkout не потеряны. Новое разрешение на CLI-анализ закреплено в AGENTS и [главе 30](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/30_CLI_Document_Analysis.md); прежние specs/reports и глава 29 не переписаны.

Изменены только `local_web_cli.py`, `local_web_cli_analysis.py`, узкие entry points `local_web_service.py` / `local_web_http.py`, direct-export ветка `local_web_exchange.py`, GPT_PREPARATION, interview assets и metadata. `app.js` меняет одну строку объяснения вкладки. Существующие browser drivers адаптированы к отсутствию старой формы категорий; classified API tests сохранены. Также адаптированы obsolete selector interactions в `local_web/windows/final_acceptance.py`: этот широкий driver не запускался; его output hash записан отдельно, dedicated before hash в этом baseline не сохранён. Core schemas/registries, executors, operation guard, accepted history и state machines не менялись. [Точные изменения](CHANGED_FILE_HASHES.json), [runtime diff](SOURCE_DIFF.patch), [test diff](TESTS_DIFF.patch).

Browser → фиксированные service routes → public draft/export/preview APIs. Native `codex.exe` обнаруживается на компьютере, проверяется по SHA-256; paths/argv из HTTP не принимаются. Официальная versioned launcher junction разрешается только при CLI discovery, правила project/upload paths не меняются. Подключение хранит executable/version/hash, без credentials. GET состояния не запускает процессы.

Для анализа используются полные exact pack parts через stdin, фиксированный `exec`, `--ignore-user-config --ignore-rules --ephemeral --sandbox read-only`, отключённые shell/view_image/apps/plugins/skills discovery/web/multi-agent. Нет Task executor или shell/filesystem gateway. Процесс скрыт, shell=False; stdout/stderr, вход, время и сохранённые jobs ограничены. Отмена завершает только собственный дочерний process tree. Перезапуск приложения не повторяет model request. Replay key не создаёт новый запуск; stale документы/ответы и changed executable отвергаются.

Результат проходит прежний strict v2 preview/binding/revision contract. CLI не делает commit, не назначает approvals и не изменяет продуктовые файлы. Direct пакеты честно `UNCLASSIFIED` с `EXPLICIT_ANALYSIS_ACTION` / `NOT_CLASSIFIED_BY_OPERATOR`; не выдумываются PUBLIC/INTERNAL. Secret scan и явно заданная restricted-project policy сохранены. Прежний classified export API доступен без изменений своего входного контракта.

## Целевая проверка

Только новая feature и прямая упаковочная граница; весь движок не запускался. Команды, interpreter, platform, exit, длительность и log hashes сохранены рядом в `*.run.json`.

| Проверка | Результат | Evidence |
|---|---|---|
| Independent installed wheel вне source tree, 8 CLI/HTTP/process + 2 Edge метода | 10 PASS, 0 FAIL/ERROR/SKIP; exit 0 | [команда](wheel-tests.run.json), [log](wheel-tests.log), [среда](WHEEL_ENVIRONMENT.json), [результаты](WHEEL_RESULTS.json) |
| Настоящий native Codex 0.154.0, отдельный синтетический MD | PASS, 1 PREVIEW, draft unchanged; command events 0; unrelated MCP startup false | [команда](native-analysis-03.run.json), [результат](NATIVE_ANALYSIS_RESULT-03.json), [sanitized transport](NATIVE_CLI_TRANSPORT-03.json) |
| Docs validator по распакованному каталогу | PASS, 0 errors; ожидаемый WARN без ZIP | [log](docs-validator.log), [команда](docs-validator.run.json) |
| Source/build/wheel/frozen/installed bytes, docs mirrors, manifests, полный payload включая `.pyd` | PASS | [integrity](INTEGRITY.json), [log](integrity-final.log), [freeze](RUNTIME_FREEZE.json) |
| Frozen и UNSIGNED installer | Собраны из canonical src, package check exit 0 | [build log](frozen-build.log), [build result](BUILD_RESULT.json) |
| Штатная остановка и operator upgrade | PASS, без force kill; package/doctor exit 0; данные и previous version сохранены | [stop](STOP_FOR_UPDATE.json), [upgrade](OPERATOR_UPGRADE.json), [native installer log](installer-native.log), [ярлыки](SHORTCUTS.json) |

Среда wheel: Windows 11 x64 10.0.26200, CPython 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, Playwright 1.64.1 / установленный headless Edge, настоящий TCP. Runtime импортирован из независимой venv site-packages, не из src; package inventory совпал с final source. HTTP/browser tests используют **явный FixtureCli**, не выдаются за разговор с провайдером. Native process method запускает собственные Python children и проверяет UTF-8, timeout, cancel, output bound. Отдельный native positive действительно вызывает установленный Codex; пользовательские uploads не использовались. [Скриншоты](screenshots-wheel/01-two-analysis-choices.png), [результат в браузере](screenshots-wheel/02-cli-result-in-browser.png).

Проверены readonly GET, connect/login failure, unknown fields/foreign Origin, изменённый executable, stale input до запуска, one-click manual/replay/no fabricated classification, output PREVIEW/no commit, busy/cancel, invalid/stale reply, restart interruption/no replay, secret/restricted negatives, browser connect persistence/progress/reload/cancel/result/commit provenance. После source pilot wheel-run выполнен по конкретной причине: новые модули и ресурсы должны работать из поставки. Прошедшие проверки на той же границе без новых изменений не повторялись.

## Предварительные результаты и исправления

Raw logs сохранены, не подменены финальными PASS. Первый source pilot: 3 PASS, 1 FAIL, 2 ERROR. Исправлены Windows extended-path conversion при чтении job records, ошибочный fixture path, contention progress/cancel с project guard; canonical guard для mutation сохранён. Повторяли только затронутые методы. В одном negative assertion уточнён точный существующий код `STALE_EXCHANGE`; ожидание отказа и неизменности черновика сохранено. [Первый run](connection-http-process.run.json), [исправленные cases](corrected-http-cases.run.json), [cancel diagnostic](cancel-concurrency-fixed.run.json), [cancel/restart PASS](cancel-restart-final.run.json), [browser/policy PASS](browser-and-policy.run.json).

Первый actual CLI run не дошёл до модели из-за официального launcher junction; fixed discovery описан выше. Второй дал корректный PREVIEW, но sanitized transport выявил посторонний MCP startup из окружения plugins. Добавлены явные отключения plugins/remote_plugin/skill_search/skill_mcp_dependency_install/shell_snapshot; final03 подтвердил отсутствие этого startup и command events. Не скрывается более узкий критерий PASS второго pilot. В модели проверялся только синтетический учебный проект. [Первый log](native-analysis.log), [второй transport](NATIVE_CLI_TRANSPORT-02.json), [финальный transport](NATIVE_CLI_TRANSPORT-03.json).

Первый integrity helper пропустил `app.js` в локальном allowlist, хотя этот файл изначально разрешён в baseline; проверка остановилась на scope assertion. Allowlist исправлен после просмотра однострочного diff, runtime bytes не менялись. [Исходный FAIL](integrity.run.json), [финальный PASS](integrity-final.run.json). Разовый вывод diff прервался на кодировке консоли; повтор с PYTHONUTF8=1 успешен, файлы не повреждены.

## Артефакты и ограничения

- Source digest: `sha256:ab26e808d3876f52e0f6006865b962de4b953e01b19f2b185629b1cf9e79a851`.
- Wheel SHA-256: `27124f375c4425efea92028aa876bc14ae3c596c76f5e47db114e40974aa1f04`.
- UNSIGNED installer SHA-256: `ffb1f32cab59b4c1aa646ef3178659bf39d0c4ce6e6138680be0a0bcb76ab4a5`.
- Полные inventories и hashes: [freeze](RUNTIME_FREEZE.json), [outputs](OUTPUT_HASHES.json), [evidence index](EVIDENCE_INDEX.json).

Full engine/core regression, полная PH-LW matrix, actual installed-EXE browser reacceptance и все виды provider/model ошибок **NOT RUN**: они не являются обязательной широкой перепроверкой этой feature. Установленный EXE проверен по точным bytes и package/doctor; браузерная feature проверена на final installed wheel. Actual native positive — на final CLI backend из src. Отсутствие CLI/его входа либо лимит провайдера потребуют устранить причину или использовать ручной пакет. Истечение 300 секунд завершает конкретный анализ, не отключает модельные лимиты и не повторяет запрос автоматически.

PH-LW-04/05/12 и LOCAL_WEB_MANUAL: прежние исторические verdicts сохранены в их exact-byte границах, полной новой приёмки нет. Новая CLI_DOCUMENT_ANALYSIS feature — targeted PASS с указанными границами. `AUTOMATIC_EXECUTOR`: disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. Podman/egress/product execution не включались. Никакого перехода к следующим этапам.

Следующий разрешённый шаг: открыть прежний ярлык Harness → «Опрос и GPT» → выбрать CLI-анализ либо ручной пакет. Для дальнейших правок исходников можно использовать прежний ярлык «Project Harness — разработка» и штатный перезапуск без переустановки; обычный installed EXE самостоятельно исходники не обновляет.
