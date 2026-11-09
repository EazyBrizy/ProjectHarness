# PH-LW-03 — Application service, shared operation guard и recovery

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап реализации:** PH-LW-03, 2026-11-02  
**Engine version:** v0.5.1 WIP / NOT RELEASED  
**Local Web companion:** 0.1.0-dev  
**Статус:** сервисный Python слой реализован; native Windows/NTFS **NOT RUN**; HTTP, UI и installer **ещё не реализованы**. Полная v0.5.1/automatic остается **NO-GO**.

## 1. Назначение и граница

`project_harness.local_web_service.LocalWebService` — bounded Python application service без HTTP. Не дублирует Kernel/Stage/Gate state: путь зарегистрированного intake workspace или prepared Project Instance привязывается к непрозрачному `LWP-*`; браузерный payload не содержит `project_root`, shell/CLI strings, output path или возможности использовать произвольный абсолютный путь. Регистрация `register_existing(path, kind="workspace"|"project")` — отдельный **trusted operator call**, не веб-операция. Внешняя `app_data` должна быть изолирована от всех project/workspace roots; POSIX требует mode 0700, Windows per-user ACL предстоит проверить нативно.

Core/Stage State остаётся единственным источником истины. Успех UI operation означает завершение вызова core API и не означает automatic Codex, завершение Tasks, Stage acceptance либо semantic Gate PASS. `execute-current` в сервисе **disabled** с явной причиной, независимо от наличия Linux automatic API. Не добавлены automatic egress, provider API, shell/terminal, browser assets, Git/PR, background daemon или второй executor/sandbox.

## 2. Операции PH-LW-03

Сервис принимает типизированный `OperationRequest(project_id, action, payload, idempotency_key, expected_fingerprint)`; обязательные поля проверяются до записи. Отдельный `get_status(project_id)` и `get_operation(project_id, operation_id)` — **read-only**. В текущем этапе зарегистрированы и исполнимы только:

| Action | Корень | Payload | Core API / ограничение |
|---|---|---|---|
| `update-draft` | workspace | `patch` (45 allowlisted dotted leaves), `expected_input_digest` | `local_web_drafts.update_provisional_draft`; strict schema + semantic readiness, atomic `PROJECT_INPUT.yaml`, invalidation всех ранее подтверждённых draft approvals при материальном изменении |
| `check-intake` | workspace | `{}` | `intake.check_intake`; mutation, **не** GET/polling |
| `prepare` | workspace | `{}` | `compiler.prepare_handoff` в **новой приватной** `app_data/artifacts/<operation_id>`; никакой пользовательский `keep_directory` в payload |
| `next` | project | `{}` | `runtime.next_task` для exact current Task/Run; изменение Run/JIT возможно только по POST-like request |
| `validate-project` | project | `{}` | реальный `validation.validate_project_directory`; результат отдельной явной операции |
| `verify` | project | `{}` | `runtime.verify_current(allow_command_execution=False)`; не запускает project verification commands без bounded per-Run consent (будущий PH-LW-09) |

Остальные элементы из `LOCAL_WEB_CONTROL_MAP@1` доступны как DTO с `enabled=false`, `disabled_reason`, а не как фиктивные успешно завершённые действия. В частности, `accept-stage`, `level-up`, `start-maintenance`, `cancel-maintenance`, `complete` через UI не активированы до соответствующих PH-LW; CLI/public API ядра остаются доступны по прежнему контракту. Режим automatic execution в Local Web manual запрещён независимо от `--network` и профиля. Нет generic arbitrary Python/CLI dispatcher (`eval`, `getattr`, shell).

`update-draft` не разрешает изменять project ID/name/mode/slug, source inventory, `metadata`, `execution`, `approvals` или произвольные nested YAML ключи. Кандидат проверяется через текущую `SCHEMA-PROJECT-PREPARATION-INPUT@4` в provisional режиме и существующую `validate_project_input`. Незакрытые вопросы сохраняют честный `WAITING_INPUT` / `WAITING_DECISION`; невозможные values и unknown fields блокируются **до** записи. Положительное решение, полученное из ответа GPT, **не** принимается как human approval. Изменение смыслового черновика сбрасывает `approved/actor/approved_at/notes` для всех draft approval subjects в **том же атомарно заменённом файле**. Исторические accepted inputs/stage decisions не меняются.

## 3. Read-only view и exact context

`get_status()` читает canonical файлы и вызывает только `validate_project_input`, `runtime.project_status`, `stages.stage_status` и read-only fingerprint functions; **никогда** не вызывает `check_intake`, `next_task`, `recover_stage_transactions`, `executor-doctor` или external commands. Возвращает `core_status`, `core_route`, `done`, `current`, `blockers`, `required_user_action`, все доступные mapped actions, exact `refs` (session/input SHA либо Task/Run/Stage Plan/Gate/baseline/revisions), `fingerprint`. `readiness` вычисляется из текущего provisional draft без исправления уже сохранённого `STATE/READINESS`. В Project Instance status не подменяет `TARGET_LEVEL_REACHED`, `BLOCKED`, `VERIFYING` и Stage/Gate routes.

`core_fingerprint` для workspace включает raw digests `PROJECT_INPUT`, `STATE`, `READINESS`, `SESSION`, inventories. Для prepared project он включает CURRENT_STATE, canonical Stage State, Task/WP/Plan/Gate indexes, Run control ref и canonical `product_baseline_revision`. Это **консервативный replay fence**, не криптографическая транзакция внешнего git/host FS. До mutation fingerprint сверяется повторно внутри OS lock. Наличие `LWO-*` в журнале не может отменить выполненную core транзакцию или заменить проверку control-plane.

## 4. Долговечный журнал, locking, retry

Один `ThreadPoolExecutor(max_workers=1)` обрабатывает bounded локальные операции после сохранения `QUEUED` intent. Закрытие вкладки не отменяет worker. JSON-запись в private `app_data/operations/LWO-*.json` атомарна, с `record_digest`; содержит action ID, project ID, payload SHA, expected/current fingerprint, idempotency key, timestamps, non-sensitive result/error refs, `core_outcome`. Full GPT/doc body, raw prompts, secrets, environment variables и runtime stdout/stderr **не журналируются**. `operation_receipt_v1.schema.json` остаётся отдельным strict contract `LOCAL_WEB_OPERATION_RECEIPT@1` (дополнено действие `LW-DRAFT`). Ядро не читает UI receipts как governance evidence.

`project_operation_guard` находится **снаружи** существующего Stage transaction lock: OS `flock` (Linux/macOS) либо `msvcrt.locking(LK_NBLCK, 1)` (Windows), отдельный приватный temp lockfile по canonical root, без записи в `.harness`. Guard reentrant в **одном thread**, но fail-closed при втором thread/process. Public mutations `start_intake`, `check_intake`, `prepare_handoff`, Task lifecycle, Stage acceptance/level-up, planning, maintenance, Brownfield assessment, migration и Gate recovery используют общий decorator, поэтому вызовы из CLI и сервиса по тому же корню видят один fence. Нельзя менять порядок Stage→outer guard; Stage остаётся inner. Native Windows byte-range concurrency требует реальной Windows проверки.

Повтор `(project ID, idempotency key, action, payload digest, expected fingerprint)` возвращает тот же `operation_id`, **без** повторного вызова ядра. Переиспользование ключа с иным payload/action/fingerprint — `OPERATION_CONFLICT`. Stale fingerprint отклоняется до мутации с кодом и русской подсказкой. Сервис не хранит сырые тексты документов в runtime operation log. Изменение project source/accepted scope не разрешается UI journal.

## 5. После crash и cancellation

`get_operation`/polling только читают receipt и не запускают recovery. Явный `reconcile_operation` под OS guard:

1. `QUEUED`, у которого не было mutation boundary, переводится в `INTERRUPTED / CONFIRMED_REJECTED`, без автоповтора.
2. Для project сначала вызывает **существующий** `recover_stage_transactions`, если он нужен; UI не переписывает Stage journal/accepted history и не объявляет rollback после фактического commit.
3. Для `update-draft` сравнивает заранее сохранённый expected new input SHA с фактическим canonical file. Для `prepare` валидирует существующий exact ZIP в app-owned operation directory. Для `next` читает текущий Run, но изменение Run ref относительно `before_active_run_ref` **не доказывает**, что Run создала именно эта операция: другой CLI мог успеть стартовать Run после crash. Поэтому без exact kernel provenance record такой `next` остаётся `BLOCKED / UNKNOWN_RECONCILE`; не допускается ложный `SUCCEEDED`. Только доказанное завершение возвращает `CONFIRMED_COMMITTED`.
4. `check-intake`, `verify`, а также операция с неоднозначным состоянием без exact доказательств остаются `BLOCKED / UNKNOWN_RECONCILE`, с действием оператора. **Verification commands, next и formal approvals не запускаются автоматически снова.**

`cancel_queued` допустим только при `QUEUED` до начала работы. После `RUNNING/MUTATING` и после commit отмена через UI запрещена; завершение операции ожидается или проводится явная сверка состояния. Ошибки возвращаются с устойчивым кодом, русским пояснением и `next_action_ru`, а не скрываются как «internal failure». Реальные filesystem/OS failures остаются видимыми.

## 6. Пример public Python API, без HTTP

```python
from pathlib import Path
from project_harness.local_web_service import LocalWebService, OperationRequest

with LocalWebService(Path('/private/app-data')) as service:
    # Только доверенный локальный оператор выбирает реальный каталог:
    project_id = service.register_existing(Path('/projects/current'), kind='project')
    view = service.get_status(project_id)  # без мутации canonical tree
    request = OperationRequest(
        project_id=project_id,
        action='next',
        payload={},
        idempotency_key='manual-next-request-0001',
        expected_fingerprint=view['fingerprint'],
    )
    receipt = service.submit(request)
    # В приложении браузер вызывает read-only get_operation по operation_id.
    latest = service.get_operation(project_id, receipt['operation_id'])
```

Unix пути в примере — схема вызова API, **не** заявление о поддержке их в Windows; native Windows оператор выбирает локальный абсолютный drive root. Нет встроенного AI provider, ни одной автоматической отправки GPT/Codex и нет ещё Web server.

## 7. Проверки и остающиеся ограничения

Целевые positive/negative реальные API тесты: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_03_service`. Дополнительно применимы `tests.test_ph_lw_01_contract`, `tests.test_ph_lw_02_windows_core`, все сохранённые Stage/Run/intake regression modules, source/wheel/doctor и docs validator. Test report `PH_LW_03_TEST_REPORT.md` содержит **фактически** выполненные команды и результаты. Позднейшие PH-LW-04..12 должны подтвердить GET vs POST/CSRF, secure loopback, браузерные race, Win32 ACL/NTFS/shared locking, UI crash/relaunch/installer. Linux child-process contention и fault injection — не Windows acceptance. Для отдельного нативного прогона PH-LW-03 на Windows 11 x64/NTFS подготовлен `local_web/ci_ph_lw_03_windows.ps1` (с аргументом `-DocumentationZip`); наличие скрипта в ZIP не подтверждает его выполнение.

**Не закрыто:** real Windows/NTFS test stand, реальный browser/launcher, full Podman isolation acceptance, позитивный approval-bound egress. Полный v0.5.1 release **NO-GO / NOT RELEASED**; исторические PH-051-12/PH-LW-01/02 отчёты не изменяются.
