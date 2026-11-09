# Безопасное параллельное выполнение задач

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Harness должен разрешать параллельную работу только там, где задачи причинно готовы и не могут повредить результаты друг друга. Типичный пример — backend и frontend после принятия общего API contract.

Параллельность является оптимизацией. Correctness, traceability и интеграция имеют приоритет.

## 2. Read/write model

Каждая task объявляет sets по нескольким ресурсным доменам:

```yaml
access_sets:
  repository_paths:
    read: [contracts/search/**, src/shared/types/**]
    write: [src/backend/search/**]

  contracts:
    read: [CNT-SEARCH@2]
    write: []

  documentation:
    read: [docs/api/search.md#endpoint-search]
    write: [docs/implementation/backend-search.md]

  database:
    read: [schema@12]
    write: []

  environment:
    read: [ENV-TEST-APP]
    write: []

  shared_artifacts:
    read: [LOCK-NPM@4]
    write: []
```

Домены должны поддерживать минимум:

- repository paths;
- public/internal contracts;
- documentation sections;
- database schema and migration head;
- dependency lockfiles;
- generated clients/code;
- shared configuration;
- test environments;
- release manifests;
- external systems.

## 3. Условие безопасной параллельности

Для каждой пары задач A и B должно выполняться:

```text
write(A) ∩ write(B) = ∅
write(A) ∩ read(B)  = ∅
read(A)  ∩ write(B) = ∅
```

Одинаковый read-only artifact разрешён, если обе task закреплены на одной accepted revision.

Дополнительно:

- обе tasks находятся в `READY`;
- нет causal dependency A→B или B→A;
- нет exclusive environment/capability lease conflict;
- integration route определён;
- rollback одной task не отменяет обязательный результат другой;
- shared contract frozen на время batch.

## 4. Parallel Batch Contract

```yaml
parallel_batch:
  id: PBT-SEARCH-001
  work_package_ref: WP-SEARCH-001
  task_refs:
    - TSK-DB-SEARCH-020
    - TSK-BE-SEARCH-030
    - TSK-FE-SEARCH-040

  frozen_inputs:
    - ref: CNT-SEARCH@2
      hash: sha256:...
    - ref: ADR-SEARCH-004@1
      hash: sha256:...

  conflict_analysis_ref: CFA-PBT-SEARCH-001
  lease_refs:
    - LSE-WT-BACKEND-001
    - LSE-WT-FRONTEND-001
    - LSE-DB-SCHEMA-001

  integration_task_ref: TSK-INT-SEARCH-050
  failure_policy: CONTINUE_INDEPENDENT_TASKS
  status: READY
```

## 5. Frozen contract rule

Frontend и backend могут читать один API contract. Они не могут одновременно менять его.

```text
Contract status ACCEPTED
→ revision/hash frozen in batch
→ all consumers compile against that revision
→ proposed change creates new Change Pack
→ affected tasks pause or finish under old revision by explicit policy
```

Contract writer task является отдельной causal prerequisite и не входит в consumer batch.

## 6. Worktrees и ownership

Для Git-backed проектов рекомендуется:

- отдельный worktree/branch на task;
- lease на write paths;
- task-scoped base revision;
- no implicit push;
- merge/integration owner;
- pre-merge conflict and stale checks.

Lease не заменяет declared scope. Даже при технической возможности agent не должен писать вне Task Contract.

## 7. Special shared resources

### 7.1. Dependency lockfile

Если две tasks могут изменить один lockfile, они конфликтуют. Варианты:

- объединить dependency changes;
- назначить одну dependency task;
- последовательный merge/rebase gate;
- использовать isolated package scopes, если lockfiles действительно независимы.

### 7.2. Database migrations

Две migration-writing tasks нельзя параллелить на одном migration head без reservation protocol. Допустимы:

- migration sequence lease;
- заранее выделенные non-conflicting namespaces, если framework поддерживает;
- отдельная integration migration task.

### 7.3. Generated clients

Producer contract может быть frozen, но генерация одного и того же client output directory двумя tasks запрещена. Генерацию следует вынести в одну producer task.

### 7.4. Test environment

Shared mutable environment требует lease или per-run isolation. Read-only use разрешён при доказанной изоляции test data.

## 8. Failure policy

```text
FAIL_FAST_BATCH
CONTINUE_INDEPENDENT_TASKS
PAUSE_ON_SHARED_INPUT_RISK
```

Default — `CONTINUE_INDEPENDENT_TASKS`, если failure не влияет на frozen inputs и shared environment. При подозрении на contract/environment corruption batch приостанавливается.

## 9. Integration Gate

После завершения parallel tasks integration task выполняет:

- merge/rebase checks;
- contract compatibility;
- cross-component tests;
- database/app ordering;
- documentation reconciliation;
- combined acceptance criteria;
- release readiness impact.

Нельзя объявлять Work Package `COMPLETED` только потому, что все parallel tasks по отдельности зелёные.

## 10. Пример backend/frontend

```text
TSK-CNT-SEARCH-010  принимает CNT-SEARCH@2        DONE

Parallel Batch:
  TSK-DB-SEARCH-020 writes migrations/search/**
  TSK-BE-SEARCH-030 writes backend/search/**
  TSK-FE-SEARCH-040 writes frontend/search/**
  all read CNT-SEARCH@2

TSK-INT-SEARCH-050:
  merge + generated client + e2e + docs
```

Если frontend task хочет изменить contract, она возвращает `WAITING_DECISION` или создаёт change proposal, но не редактирует frozen contract.

## 11. Dynamic conflict detection

До run выполняется static analysis declared sets. Во время run Tool Adapter проверяет actual writes. Если actual write выходит за scope:

```text
stop tool action
→ record SCOPE_VIOLATION
→ mark run FAILED_RECOVERABLE or BLOCKED
→ preserve evidence
→ recompute batch safety
```

Нельзя автоматически расширять write scope по факту попытки.

## 12. Критерии приёмки

1. Две tasks могут читать один frozen contract параллельно.
2. Любое write/read или write/write пересечение блокирует batch.
3. Planner учитывает paths, contracts, docs, DB, lockfiles и environments.
4. Worktrees и leases привязаны к task/run.
5. Actual writes проверяются runtime adapter.
6. Failure одной independent task не обязательно останавливает весь batch.
7. Integration task обязательна для общего user outcome.
8. Parallel batch пересчитывается при staleness или изменении shared input.
