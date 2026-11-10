# Локальный вход удалён; только целевые проверки

Дата: 2026-11-09. Build `NO-LOCAL-LOGIN-20261109` установлен в `%LOCALAPPDATA%/Programs/ProjectHarness`.

## Результат

Удалены формы входа/выхода, bootstrap-коды, LocalWebAuth, session store/TTL, auth cookies, CSRF headers/checks, session routes и DPAPI/challenge-response launcher channel. Обычный loopback URL сразу открывает интерфейс. `/api/session`, `/api/session/bootstrap`, `/api/session/logout` возвращают 404. Instance discovery хранит только PID/port; старый private record выводится из использования. Exact Host/Origin/port, loopback binding, operation guard, schemas, revision/replay и проектные approvals сохранены. Правило изменения auth-контракта явно записано в AGENTS.md и [главе 26](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/26_No_Local_Login.md); исторические нормы и отчёты сохранены.

Обычный desktop shortcut указывает на новую установленную сборку. «Project Harness — разработка» использует canonical src и не требует переустановки для последующих source changes. [Проверка ярлыков](SHORTCUTS.json). [Обновление пользователя](OPERATOR_UPGRADE.json): exit 0, прежняя версия сохранена, aggregate hashes app-data/projects до и после одинаковы; `--check-package` и `--doctor` exit 0. Проверочные серверы остановлены, видимых окон браузера не открывали. Для работы открыть привычный ярлык; коды и пароли не нужны.

## Правило проверок — прямое указание пользователя

**Проверяем только то, что меняем, и доказанные прямые зависимости. Весь движок раз за разом не проверяем. Полный прогон — только по отдельному явному запросу пользователя.** Уже прошедшие проверки без новых изменений или конкретной причины не повторяем. Зафиксировано в AGENTS.md, CURRENT_TASK.md, RUNBOOK.md и [главе 27](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/27_Targeted_Verification.md), включая embedded mirror. Это указание имеет приоритет над прежними широкими командами в исторических планах/prompts.

## Целевые проверки финальных bytes

| Проверка | Результат | Evidence |
|---|---|---|
| Изменённый HTTP contract и instance discovery, installed wheel вне source tree | 7 PASS, 0 FAIL/ERROR/SKIP | [log/command](targeted-wheel.run.json), [results](WHEEL_RESULTS.json) |
| Direct entry, ZIP import/feedback, active document controls, missing fields, cookie clear/reload/new tab, service restart | Actual installed EXE: 12 PASS, 0 FAIL/ERROR/SKIP | [results](installed-exe/RESULT.json), [browser log](installed-exe/browser.log), [command](installed-exe-tests.run.json) |
| Source pythonw launcher, second launch plain URL, restart, legacy record retirement, direct stop | PASS, isolated fixture | [results](LAUNCHER_SMOKE.json), [command](launcher-smoke.run.json) |
| Updated source/build/wheel/frozen bytes, full payload including .pyd, mirrors/manifests | PASS | [integrity](INTEGRITY.json), [freeze](RUNTIME_FREEZE.json) |
| Updated documentation, including targeted-verification rule | PASS; expected warning: ZIP not supplied | [result](DOCS_FINAL.json), [command](docs-final.run.json) |

Windows 11 x64/NTFS/non-admin; CPython 3.14.10; Flask 3.1.3; Waitress 3.0.2; headless Edge over real TCP. Build tools/pins/commands: [final build](frozen-build-final.run.json), [BUILD_RESULT](BUILD_RESULT.json). Browser tests used only synthetic documents, isolated roots and a sanitized installed-process PATH. [Screenshots](installed-exe/screenshots/direct-documents.png).

## Preliminary runs и ограничения

`initial-http-ui`: 37 PASS на предварительных bytes, не финальная приёмка. `source-local-web` и `wheel-tests` — широкие предварительные runs, остановлены; raw logs/exit сохранены. Их результаты не засчитаны финальной matrix. Obsolete CSRF-negative expectations заменены в связи с явным удалением auth-контракта; Host/Origin, schema, replay и business negatives сохранены. Выявленная ошибка instance record (`ensure_native_path` без `file_ok=True`) исправлена; [focused regression](instance-fixed.run.json), финальные wheel/EXE/launcher checks PASS. В широком candidate был PH-LW-08 browser FAIL без завершённого traceback/report; причина не исследована после сужения scope пользователем, не объявлена исправленной. Этот run не даёт нового full-manual verdict. [Решение о сужении scope](TARGETED_SCOPE_DECISION.json).

PH-LW-04: целевые проверки нового direct-access contract PASS, прежний auth contract отменён пользователем. PH-LW-05: затронутый upload/UI path PASS. Полная новая PH-LW matrix и LOCAL_WEB_MANUAL: NOT RUN; исторические GO относятся к прежним exact bytes. AUTOMATIC_EXECUTOR disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. Clean machine, physical offline, actual Unicode username, real disk-full, visible default-browser launch и EXE timing-latch injection не выполнялись. Engine/Documentation ZIP не создавались.

## Hashes и scope

- Source digest: `sha256:1ec51e8fdb4e585749cd8f884d9dabbc7df0f56ca5936b8b7a0155e1f1612e86`.
- Wheel SHA-256: `b6da0166d7e07b7a3457a7230555c558d9764a44a74405d7f21450abe17e47d5`.
- Installer SHA-256: `f6e0bdbe6b8e0ab9de338ca3dd06c020db4c16477fcb292ca3369d2ba58469f4`.
- PACKAGE_FILES SHA-256: `19ddb73aa49656350831f4c858e4b226697f06c79c0f582b3bdf719b05fd3e68`.
- [Input baseline](INPUT_BASELINE.json), [scope addendum](SCOPE_ADDENDUM.json), [final changed hashes](FINAL_CHANGED_FILE_HASHES.json), [diff относительно сохранённой базы](FINAL_CODE_AND_TEST_DIFF.patch).

Изменены только auth/entry runtime paths, связанные tests/drivers, инструкции/операторские главы и generated artifacts. Остальной runtime/core, прежние тесты вне auth-affected списка и историческая документация сохранены; это проверено по baseline hashes. Чужие исходные изменения не отменялись. Дальше — использовать приложение; другие этапы и широкие прогоны не запускать самостоятельно.
