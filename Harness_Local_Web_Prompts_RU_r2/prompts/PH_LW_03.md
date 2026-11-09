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
