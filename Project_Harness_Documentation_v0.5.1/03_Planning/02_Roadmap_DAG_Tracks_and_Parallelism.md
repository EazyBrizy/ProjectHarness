# Work Package DAG, tracks и безопасная параллельность

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Причинный граф

Harness uses DAG because definition/gates are ordered, while independent delivery tracks may proceed in one causal layer. Work Package groups one user outcome; atomic tasks are executable nodes.

## 2. Graph entities

```text
Work Package
Track
Atomic Task
Artifact
Decision/Contract/Bootstrap Task
Dependency Edge
Parallel Batch
Integration Task
Gate/Release Boundary
```

## 3. Dependency types

```text
REQUIRES_ARTIFACT
REQUIRES_DECISION
REQUIRES_ENVIRONMENT
REQUIRES_CAPABILITY
REQUIRES_VERIFICATION
REQUIRES_INTEGRATION
ORDER_ONLY
```

Every required artifact has producer, version/status and access mode. `ORDER_ONLY` needs rationale.

## 4. Readiness

Task is READY only when:

- schema and documentation refs valid;
- all required artifacts accepted/current;
- material decisions resolved;
- effective constraints computed;
- active primary skill and verification profile exist;
- compatible agent/tools/environment/capabilities available;
- base revisions current;
- no write/resource conflict;
- rollback/compensation defined;
- task not stale/cancelled/superseded.

## 5. Deterministic next task

```text
1. explicit user selection
2. critical-path unblock
3. risk/uncertainty reduction
4. integration dependency urgency
5. priority
6. reversible small step
7. stable task ID
```

## 6. Safe parallelism

For every resource domain:

```text
write(A) ∩ write(B) = ∅
write(A) ∩ read(B)  = ∅
read(A)  ∩ write(B) = ∅
```

Tasks may read the same accepted frozen contract revision. Planner checks paths, contracts, docs sections, DB migration head, lockfiles, generated outputs, config, test environments and external systems.

## 7. Worktrees/leases

Writing task receives isolated worktree/branch and leases for declared write/exclusive resources. Runtime compares actual writes with contract and stops scope violation.

## 8. Integration

After parallel tracks, integration task checks merge, contract compatibility, generated clients, combined tests, migration order, documentation sync and Work Package acceptance.

Full specifications: [`../12_Implementation_Specifications/07_Causal_Development_Sequence.md`](../12_Implementation_Specifications/07_Causal_Development_Sequence.md) and [`../12_Implementation_Specifications/08_Safe_Parallel_Execution.md`](../12_Implementation_Specifications/08_Safe_Parallel_Execution.md).

## 11. v0.5.0 active-stage planning fence

Stage path строится последовательно до target. Stage Plan outlines существуют для всех уровней пути, но detailed Work Packages, atomic Tasks, Context/Prompt Plans и compiled bundles разрешены только `STAGE_STATE.active_stage`.

Каждый executable artifact получает `implementation_stage`. `_next_runnable` фильтрует Task по active stage; future outline не входит в Task DAG. После acceptance следующая Stage пересчитывается от immutable baseline, а старые future assumptions получают stale/superseded semantics.
