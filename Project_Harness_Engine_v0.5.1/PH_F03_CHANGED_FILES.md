# PH-F03 — состав точечных изменений Project Harness Engine / Documentation v0.5.0

**Исходная база:** `Project_Harness_Engine_v0.5.0 (3).zip` (результат PH-F02), `Project_Harness_Documentation_v0.5.0 (2).zip`, неизменённая спецификация v0.5.0 и `Project_Harness_v0.5.0_Remediation_Plan_RU.md`.

**Версия движка и нормативных registry: без изменения — v0.5.0.** PH-F03 не считается финальным PH-F08 release gate.

## Engine source

- `src/project_harness/active_stage_planning.py` — новый отдельный bounded next-stage governed planner, Python API, схема ревью, binding текущей стадии, accepted reports, scope, Stage State, Gate и product tree. Обеспечивает read-only draft и transactionally-applied current-stage Work Package, Tasks, DAG, Verification/Context/Prompt Plans, first READY JIT и safe replay. Новый ID для retry после rolled-back journal, сохранение запрета повторно использовать transaction ID.
- `src/project_harness/cli.py` — публичные `prepare-active-stage-plan`, `plan-active-stage` и флаги `--project`, `--output`, `--plan`, `--force`.
- `src/project_harness/stages.py` — публичные API forwarding functions; исполнимая next-operator route в `stage-status` для `PLAN_ACTIVE_STAGE`.
- `src/project_harness/runtime.py` — actionable next command для boundary `STAGE_PLANNING_REQUIRED`.
- `src/project_harness/stage_transactions.py` — узкая compatibility поправка проверки transaction canonical `NEXT_TASK`: до резервирования первого Run Stage называется `active_stage`, после — `implementation_stage`. Не изменена B-02 crash-recovery/reuse policy.
- `src/project_harness/validation.py` — проверка **первоначального** first JIT только для начального handoff, без ошибочного отклонения новых, исторически допустимых JIT при принятом предыдущем уровне.
- `schemas/active_stage_plan_review.schema.json` + `src/project_harness/resources/schemas/...` — строгий `SCHEMA-ACTIVE-STAGE-PLAN-REVIEW@1` без дополнительных properties на нормативных объектах.
- `tests/test_ph_f03_active_stage_planning.py` — rejection, idempotency, before-commit recovery, immutability и both primary stage transitions.
- `build/lib/project_harness/*`, `dist/project_harness_engine-0.5.0-py3-none-any.whl` — синхронизированный код/resources и пересобранный installable wheel; executable `bin/project-harness` сохранён.

## Operator documentation and packaging

- `README.md`, `MANUAL_INSTALL.md`, `CHANGELOG.md` (Engine) — новые команды, входной schema, review rules, statuses, failure/recovery, запрет расширения scope.
- `03_Planning/07_Implementation_Levels_and_Stage_Plans.md`, `README.md`, `CHANGELOG.md` (Documentation) — PH-F03 public governed runbook без изменения нормативной модели Gate evidence.
- `FILE_INDEX.md`, `Project_Harness_Architecture_v0.5.0_FULL.md`, `MANIFEST.sha256` (Documentation) — регенерация только механически зависимых агрегатов и sha256 inventory.
- `docs/Project_Harness_Documentation_v0.5.0/` (Engine) — точная копия обновлённой Documentation.
- `MANIFEST.sha256` (Engine) — обновлённая проверяемая контрольная сумма поставки.

## Сохранённые границы

- Accepted scope/constraints, target authority, canonical maturity scale, no future Stage Tasks, immutable input, reports, evidence и completed Runs не изменены.
- Formal Stage approval и v0.5.0 subject-specific PH-F02 proof по-прежнему обязательны; новый planner не создаёт фиктивный PASS evidence.
- Отсутствуют новые Codex CLI Executor, OS sandbox, Git/PR, deployment, remote control-plane и возможности следующих версий.
- PH-F04 reachability-инварианты и PH-F05–PH-F08 целиком не реализовывались.
