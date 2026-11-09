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
