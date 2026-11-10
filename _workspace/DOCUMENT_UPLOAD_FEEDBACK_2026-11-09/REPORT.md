# Понятная загрузка документации — 2026-11-09

Исправление **PASS в целевом scope**. Новый build `DOC-UPLOAD-UX-20261109` установлен в стандартный пользовательский каталог. Ярлык `Project Harness` указывает на новую версию. Приложение после обновления не запускалось; новых видимых окон браузера не открывалось.

## Проблема и изменение

Выбор ZIP сам по себе не отправлял файл. До создания intake кнопка импорта оставалась недоступной без объяснения. После импорта существовала текстовая сводка, но не было явной кнопки следующего шага.

Форма теперь показывает три шага: создать/выбрать проект, выбрать и импортировать документы, перейти к опросу. Выбор файла до создания проекта сохраняется и сопровождается инструкцией. Статусы различают выбранные файлы, передачу, серверную проверку, успешный импорт и ошибку. Завершение передачи не считается успешной проверкой. Кнопки импорта и перехода выделены; можно снять выбор файлов. «Перейти к опросу и GPT» доступна после сохранённых MD или явного ответа «Документации нет», при отсутствии неимпортированного выбора.

Успешный статус после reload выводится из read-only inventory. Повторный импорт сообщает об уже загруженных файлах; опасный ZIP не заменяет прежние источники. Потеря ответа после commit показывает неизвестный результат и предлагает перечитать состояние; автоматического повторного POST нет. При переходе между проектами список/preview и доступность продолжения соответствуют выбранному проекту.

Изменены только `resources/local_web/assets/app.js`, `index.html`, `app.css` и build identity/digest в `metadata_v1.json`. Backend importer, public Engine APIs, canonical states, schemas, registries и HTTP admission не менялись. Новые tests/EXE driver, операторская глава 24, generated docs index/mirrors, wheel/frozen/installer/manifests и этот evidence составляют остальные изменения. Область зафиксирована до runtime edits в [BASELINE.json](BASELINE.json).

## База и точные bytes

Git HEAD на входе: `f2d8cc16cf311b0f6fd5e86cb699319c25e7cec8`. Принятая FIX5: source digest `sha256:0789035971ad3488b37a3d1cc480a9c7c63effcc3c67c540630e452b77f936ae`, wheel `22ce3cdca5fe875430d4780f163975ba896c3348fa2f30b5a88199064bec54a1`, installer `a4c7432852aadf93fd19fa4646ef8306854369be8ff8fd941ce6d1d268cc5964`. До изменений прошли прежняя read-only integrity и repository preflight. [Входные hashes](INPUT_HASHES.json), [сохранённый CURRENT_TASK](CURRENT_TASK.before.md), [baseline integrity log](baseline-integrity.log).

Новый source digest: `sha256:629263b3719a325337b976402d37bfad8d3ef369a9d531eb937373d77c499386`.

| Артефакт | SHA-256 |
|---|---|
| Wheel | `a0b41b1067b46d24ee506b86c9f8ccfcc49b5d7032c4e4acf67513005f2dfc1d` |
| UNSIGNED installer | `f90a108596eadf321bfa79c660b2cc39b6a8301833739fe863aebae10a2ba591` |
| Frozen PACKAGE_FILES | `2c2942c13d0bb7dfcf55903dbd5db315b02bf2f74b9a0666bbc179b781c8382f` |

[RUNTIME_FREEZE.json](RUNTIME_FREEZE.json) содержит полные source/docs hashes. [CHANGED_INPUT_HASHES.json](CHANGED_INPUT_HASHES.json) и [CODE_DIFF.patch](CODE_DIFF.patch) связывают before/after. Прежние installer, wheel и frozen bundle сохранены обычными файлами в `_scratch/document_upload_feedback_20261109/before-publication/`; исторические acceptance reports, архивы и inputs не менялись. Engine/Documentation ZIP не создавались.

## Проверки

Настоящий Windows 11 x64, build 26200, NTFS, non-admin; CPython 3.14.10 x64. Pinned Flask 3.1.3 / Waitress 3.0.2; Playwright 1.64.1 и установленный headless Edge. Wheel установлен offline в новую независимую venv с hash-locked runtime/dev dependencies; CWD — отдельный Unicode каталог, PYTHONPATH пуст. EXE установлен настоящим Inno installer в fixture-каталог и запущен с PATH без developer tools. Системные настройки не менялись.

| Run | Результат | Evidence |
|---|---|---|
| Source UI/import/security regression | 29 PASS / 0 FAIL / 0 SKIP; до последнего оформления кнопок | [log](source-ui-final.log), [command/environment/exit](source-ui-final.run.json) |
| Финальный installed wheel: новые UI scenarios + PH-LW-04/05/06 regressions | **50 PASS / 0 FAIL / 0 ERROR / 0 SKIP** | [log](wheel-tests-final.log), [run](wheel-tests-final.run.json), [matrix summary](WHEEL_TEST_RESULTS.json) |
| Actual installed EXE: выбор до проекта, импорт/переход, reload/replay/смена проекта, malicious ZIP/retry, no-doc, lost response recovery | **5 PASS / 0 FAIL / 0 ERROR / 0 SKIP** | [run](installed-exe-final.run.json), [actual result](INSTALLED_EXE_RESULT.json), [browser log](installed-exe-browser.log) |
| Installed console doctor/help/launcher/loopback health + bind assertion | PASS, exit 0 | [log](wheel-launcher-recheck.log), [run](wheel-launcher-recheck.run.json) |
| Документационный validator | PASS; 36 checks, 0 errors; ожидаемый WARN без ZIP | [result](DOC_VALIDATION_FINAL.json), [run](docs-final.run.json) |
| Source/build/wheel/frozen, полная frozen payload включая `.pyd`, docs mirrors и manifests | PASS | [INTEGRITY.json](INTEGRITY.json) |
| Обновление пользовательской установки, package/doctor, сохранность данных и прежней версии | PASS, installer/package/doctor exit 0 | [OPERATOR_UPGRADE.json](OPERATOR_UPGRADE.json), [run](operator-upgrade.run.json) |

Новые tests проверяют также недоступность следующего шага при выбранных, но ещё не импортированных файлах, отсутствие внешних browser requests, неизменную revision после rejected ZIP и отсутствие второго POST после потери ответа. Тест завершения передачи использует только timing latch перед настоящим importer: он выполнен на source/wheel; против EXE этот инструментированный timing case отдельно **NOT RUN**. Остальные пять scenarios используют реальные TCP/Waitress/Edge и тот же final EXE.

Ранние попытки сохранены: `source-ui.log` — FAIL одного нового test expectation (`NONE` закономерно создаёт revision 1, тест ошибочно ожидал 0); исправлен fixture expectation, проверки источников не ослаблены. `wheel-acceptance.log` — FAIL launcher preflight, поскольку пользователь запустил свой FIX5 и занял SID mutex; runtime tests этой попытки не запускались. После штатного завершения пользователем выполнен отдельный успешный launcher recheck. Первый `windows-build` собран до финального оформления и не использован для установки/приёмки; финальный `windows-build-final` проверен на byte equality с source. Первоначальные FAIL и команды/exit сохранены, не заменены PASS.

## Установка и пределы результата

Обновлён `C:\Users\gvenv\AppData\Local\Programs\ProjectHarness`, текущий build `DOC-UPLOAD-UX-20261109`. Старый FIX5 сохранён в `versions`. Перед/после установки сравнены агрегированные hashes пользовательского app-data и default project roots; различий нет. Приватные uploads/auth и их содержимое в evidence не публиковались. Desktop shortcut указывает на новый `Harness.exe`; `--check-package` и `--doctor` завершились с exit 0. Пользователь может запустить прежний ярлык.

| Verdict | Область |
|---|---|
| Document upload feedback | **PASS**, целевая проверка новой сборки |
| PH-LW-04 / PH-LW-05 | Применимые regressions новой сборки PASS; прежние полные stage verdicts сохраняют привязку к FIX5 |
| PH-LW-12 / LOCAL_WEB_MANUAL | Прежний GO с принятыми ограничениями относится к FIX5; полная повторная matrix нового build **NOT RUN**, этот отчёт её не подменяет |
| AUTOMATIC_EXECUTOR | Прежний NO-GO, disabled |
| Podman / positive governed per-Run egress | Прежний отдельный NO-GO |
| Полная v0.5.1 | NO-GO / NOT RELEASED |

Новых blockers в целевом upload scope нет. Проверка именно пользовательского ZIP не выполнялась: тесты используют synthetic fixtures. Следующий разрешённый шаг — запуск установленного manual companion и работа с документацией. Другие этапы и automatic executor не запускать самостоятельно. `tools/check_repository.py` остаётся exact-Git verifier исторической FIX5; для текущей незакоммиченной правки есть отдельный `python -B tools/document_upload_feedback_checkpoint.py verify`. Это не публикация в Git и не новая полная release acceptance.
