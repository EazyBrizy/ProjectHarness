# PH-LW-02 — Нативная Windows-совместимость подготовки и ручного ядра

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-02

`__init__.py`, точечные imports/capability boundaries CLI/runtime/apply/execution roots; минимально необходимые path/atomic I/O helpers; тесты Windows и сохранения Linux semantics. Не портировать rootless executor на host Windows.

Устрани блокировку manual/preparation CLI и API из-за Linux-only imports. Само отсутствие `fcntl` не повод выключать безопасность или делать `flock = no-op`.

### Требуется

1. Проверь весь import graph, начиная с `import project_harness`, а не только `cli.py`. Изолируй optional automatic imports так, чтобы `doctor`, intake, prepare, validation, status и manual lifecycle были доступны на Windows без Podman/WSL. Для неподдержанного automatic operation верни структурированный unavailable/BLOCKED с причиной; не запускай host agent и не фальсифицируй sandbox PASS.
2. Проверь реальные Windows semantics путей: кириллица/пробелы, drive-relative/UNC/device forms, path containment, CRLF/UTF-8, tempfile/reopen/delete, case-insensitive collisions, file handles при replace, read-only files. Не меняй immutable content/refs для «нормализации». Не поддерживаемые roots отклоняй до записи с объяснением.
3. Там, где manual flow использует Linux-only filesystem assumptions, добавь минимальный проверяемый platform backend. Atomic publication/recovery остаются действительными; shared Windows locking должен быть настоящим OS-level lock. Не переносить Linux agent mounts, `geteuid`, UID validation или apply sandbox semantics на Windows фиктивными эквивалентами. Automatic apply остаётся изолированным unsupported route.
4. Сохрани Stage transaction recovery и all-old/all-new для затронутых операций. Windows `fsync`/replace и долгоживущие handles проверяй явно; не заявляй power-loss durability сильнее фактического теста. Не глуши все `OSError` ради зелёного теста.
5. Прогони manual Greenfield `start_intake → check_intake → prepare_handoff → validate_handoff → validate_project_directory → next_task`, затем реальный test-fixture task `verify_current → complete_current`. Проверяй структурированные outcomes, не только import success. SDK самого продукта не ставь автоматически и не подменяй frozen launcher Python-интерпретатором продукта.
6. Повтори существующие Stage/assessment/evidence/maintenance regressions на поддерживаемой платформе; запускай всю прежнюю Linux suite, включая automatic unit tests. Раздели genuine Linux-only tests и реальные regressions; массовые Windows skips не считать native support.

### Обязательные отрицательные тесты

Нет Podman/`fcntl` — manual APIs импортируются, automatic operation блокируется; unsafe path/outside root; занятый файл/нет прав; второй процесс не обходит lock; исключение между writes не оставляет смешанную Stage историю. Запрет shell fallback остаётся.

### Приёмка

На реальной Windows работает поддержанный manual/preparation маршрут, ядро не зависит от web assets, Linux regressions сохранены. Без реальной Windows — исходники и тесты могут быть готовы, но результат `WINDOWS_NOT_TESTED`, а не PASS. Не объявляй, что GUI уже реализован.
