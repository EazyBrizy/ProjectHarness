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
