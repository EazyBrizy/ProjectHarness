# Implementation Levels и Stage Plans

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE THEMATIC VIEW

## 1. Назначение

Implementation Level определяет глубину, надёжность и evidence burden для уже принятого project scope. Он не добавляет функции и не заменяет profile, execution mode или deployment model.

```text
effective stage requirements
= level defaults
+ accepted project constraints
+ profile-mandatory controls
+ explicit acceptance criteria
```

Hard constraint действует на любой стадии. Например, regulated data может потребовать ранние security controls, но это оформляется explicit override и не превращает Prototype в Beta.

## 2. Canonical scale

| Level | Основная цель | Gate boundary |
|---|---|---|
| `PROTOTYPE` | Доказать один полезный end-to-end core flow | Чистый accepted baseline запускается локально; core flow работает в declared use boundary |
| `ALPHA` | Рабочая версия для разработчика или небольшой внутренней группы | Внутренний пользователь устанавливает и выполняет основные операции без постоянного вмешательства автора |
| `BETA` | Ограниченный пилот для реальных пользователей | Основные сценарии работают; critical core defects отсутствуют; rollback доказан |
| `MVP` | Минимальный production-продукт | Пользователь получает value; owner способен deploy/observe/recover/support |
| `RELEASE` | Полностью подготовленный accepted release scope | Checklist, обязательные checks и approvals закрыты; critical defects отсутствуют |

Порядок единственный и последовательный:

```text
PROTOTYPE → ALPHA → BETA → MVP → RELEASE
```

`MVP` имеет display name `Production MVP`. `UNSURE`, `UNKNOWN` и `NONE` не являются уровнями scale: это decision/intake sentinel values с ограниченной применимостью.

## 3. Intake semantics

Target level спрашивается после source analysis и core outcome, но до Architecture, Technology и Work Packages. В approved input обязательна секция:

```text
implementation.target_level
implementation.claimed_current_level
```

Правила:

- target принимает только пять canonical values;
- Greenfield claimed value равен `NONE`;
- Brownfield/Hybrid claimed value может быть canonical level либо `UNKNOWN`;
- `UNSURE` возвращает `WAITING_DECISION` до явного выбора;
- `active_stage`, `observed_candidate_level` и `highest_accepted_level` не являются user-editable intake facts.

Для внешнего intake workspace, где Stage State ещё не создан, current target читается только из текущего `PROJECT_INPUT.yaml`. При `prepare` принятый input сохраняется в `.harness/state/PROJECT_INPUT_ACCEPTED.yaml` как immutable historical record. Его `implementation.target_level` является **initial accepted target** и не переписывается последующими `level-up`.

## 4. Stage path

Planner строит маршрут от `PROTOTYPE` до target включительно. Примеры:

```text
target PROTOTYPE → [PROTOTYPE]
target BETA      → [PROTOTYPE, ALPHA, BETA]
target MVP       → [PROTOTYPE, ALPHA, BETA, MVP]
```

Пропуск стадии запрещён. Brownfield baseline transaction может последовательно принять несколько уже доказанных стадий, но создаёт отдельный immutable acceptance report для каждой.

## 5. Stage State

Canonical state хранится по exact path `.harness/stages/STAGE_STATE.yaml` и разделяет:

- target level текущего цикла;
- claimed current level пользователя;
- observed candidate level assessment;
- highest accepted level;
- единственную active stage;
- sequential stage path;
- revision и ссылки на последнее acceptance/assessment.

Поле `current_level` запрещено, потому что смешивает мнение, наблюдение, доказанный baseline и разрешённую execution stage.

Для подготовленного Project Instance единственным canonical current-cycle target является `.harness/stages/STAGE_STATE.yaml -> implementation.target_level`. Поля `.harness/config/PROJECT.yaml -> project.target_implementation_level` и `.harness/state/CURRENT_STATE.yaml -> state.target_implementation_level` являются согласованными projections этого значения и изменяются вместе с Stage State в одной Stage transaction. После `level-up` initial accepted target в `PROJECT_INPUT_ACCEPTED.yaml` может отличаться от current target и не считается ошибкой. Routing, planning, maturity assessment, status/rendering и validation подготовленного проекта используют Stage State, а не immutable accepted input.

## 6. Stage Plan

Для каждой стадии пути создаётся revisioned Stage Plan в `.harness/stages/PLANS/`. Он фиксирует level, target, accepted baseline ref, scope refs, required outcomes, criteria profile, hard-constraint overrides, Work Package outlines и deferred work.

Только active Stage Plan может содержать detailed Work Package refs. Future Stage Plan:

- имеет status `PLANNED`;
- хранит только outline и expected outcomes;
- не содержит atomic Tasks или compiled prompts;
- пересматривается после принятия предыдущего baseline;
- не является обязательством выполнить заранее предположенные детали.

## 7. Active-stage detail boundary

Детализируются только:

```text
active Stage Plan
→ Work Packages
→ atomic Tasks
→ Context Plans
→ Prompt Plans
→ one current JIT Prompt Bundle
```

Каждый Work Package, Task, Run Plan, Prompt Plan и Compiled Prompt Bundle несёт `implementation_stage`. Runtime выдаёт или компилирует artifact только при равенстве Stage State `active_stage`.

## 8. Prompt fence

Compiled prompt обязан явно передать current stage, target level и запрет future-stage-only work. Полезное будущее улучшение записывается в Next Stage Gap Backlog, но не реализуется текущей Task без прямого hard constraint.

Сознательная реализация future-only mechanism классифицируется как `STAGE_SCOPE_VIOLATION`. Это scope failure, а не повод автоматически активировать следующую стадию.

## 9. Replanning после acceptance

Переход строится только от принятого baseline:

```text
accepted baseline
→ recompute next-stage delta
→ explicit review при material change
→ create active-stage atomic plan
→ JIT compile current READY Task
```

Completed Runs и accepted reports остаются неизменяемыми. Future plans на старых assumptions получают новую revision либо `SUPERSEDED`/`STALE` semantics.

## 10. Governed same-level maintenance

Bugfix, documentation repair, refactoring или стабилизация принятого baseline не обязаны повышать maturity. Публичный route `MAINTAIN_CURRENT_STAGE` запускается только формальным exact-bound plan:

```bash
project-harness start-maintenance --project <root> --plan <record>
```

Plan проходит strict `SCHEMA-MAINTENANCE-PLAN@1` validation и связывается с текущими `highest_accepted_level`, target, `last_acceptance_ref` и accepted scope. Он содержит objective/rationale, start Decision `DEC-*`, actor `ACT-*`, atomic Work Package/Tasks, verification rules и явные rollback/cancel constraints. `implementation_stage` плана, WP и каждой Task обязан точно равняться `highest_accepted_level`; `future_stage_work` всегда `FORBIDDEN`.

Start разрешён, только когда accepted level существует и нет active Run, stage-planning application, Gate transition или другого open maintenance WP. Governed start materializes immutable Decision and plan, revisioned WP/Tasks, DAG, Verification Profiles, Context/Prompt Plans, maintenance indexes/current state, `NEXT_TASK` и ровно один idempotent first JIT bundle. Все executable artifacts несут:

```yaml
implementation_stage: <highest_accepted_level>
maintenance_route: MAINTAIN_CURRENT_STAGE
maintenance_plan_ref: <exact RQP-...@revision>
```

Task execution использует обычный `next → verify → complete`. Завершение последней mandatory Task переводит maintenance WP в `COMPLETED`, создаёт immutable `MAINTENANCE_COMPLETION` report с Decision/Task Report/Run/evidence refs, очищает maintenance current state и восстанавливает предыдущий valid route. Stage acceptance не запускается; target, `highest_accepted_level`, accepted Stage Plan/Gate/Acceptance revisions и completed Runs не меняются.

Отмена требует отдельной strict formal Decision:

```bash
project-harness cancel-maintenance --project <root> --approval <record>
```

До completed product-changing Task open Tasks/WP могут быть атомарно переведены в `CANCELLED` и previous route восстановлен. Если completed Task помечена product-changing или её Task Report показывает product changes, silent cancel запрещён; требуется завершить route либо использовать уже существующий governed compensation/rollback route. Автоматический rollback не создаётся. Exact replay того же plan/Decision идемпотентен; conflicting reuse тех же immutable identifiers отклоняется, а historical WP/Task/Run/report revisions сохраняются.

`level-up` блокируется только пока maintenance WP имеет open status (`PLANNED`, `READY`, `IN_PROGRESS`, `BLOCKED`). После valid `COMPLETED`, `CANCELLED` или `SUPERSEDED` route больше не препятствует повышению target.

## 11. Invariants

1. Level изменяет implementation depth, не product scope.
2. Stage path последовательный и не содержит пропусков.
3. Active stage единственна.
4. Future stage не получает executable artifacts.
5. Hard constraints не откладываются из-за низкого level.
6. Accepted history не переписывается.
7. Target ниже accepted level не создаёт destructive downgrade plan.
8. Stage Plan status и Gate status согласованы с Stage State.
9. В подготовленном проекте `PROJECT`, `CURRENT_STATE` и все current-target consumers согласованы с canonical target из Stage State.
10. Initial accepted target в immutable `PROJECT_INPUT_ACCEPTED` может исторически отличаться от current-cycle target после `level-up`.
11. Maintenance artifacts всегда bound к `highest_accepted_level` и не меняют accepted maturity.
12. Open maintenance WP блокирует level-up; terminal maintenance history его не блокирует.
13. Maintenance cancel не выполняет silent rollback и не переписывает completed product-changing history.

## 12. Источники

Нормативные contracts и acceptance criteria: [`../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md`](../12_Implementation_Specifications/24_Implementation_Levels_Stage_Planning_and_Brownfield_Maturity_v0.5.0.md). Machine scale: [`../registries/implementation_levels.yaml`](../registries/implementation_levels.yaml).

## PH‑F03 — планирование следующей активной стадии через публичный CLI/API

**Текущая инструкция для оператора:** [сквозной runbook PH‑F07](../08_Distribution/04_Operator_Runbook_v0.5.0.md), §§ 6–8. Он различает неизменённый draft без дополнительной DEC, reviewed edits внутри scope и material scope divergence, а также отвергаемый stale baseline. PH‑F03 остаётся историческим implementation пакетом, а не новой версией договора.

Сразу после успешного `accept-stage`, когда target ещё не достигнут, или после
`level-up` из `TARGET_LEVEL_REACHED` Stage State устанавливает
`next_route: PLAN_ACTIVE_STAGE`; `next` показывает `STAGE_PLANNING_REQUIRED`.
Только **следующий последовательный уровень** разрешён: после принятого Prototype
активируется Alpha, после принятого MVP при `level-up RELEASE` — Release.
Предыдущий accepted baseline, last Acceptance Report и принятый product scope
не пересоздаются и не переписываются.

### Операторский runbook

В каталоге исходного Engine или через установленную команду `project-harness`:

```bash
project-harness stage-status --project /path/to/project
project-harness next --project /path/to/project
project-harness prepare-active-stage-plan --project /path/to/project --output /tmp/active-stage-review.json
: 'Проверьте строгое содержимое active_stage_plan_review и scope каждого Task.'
project-harness plan-active-stage --project /path/to/project --plan /tmp/active-stage-review.json
project-harness next --project /path/to/project
project-harness validate-project --project /path/to/project
```

При запуске из распакованного Engine поддерживается равнозначный вариант:
`python project-harness.py <command> <flags>`. `--output` — файл JSON
(также принимается JSON-синтаксис с `.yaml` расширением) **вне** product root,
либо в `.harness/operator/`. Подготовка только записывает operator draft;
она не активирует Stage, не изменяет canonical state и не утверждает
решение. Повторный вывод в тот же путь с отличным содержимым требует
`--force`. Код API:
`project_harness.stages.prepare_active_stage_plan(root, output_path, force=False)`
и `project_harness.stages.plan_active_stage(root, plan_path)`.

### Contract `SCHEMA-ACTIVE-STAGE-PLAN-REVIEW@1`

Внешний record имеет один envelope `active_stage_plan_review`; JSON Schema
лежит в `schemas/active_stage_plan_review.schema.json`. Read-only preparation
формирует machine-validated поля:

- `schema_version: 1`, `schema_ref`, `record_kind: ACTIVE_STAGE_PLAN_REVIEW`,
  `id: RQP-...`, `revision: 1`, `route: PLAN_ACTIVE_STAGE`;
- `binding`: current Stage State revision и digest, `highest_accepted_level`,
  `active_stage`, canonical `target_level`, exact Stage Plan/Gate ref и digest,
  exact last Acceptance Report ref и digest, accepted/current product tree
  baselines, immutable scope/input digests и (при наличии) завершённую
  maintenance report ref/digest;
- `planning_basis`: `required_outcomes`, level criteria, profile controls,
  hard constraints, accepted requirements/constraints, scope in/out,
  predecessor `next_stage_gaps`, known limitations, permitted use и
  список существующих product files;
- `work_packages`: текущая Stage, атомарные Tasks с exact criterion refs,
  зависимостями, ограниченными path scopes, routes, verification и
  acceptance criteria; `candidate_work_digest` фиксирует исходное предложение;
- `review: {material_change: false, scope_confirmed: true, decision: null}`;
  `future_stage_work: FORBIDDEN`.

Для **неизменённого** draft отдельный формальный approval не создаётся:
вызов `plan-active-stage` считается явным принятием подготовленного
плана только внутри ранее принятого scope. Изменение `work_packages`
(например, Task purpose/verification) требует `review.decision` со
строгим `kind: ACTIVE_STAGE_PLAN_REVIEW`, canonical
`id: DEC-<record-id-without-RQP->-REVIEW`, `approved: true`,
`actor: ACT-*`, ISO date-time `approved_at` и непустым `rationale`.
Новые requirements, future-stage Tasks, защищённые paths и
`review.material_change: true` блокируются даже при формальном review:
изменение принятого scope должно проходить отдельный предусмотренный
процесс изменения, а не подменяться Stage planning.

### Application и продолжение

`plan-active-stage` перед любой записью перепроверяет все bindings,
текущий product-tree digest, согласованность last accepted history и
отсутствие текущего Run, незавершённого Gate, конкурирующего planning и
открытой maintenance. Если baseline изменился после принятого Stage,
требуется подтверждённая завершённая maintenance; её report связан
с exact last Acceptance и current draft. Stale/malformed records отклоняются
**без** Stage mutation.

Governed application делает один journaled `PLAN_ACTIVE_STAGE` commit:
новые revisioned active Stage Plan и Gate, Work Packages/Tasks,
dependency DAG, отдельные Verification/Context/Prompt Plans, indexes,
`STAGE_STATE`, `CURRENT_STATE` и `NEXT_TASK`. Gate сохраняет точные
outcome/criterion/profile/hard-constraint bindings; одна первая Task получает
`READY` и JIT bundle. Положительный результат: `STAGE_PLANNED` и
`first_jit.status: READY_FOR_CODEX`. Повтор идентичного `--plan` после
COMMITTED — идемпотентный replay; не создаёт повторный Run/Task/Gate.

При сбое **до commit** Stage transaction восстанавливается через
существующий `recover_stage_transactions`; ID `ROLLED_BACK` больше не
используется. После recovery оператор выпускает draft заново командой
`prepare-active-stage-plan --force`, получает новый ID с суффиксом
повторной попытки, проверяет его и запускает `plan-active-stage`.
При interruption **после commit** повтор того же `plan-active-stage`
получает persisted commit result и пытается восстановить первый JIT;
план/accepted history не дублируются. При recoverable ошибке JIT можно
выполнить `next --project <root>`.

План не исполняет продуктовые команды и не утверждает Stage Gate.
Внешний Codex/оператор последовательно выполняет `next → verify → complete`,
затем обязательную subject-specific Gate proof процедуру PH‑F02 и
формальный `accept-stage`. Само наличие compiled JIT **не доказывает**
достижение criteria и не меняет highest accepted level.
