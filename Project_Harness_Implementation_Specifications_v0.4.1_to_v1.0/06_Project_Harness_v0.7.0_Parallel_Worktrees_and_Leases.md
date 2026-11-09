# Project Harness v0.7.0 — Parallel Worktrees, Local Ownership Leases и Integration Batches

**Базовая версия:** Project Harness Engine v0.6.1  
**Целевая версия:** v0.7.0  
**Тип релиза:** MINOR / conservative local parallel execution  
**Статус документа:** NORMATIVE IMPLEMENTATION SPECIFICATION  
**Зависимости:** полностью принятые v0.4.1–v0.6.1; automatic parallel execution требует v0.5.1 и Git commit path v0.6.0  
**Порядок реализации:** шестой документ серии

## 1. Назначение версии

v0.7.0 позволяет выполнять несколько независимых READY-задач параллельно в одном локальном Git repository, не смешивая рабочие копии и изменения.

Canonical route:

```text
READY tasks
→ declared access sets
→ conservative conflict analysis
→ Parallel Batch
→ atomic local leases
→ dedicated Git worktree/branch per Task
→ sandboxed Runs
→ independent verification and local commits
→ dedicated integration task/worktree
→ combined verification
```

Параллельность является opt-in оптимизацией. Если безопасность нельзя доказать, Harness выполняет задачи последовательно.

## 2. Не входит в scope

v0.7.0 не должна включать:

- distributed leases;
- multi-node workers;
- remote multi-user scheduler;
- polyrepo parallel execution;
- cross-repository atomic commit;
- automatic merge в protected/default branch;
- arbitrary semantic source-code conflict inference;
- speculative task splitting ради concurrency;
- dynamic увеличение write scope;
- parallel execution в manual handoff mode;
- shared mutable production environments;
- database migration namespace allocator;
- general-purpose resource scheduler;
- максимизацию throughput за счёт ослабления safety rules.

Для polyrepo или неоднозначного repository boundary Runtime остаётся serial.

## 3. Preconditions

Parallel Batch разрешён только если:

- repository `GIT_LOCAL` и один canonical root;
- все Tasks принадлежат одной active Implementation Stage;
- каждая Task `READY`;
- между Tasks нет causal DAG dependency;
- Task Contracts и Access Sets frozen;
- base revision один и тот же;
- active skill revisions/digests frozen;
- adapter/sandbox profiles compatible;
- conflict analysis `PASS`;
- integration task определена;
- concurrency policy включена;
- `max_concurrency == 2`;
- automatic executor available;
- user canonical worktree не имеет conflicting unknown changes.

Default configuration после migration:

```yaml
parallel_execution:
  enabled: false
  max_concurrency: 2
  lease_backend: LOCAL_ATOMIC_FILES
  conflict_policy: CONSERVATIVE
  failure_policy: CONTINUE_INDEPENDENT_TASKS
```

## 4. Access Set Contract

Каждая Task получает декларативные read/write sets.

В scope v0.7.0 входят только следующие domains:

```text
REPOSITORY_PATHS
DEPENDENCY_LOCKFILES
DATABASE_MIGRATION_HEAD
GENERATED_OUTPUTS
TEST_ENVIRONMENTS
RELEASE_MANIFESTS
```

Контракты и документация выражаются через repository paths либо frozen refs. Полный универсальный logical-resource language не требуется.

Пример:

```yaml
access_sets:
  repository_paths:
    read:
      - contracts/search/**
      - src/shared/types/**
    write:
      - src/backend/search/**
      - tests/backend/search/**
  dependency_lockfiles:
    read:
      - LOCK-PNPM@4
    write: []
  database_migration_head:
    read:
      - primary@12
    write: []
  generated_outputs:
    read: []
    write: []
  test_environments:
    shared_read: []
    exclusive_write:
      - ENV-TEST-BACKEND
  release_manifests:
    read: []
    write: []
```

Rules:

- paths normalized relative to repository root;
- absolute paths, `..` escape и unresolved symlink scopes запрещены;
- empty/unknown write set не означает unrestricted write;
- generated output producer обязан объявить output directory;
- lockfile writer conflicts with every Task reading/writing same lockfile;
- migration-head writer exclusive;
- shared mutable test environment exclusive unless separate per-Run environment IDs доказаны.

## 5. Conflict Analysis

Использовать существующий prefix `CFA`.

Для каждой пары A/B проверяется:

```text
write(A) ∩ write(B) = ∅
write(A) ∩ read(B)  = ∅
read(A)  ∩ write(B) = ∅
```

Та же логика применяется к special resources.

### 5.1. Conservative path comparison

v0.7.0 не обязана реализовывать полный theorem prover glob patterns. Поддерживается ограниченный, детерминированный subset:

- exact file;
- directory prefix `path/**`;
- normalized repository-relative path;
- project-defined aliases, уже resolved в exact/prefix sets.

Если patterns сложнее и disjointness нельзя доказать:

```text
analysis: UNKNOWN
route: SERIALIZE_TASKS
```

Не допускается предположение «скорее всего не пересекутся».

### 5.2. Conflict Analysis record

```yaml
conflict_analysis:
  id: CFA-PROJECT-PBT-001
  revision: 1
  base_revision: abc123
  task_refs:
    - TSK-PROJECT-BE-001@2
    - TSK-PROJECT-FE-001@1
  comparisons:
    - left: TSK-PROJECT-BE-001@2
      right: TSK-PROJECT-FE-001@1
      path_result: DISJOINT
      special_resource_result: DISJOINT
      dependency_result: NONE
      status: PASS
  unresolved_patterns: []
  decision: PARALLEL_SAFE
  status: PASS
```

Любое изменение Task revision, base, Stage, skill, access set или frozen input делает analysis `STALE`.

## 6. Parallel Batch Contract

Использовать существующий prefix `PBT`.

```yaml
parallel_batch:
  id: PBT-PROJECT-SEARCH-001
  revision: 1
  work_package_ref: WP-PROJECT-SEARCH-001@1
  implementation_stage: BETA
  base_revision: abc123
  task_refs:
    - TSK-PROJECT-BE-001@2
    - TSK-PROJECT-FE-001@1
  frozen_inputs:
    - ref: DOC-PROJECT-API-SEARCH@2
      digest: sha256:...
    - ref: ADR-PROJECT-SEARCH-001@1
      digest: sha256:...
  conflict_analysis_ref: CFA-PROJECT-PBT-001@1
  lease_refs: []
  integration_task_ref: TSK-PROJECT-INT-001@1
  failure_policy: CONTINUE_INDEPENDENT_TASKS
  status: READY
```

Batch не может менять membership после `READY`. Изменение создаёт новую revision и освобождает старые leases.

## 7. Local Ownership Lease

Использовать prefix `LSE` и существующий lifecycle:

```text
REQUESTED → ACTIVE → RELEASED
                  ↘ EXPIRED
                  ↘ REVOKED
```

Lease является coordination record, а не permission. Capability Grants и Task scope проверяются отдельно.

```yaml
ownership_lease:
  id: LSE-PROJECT-BE-001
  revision: 1
  batch_ref: PBT-PROJECT-SEARCH-001@1
  task_ref: TSK-PROJECT-BE-001@2
  run_ref: RUN-PROJECT-BE-001@1
  repository_ref: REP-PROJECT-001@2
  base_revision: abc123
  resources:
    repository_paths:
      write:
        - src/backend/search/**
        - tests/backend/search/**
    dependency_lockfiles:
      write: []
    database_migration_head:
      write: []
    generated_outputs:
      write: []
    test_environments:
      exclusive_write:
        - ENV-TEST-BACKEND
  acquired_at: ...
  expires_at: ...
  heartbeat_at: ...
  owner_process_id: <opaque-local-id>
  status: ACTIVE
```

## 8. Lease backend

Первая реализация:

```text
LOCAL_ATOMIC_FILES
```

Canonical Lease records сохраняют существующий contract path:

```text
.harness/runtime/LEASES/<LEASE_ID>.yaml
```

Ephemeral atomic resource keys хранятся отдельно и не входят в export:

```text
.harness/runtime/LEASE_LOCKS/<RESOURCE_KEY_HASH>.lock
```

Lease record содержит state/events; lock file существует только для atomic local exclusion. Это не меняет существующий `ownership_lease` storage contract и не смешивает history с coordination primitives.

Acquisition:

1. canonicalize all resource keys;
2. sort keys lexicographically;
3. acquire all locks in sorted order using atomic create (`O_CREAT|O_EXCL`);
4. validate no stale conflicting active record;
5. write lease record durably;
6. if any acquisition fails, release all newly acquired keys;
7. only then transition lease to `ACTIVE`.

Это предотвращает partial lease set и снижает deadlock risk.

Lease file не считается безопасным при network filesystem semantics, которые не гарантируют local atomic create. v0.7.0 поддерживает local filesystem only.

## 9. TTL и heartbeat

Automatic executor обновляет heartbeat. Rules:

- TTL bounded и больше expected heartbeat interval;
- expiry не удаляет lease silently;
- expired lease переходит `EXPIRED` после reconciliation;
- process death не означает автоматически, что внешние side effects отсутствуют;
- перед reuse worktree/resource Kernel проверяет container/process state и actual repository state;
- manual force-revoke требует approval и reason.

Новый write после expiry запрещён. Sandbox wrapper должен проверять active lease перед Run start и перед apply/commit.

## 10. Dedicated worktree per Task

Actual worktree directory находится вне canonical repository:

```text
<configured-runtime-root>/<project-id>/worktrees/<BATCH_ID>/<TASK_ID>/
```

В `.harness/runtime/WORKTREE_BINDINGS/` хранится только canonical binding metadata. Это исключает рекурсивное размещение Git worktree внутри project/control tree и упрощает export/cleanup.

Git branch:

```text
harness/<task-id>-<slug>
```

Creation algorithm:

1. verify repository base revision;
2. verify branch/worktree name not conflicting;
3. create branch at exact base;
4. create worktree;
5. validate clean index/worktree;
6. bind Task/Run/Lease refs in metadata;
7. provide worktree as canonical product root for v0.5.1 disposable execution;
8. never mount user’s primary worktree to agent.

A Task worktree remains until:

- Task result verified;
- local commit created;
- integration succeeds or recovery decision made;
- cleanup route records branch/worktree disposition.

`git worktree remove --force` is not automatic for uncertain state.

## 11. Scheduler

Добавить optional scheduler module:

```text
parallel/scheduler.py
parallel/conflicts.py
parallel/leases.py
parallel/worktrees.py
parallel/batches.py
parallel/integration.py
```

Scheduling algorithm:

1. collect causally READY Tasks active stage;
2. exclude non-Git/polyrepo/manual-only tasks;
3. group only within same Work Package/outcome when integration route known;
4. build pairwise conflict matrix;
5. choose deterministic safe set up to `max_concurrency`;
6. create Batch/Analysis;
7. acquire leases atomically;
8. create worktrees;
9. launch v0.5.1 executions;
10. monitor outcomes;
11. create/activate integration task after eligible member completion.

Tie-breaking must be deterministic, for example:

```text
priority → topological order → task ID
```

No adaptive priority engine is required.

## 12. Runtime write enforcement

Static analysis до Run недостаточен. После agent execution actual writes проверяются против:

```text
Task write scope
∩ active Lease write resources
∩ sandbox writable product root
```

Scope violation:

```text
stop apply
→ Run BLOCKED or FAILED_RETRYABLE
→ preserve diff evidence
→ revoke/release lease after reconciliation
→ recompute Batch safety
```

Harness не расширяет lease автоматически по attempted write.

## 13. Special resource rules

### 13.1. Dependency lockfiles

Две Tasks не могут параллельно менять один lockfile. Даже Task, которая только читает lockfile, конфликтует с writer. Dependency changes лучше выделять в отдельную prerequisite/integration Task.

### 13.2. Database migrations

Один migration head — один writer lease. Две migration-writing Tasks на одном head сериализуются. Namespace allocator вне scope.

### 13.3. Generated outputs

Один output directory — один producer. Consumers читают frozen generated revision. Producer generation часто переносится в integration task.

### 13.4. Test environments

Если tests используют общий mutable DB/service, нужен exclusive environment lease. Per-Run isolated environment может иметь уникальный `ENV` resource и не конфликтовать.

### 13.5. Release manifest

Любая запись в общий version/release manifest сериализуется либо выполняется integration owner.

## 14. Failure policy

v0.7.0 поддерживает одну policy:

```text
CONTINUE_INDEPENDENT_TASKS
```

Это уменьшает scheduler scope. Pause при изменении shared/frozen input является обязательным invariant, а не отдельной настраиваемой policy. `FAIL_FAST_BATCH` и другие варианты остаются вне v0.7.0.

Rules:

- failure независимой Task не останавливает уже running disjoint Task;
- изменение/corruption frozen input останавливает batch;
- lease loss останавливает affected Task и блокирует integration;
- Task success не означает Batch success;
- failed member может быть retried в новой Run revision/worktree state, если base/frozen inputs unchanged;
- material replan создаёт новую Batch revision.

## 15. Integration Task и Integration Batch

Integration task обязательна. Она не должна быть скрытой процедурой scheduler.

Integration worktree создаётся от exact batch base либо approved integration branch state. Затем Harness применяет verified task commits в детерминированном порядке:

```text
priority → task ID
```

Предпочтительный mechanism первой версии:

```text
cherry-pick exact verified commits
```

Алгоритм:

1. проверить все required member commits/evidence;
2. проверить frozen inputs;
3. создать integration worktree/branch;
4. cherry-pick commits по order;
5. при conflict остановиться без auto-resolution;
6. выполнить combined verification;
7. проверить contract compatibility и final diff;
8. создать integration commit/evidence;
9. только после PASS Work Package может стать `COMPLETED`.

Auto-merge в main/protected branch не выполняется. Дальнейший push/PR использует v0.6.0.

## 16. Integration conflict route

При cherry-pick conflict создаётся blocker с options:

```text
CREATE_EXPLICIT_INTEGRATION_FIX_TASK
SERIALIZE_AND_REPLAN
DROP_FAILED_MEMBER_WITH_SCOPE_REVIEW
REQUEST_USER_DECISION
```

Harness не выбирает конфликтные строки автоматически. Integration fix является новой Task с собственным scope и lease.

## 17. Frozen inputs и staleness

Перед каждым member apply/commit и перед integration проверяются digests:

- base revision;
- Task Contract;
- accepted contract/document refs;
- Stage State;
- active skill refs;
- adapter/sandbox profiles;
- Conflict Analysis;
- Batch membership.

Любое изменение:

```text
Batch/Run Plan → STALE
new conflict analysis required
```

Уже successful immutable Run сохраняется как evidence, но его commit может потребовать revalidation against new base.

## 18. CLI

Добавить:

```bash
project-harness parallel-plan --project <root>
project-harness parallel-execute --project <root> --batch <ref>
project-harness batch-status --project <root> --batch <ref>
project-harness integrate-batch --project <root> --batch <ref>
project-harness lease-status --project <root>
project-harness lease-revoke --project <root> --lease <ref> --approval <record> --reason <text>
project-harness parallel-cleanup --project <root> --batch <ref> --approval <record>
```

`parallel-plan` может вернуть `NO_ACTION` и serial recommendation. Это нормальный безопасный результат.

### 18.1. Строгая parallel configuration

Project configuration получает:

```yaml
parallel_execution:
  enabled: false
  max_concurrency: 2
  lease_backend: LOCAL_ATOMIC_FILES
  conflict_policy: CONSERVATIVE
  failure_policy: CONTINUE_INDEPENDENT_TASKS
```

В v0.7.0 `max_concurrency` имеет единственное поддерживаемое значение `2`. Это даёт реальную параллельность без преждевременного general scheduler. `enabled: true` требует automatic executor, local Git repository и successful parallel doctor.

Versioning:

```text
PROJECT_INPUT.schema_version: 7
SCHEMA-PROJECT-PREPARATION-INPUT@7
Harness canonical SCHEMA_VERSION: 10
Migration: MIG-ENGINE-0.6.1-TO-0.7.0
```

## 19. Statuses и schemas

`statuses.yaml` v0.4.0 уже содержит canonical `parallel_batch` group:

```text
DRAFT
PLANNED
READY
IN_PROGRESS
INTEGRATING
PARTIAL
BLOCKED
COMPLETED
STALE
CANCELLED
SUPERSEDED
```

v0.7.0 должна использовать эти значения без создания второго vocabulary:

- execution members active → `IN_PROGRESS`;
- переход к integration task → `INTEGRATING`;
- combined integration PASS → `COMPLETED`;
- material membership/revision replacement → `SUPERSEDED`.

Lease lifecycle также уже существует. Изменение `statuses` registry требуется только если validation metadata/contract reference отсутствуют; сами перечисленные values не переименовываются.

Schemas:

```text
access_sets.schema.json
conflict_analysis.schema.json
parallel_batch.schema.json
ownership_lease.schema.json
worktree_binding.schema.json
integration_result.schema.json
```

`access_sets` встраивается в Task revision и требует обновления Task schema; отдельный top-level entity для него не создаётся.

### 19.1. Contract catalog и registry versions

В `contracts.yaml` добавить:

```yaml
conflict_analysis:
  id_prefix: CFA
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/runtime/CONFLICT_ANALYSES/{id}@{revision}.yaml
  revision_policy: IMMUTABLE
worktree_binding:
  id_prefix: ART
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/runtime/WORKTREE_BINDINGS/{id}.yaml
  revision_policy: IMMUTABLE
integration_result:
  id_prefix: EVD
  persistence: PERSISTENT
  lifecycle: IMMUTABLE_RECORD
  storage_path: .harness/evidence/INTEGRATION/{id}.yaml
  revision_policy: IMMUTABLE
```

`parallel_batch` и `ownership_lease` уже зарегистрированы в v0.4.0; их paths/lifecycles не дублируются. Expected registry versions:

```text
REG-CONTRACT-CATALOG: 7 → 8
REG-ID-PREFIXES:      остаётся 4
REG-STATUSES:         остаётся 7
```

## 20. Migration v0.6.1 → v0.7.0

- `parallel_execution.enabled: false`;
- `max_concurrency: 2`;
- существующие Tasks получают no implicit Access Sets; они остаются serial;
- Planner может предложить access sets только для новых/replanned Tasks;
- existing branches/worktrees не импортируются автоматически как Harness-owned;
- completed commit evidence сохраняется;
- polyrepo projects получают `SERIAL_ONLY`.

## 21. Crash recovery

При startup Runtime выполняет reconciliation:

1. найти active lease files;
2. проверить owner process/container;
3. проверить worktree existence/status;
4. проверить Run status/evidence;
5. классифицировать lease как active, expired-uncertain или releasable;
6. не запускать новый writer до решения uncertainty;
7. сохранить event log.

Worktree с uncommitted changes после crash quarantined. Он не удаляется и не переиспользуется автоматически.

## 22. Тестовый план

### 22.1. Conflict analysis

- disjoint directory writers PASS;
- write/write overlap conflict;
- write/read overlap conflict;
- shared read PASS at same digest;
- complex unknown glob serializes;
- lockfile writer conflicts;
- migration head writer conflicts;
- generated output conflict;
- environment exclusive conflict;
- dependency edge blocks same batch.

### 22.2. Leases

- atomic acquisition;
- sorted all-or-none locking;
- concurrent conflicting acquire: only one succeeds;
- release/expiry/revoke transitions;
- heartbeat;
- expired uncertain resource not reused;
- local filesystem precondition;
- actual write requires active lease.

### 22.3. Worktrees

- exact base creation;
- user worktree unchanged;
- one branch/worktree per Task;
- crash preserves uncertain worktree;
- verified commit belongs to correct Task/base;
- cleanup auditable;
- polyrepo rejected to serial.

### 22.4. Batch/runtime

- max concurrency respected;
- deterministic task selection;
- independent failure policy;
- frozen input mutation makes batch stale;
- scope violation blocks affected Task;
- integration required before WP completion;
- cherry-pick conflict creates blocker;
- combined tests required;
- no automatic protected-branch merge.

## 23. Критерии приёмки v0.7.0

Версия готова, когда:

1. parallel mode opt-in и default disabled;
2. поддерживается только local single-repository Git mode и ровно две одновременные Task executions;
3. conflict analysis консервативен и serializes unknown cases;
4. read/write intersections проверяются по paths и заявленным shared resources;
5. leases выдаются atomic local backend;
6. каждая writing Task имеет dedicated worktree/branch;
7. actual writes проверяются против Task и active Lease;
8. frozen input change делает Batch stale;
9. independent Task failure не обязательно останавливает disjoint work;
10. обязательная integration task применяет exact verified commits;
11. combined verification обязательна до Work Package completion;
12. conflict не разрешается автоматически;
13. primary user worktree и protected branch не изменяются;
14. crash recovery сохраняет uncertain artifacts;
15. distributed/polyrepo parallelism остаётся вне scope.

## 24. Порядок реализации

1. Добавить Access Set schema и planner population.
2. Реализовать deterministic Conflict Analyzer.
3. Реализовать Local Atomic Lease backend и concurrency tests.
4. Реализовать worktree binding/cleanup lifecycle.
5. Добавить optional scheduler и Batch contract.
6. Интегрировать automatic executor/sandbox per worktree.
7. Интегрировать commit evidence per member.
8. Реализовать integration worktree/cherry-pick route.
9. Добавить combined verification и WP Gate.
10. Реализовать crash reconciliation.
11. Выполнить stress/concurrency test matrix.
12. Оставить serial fallback для любого недоказанного случая.

v0.8.0+ заменит local coordination authority сервером только в remote mode; semantics Batch/Lease должны остаться теми же.
