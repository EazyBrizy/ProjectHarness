# PH-LW-09 — Task/JIT и ручной цикл исполнения

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-07  

Дополнение по отдельному заданию: поддержанный Task-level manual evidence intake описан в [главе 17](17_PH_LW_09_Task_Manual_Evidence.md). Упоминание отсутствующего intake ниже фиксирует ограничение первого PH-LW-09 checkpoint; актуальный public API и повторная приёмка находятся в новой главе и новом отчёте. Первый NO-GO report сохраняется.

Local Web `0.1.0-dev` предоставляет ручной Task/Run пульт. Фактический verdict и команды проверки находятся в `PH_LW_09_TEST_REPORT.md` и `PH_LW_09_LOGS` Engine. Automatic executor выключен. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; полная v0.5.1 — `NO-GO / NOT RELEASED`. PH-LW-10 не реализуется этим дополнением.

## Работа оператора

1. Выберите опубликованный Project Instance, откройте «Задачи и Run». Проверьте active Stage, Work Packages/Tasks, status и dependencies. Future stages показаны только outlines. Current Task содержит цель, acceptance criteria, allowed/forbidden paths, expected paths, verification plan, exact Task/Run/JIT refs и Context Packet.
2. «Копировать промпт» копирует существующий закреплённый JIT. Передайте его внешнему Codex вручную. Если clipboard недоступен, выделите текст и нажмите Ctrl+C. Открытие/обновление страницы ничего не компилирует. «Получить следующую задачу» — защищённый идемпотентный POST, использующий `next_task`; он не создаёт будущие prompts. После completion ядро может уже закрепить следующий JIT: next вернёт его без нового Run.
3. После фактической работы агента обновите состояние и выберите JSON Agent Task Result, затем «Получить результат из файла». Альтернатива — «Получить из exact canonical channel», если агент записал результат в точный путь текущего Run. Произвольный путь в форме отсутствует. Импорт проходит private staging, strict validation и kernel ingestion. Максимум — 1 MiB, один неизменяемый result на Run.
4. Состояние `RESULT_RECEIVED` означает только получение заявления агента. `COMPLETED` внутри JSON, текст summary и exit code агента не являются independent PASS и не завершают Task. Нажмите «Проверить» для реального `verify_current`.
5. Если план содержит команды, сначала изучите точные argv, абсолютный cwd, timeout и prerequisite. Выполнение кода на вашем компьютере, не sandbox. Отдельный checkbox разрешает только показанный план для exact Run и текущего product baseline. Без него команды не запускаются; command gate остаётся BLOCKED. Согласие сбрасывается после обновления формы. Инструменты продукта не устанавливаются автоматически.
6. Прочитайте фактический report: gates, scope diff, missing paths, stdout/stderr и ошибки. Кнопка «Завершить» доступна после текущего PASS и полученного результата. `complete_current` снова проверяет result digest, фактические изменения и точный post-verification product snapshot. Изменение baseline требует нового чтения и проверки, а изменённый уже принятый result — нового Run.
7. В «Block / resume» укажите причину; для продолжения выберите exact OPEN blocker revision и опишите resolution. Обычный blocker допускает новый Run. Safety/control-plane blocker не допускает in-place resume. Восстановите доверенный handoff/backup согласно core recovery route; UI не снимает safety gate.

## Public API и HTTP

`manual_tasks.task_console` — read-only projection. `validate_manual_result` — read-only admission. `ingest_manual_result`, `verify_manual_task`, `complete_manual_task`, `block_manual_task`, `resume_manual_task`, `next_manual_task` работают под общим project operation guard и вызывают существующий runtime. Kernel пишет result/receipt/phase boundary; HTTP, UI и companion service не редактируют `.harness`.

| Route | Данные и смысл |
|---|---|
| `GET /api/projects/{pid}/tasks` | bounded current-stage view, fingerprint, exact binding, prompt/context/report; без mutation |
| `POST …/tasks/result-upload` | multipart: один `result`, `expected_fingerprint`, `binding_digest`; private staged upload, не completion |
| `POST …/operations` | exact action/payload, expected fingerprint и idempotency key |
| `GET …/operations/{oid}` | read-only status существующей операции |
| `POST …/operations/{oid}/reconcile` | `confirm:true`, явная сверка; команды не повторяются |

Action payloads: `next:{}`; `receive-result:{upload_id,binding_digest}` (`upload_id:null` для canonical channel); `verify:{binding_digest,plan_digest,consent}`; `complete:{binding_digest}`; `block:{run_ref,reason}`; `resume:{blocker_ref,resolution}`. Reason/resolution — 1–4000 символов. Старый service `verify:{}` сохраняет command-disabled режим. Browser использует полный plan-bound payload. Unknown fields, чужие uploads/refs, duplicate JSON keys, nonfinite numbers, stale fingerprint и изменение результата отклоняются. Session, exact Host/Origin/port и CSRF обязательны; generic exec endpoint отсутствует.

`LOCAL_MANUAL_RESULT_RECEIPT_V1` — internal kernel receipt, не новый core status, не цифровая подпись оператора. Он фиксирует exact Run/Task, snapshot ref/hash, текущий product digest и raw result SHA-256; защищается existing control-plane phase boundary. Он не является semantic Stage evidence. Core schemas/registries и accepted history не изменены.

## Ошибки, повторы и границы

Одинаковый idempotency key и payload возвращают существующую операцию. Тот же key с другим payload — conflict. Другая вкладка со старой revision получает conflict и перечитывает view. После потери соединения operation ID сохраняется в sessionStorage без credentials; reopening не запускает команд. Явная сверка не выдаёт UI success по одному факту существования более позднего Run. Неоднозначный commit остаётся `AMBIGUOUS_COMMIT`, требует canonical диагностики, не повторяется автоматически.

При stale result baseline безопасный путь для исправленного продукта — block с объяснением и resume в новый Run. Уже полученный результат не перезаписывается. Если публикация прервана до sealing phase boundary, control check блокирует продолжение; partial files сохраняются для диагностики. Physical power-loss recovery не объявляется проверенным по одной симуляции исключения.

`allow_manual:true` разрешает manual route, но не доказывает manual checks. При непустом `manual_checks` без поддержанного task-level evidence API gate остаётся BLOCKED. UI не переводит manual check, scope violation или missing evidence в PASS и не переименовывает evidence kinds для Stage Gate. Это fail-closed исправление прежнего shortcut в manual runtime.

Существующие `LOCAL_AUTOMATIC` projects открываются без смены policy. Запуск, external manual intake и host verification для них отключены с причиной. Тестовый external agent пишет только fixture product files; это не доказательство реального Codex/Podman. Installer/clean-machine, полный manual lifecycle, governed per-Run egress и rootless Podman security остаются отдельными gates. Engine/Documentation ZIP этим этапом не создаются.

Повторный `verify_current` сохраняет прежние immutable report/evidence: первый check использует исторический ID, последующие — новые exact refs с суффиксом `V002`, `V003` и далее (до 1000 checks на Run). Новое состояние active Run указывает на последний report; completion не использует прежний PASS после более позднего FAIL. Исправление устраняет перезапись report перед отказом immutable evidence при повторной проверке.

Ограничения проекции и staging: до 1000 записей в Task/WP index, до 8 MiB на читаемый canonical artifact, до 256 KiB закреплённого prompt preview, до 1000 приватных staged results на app-data. При превышении операция отклоняется; cleanup staged results не запускается через GET. Companion operation receipts используют ограниченный Windows retry только атомарной записи при кратком read handle; kernel операции и продуктовые команды этим retry не повторяются.

Приёмка выявила blocker PH-LW-09: текущий active Stage planner создаёт Tasks с manual checks, а поддержанного Task-level manual proof intake нет. Старый PH-F06 lifecycle проходил такие проверки по одному `allow_manual:true`; теперь его setUpClass получает BLOCKED, четыре метода не выполняются. Отдельные Stage evidence, поступающие позже, не являются proof конкретной Task. Этот новый manual regression сохраняется как NO-GO этапа; исправление требует согласованного evidence contract и проверки полного пути. Целевые PASS не закрывают этот gate. Planner, старые tests и исторический PH-F06 PASS не переписаны.
