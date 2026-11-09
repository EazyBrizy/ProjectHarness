# Изолированный Harness Maintenance Plane

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Пользователь должен иметь возможность одним natural-language запросом изменить маршрутизацию, prompt modules, skills, schemas или другие элементы Harness. Такое изменение не должно смешиваться с текущей feature development и не должно незаметно менять правила уже выполняемой задачи.

## 2. Три плоскости изменений

```text
PRODUCT
PROJECT_CONTROL
HARNESS_DISTRIBUTION
```

| Plane | Что изменяет | Пример |
|---|---|---|
| `PRODUCT` | Код, инфраструктуру, данные, документацию создаваемого проекта. | Добавить endpoint. |
| `PROJECT_CONTROL` | `.harness/` конкретного проекта: local routes, prompts, skills, policies, adapters. | Изменить project-specific skill. |
| `HARNESS_DISTRIBUTION` | Universal kernel, schemas, generic modules, profiles, adapters, migrations. | Добавить новый Request Class. |

Один Change Pack имеет ровно один `target_plane`. Mixed-plane пакет запрещён.

## 3. Maintenance Request

Natural-language запрос:

> Пропатчь маршрутизацию: bug-fix задачи должны сначала проверять наличие reproduction test.

Классифицируется как `PROJECT_CONTROL_MAINTENANCE` или `HARNESS_DISTRIBUTION_MAINTENANCE` в зависимости от scope. Harness показывает выбранный plane до применения.

## 4. Change Pack Contract

```yaml
change_pack:
  id: CHP-20260806-001
  revision: 1
  request_ref: RQ-20260806-0020

  kind: PROJECT_CONTROL_MAINTENANCE
  target_plane: PROJECT_CONTROL
  target_project_ref: project-example
  target_distribution_ref: null
  mixed_plane: FORBIDDEN

  objective: "Добавить reproduction gate для bug-fix routes"
  affected_entities:
    - SKL-PROJECT-BUG-FIX@2
    - PLC-ROUTING-BUG-FIX@1

  normalized_changes: []
  migration_plan_ref: MIG-CHP-001
  impact_analysis_ref: IMP-CHP-001
  evaluation_plan_ref: EVS-CHP-001
  rollback_plan_ref: RBP-CHP-001

  required_capabilities: [PROJECT_CONTROL_WRITE]
  status: PROPOSED
```

## 5. Maintenance lifecycle

```text
RECEIVED
→ QUARANTINED
→ ANALYZED
→ PROPOSED
→ VALIDATED
→ APPROVED
→ APPLIED
→ CANARY
→ ACTIVE
```

Альтернативные lifecycle outcomes:

```text
REJECTED
ROLLED_BACK
FAILED_RECOVERABLE
```

Отдельное поле `compensation_status` может иметь `PARTIALLY_COMPENSATED`; это не lifecycle status Change Pack.

`QUARANTINED` означает, что входящий patch не влияет на active runtime до validation/approval.

Определение `kind` и `target_plane` выполняется при приёме, но не создаёт отдельный lifecycle status `CLASSIFIED`.

## 6. Протокол применения

```text
1. Resolve target plane and scope.
2. Snapshot current control/distribution revision.
3. Parse requested semantic change.
4. Produce normalized Change Pack.
5. Run impact analysis over routes, tasks, skills, prompts, schemas and migrations.
6. Build migration and rollback plans.
7. Apply changes in isolated maintenance workspace.
8. Run structural, behavioral, adversarial and compatibility suites.
9. Ask approval for material semantics.
10. Activate through atomic pointer/version switch where possible.
11. Mark affected future plans/tasks stale.
12. Observe canary and rollback on policy threshold.
```

## 7. Project Control Maintenance

Может изменять только project-local:

- routing policies;
- Prompt Modules/Specs;
- project skills;
- Context Policies;
- verification profiles;
- adapter configuration;
- project schemas/extensions;
- generated guidance templates.

Не может изменять universal semantics или schemas без distribution migration. Не может одновременно менять product code.

## 8. Harness Distribution Maintenance

Может изменять:

- kernel behavior;
- core contracts and registries;
- universal profiles;
- generic prompts and skills;
- adapters;
- migrations;
- semantic validator;
- release packaging.

Требует:

- `HARNESS_DISTRIBUTION_WRITE` capability;
- отдельного repository/worktree;
- version bump;
- migration and compatibility declaration;
- cross-profile regression;
- distribution archive integrity check;
- rollback/reinstall path.

## 9. Влияние на текущую разработку

Active run использует immutable bundle и grants. Maintenance activation:

- не меняет уже завершённый или выполняющийся bundle;
- может запретить дальнейшие tool calls только при emergency security policy;
- помечает queued plans `STALE`;
- пересчитывает READY tasks;
- показывает affected Work Packages;
- не изменяет product files.

При emergency suspension создаётся explicit event и Result Envelope, а не скрытая остановка.

## 10. One-prompt patch UX

Пользователь может сформулировать изменение одним сообщением. Harness обязан сам:

- определить target plane;
- показать scope;
- задать вопрос только при material ambiguity;
- создать Change Pack;
- провести проверки;
- вернуть, что изменено в routes/prompts/skills/schemas;
- перечислить invalidated tasks/plans;
- дать rollback reference.

«Одним промтом» означает один пользовательский request, но не отменяет внутренних этапов validation и approval.

## 11. Evaluation requirements

Для routing/prompt/skill change обязательны:

- structural schema checks;
- positive route fixtures;
- negative/misrouting fixtures;
- material ambiguity fixture;
- scope/permission adversarial fixture;
- representative project profile fixtures;
- old-version compatibility or migration fixture;
- canary outcome comparison.

## 12. Rollback

Rollback восстанавливает previous active revision/pointer. Он не удаляет history:

```yaml
rollback_result:
  change_pack_ref: CHP-20260806-001
  restored_revision: sha256:...
  compensation_status: COMPLETE
  affected_runs: []
  affected_queued_tasks: [TSK-FIX-020]
```

Если migration необратима, Change Pack не может быть approved без explicit restore/forward-fix strategy.

## 13. Критерии приёмки

1. Product, Project Control и Distribution changes не смешиваются.
2. Один пользовательский request создаёт isolated Change Pack.
3. Active runs не переписываются после activation.
4. Future prompt plans/tasks инвалидируются детерминированно.
5. Routing/prompt/skill changes проходят behavioral and negative fixtures.
6. Material semantics требуют approval.
7. Rollback and migration всегда определены.
8. Result Envelope показывает scope, изменения, проверки и affected routes.
