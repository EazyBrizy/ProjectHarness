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
