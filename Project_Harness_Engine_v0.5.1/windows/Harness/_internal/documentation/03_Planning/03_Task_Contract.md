# Декомпозиция, Work Package и Task Contract

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Правило

```text
Request → one Work Package per user outcome → minimum sufficient atomic tasks
```

Work Package is not executed. Agent runs one atomic READY task or an approved safe parallel batch.

## 2. Split criteria

Split when there are independent outcomes, material decision plus implementation, incompatible skills/permissions/write scopes, multiple deployables, separate artifact producers/consumers, unrelated acceptance or rollback boundaries.

Do not split by file/function/command when changes share one result, scope, skill and verification.

## 3. Work Package contract

```yaml
work_package:
  id: WP-SEARCH-001
  revision: 1
  request_refs: [RQ-20260806-001]
  objective: "Пользователь ищет записи по названию"
  requirement_refs: [REQ-SEARCH-001]
  architecture_refs: [ADR-API-004]
  documentation_refs: [DOC-REQ-SEARCH@2]
  mandatory_task_refs:
    - TSK-CNT-SEARCH-010
    - TSK-BE-SEARCH-020
    - TSK-FE-SEARCH-030
    - TSK-INT-SEARCH-040
  dependency_graph_ref: DAG-WP-SEARCH-001@1
  aggregation_rule: ALL_MANDATORY_PASS
  status: READY
```

## 4. Task contract

```yaml
task:
  id: TSK-BE-SEARCH-020
  revision: 1
  work_package_ref: WP-SEARCH-001
  implementation_stage: PROTOTYPE
  title: "Реализовать backend search endpoint"
  type: IMPLEMENT
  track: BACKEND

  purpose: "Серверная реализация принятого search contract"
  expected_result: "Endpoint соответствует CNT-SEARCH@2"

  requirement_refs: [REQ-SEARCH-001]
  constraint_refs: []
  architecture_refs: [ADR-API-004]
  documentation:
    source_refs: []
    impact: UPDATE_EXISTING
    required_updates: []

  depends_on_tasks: [TSK-CNT-SEARCH-010]
  requires_artifacts:
    - ref: CNT-SEARCH@2
      producer_task_ref: TSK-CNT-SEARCH-010
      required_status: ACCEPTED
      access: READ
  produces_artifacts: []

  scope:
    read: []
    write: [src/backend/search/**, tests/search/backend/**]
    forbidden: [src/frontend/**]

  access_sets:
    contracts:
      read: [CNT-SEARCH@2]
      write: []
    documentation:
      read: []
      write: [docs/api/search.md#endpoint-search]

  route:
    primary_skill_ref: SKL-UNIVERSAL-IMPLEMENT@3
    supporting_skill_refs: []
    required_capabilities: [FILESYSTEM_WRITE, COMMAND_EXECUTE]

  prompt_spec_ref: PSP-IMPLEMENT@1
  context_policy_ref: CTP-TASK-STANDARD@1
  verification_profile_ref: VFP-CODE-TARGETED-001@1
  acceptance_criteria: []
  rollback: {strategy: REVERT_WORKTREE}
  status: PLANNED
```

## 5. Lifecycle

```text
DRAFT → PLANNED → READY → CLAIMED → RUNNING → VERIFYING → DONE
                           ↘ BLOCKED | FAILED_RECOVERABLE | SPLIT
Any non-terminal → STALE | CANCELLED | SUPERSEDED
```

`DONE` requires all REQUIRED_NOW checks and resolved documentation impact.

## 6. Runtime split

Original task becomes `SPLIT`, child tasks inherit traceability and a new aggregation rule. Original history is retained and not executed again.

## 7. Staleness

Change to applicable requirement, constraint, ADR, contract, skill, verification profile, repository base or documentation source revision makes task/prompt plan stale and requires readiness re-evaluation.

Full contract: [`../12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md`](../12_Implementation_Specifications/03_Work_Packages_Tasks_and_Subtasks.md).
