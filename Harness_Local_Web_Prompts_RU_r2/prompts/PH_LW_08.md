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
