# PH-LW-07 — отдельные согласования и инвалидирование

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-07  
**Companion:** 0.1.0-dev, build `PH-LW-07-20261107`  
**Область:** provisional intake approvals, companion receipts, invalidation/recovery. Automatic executor выключен. Подготовка Project Instance ожидает PH-LW-08.

## Маршрут оператора

1. Выбрать intake, заполнить material fields в «Опрос и GPT». Импортированный GPT draft не является согласием. Неопределённый target, UNKNOWN sensitivity, отсутствующие architecture/technology и остальные material gaps блокируют подтверждение.
2. Открыть «Согласования». Явно установить имя оператора один раз для этой intake session. Оно показывается перед каждым действием и в каждом receipt. Изменение имени в этой session не поддерживается; exact повтор того же имени идемпотентен. Имя не является удостоверением личности.
3. Для Greenfield отдельно пройти `project_definition` → `architecture_baseline` → `technology_baseline` → `codex_handoff`. Для Brownfield/Hybrid после Project Definition обязательно отдельное `brownfield_baseline`. Список и порядок берутся из `approvals_for_mode()`, не из нового UI enum.
4. Перед каждым подтверждением прочитать показанное содержание и отметить отдельный checkbox. Project Definition содержит project/scope/constraints, profile и target; Architecture — полную architecture и constraints; Technology — selections, команды как текст и skills; baseline — summary, дефекты/пробелы/долг, read-only repository inventory и evidence context; handoff — полный неутверждённый draft и обязанности ручной передачи. Команды из этих данных не исполняются.
5. Нажать подтверждение только этого предмета. Browser не отправляет `approved`, actor или timestamp решения. Server проверяет актуальность, создаёт timestamp UTC и записывает фактические `approved/actor/approved_at/notes` через public approval API. После commit выполняется `check_intake`; другие решения автоматически не создаются.
6. «На доработку» требует комментарий, сохраняет его в receipt и notes актуального draft, сбрасывает выбранное согласование и зависимые последующие согласования. Более ранние подтверждения сохраняются. UI открывает уточнение; комментарий виден в опросе и форме до нового подтверждения этого предмета. Прежние receipts и accepted Project history остаются неизменными.
7. Последнее действие называется «Подтвердить передачу и подготовить проект». В этом checkpoint оно оформляет только согласование передачи и возвращает `PREPARATION_PENDING_PH_LW_08`: **Project Instance пока не создан**. HTTP `prepare` отклонён до отдельной реализации PH-LW-08; прежний trusted Python/CLI preparation API не изменён.

Новые Brownfield/Hybrid intake с репозиторием через браузер по-прежнему не создаются. Формы PH-LW-07 работают с такими intake, заранее созданными public `start_intake` и зарегистрированными trusted local operator API `register_existing`. Перед baseline approval repository читается без команд, сравнивается live tree digest с inventory; drift блокирует подтверждение и требует отдельного уточнения baseline. Browser не принимает filesystem paths.

## API и точная привязка

| Метод и route | Назначение |
|---|---|
| GET `/api/projects/<project_id>/approvals` | Текст предметов, actor, bindings, read-only проекция readiness, receipts, invalidation и recovery flags |
| POST `.../approvals/actor` | Точный object: `actor`, `expected_fingerprint` |
| POST `.../approvals/decisions` | `subject`, `decision`, `comment`, `review_digest`, `subject_digest`, `expected_fingerprint`, `idempotency_key`, `confirm` |
| POST `.../approvals/recover` | Явное `confirm:true`; сверка прерванного действия |

Все приватные routes требуют session; POST — также exact Host/Origin/port и CSRF. Unknown/duplicate fields, неподдержанные типы и keys, stale fingerprint/digest и wrong sequence отклоняются до mutation. Decisions — `APPROVE`, `REWORK`, а для несвязанных current approval fields — отдельный явный `INVALIDATE`. Кнопки «одобрить всё» нет. Поля модели `actor`, `approved_at`, `approved:true` по-прежнему отвергает strict GPT exchange.

`LocalWebService.get_approval_review`, `set_approval_actor`, `decide_approval`, `recover_approval` — application API. Canonical input меняет только public `apply_provisional_approval`; `approval_candidate` проверяет schema, manual policy, полноту subject, порядок и before/after bytes. Из UI/HTTP нет записи `.harness`, Task/Run/Stage/Gate states.

Companion version 1 хранится отдельно от PROJECT_INPUT в provisional `intake/.local-web-approvals/`: `actor.json`, immutable `LWA-*.json`, временный checksummed `pending.json`. Это не новый core schema/DEC/ACT contract. Receipt содержит server actor/time, decision/comment, project ID, sequence, exact input revision и core fingerprint, source revision/snapshot/inventory/tree digests, subject content/digest, semantic content digest, after digest и request digest. Metadata hashes проверяют audit consistency, но **не являются криптографической подписью** и не защищают от malware с правами того же OS user.

`input_revision` — SHA-256 точных bytes PROJECT_INPUT. `content_digest` связывает весь input без изменяемых approval полей с источниками; поэтому следующий отдельный approval не инвалидирует предыдущий при неизменном предмете. `review_digest` дополнительно связывает current input/fingerprint и actor. Canonical `approved:true` считается действующим в companion только при совпадении содержания, subject digest и четырёх canonical fields с committed receipt. Несвязанные fields требуют отдельного явного сброса; при GET ничего не сбрасывается.

Source refresh и material draft edit используют прежние public APIs и консервативно сбрасывают current draft approvals. GET формы показывает, какие предметы требуют повторения и почему: `SOURCE_CHANGED`, `MATERIAL_DRAFT_CHANGE` либо `REWORK_OR_EXTERNAL_APPROVAL_CHANGE`, со ссылкой на сохранённый receipt. В записи ранее принятого решения ничего не переписывается. После успешной service preparation новые согласования/сбросы запрещены; accepted Project Instance вообще не принимается этим API.

## Atomic commit, повторы и восстановление

Один cross-process `project_operation_guard` сериализует решения с другими guarded operations. Exact idempotency key связан с project/action/request: retry возвращает прежний receipt без нового timestamp, другой payload с тем же key — conflict. Изменение во второй вкладке требует нового просмотра. При потере ответа UI позволяет явно повторить тот же request; refresh/restart читает историю без повторного POST.

Commit: проверка → durable intent → atomic single-file PROJECT_INPUT write через public API → `check_intake` projections → committed receipt → удаление intent. Только успешная mutation обновляет persisted READINESS/QUESTIONS/STATE/SESSION; GET показывает текущую read-only проекцию и ничего не записывает, не подтверждает и не восстанавливает. При частичном обновлении projections recovery завершает их через тот же public `check_intake`.

После interruption новые service mutations блокируются. Явный recover сравнивает exact sources и before/after input digests: after → `COMMITTED_RECOVERED`; before без committed receipt → `NOT_COMMITTED` (не повторяет решение); постороннее изменение, повреждённый intent или sources → `APPROVAL_RECOVERY_AMBIGUOUS`, без overwrite. Сохранённый receipt после crash перед удалением marker возвращается без второго решения. Public CLI mutation после crash может сделать восстановление неоднозначным; её bytes не перезаписываются.

Лимиты: имя 120 символов, комментарий 2000, decision HTTP body 16 KiB, один intent до 2 MiB, до 256 решений и 16 MiB companion store с резервом на intent/receipt. При превышении — отказ, история автоматически не удаляется. Auth tokens и raw uploads туда не копируются; companion записи не объявляются Stage evidence.

## Проверка и границы

Новые tests: `tests.test_ph_lw_07_approvals` и `tests.test_ph_lw_07_http`. Native runner: `local_web/ci_ph_lw_07_windows.ps1 -PythonExecutable <Python314> -LogDirectory <новый каталог> -SkipRegressions`, затем отдельная общая matrix. Installed-wheel run использует независимые venv и Unicode CWD, реальный Waitress/TCP/Edge. Фактические counts, команды, deps/platform/exit, ранние FAIL и финальные результаты — `PH_LW_07_TEST_REPORT.md` и `PH_LW_07_LOGS` в Engine.

Аварийные tests завершают настоящий Windows subprocess через `os._exit` до input commit, после него и после receipt. Это не имитация power loss или NTFS storage failure. Browser draft fixtures синтетические; реальный GPT/provider не вызывался. Formal Stage/level-up schemas/tests не изменены.

Рабочие files и evidence сохраняются распакованными, docs mirror побайтовый, wheel пересобирается. Engine/Documentation ZIP не создаются без отдельного запроса пользователя. Старые reports и архивы сохраняют свои прежние verdicts.

`LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1: `NO-GO / NOT RELEASED`. PH-LW-08, installer/clean-machine acceptance, positive governed per-Run egress и фактическая rootless Podman security acceptance этим этапом не закрываются.
