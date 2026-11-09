# Карта 26 публичных CLI действий и Python API

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап подготовки:** PH-LW-01, 2026-11-01  
**Статус:** CONTRACT DESIGN / NOT IMPLEMENTED / NATIVE WINDOWS NOT RUN

## Точная карта интерфейса

Разметка `LW-Cxx` — только ID действия UI companion, `LW-Exx` — сценарий из `ACCEPTANCE_MATRIX.md`. CLI 26 команд — фактический `src/project_harness/cli.py`; Python API из модулей core проверяется тестом. Методы `POST` защищаются CSRF/Origin и exact context; команда `demo` (CLI public) не имеет публичного безопасного Python API, поэтому в UI disabled до обёртки с отдельной проверкой.

| ID / экран | Действие и CLI | Public Python API | Состояние и consent | Exact context / preconditions | Outcome → next | Test |
|---|---|---|---|---|---|---|
| LW-C01 / Диагностика | Проверить комплект / `doctor` | `validation.doctor` | EXPLICIT_DIAGNOSTIC; NONE / POST | distribution digest,manifest; Distribution root exists; no skip-manifest in Web | PASS or INVALID; no project mutation → Fix distribution / continue | LW-E02 |
| LW-C02 / Новый проект | Создать intake / `start-intake` | `intake.start_intake` | MUTATION; SOURCE_IMPORT / POST | new workspace id, source snapshot digest, expected absent; Disjoint new workspace/source/repository roots; force forbidden | WAITING_INPUT / WAITING_DECISION / READY_FOR_HANDOFF → Answer questions | LW-E03 |
| LW-C03 / Опрос | Сохранить ответы и перепроверить / `check-intake` | `intake.check_intake` | MUTATION; INTAKE_REVISION / POST | workspace id,input digest,expected revision; Persisted input draft; no silent approval | Readiness/questions/session updated, may WAITING_INPUT → Answer/approve next item | LW-E06 |
| LW-C04 / Подготовка | Собрать handoff и опубликовать / `prepare` | `compiler.prepare_handoff` | MUTATION; PUBLISH_DESTINATION / POST | workspace input digest,output id,new staging id; All formal intake approvals, MANUAL_HANDOFF, new destination; no existing keep_directory | READY_FOR_CODEX + initial ZIP / directory → Validate handoff, open tasks | LW-E11 |
| LW-C05 / Подготовка | Проверить handoff ZIP / `validate-handoff` | `validation.validate_handoff` | READ_DIAGNOSTIC; NONE / POST | handoff immutable digest; Immutable original ZIP or directory | PASS / FAIL; no state change → Repair or publish | LW-E11 |
| LW-C06 / Обзор | Проверить текущий проект / `validate-project` | `validation.validate_project_directory` | READ_DIAGNOSTIC; NONE / POST | project id,baseline digest; Current project exists, canonical paths resolved | PASS / FAIL diagnostics; verify no mutation → Repair diagnostic | LW-E29 |
| LW-C07 / Обслуживание | Мигрировать проект / `migrate-project` | `migration.migrate_project` | MUTATION; MIGRATION_APPROVAL / POST | project id,engine/schema/history refs; Supported predecessor and exact current history; explicit user consent | Migrated/idempotent or guarded reject → Validate project / repair | LW-E22 |
| LW-C08 / Обзор | Показать состояние / `status` | `runtime.project_status` | READ_SNAPSHOT; NONE / GET | project id,core fingerprint; Bound project, permitted owner session | Persisted status only; no created Run → Call next via POST only | LW-E28 |
| LW-C09 / Задачи | Следующий Run/JIT / `next` | `runtime.next_task` | MUTATION; RUN_RESERVATION / POST | project id,task/run/stage expected refs; Current stage/task/baseline valid; lock held | READY_FOR_CODEX / STAGE_PLANNING_REQUIRED / BLOCKED / target → Show current task or stage action | LW-E14 |
| LW-C10 / Диагностика | Проверить auto executor / `executor-doctor` | `runtime.executor_doctor` | EXPLICIT_DIAGNOSTIC; NONE / POST | project id,active ADP/SBX refs; Only explanatory; native Windows automatic unavailable | BLOCKED/unsupported or factual diagnostics; never fake PASS → Use manual route | LW-E33 |
| LW-C11 / Диагностика | Execute-current (disabled) / `execute-current` | `runtime.execute_current` | DISABLED; NOT_AVAILABLE / DISABLED | project id,capability reason; Manual Windows companion disallows automatic mode entirely | No invocation; capability reason only → Manual Codex handoff | LW-E33 |
| LW-C12 / Задачи | Проверить результат / `verify` | `runtime.verify_current` | MUTATION; COMMAND_EXECUTION_IF_SELECTED / POST | project id,run ref,verification plan digest,baseline; Actual product changes; command argv preview and exact consent when allowed | PASS / FAIL / BLOCKED; separate verification evidence → Complete only after PASS | LW-E16 |
| LW-C13 / Задачи | Завершить Task / `complete` | `runtime.complete_current` | MUTATION; TASK_COMPLETION / POST | project id,run ref,result id,digest; Independent PASS and valid Agent Task Result, exact changed paths | Task DONE or guarded rejection → Next/task or gate | LW-E14 |
| LW-C14 / Задачи | Создать blocker / `block` | `runtime.block_current` | MUTATION; BLOCKER_RECORD / POST | project id,run/task revision; Active ordinary Run, reason/options nonempty | BLOCKED with bounded choices → Resume or modify scope | LW-E17 |
| LW-C15 / Задачи | Возобновить Run / `resume` | `runtime.resume_blocked` | MUTATION; BLOCKER_RESOLUTION / POST | project id,exact blocker ref,current task; OPEN ordinary blocker, valid explicit resolution | New attempt or BLOCKED; historical Runs immutable → Next/verification | LW-E17 |
| LW-C16 / Стадии | Показать уровни / `stage-status` | `stages.stage_status` | READ_SNAPSHOT; NONE / GET | project id,Stage State revision; Canonical Stage State exists | Active,target,observed,accepted separately → Gate/planning/maintenance route | LW-E18 |
| LW-C17 / Стадии | Подготовить approval draft / `prepare-stage-approval` | `stages.prepare_stage_approval` | WRITE_APP_ARTIFACT; NONE / POST | Stage Plan/Gate revision,baseline; VERIFYING or recoverable BLOCKED; app-owned new output path | Exact-bound draft only, approved=False → Human review → accept-stage | LW-E18 |
| LW-C18 / Стадии | Подготовить Stage plan draft / `prepare-active-stage-plan` | `active_stage_planning.prepare_active_stage_plan` | WRITE_APP_ARTIFACT; NONE / POST | Stage State/accepted baseline/source digest; STAGE_PLANNING_REQUIRED, exact refs; new app-owned path | Draft only, no activation → Human review → plan-active-stage | LW-E18 |
| LW-C19 / Стадии | Применить reviewed plan / `plan-active-stage` | `active_stage_planning.plan_active_stage` | MUTATION; REVIEWED_PLAN / POST | project id,Stage State rev,Plan/Gate refs,scope; Reviewed exact draft; no material divergence unless approved | Active Plan/Gate + first READY JIT → Next manual Task | LW-E18 |
| LW-C20 / Стадии | Повторить Gate-readiness / `resume-stage-gate` | `stage_gate_lifecycle.resume_stage_gate` | MUTATION; GATE_RECOVERY / POST | project id,Gate/ref revision,blockers; Persisted gate-related BLOCKED and supplied proof | VERIFYING or BLOCKED; no false PASS → Prepare Stage approval | LW-E17 |
| LW-C21 / Brownfield | Провести assessment / `assess-maturity` | `stages.assess_maturity` | WRITE_CORE_ASSESSMENT; ASSESSMENT_REQUEST / POST | workspace/product tree digest,claimed level; Brownfield workspace, exact repository; no repo commands | Immutable assessment record or gaps/UNKNOWN → Review baseline separately | LW-E21 |
| LW-C22 / Стадии | Принять Stage / `accept-stage` | `stages.accept_stage` | MUTATION; FORMAL_STAGE_DEC_ACT / POST | level,Stage Plan/Gate refs,baseline,evidence refs; VERIFYING Gate, validated evidence, exact formal approval schema | Immutable acceptance, next Stage or target reached → Plan next Stage / maintenance | LW-E18 |
| LW-C23 / Стадии | Повысить целевой уровень / `level-up` | `stages.level_up` | MUTATION; FORMAL_LEVEL_UP_DEC_ACT / POST | accepted level,target,last report,Stage State rev; TARGET_LEVEL_REACHED, sequential increase, no scope expansion | New target/active planning route; idempotent replay → Prepare active Stage plan | LW-E19 |
| LW-C24 / Обслуживание | Начать maintenance / `start-maintenance` | `maintenance.start_maintenance` | MUTATION; FORMAL_MAINTENANCE_PLAN / POST | highest accepted,target,scope,last acceptance; TARGET_LEVEL_REACHED, exact approved same-level plan | Active maintenance tasks; maturity unchanged → Next manual Task | LW-E20 |
| LW-C25 / Обслуживание | Отменить maintenance / `cancel-maintenance` | `maintenance.cancel_maintenance` | MUTATION; FORMAL_MAINTENANCE_CANCEL / POST | maintenance plan,work package,revision; No completed product-changing maintenance Task; strict cancel approval | Cancelled, no accepted maturity change → Review status/next | LW-E20 |
| LW-C26 / Диагностика | Создать demo / `demo` | private helper `_demo`; UI disabled | UNAVAILABLE_WRAPPER; DEMO_DESTINATION / DISABLED | new isolated demo root; Private CLI helper, NOT a supported public Python API | Disabled until bounded public fixture wrapper; no delete → Choose new demo directory | LW-E33 |

## Детерминированный guard для каждого route

1. Browser authentication + trusted Host/Origin + CSRF + idempotency key + current project ownership + exact expected `core_fingerprint`; затем single-project cross-process lock.
2. Проверить status/task/Stage/baseline/allowed roots; представить exact payload/verification argv/destination human, собрать соответствующее согласие только из явного UI click. Ни одна модель/документ не выдаёт согласия.
3. Вызывать один разрешённый public Python API с typed paths/ref, а не конструировать shell CLI или писать `.harness` из handler. Для `check-intake` и `next` POST, с реальным возможным persistence.
4. Записать `LOCAL_WEB_OPERATION_RECEIPT@1`: `UNKNOWN_RECONCILE` при ambivalent crash, никогда не реисполнять unverified commit/verification, reconciling core authoritative records.
5. Видимые состояний после результата: confirmed committed/rejected/pending/unknown; next action из core. Disabled controls объясняют причину.

## Для тестов

Machine map в `resources/local_web/control_map_v1.json`; `tests/test_ph_lw_01_contract.py` проверяет ровно 26 имен CLI, Python API, schema + context fields, GET/POST и security contract. Наличие map не доказывает работоспособный UI, E2E acceptance каждого `LW-Exx` остаётся на будущие этапы.
