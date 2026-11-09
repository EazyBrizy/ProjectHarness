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
