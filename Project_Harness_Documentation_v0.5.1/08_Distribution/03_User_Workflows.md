# Пользовательские workflows через единую точку входа

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** IMPLEMENTED USER WORKFLOW BASELINE

**Фактически исполняемая последовательность v0.5.0:** [operator runbook](04_Operator_Runbook_v0.5.0.md). Концептуальные примеры ниже, для которых нет публичного CLI route, **не** являются обещанием автоматической реализации в Engine v0.5.0.

## 1. Ordinary question

User:

> Почему выбрана эта база данных?

Harness classifies `QUERY/READ_ONLY`, answers from Technology Baseline/ADR, returns `ANSWERED`, creates no product task.

## 2. New project

User:

> Хочу создать приложение для учёта оборудования.

Harness:

1. asks mandatory documentation question;
2. analyzes supplied sources;
3. asks 3–5 understandable questions per batch;
4. shows Project Definition Draft;
5. after acceptance prepares architecture/technology/skills/bootstrap/DAG;
6. returns first READY task, not a mass of prompts.

## 3. Existing project

User:

> Подключи этот репозиторий и подготовь продолжение разработки.

Harness performs read-only inventory, asks only material gaps, proposes Brownfield Baseline and route portfolio:

```text
continue development
fix bugs
improve project
stabilize baseline
```

## 4. Development request

User:

> Добавь поиск в backend и frontend.

GPT proposes a bounded Work Package with an initial contract prerequisite and separate backend/frontend/integration Tasks. In Engine v0.5.0 only the active-stage Task is handed to an **external** Codex; the operator runs `next → verify → complete` one Task at a time. Do not treat a conceptual safe-parallel batch as a supported local executor/worktree route; parallel worktrees are a later-version feature.

## 5. Status

User:

> Что сейчас происходит и какой следующий шаг?

Harness reads state/trace and returns active outcome, completed/blocked tasks, decisions, evidence and deterministic next route. Для Stage-aware статуса используется:

```bash
project-harness stage-status --project <root>
```

Output включает exact current Stage Plan/Gate refs, paths, revisions, Gate digest, canonical product baseline, result/WP/blocker counts и `next_operator_route`.

### PH‑F04. Runtime continuation and validation

Use the **persisted** route rather than guessing from an empty current task:

```bash
project-harness next --project <root>
project-harness stage-status --project <root>
project-harness validate-project --project <root>
```

`next.next_operator_route` and `stage-status.next_operator_route` contain the actual `route`, supported `command`, `reason` and, when applicable, `follow_up_command` or `external_prerequisite`; `stage-status.runtime_phase` distinguishes the current execution boundary. `validate-project` includes the named check `Persisted runtime continuation and Stage boundary reachability`.

| Persisted state / route | Supported continuation |
| --- | --- |
| `ACTIVE / PLAN_ACTIVE_STAGE` (`STAGE_PLANNING_REQUIRED`) | `prepare-active-stage-plan --project <root> --output <record>` followed by reviewed `plan-active-stage --project <root> --plan <record>` |
| `ACTIVE / READY` (unreserved Task) | `next --project <root>` reserves/replays a single current-stage JIT |
| `ACTIVE / EXECUTE_CURRENT_TASK_WITH_CODEX` or verification follow-up | Perform the external work/manual checks, then `verify --project <root> --allow-command-execution`; after verified PASS use `complete --project <root> --result <record>` |
| `ACTIVE / STAGE_GATE_REVIEW` (`VERIFYING`) | `prepare-stage-approval --project <root> --output <record>`, explicit human review, then `accept-stage --project <root> --level <stage> --approval <record>` |
| `BLOCKED / RESOLVE_STAGE_GATE` | `resume-stage-gate --project <root>` after the missing semantic proof is supplied |
| `BLOCKED / RESOLVE_BLOCKER_OR_CHANGE_SCOPE` | `resume --project <root> --resolution <record>` after recorded Task blocker resolution |
| `BLOCKED / RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN` | No unsafe in-place command; manually restore the trusted handoff/backup or restart under a trusted state |
| `TARGET_LEVEL_REACHED / TARGET_ALREADY_REACHED` | Formal `level-up --project <root> --target <higher-level> --approval <record>` only when accepted level is below `RELEASE`; at terminal `RELEASE` only optional governed `start-maintenance` is offered |
| Open same-level maintenance | Existing `next → verify → complete` at the accepted stage, without raising maturity; `cancel-maintenance` only with eligible formal approval |
| `ACTIVE / EVALUATE_STAGE_GATE_READINESS` (interrupted boundary) | Idempotent `next --project <root>` re-evaluates Stage Gate readiness |
| Migrated completed legacy `REVIEW_MATURITY_ASSESSMENT` | `assess-maturity --workspace <root>` followed by explicit human governance; assessment does **not** auto-accept the Stage |

A human approval/prerequisite is not an unreachable-route defect. An invented CLI command, contradictory current Plan/Gate/State revisions, unresolved Task dependencies, unapproved future-stage task, or an empty Task with no real continuation **is** a `validate-project` failure. Repeated read-only `next` at a boundary never advances Stage or produces an implicit approval. Replaying a current `plan-active-stage` is still handled by PH‑F03 exact-bound idempotency; PH‑F04 introduces no new planning or executor functionality.

## 6. Blocker/resume

User answers a material question or chooses recovery option. Harness evaluates exact resume condition, revalidates state, recompiles stale bundle and creates a new Run.

## 7. Stage Gate approval

После последней ordinary mandatory Task active Stage выполняется deterministic readiness evaluation на final product tree:

```text
all exact evidence needs closed → VERIFYING
missing exact evidence          → STAGE_ACCEPTANCE_PREPARATION WP/Task
```

Preparation route создаёт stable/idempotent WP и atomic Task только из missing mandatory outcomes/criteria/hard constraints/profile controls, materializes Context/Prompt/Verification Plans и DAG, обновляет current task/index/state и выдаёт ровно один первый JIT bundle. Task выполняется обычным `next → external work → verify → complete`; только **конкретно проверенное** subject-specific evidence с подходящими source/method/coverage/baseline может быть создано после PASS. No-op или общий PASS не доказывает `ARCHITECTURE_RECORD`, `LIMITATIONS_RECORD`, `PERMITTED_USE_RECORD`, `EXTERNAL_EVIDENCE` и другие несвязанные kinds. При remaining gaps Gate остаётся `BLOCKED` с recovery, повтор одинаковой подготовки не плодит Tasks; в `VERIFYING` переходят лишь при достаточном compatible evidence coverage. Future-stage features и accepted-scope expansion запрещены.

Поддерживаемый операторский цикл в `VERIFYING`:

```text
stage-status
→ prepare-stage-approval
→ добавить/проверить evidence и formal fields
→ accept-stage
```

### 7.1. Prepare exact operator record

```bash
project-harness stage-status --project <root>
project-harness prepare-stage-approval \
  --project <root> \
  --output ../operator-records/prototype-approval.yaml
```

`prepare-stage-approval` создаёт обязательный output file; console JSON содержит только summary. Generated record является strict `SCHEMA-STAGE-APPROVAL@1` `DRAFT`:

- `approved: false`;
- `id`, `actor`, `approved_at`: `null`;
- all outcome/criterion/hard-constraint/profile-control statuses: `UNKNOWN`;
- exact current Plan/Gate/baseline bindings;
- required Work Packages и critical blockers с current statuses;
- current permitted-use template;
- compatible evidence candidates и unresolved gaps.

Сама команда не меняет Stage/Gate, не принимает Stage, не создаёт WP/Decision/Acceptance Report, не запускает repository commands и не меняет product tree. Existing output требует explicit `--force`. Внутри проекта разрешён только `.harness/operator/APPROVALS/...`; обычный пользовательский файл предпочтительно хранить вне product/control tree.

### 7.2. Fill formal conclusions

Operator/validator проверяет фактическое evidence и изменяет formal fields:

```yaml
record_state: APPROVED
id: DEC-PROJECT-STAGE-PROTOTYPE-001
approved: true
actor: ACT-STAGE-APPROVER-001
approved_at: 2026-08-20T12:00:00Z
```

Каждый mandatory result закрывается `PASS` с compatible exact normalized `EVD-*` refs либо применимым `NOT_APPLICABLE` с rationale/validator. Candidate evidence из draft не является автоматическим решением. `permitted_use.status` переводится в `CONFIRMED`; limitations/gaps записываются явно.

### 7.3. Accept exact current Stage

```bash
project-harness accept-stage \
  --project <root> \
  --level PROTOTYPE \
  --approval ../operator-records/prototype-approval.yaml
```

Перед mutation движок повторно валидирует strict schema и exact binding. Изменение product tree, Gate revision или другого bounded context делает старый record stale; оператор повторяет `prepare-stage-approval`. Draft/not-approved record не создаёт acceptance artifacts.

Malformed approval—schema error, invalid N/A, wrong refs or invalid evidence—fails with zero mutation. Structurally valid review с mandatory `UNKNOWN/PARTIAL/FAIL` atomically persists BLOCKED Plan/Gate revisions, exact diagnostics, `STAGE_GATE_BLOCKER` and project route `RESOLVE_STAGE_GATE`; no Acceptance Report or next Stage is created.

### 7.4. Recover a persisted Gate blocker

```bash
project-harness stage-status --project <root>
project-harness resume-stage-gate --project <root>
```

For Gate-related BLOCKED, `stage-status.next_operator_route.route == RESUME_STAGE_GATE`. Recovery is allowed only for that blocker, revalidates current baseline/evidence, preserves blocked history and creates new revisions. It returns to ACTIVE preparation when gaps remain or VERIFYING when evidence needs are closed. Repeated recovery is idempotent. Ordinary Task `block/resume` remains a separate route.

## 8. Project evolution

Этот пример описывает target governance/change-pack модель. В v0.5.0 нет универсальной public CLI команды `project-evolution`, которая сама создаёт или применяет такой Change Pack; не используйте пример как исполненный операторский шаг.

User:

> Заменим текущую БД на другую.

Harness creates `PROJECT_EVOLUTION` Change Pack, alternatives/ADR, impact/migration/rollback and only then product tasks.

## 9. Same-level product maintenance

This workflow repairs or stabilizes the already accepted product scope without changing maturity. It is distinct from the future Harness Distribution Maintenance Change Pack described in the next section.

1. Prepare a strict `SCHEMA-MAINTENANCE-PLAN@1` record outside the Project Instance. Bind it to exact `highest_accepted_level`, current target, `last_acceptance_ref` and accepted scope. Every Task uses that accepted level and declares `future_stage_work: FORBIDDEN`.
2. Start the route:

```bash
project-harness start-maintenance --project <root> --plan ./maintenance-plan.yaml
```

The result includes the immutable Decision, plan/WP/task refs and the one first JIT bundle. Repeating the identical command returns the same reservation.

3. Execute through the ordinary runtime:

```bash
project-harness next     --project <root>
project-harness verify   --project <root> --allow-command-execution
project-harness complete --project <root> --result <exact-result-path>
```

Repeat for subsequent maintenance Tasks. The last mandatory Task produces an immutable completion report and restores the pre-maintenance route. Do not run `accept-stage`; maintenance does not change target or accepted level.

4. To cancel before product-changing completion, create a strict exact-bound cancel approval and run:

```bash
project-harness cancel-maintenance --project <root> --approval ./maintenance-cancel.yaml
```

Cancel is rejected after a completed product-changing Task, an observed completed product diff, a submitted Agent Result, or uncommitted product drift from the trusted Run snapshot. Project Harness does not roll back product files automatically. Complete the route or use an already defined governed compensation route.

5. `level-up` may be requested only after the maintenance WP reaches `COMPLETED`, valid `CANCELLED` or `SUPERSEDED`. Historical plans, WP/Task revisions, Runs and maintenance reports remain immutable.

## 10. Harness maintenance

Ниже приведена концептуальная модель изменения **дистрибутива** Harness, а не доступная публичная `start-maintenance` для продукта. Формальный product same-level route описан в разделе 9.

User:

> Измени project routing: bug fix должен начинаться с reproduction test.

Harness creates isolated Project Control Maintenance Change Pack, evaluates fixtures, activates revision and lists invalidated future plans. Product code is not changed in the same pack.

## 11. Optional command aliases

Фактически доступны `status`, `next`, `resume` и другие команды `project-harness --help`; команды `approve` в публичном CLI **нет**. Для `accept-stage`, `plan-active-stage`, `level-up` и maintenance используются exact перечисленные выше действия с reviewed records; свободный текст или `--yes` не заменяет approval.

## 12. Миграция проекта v0.4.0 (историческая процедура)

Историческое описание относится к переходу v0.4.0 → v0.4.1. В текущем v0.5.0 CLI поддерживается **прямая** миграция только с валидного v0.4.1/schema 5 и strict approved `PROJECT_INPUT@3`; v0.4.0 следует мигрировать последовательно. Новый Run до миграции запрещён. Активный Run блокирует миграцию без записи изменений.

Greenfield может использовать stored accepted input. Brownfield/Hybrid передаёт `PROJECT_INPUT@2` с отдельным `brownfield_baseline` approval. Повторный вызов возвращает `NO_ACTION` только после полной v0.4.1 validation. Полный порядок описан в [`../MIGRATION_FROM_v0.4.0.md`](../MIGRATION_FROM_v0.4.0.md).
