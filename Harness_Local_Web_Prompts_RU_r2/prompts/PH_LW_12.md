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
