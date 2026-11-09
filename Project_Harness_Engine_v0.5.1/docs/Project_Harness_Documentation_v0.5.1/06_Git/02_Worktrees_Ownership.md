# Worktrees, leases и ownership

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Назначение

Ownership model предотвращает конфликт между параллельными задачами. Конфликт определяется не только по файлам, но и по contracts, documentation sections, database migration heads, generated artifacts, shared lockfiles и внешним environments.

## 2. Worktree policy

- writing task получает dedicated worktree, если repository поддерживает Git;
- worktree создаётся от зафиксированного base revision;
- один active writer допускается на каждый пересекающийся write target;
- user worktree и unrelated dirty changes не изменяются без отдельного решения;
- завершение Run не удаляет worktree до review/commit/cleanup route;
- cleanup является отдельным auditable action;
- отсутствие Git не отменяет logical ownership lease.

## 3. Ownership Lease Contract

```yaml
ownership_lease:
  id: LSE-TSK-BACKEND-040
  task_ref: TSK-BACKEND-040@3
  run_ref: RUN-20260806-0001
  repository_ref: REP-BACKEND-001
  base_revision: abc123

  resource_sets:
    paths:
      read:
        - services/backend/src/common/**
        - contracts/search/**
      write:
        - services/backend/src/search/**
        - services/backend/tests/search/**

    contracts:
      read: [CNT-SEARCH@2]
      write: []

    documentation:
      read: [DOC-API-SEARCH@2]
      write: [DOC-API-SEARCH]

    database:
      read: []
      write: []

    generated_artifacts:
      read: []
      write: []

    lockfiles:
      read: [LOCK-PNPM@1]
      write: []

    environments:
      shared_read: []
      exclusive_write: [ENV-TEST-BACKEND]

  acquired_at: 2026-08-06T10:00:00Z
  expires_at: 2026-08-06T12:00:00Z
  status: ACTIVE
```

Lease не выдаёт permission. Capability Grant проверяется отдельно.

## 4. Read/write semantics

Две задачи могут читать один и тот же frozen contract или documentation section параллельно. Конфликт существует, если write set одной задачи пересекает read или write set другой:

```text
write(A) ∩ write(B) ≠ ∅
write(A) ∩ read(B)  ≠ ∅
read(A)  ∩ write(B) ≠ ∅
```

Read/read overlap безопасен при одинаковой зафиксированной revision.

## 5. Path ownership

Paths нормализуются с учётом:

- symlinks and real paths;
- case sensitivity;
- submodules/worktree boundaries;
- generated outputs;
- ignored files;
- package boundaries;
- files created during Run.

Write outside lease scope блокируется wrapper enforcement, даже если prompt просит иначе.

## 6. Logical contract ownership

Logical contract может быть распределён по нескольким файлам/repositories. Примеры targets:

```text
api:/api/v1/session
schema:subjects
event:user-authenticated
config:oidc-session-policy
migration-head:primary-db
document-section:docs/api.md#session
```

Поэтому отсутствие path overlap недостаточно для разрешения parallel execution.

## 7. Exclusive resources

Отдельно регистрируются:

- database migration head;
- generated API client;
- dependency lockfile;
- release manifest;
- shared test database/environment;
- device/GPU;
- deployment slot;
- external service namespace;
- artifact alias;
- protected branch target.

## 8. Conflict resolution

При overlap Harness выбирает один из явных маршрутов:

```text
SERIALIZE_TASKS
CREATE_CONTRACT_FIRST_TASK
CREATE_INTEGRATION_OWNER
NARROW_TASK_SCOPE
SPLIT_RESOURCE
HANDOFF_LEASE
REQUEST_MATERIAL_PRIORITY
```

Нельзя разрешать конфликт только указанием «агентам быть осторожными».

## 9. Lease lifecycle

```text
REQUESTED → ACTIVE → RELEASED
                  ↘ EXPIRED
                  ↘ REVOKED
```

Потеря или expiry lease немедленно запрещает новые writes. Уже выполненный uncertain side effect проходит reconciliation; новый Run не повторяет его автоматически.

## 10. Parallel batch integration

Parallel batch фиксирует frozen inputs, leases, conflict analysis и integration task. Backend и frontend могут выполняться параллельно только после принятия общего API contract и не могут одновременно изменять его.

Подробный алгоритм: [`../12_Implementation_Specifications/08_Safe_Parallel_Execution.md`](../12_Implementation_Specifications/08_Safe_Parallel_Execution.md).
