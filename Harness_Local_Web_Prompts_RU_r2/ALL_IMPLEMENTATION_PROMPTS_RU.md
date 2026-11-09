# Project Harness — все 12 промптов Windows Local Web

Исходная дата: 2026-10-30. Уточнение r2: 2026-11-01 — WIP/NO-GO baseline, без изменения функционального scope. Это задания на будущую реализацию, не выполненный патч. Каждый раздел самодостаточен и выполняется в отдельном диалоге на результатах предыдущего. Архитектура и матрицы находятся в отдельных файлах набора.

## Оглавление

1. PH-LW-01 — Контракт Local Web, карта управления и проверяемая база
2. PH-LW-02 — Нативная Windows-совместимость подготовки и ручного ядра
3. PH-LW-03 — Application service, единый статус и безопасные операции
4. PH-LW-04 — Защищённый локальный веб-сервер и рабочая оболочка интерфейса
5. PH-LW-05 — Безопасная загрузка MD/ZIP и управление источниками
6. PH-LW-06 — Опрос и управляемый обмен с GPT без ручного YAML
7. PH-LW-07 — Отдельные пользовательские согласования и инвалидирование
8. PH-LW-08 — Автоматическая сборка и безопасное размещение проекта
9. PH-LW-09 — Веб-пульт Task/JIT и ручного исполнения
10. PH-LW-10 — Визуальные Stage Gates, планирование, level-up и обслуживание
11. PH-LW-11 — Один Windows-запуск: launcher, self-contained installer и resume
12. PH-LW-12 — Финальная Windows/browser/security приёмка и поставка


---

# PH-LW-01 — Контракт Local Web, карта управления и проверяемая база

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-01

Документы нового companion, карта API/UX, test fixtures/configuration и метаданные. Без нового runtime execution и без UI-макета вместо контракта.

Используй именно WIP snapshots с открытым NO-GO, не называя PH-051-12 успешно принятым. Исходные SHA-256: Engine `c4bd7bd446f926f32ccfe185fe89ede27207ca6ef0998a35ba3c971293b91174`, Documentation `3a5eee4fac314b5ecaec2edb338d64dd26ecddecc3d0e9212fdeff62ca88209a`. Если загруженная база отличается, установи по manifest/отчёту её происхождение, а не называй её совпавшей.

### Требуется

1. Зафиксируй additive спецификацию Windows Local Web: Python/Flask/Waitress, локальные assets, loopback-only, manual mode, один OS-user, без обязательных Python/Node/WSL/Podman у конечного пользователя. Закрепи Windows 11 x64/NTFS как первую проверяемую platform matrix, конкретную поддержанную Python runtime и reproducible dependency lock. UI dependencies отдели от minimal CLI, чтобы консольный пакет не импортировал web framework без необходимости.
2. Инвентаризируй все 26 публичных команд исходного CLI и используемые Python API. Для каждой опиши кнопку/экран, preconditions, read/mutation semantics, formal consent, ожидаемые outcomes, next action и test ID. Включи manual startup, validate/status, tasks, Stage Gate/plan/level-up, maintenance, Brownfield, migration, diagnostics. Automatic commands отображай честно как diagnostic/недоступные на выбранной платформе; никаких «скрытых» переключателей bypass.
3. Проверь фактические схемы. Intake approval `{approved,actor,approved_at,notes}` не подменяй Stage approval DEC/ACT schema. Зафиксируй новый draft-only GPT exchange envelope и UI receipt/version namespaces отдельно от core schemas. Раздели canonical state, derived view model и operation journal.
4. Опиши путь установки и хранения: один per-user offline installer + launcher; app-data отдельно от продукта; imports и intake — непересекающиеся; отсутствие Python относится к подготовке, а не автоматически ко всем будущим продуктовым tests. Выбери один installer tool с официально проверенной Windows non-admin configuration.
5. Зафиксируй HTTP threat model, session bootstrap, Host/Origin/CSRF/CSP, payload budgets, unsafe ZIP/Windows filenames, доверие к документам, opt-in передачи GPT и consent на manual verification commands. UI нельзя выдавать за sandbox от процесса того же пользователя.
6. В test baseline отдельно перечисли унаследованные automatic blockers, applicable manual regressions и новые Windows requirements. Отсутствие Podman не блокирует саму разработку manual companion, но не закрывает полную приёмку v0.5.1. Составь acceptance matrix по `ACCEPTANCE_MATRIX.md`, выдели real Windows/browser build evidence, Linux legacy regressions и прежние Podman NOT RUN. Зафиксируй exact baseline test discovery/результаты доступного прогона, не переписывай исторический счётчик 346 как новый результат.
7. Добавь минимальные golden fixtures без invented evidence: Greenfield single MD, nested MD ZIP, no-doc draft, Brownfield existing repository, accepted-stage/maintenance fixture и untrusted GPT response. Fixture approvals не являются пользовательскими approvals реальных проектов.

### Приёмка

Существует однозначная карта «экран → действие → публичный API → exact context → expected state → тест», package/version strategy и runnable baseline command для development/CI. Все последующие PH-LW могут работать без переизобретения контрактов. Production logic на этом этапе не меняется; выявленные Windows blockers описаны точно, включая `__init__.py/runtime.py/apply.py`, mutating `check_intake`/`next` и destructive `keep_directory`.

Если native Windows стенд недоступен, подготовь исполнимый Windows CI/test entrypoint и укажи NOT RUN; не объявляй Windows compatibility доказанной.

---

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

---

# PH-LW-03 — Application service, единый статус и безопасные операции

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-03

Новый bounded application/service слой Local Web, локальный catalog/operation journal, shared operation guard, точечное подключение CLI/public API к concurrency fence, тесты. Без HTTP и UI.

Создай одну точку, через которую будущий веб-интерфейс вызывает существующие операции Harness. Не строй второе ядро и не копируй governance logic из runtime/stages.

### Требуется

1. Реализуй typed/request-validated service operations по карте PH-LW-01. Используй явную allowlist функций, не `eval/getattr` по произвольному имени и не shell CLI strings. Root разрешается из зарегистрированного project/workspace ID; произвольный абсолютный путь в payload не передаётся напрямую в core.
2. Для provisional input предоставь bounded публичный draft-update API: allowlisted fields, schema validation, revision/fingerprint, atomic update и invalidation draft approvals. HTTP routes впоследствии вызывают его, а не делают самостоятельный `write_data` в control plane.
3. Сделай read-only view model: current core status/route, done/current/blockers/required user action, available actions с disabled_reason и exact refs/revisions. `get_status` не вызывает mutating `check_intake`, `next_task`, recovery или external diagnostics. Если существующий status helper имеет side effect, выдели узкий read-only reader без изменения прежней CLI-семантики.
4. Внешний app-data store хранит catalog, UI receipts и bounded durable operation records. Core остаётся источником состояния. Operation record: action, project ID, payload digest, expected fingerprint, idempotency key, timestamps, фактический result/error refs; без auth/secret values. Не сохраняй полный текст чувствительных документов в debug log.
5. Введи per-project cross-process serialization и повторную проверку fingerprint. UI, CLI и затронутые публичные mutations должны использовать совместимый fence либо безопасно отвергать конфликт до mutation. In-process mutex/disabled button недостаточны. Учитывай nested calls и lock ordering, не вноси deadlock в Stage transactions.
6. Долгие операции выполняются одним bounded local worker, с operation_id и чтением прогресса; не добавляй distributed job queue/remote worker. Duplicate request возвращает ту же операцию; key+иной payload — conflict. После reconnect/browser close работа не должна повторяться.
7. Reconciliation после crash сверяет реальные core transaction/result refs. Committed operation восстанавливает result; uncommitted использует существующий recovery; ambiguous non-idempotent action остаётся BLOCKED/нуждается в проверке. Не повторяй команды verification автоматически, не делай rollback committed state по ошибке UI-log. Cancellation разрешается только до начала mutation или в доказанной safe boundary.

### Приёмка и тесты

Реальные core APIs через сервис, не mocks всего ядра: duplicate next/prepare/action; две вкладки/два процесса; CLI-vs-service race; stale fingerprint; crash до mutation, после core commit до записи UI result; read-only status byte equality; unknown action/path отвергнуты. Ошибки показывают русский текст, stable code и next action, не скрывают WAITING_INPUT как internal failure. Все API paths вне текущего этапа можно зарегистрировать только как недоступные с причиной, но не как false-success stub.

---

# PH-LW-04 — Защищённый локальный веб-сервер и рабочая оболочка интерфейса

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-04

Local Web HTTP/server/auth/assets, command entrypoint `project-harness ui`, интеграция с application service, security/browser tests. Без реализации отсутствующих бизнес-операций в JavaScript.

Подними реальный localhost-интерфейс, который работает из package и не требует Node/npm от пользователя. `project-harness ui` — новая команда этого этапа; не путай её с уже имеющимся baseline CLI.

### Требуется

1. Flask + Waitress, debug/reloader/development server выключены. Listener только `127.0.0.1`, реальный bind до открытия browser, свободный порт выбирается безопасно. Не используй `0.0.0.0`, host auto-discovery, reverse proxy или firewall rule. Ограничения request body/connections/timeouts должны работать и на WSGI уровне: Waitress буферизует request body, одной проверки после `request.files` мало.
2. Реализуй launcher-ready session bootstrap: криптографически случайный одноразовый секрет, короткий срок, обмен на session, безопасное browser open. Не записывай секрет в query/logs/analytics/export. URL fragment допустим с немедленным удалением из history и POST exchange. Проверяй full Host/Origin включая порт, отклоняй unknown Host/Origin и `null` на mutation. Защити session cookies/CSRF, запрети permissive CORS. Не называй localhost достаточной авторизацией.
3. Все project metadata, file previews/downloads и mutations требуют session. Public health не раскрывает пути/версии приватных проектов. Artifact downloads — через opaque ID и membership/root checks, не `?path=C:\...`. Запрет generic filesystem и shell endpoints.
4. HTTP GET только read. Actions — защищённые POST с expected revision/idempotency; polling читает operation ID. Браузерное обновление страницы не запускает intake/next/verify/recovery. Ошибки context/schema/permission возвращают нормальный structured failure, не HTML traceback.
5. CSP для локальных assets, framing запрещён, nosniff/no-referrer, private responses no-store. User/GPT strings выводи как текст; raw HTML/JS, markdown links `javascript:`, внешние изображения и SVG из upload не исполняй. Все CSS/JS/icons/help локальные, без CDN/fonts/telemetry.
6. Создай UI shell с разделами из плана, списком проектов, read-only overview, текущей стадией/target и next action. Ещё не реализованные операции явно disabled. Русские подписи, keyboard navigation, readable focus, text-status кроме цвета, loading/empty/stale/error. Покажи копируемую browser address при неуспешном auto-open без утечки постоянного токена.
7. Добавь package-data для assets и tests запуска из installed wheel вне source tree. Клиент не принимает security решения, доступность действий повторно проверяет сервер.

### Приёмка и обязательные тесты

Реальный HTTP listener + browser test: нет session, cross-origin form/fetch, bad Host/DNS-rebinding header, wrong port, token replay/expired bootstrap, XSS filename/Markdown, path traversal download, GET refresh immutability. Listener не доступен через LAN interface. Проверяй CSP и отсутствие external requests. Security проверяется также против реального Waitress, не только Flask test client. Windows session smoke должен отличаться от Linux smoke в отчёте.

---

# PH-LW-05 — Безопасная загрузка MD/ZIP и управление источниками

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-05

Importer/service/public intake helper, UI «Документы», source snapshot metadata и fixtures. Не добавлять PDF/DOCX/RAR/7z, OCR, внешние URL загрузки или code execution.

Реализуй drag-and-drop/выбор одного или нескольких MD и ZIP с MD, без ручной распаковки/переноса. Исходные файлы пользователя никогда не изменяются.

### Требуется

1. Upload в private quarantine, staged validation, immutable source snapshot с исходным именем, безопасным storage name, relative path, byte size, SHA-256, import revision и extraction provenance. Импорт публикуется целиком после успеха; частично распакованный архив не считается принятым. Повтор byte-identical import идемпотентен, различающийся source — новая revision, не скрытая перезапись.
2. Строго реализуй budgets PH-LW-01 на body, количество entries, размер entry/суммы, глубину, ratio; считай реальные extracted bytes, проверяй CRC/encoding. Unsafe ZIP, encrypted archive и nested ZIP дают ясный reject/unsupported outcome. Не вызывай безусловный `extractall` на недоверенном архиве.
3. Запрети выход за root и Windows-обходы: `..`, absolute/drive-relative/UNC/device paths, slash/backslash ambiguity, ADS `:`, NUL, reserved device names, trailing dots/spaces, case-insensitive/Unicode collisions, symlinks/hardlinks/reparse points/special files. Проверяй destination и parent components; никакого follow links при копировании. Existing upload staging не переиспользуется между проектами.
4. MD читается с явной encoding policy (UTF-8/BOM минимум); неверная кодировка не должна молча портить текст. Неподдержанные вложения, например изображения, перечисляются с причиной; содержимое не извлекается и не исполняется. Опасный archive entry — reject всего ZIP, а не «пропустить и считать безопасным».
5. `.harness`, `AGENTS.md` и любые содержащиеся инструкции не получают control-plane authority. Imported MD — только источник, не активный script/config в продукте. Preview escaped plain text; no network images/HTML.
6. Создание intake использует непересекающиеся imports и workspace, учитывая существующий `start_intake` contract. Для добавления/замены источников позже используй узкий публичный refresh-sources API: inventory/revisions/answers provenance обновляются согласованно; не `start_intake(force=True)` поверх живой сессии.
7. Изменение source snapshot делает старый GPT exchange/approval stale; принятые immutable records не переписываются. После preparation запретить тихую замену accepted input через import: предложить существующий governed route либо явно unsupported.
8. Покажи file list, accepted/skipped/rejected counts, причины, progress и «документы импортированы — анализ ещё не выполнен». Кнопка «Документации нет» сохраняет осознанный ответ и ведёт к опросу без fake source.

### Приёмка

Single MD, несколько MD, nested ZIP с кириллицей и пробелами → valid sources/опрос. Все malicious archive cases отвергнуты без изменения intake/product/history; second upload/restart не плодит копий. Source import не выполняет ни одной repository/product command и не отправляет документы в интернет.

---

# PH-LW-06 — Опрос и управляемый обмен с GPT без ручного YAML

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-06

UI вопросов/ответов, draft APIs, strict exchange schemas/templates, bounded pack exporter/importer, tests. Без provider API и автоматизации браузера ChatGPT.

Автоматизируй всю техническую часть подготовки, сохраняя внешнего GPT как семантического интервьюера. Сервер не должен выдавать распаковку или поиск ключевых слов за готовую архитектуру проекта.

### Требуется

1. Отобрази реальные `QUESTIONS`/readiness через service. Первый смысловой маршрут: наличие документации → основной результат → target до architecture/technology. Known facts показывай с source refs и не спрашивай заново без конфликта; UNKNOWN/material gaps остаются вопросами, UNSURE target остаётся WAITING_DECISION. Missing schema fields не подставляй выдуманными default проектами.
2. Формы сохраняют ответы через public draft-update API с expected revision; `check_intake` вызывается как mutation под guard. Пользователь не редактирует YAML. Покажи diff imported draft и текущих ответов до применения.
3. «Подготовить пакет для GPT»: server-generated TXT/MD-пакет и стартовый prompt с актуальным GPT_PREPARATION template, exact project/export ID, source snapshot digest/revisions, current draft/questions, target/scope constraints и strict return format. Небольшой комплект — один файл. Большой — явные части с оглавлением/count/hashes; ничего не обрезай молча и не называй pack size token estimate точным model limit.
4. Перед export показывай перечень документов, data sensitivity и предупреждение о ручной передаче внешней модели; секретные/неразрешённые данные не экспортируй в обход policy. Сам сервер не отправляет файлы/ключи наружу. «Копировать prompt» и download вызываются явным действием, автоматически в clipboard не писать.
5. Зафиксируй exchange envelope отдельной версии: opaque export/project IDs, input/source revision/digest и `PROJECT_INPUT@4` draft. JSON import обязателен; YAML только через уже поддержанную безопасную схему/парсер. Допустим paste текста в UI. Unknown fields, oversize/deep input, duplicate JSON keys, wrong project/export, stale response отклоняются до mutation.
6. Ответ GPT не может выставлять approvals, принимать Stage, добавлять trusted evidence, включать LOCAL_AUTOMATIC/egress, менять server paths/IDs или назначать actor. В template явно требуй pending/unapproved decisions; подделанные approved fields отвергай с понятным объяснением. Existing UI approvals сохраняются лишь при доказанно unchanged binding, иначе invalidated receipt; не доверять импортированной копии.
7. Содержательные claims сохраняй как draft с provenance, не как verified fact. После schema/readiness validation покажи остающиеся вопросы. Если ответ неверен, сформируй bounded repair prompt с exact errors, не отправляя случайно всё локальное окружение.
8. Обеспечь продолжение после reload/перезапуска, повтор того же ответа без дублирования и отмену import до commit. Убери устаревшие `PROJECT_INPUT@3` инструкции только из актуального browser startup route, не переписывай исторические отчёты.

### Приёмка

Два Greenfield сценария — MD/ZIP и «нет документации» — проходят typed forms/GPT draft exchange без ручного control-plane editing. Test GPT response — явная fixture, не объявляй это реальным общением с моделью. Stale/source-changed/approved:true/wrong-project/unknown-field cases не изменяют сессию; значимые unknowns не становятся READY_FOR_HANDOFF.

---

# PH-LW-07 — Отдельные пользовательские согласования и инвалидирование

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-07

Approval application APIs/receipts и формы intake; точечные validators/draft revision handling. Без auto-approval, новых Stage semantics и изменения строгой PROJECT_INPUT@4 ради UI.

Убери ручное заполнение служебных approval полей, сохранив осознанность каждого решения. Не делай кнопку «одобрить всё» и не принимай слова модели за согласие оператора.

### Требуется

1. Greenfield: отдельные Project Definition, Architecture, Technology и Codex Handoff confirmations. Brownfield/Hybrid: ещё отдельный baseline approval по нормативному порядку. Используй `approvals_for_mode()` и фактическую input schema, не выдумывай Stage DEC/ACT поля в intake.
2. Перед каждым подтверждением покажи именно утверждаемое содержание: scope/constraints/target, architecture, technology, baseline/evidence context либо handoff obligations. Операторское имя/actor задаётся явно один раз и показывается в каждом receipt. Timestamp и canonical fields оформляет server по успешному явному POST; timestamp браузера/actor из GPT не доверяются.
3. Свяжи действие с exact current draft/source revisions и digest утверждаемого предмета. Если core input schema не содержит таких полей, сохраняй versioned companion receipt вне canonical input и проверяй его перед записью фактических schema fields; не добавляй неизвестные поля в strict schema. Receipt — audit binding локального действия, не криптографическая подпись/удостоверение личности.
4. Согласование производится атомарно через service с lock/revision/idempotency. Double click/retry не создаёт новое решение; changed content во второй вкладке делает запрос stale. «На доработку» сохраняет комментарий, сбрасывает только относящееся к актуальному draft approval и переводит к уточнению; accepted historical records не меняются.
5. При изменении источника/существенного draft field invalidation явно показывает, какие pending approvals и почему требуют повторения. Консервативное инвалидирование всех актуальных draft approvals допустимо, тихое сохранение stale approval — нет. Не обнуляй вручную старую accepted history после подготовки.
6. Формы нельзя использовать для обхода validation missing architecture/technology/target/sensitivity. UI submit не должен писать `approved:true` в невалидный subject. Readiness пересчитывается только после успешной mutation, не при GET.
7. Последнее подтверждение содержит явное действие «Подтвердить передачу и подготовить проект». После него разрешена idempotent preparation операция PH-LW-08, но до реализации этого этапа выводится honest pending action, а не fake created project.

### Приёмка и обязательные тесты

Четыре/пять независимых actions, missing one approval, wrong sequence/baseline, source changed, stale fingerprint, forged actor/approved_at от GPT, двойное подтверждение, crash до/после commit. После positive workflow `check_intake` возвращает действительный READY_FOR_HANDOFF; до него ни одного скрытого согласования. Текущие formal Stage/level-up schema tests не изменены.

---

# PH-LW-08 — Автоматическая сборка и безопасное размещение проекта

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-08

Preparation orchestration/public materialization helper, staging/publish/recovery, completion UI, tests. Не менять planner scope, evidence и execution policy.

После действительных согласований мастер сам создаёт проверенный Project Instance и первый JIT. Пользователь не распаковывает ZIP и не переносит `.harness` руками.

### Требуется

1. Используй существующий `prepare_handoff(workspace, output, keep_directory=...)`, но только с новым server-owned staging path. В исходном compiler существующий `keep_directory` удаляется рекурсивно; никогда не передавай сюда пользовательскую живую папку. Защити и ZIP output от перезаписи чужого файла.
2. Подготовка bound к workspace/input/source/approval revisions и engine build. Сразу перед compile перепроверь readiness/current fingerprints. `MANUAL_HANDOFF` по умолчанию; server не включает executor для обхода NO-GO.
3. Compile → validate initial handoff directory/ZIP → validate project → controlled publication в заранее подтверждённую новую директорию. Staging на том же volume для atomic rename, no-clobber destination и durable operation record. Отдельная запись app catalog не делает файл «опубликованным», пока реальный publish не завершён. Cross-volume route либо корректно staged на destination volume, либо rejected с понятным действием.
4. Directory nonempty/existing project/readonly/root collision/unsupported junction — reject до удаления/переноса. Повтор операции с тем же accepted input возвращает существующий verified результат, если он действительно тот же; stale input или другой target directory не становится replay. Не предлагай опасный `force replace` как стандартный UX.
5. Размещай только комплект compiler; local web state, auth/session tokens, original raw uploads, private logs и execution roots не попадают в handoff. Не копируй Engine целиком в каждый продукт вне требуемой существующей portable handoff структуры.
6. Сохрани exactly one first current READY JIT и подробный план только активной стадии. Compiler уже резервирует первую задачу: не создавай второй Run вызовом `next` ради показа кнопки. Если текущий core `next` идемпотентен, проверь это реальным exact-ref тестом. Stage outlines до target остаются outlines.
7. После публикации показывай папку, статус проверки, active/target, Task/Run refs, кнопки «Копировать промпт», «Открыть папку», «Экспортировать ZIP». Open-folder разрешён только на зарегистрированный каталог и без shell string interpolation. Clipboard fallback — доступное выделяемое поле.
8. Различай immutable initial `validate_handoff` и mutable `validate_project_directory`: нельзя после продуктовых изменений бездумно требовать исходный manifest как current validation.

### Приёмка

Single MD и ZIP paths приводят к реальной папке + ZIP + PASS validations + одному JIT без ручных файловых действий. Fault injection до/после compile, validation, rename, catalog commit и reconnect восстанавливается без дублирования/удаления пользовательских данных. Test sentinel в existing destination остаётся byte-identical. Проверки выполняются также на Windows с пробелами/кириллицей и занятыми handles.

---

# PH-LW-09 — Веб-пульт Task/JIT и ручного исполнения

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-09

UI текущей Task/Run, result intake service, verify/complete/block/resume wrappers и tests. Не автоматизировать Codex запуск и не писать отдельный execution engine.

Отобрази все текущие task-level действия так, чтобы оператор мог вручную передать промпт Codex и вернуться в мастер, не вводя runtime команды.

### Требуется

1. Список Work Packages/Tasks с status, dependencies и current-stage fence; future stages только outlines. Current Task показывает цель, acceptance, allowed/forbidden/expected paths, verification plan, exact Task/Run/JIT refs, prompt/context previews. Чтение страницы не создаёт нового Run.
2. «Получить следующую задачу» вызывает существующий `next_task` как idempotent POST, только когда это допускает core route. «Копировать промпт» читает уже закреплённый JIT; не добавляй к нему instructions отключить проверки. Не генерируй заранее все future prompts.
3. Приём Agent Task Result из выбранного файла либо его существующего exact canonical channel. Приватный staged upload → strict schema/run/task/baseline validation → kernel-supported bounded ingestion; не копируй arbitrary JSON прямо в `.harness`. Wrong/stale Run, unknown fields, changed result и чужие refs не разрешаются через name/prefix lookup.
4. Ясно различай «результат агента получен», «независимая проверка PASS» и «Task завершена». `COMPLETED`/exit0/text не завершают задачу. «Проверить» вызывает реальный `verify_current`; «Завершить» — `complete_current` только после его текущих проверок, результат привязан к current product baseline.
5. Manual verification без разрешения на команды не запускает их. Если core требует product commands, покажи точные argv/cwd/timeout и предупреждение «выполнение кода на вашем компьютере, не sandbox», запроси отдельный consent bound к Run и digest команды/плана. Нет persistent «разрешить всё», команды из GPT не исполняются сразу после импорта. Missing product toolchain — ясный prerequisite, без скрытой установки. Никакого generic exec endpoint.
6. Отобрази реальные verification report gates/scope diff/errors; UI не ставит PASS для missing manual checks или других evidence kinds. Сохранить существующий fail-closed и семантический evidence contract, не переписывать его для удобства.
7. Реализуй bounded block/resume формы с reason/resolution, точными blocker refs и current revision. Recovery объясняет следующий шаг. Replay/multi-tab не дублируют Run/evidence/completion; stale completion даёт conflict и обновление view.
8. Активные automatic projects открываются без неявного перевода в manual. На неподдержанном executor возможность запуска недоступна с причиной; внешний manual result не закрывает automatic Run.

### Приёмка

Реальная test Task изменяет продукт через явный fixture external agent, затем UI result→verify→complete→next без private Python editing. Позитивный и failing verification, changed baseline, forbidden write, forged result, control tamper, missing dependencies, no-consent commands, duplicate click покрыты. Запись fixture файла в тесте — действие внешнего исполнителя, не доказательство реального Codex/Podman.

---

# PH-LW-10 — Визуальные Stage Gates, планирование, level-up и обслуживание

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-10

UI/service adapters для существующих Stage/Brownfield/maintenance/migration contracts, ограниченные public preparation helpers для форм, тесты. Не переписывать core governance и не расширять accepted product scope.

Доведи визуальное управление существующим жизненным циклом, чтобы после первой задачи пользователь не возвращался к CLI для каждой границы стадии.

### Требуется

1. Stage overview показывает отдельно target, active, claimed, observed и highest accepted. Источник current-cycle target — canonical Stage State, не historical PROJECT_INPUT. История acceptance/Run/evidence — read-only. UI показывает semantically missing subjects, а не общий зелёный PASS.
2. Stage Gate: вызывай `prepare_stage_approval`, показывай exact current plan/gate/baseline, outcomes/criteria/profile controls/constraints, evidence refs и реальные ошибки. Actor/DEC/approved_at оформляй строго по существующей Stage schema после отдельного пользовательского action. Нельзя выставлять все результаты PASS одной кнопкой, превращать draft в approval автоматически или обходить evidence resolver. Apply через `accept_stage`, failure/BLOCKED остаются реальными.
3. Stage recovery: отдельное действие `resume_stage_gate` с объяснением gaps; обычный Task blocker и Gate blocker не смешивать. Для недостающих evidence используй существующие preparation Tasks или имеющиеся импортные contracts; не создавай «универсальный evidence upload = PASS».
4. Active Stage planning: `prepare_active_stage_plan` → читаемый reviewed-plan editor/import через strict schema → `plan_active_stage`. Exact baseline/target/state/accepted scope видимы; material divergence требует действующего approval, а без material change не навязывай дополнительное несуществующее решение. Планирование только ближайшей active Stage, first READY JIT без дубля.
5. Level-up: форма target и strict existing approval, показ разницы target/accepted. Следующая stage активируется последовательно; target≤accepted/no-op и stale/skip errors отображаются честно. Нет editing canonical target из UI store.
6. Maintenance: создать exact current same-level plan через form/schema, `start_maintenance`, выполнить обычный task lifecycle и `cancel_maintenance` только при допустимых preconditions. Maturity не повышается; accepted history не переписывается. Разрешён небольшой read-only draft preparer, если его действительно нет; не изменяй kernel semantics.
7. Brownfield/Hybrid: явно выбранный existing repository используется read-only на assessment/preparation. `assess_maturity` без repository commands; показать exact ref/revision/digest, unknown gaps и необходимость baseline approval. Нельзя принимать `README beta` за maturity proof. Исходный repository не перезаписывается кнопкой создания; новый подготовленный экземпляр размещается отдельно.
8. Migration: поддержанные версии определяются validator. Покажи план/ограничения, запроси явное подтверждение и вызови `migrate_project`. Default MANUAL_HANDOFF, сохранение immutable inputs/completed Runs/Stage reports и replay. Unsupported project — сообщение, не автоматический repair.
9. Формы покрывают фактически обязательные поля existing reviewed plan/approval schemas; не заставляй оператора добывать private refs/редактировать YAML. Import/export JSON/YAML может быть дополнительным advanced route, а не единственным простым путём. Все действия guard/auth/revision/idempotency из предыдущих этапов.

### Приёмка

Browser/service E2E: Prototype accept→Alpha plan→first READY; accepted target→level-up→nearest Stage; maintenance→complete/cancel permitted route; Brownfield assessment/rejection stale; migration replay. Ни один экран не повышает maturity при missing semantic evidence. Existing PH-F/PH-051 regressions проходят; production изменения только прямые necessities UI adapters.

---

# PH-LW-11 — Один Windows-запуск: launcher, self-contained installer и resume

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-11

Windows launcher/packaging/build scripts, resource discovery, lifecycle/single-instance, installer docs и реальные Windows tests. Не добавлять auto-update cloud service или automatic installation of WSL/Podman.

Упакуй работающий Local Web так, чтобы конечный пользователь не устанавливал Python/Node, не создавал venv и не распаковывал Engine/Documentation вручную.

### Требуется

1. Выпусти реальный `Harness-Setup-win-x64.exe` с frozen application/runtime, всеми dependencies и локальными static/docs/schema/registry assets. Используй один зафиксированный в PH-LW-01 build pipeline; default PyInstaller onedir + per-user installer. Не заменяй EXE файлом `.ps1`, HTML-макетом или ZIP с просьбой пользователю собрать всё самому.
2. Установка обычным пользователем в отдельный app directory; project/app state отдельно. После завершения автоматически открыть launcher/web wizard. Первый экран сразу объясняет MD/ZIP upload и «нет документации». Повторный `Harness.exe`/ярлык открывает последнюю session/project, не создаёт новый intake и не теряет approvals.
3. Один server instance на пользователя: OS-level mutex/lock и authenticated local handshake. Второй запуск открывает существующий процесс безопасно, не доверяет произвольному listener на ожидаемом порту. Порт резервируется реальным bind, другой процесс на порту не убивается. Auth bootstrap не пишется в обычные логи.
4. Без browser/default handler — понятное локальное сообщение и безопасный путь открыть UI вручную. Closing browser не приравнивай к cancellation; «Завершить Harness» проходит drain/check активных mutations и clean stop. Не оставляй бесконтрольные orphan server процессы. Не обещай отменить уже committed kernel action.
5. Проверка целостности package до активации, staged install/version switch, recovery interrupted setup и disk-full. Не перезаписывай live product или `.harness`; uninstall по умолчанию сохраняет проекты и отдельно объясняет app-data cleanup. Не меняй PATH/firewall/ExecutionPolicy без необходимости; не выключай Defender/SmartScreen/UAC. Реальная подпись при наличии signing credentials, иначе честный unsigned status, без обещания отсутствия OS warnings.
6. Работа подготовки после установки offline; не `pip install latest` на машине пользователя, не CDN. Core CLI продолжает работать отдельно. `distribution_root()`/package resources и frozen executable не должны зависеть от CWD/source repo. Не использовать launcher как Python interpreter продуктовых команд.
7. Подготовь reproducible Windows build recipe/CI и список dependency versions/hashes/licenses. Developer CI может иметь Python/packager; это не требование конечному пользователю. Source+wheel+frozen assets byte/contract согласованы.

### Реальная приёмка

Windows 11 x64 VM/host, non-admin, без Python/Node/Podman/WSL на PATH: install→browser→MD import→GPT fixture roundtrip→approvals→project/JIT; затем restart, second launch, port collision, Unicode username/path, offline, readonly/disk-full/interrupted installation. Проверить no external app requests и сохранность проектов при uninstall.

Если нет Windows builder, отдай source/build automation и два ZIP с **WINDOWS_BINARY_NOT_BUILT / NOT_TESTED**. Не создавай фиктивный EXE и не ставь GO. При реальной сборке приложи installer дополнительно к двум ZIP, его SHA-256 и реальные installation/browser logs. Сам build success не заменяет clean-machine test.

---

# PH-LW-12 — Финальная Windows/browser/security приёмка и поставка

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-12

Acceptance tests, прямые release-blocking regressions, operator docs/examples/manifests/packaging. Без нового функционала и изменения прежнего automatic executor verdict.

Выполни конечную приёмку именно доставляемых Engine/Documentation/Windows installer, а не только development tree. Следуй `ACCEPTANCE_MATRIX.md` и CONTROL_MAP; закрывай лишь прямые дефекты этой серии.

### Требуется

1. Прогони все legacy unit/regression tests исходной PH-051-12 на их поддерживаемой платформе и новые PH-LW tests. Повторяй baseline по финальным extracted ZIP/wheel bytes; записывай discovery, команды, exit, counts, skips и причины. Исторические 346 tests не являются заменой текущему discovery. Изолированная Linux suite и native Windows manual/browser suite — разные evidence.
2. На чистой Windows без пользовательского Python/Node/WSL/Podman проверь реальный installer и весь пользовательский путь: single MD; ZIP; no docs; GPT fixture roundtrip; четыре/пять approvals; auto compile/publish; exactly one first JIT; manual task verify/complete; Stage/level-up/maintenance/Brownfield/migration. Запрещены ручные YAML edits, CLI/API shortcuts вместо UI и direct control-plane patching в сквозных acceptance tests. Agent product writes в fixture допустимы и явно помечены как внешнее исполнение.
3. Проверь каждый action из CONTROL_MAP: есть working button/backend либо truthful disabled reason. `status/next` и progress не противоречат canonical state; forward flow не тупиковый. Операторская документация на русском описывает только фактически существующие элементы, скриншоты берутся из настоящего тестового интерфейса.
4. Реальная HTTP/browser security matrix: session/bootstrap replay, Host/Origin/CSRF, XSS sources/GPT/results, cross-project artifact access, download traversal, bounded uploads/ZIP attacks/Windows reparse points, no LAN/CORS/CDN/telemetry, secret/token absence в logs/export. Test client-only checks недостаточны.
5. Fault/replay/concurrency: две вкладки, два процесса и CLI, source/result changed, close/reload, crash до/после kernel commit/publish, interrupted installation. Нет duplicate Run/acceptance/evidence, no overwrite user product; recovery не повторяет commands без consent.
6. Проверь wheel/source/frozen dependencies/resources, schemas/registries exact versions, standalone/embedded docs, checksums/CRC, manifest completeness, true installer architecture. Scan секретов имеет заявленные границы, не «универсальная DLP». Raw uploads/auth roots/операторские данные не входят в distribution.
7. Обнови только текущие README/runbook/examples: первый запуск, MD/ZIP, exchange, approvals, folder/JIT, manual verification consent, состояние/repair/reopen, diagnostic no-Podman. Исторические PH-051 reports не переписывать и не переподписывать.

### Приёмка и решение о готовности

Выдай две независимые строки:
- `LOCAL_WEB_MANUAL: GO/NO-GO` — GO только после actual Windows installer + browser E2E + mandatory security/recovery matrix, без критических NOT RUN.
- `AUTOMATIC_EXECUTOR: прежний NO-GO`, пока отдельная нормативная приёмка v0.5.1 с real Podman/approved egress не закрыта надлежащим образом. Эта серия её не реализует и не переобъявляет.

При недоступности Windows — выпусти честные WIP исходники/два ZIP и NOT TESTED, не выдавай Linux browser test за Windows. При успехе приложи два согласованных ZIP PH_LW_12, настоящий installer и SHA-256 всех трёх, `PH_LW_12_TEST_REPORT.md`, changed-files, acceptance/control/security matrices, логи, platform/build IDs и ограничения. Проверенные файлы после финального прогона не менять кроме добавления отчётов/пересчёта manifests; зафиксируй это в report.
