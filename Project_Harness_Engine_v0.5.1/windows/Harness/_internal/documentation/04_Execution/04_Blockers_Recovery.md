# Blockers, recovery и resume

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. No dead-end invariant

Harness does not guarantee the original approach is possible. It guarantees at least one safe next route: answer/approve, prepare environment, create artifact, retry, replan, split, change approach/scope, replace dependency, defer or cancel.

## 2. Blocker classes

```text
BLOCKED_USER_DECISION
BLOCKED_APPROVAL
BLOCKED_DEPENDENCY
BLOCKED_ARTIFACT
BLOCKED_CAPABILITY
BLOCKED_ENVIRONMENT
BLOCKED_CONSTRAINT
BLOCKED_CONFLICT
BLOCKED_STALE_STATE
BLOCKED_EXTERNAL_SYSTEM
BLOCKED_SECURITY
```

## 3. Required fields

- Request/Work Package/Task/Run refs;
- class and stopped safe point;
- reason/impact/evidence;
- safe progress and side effects;
- minimal affected scope;
- independent READY tasks;
- 1+ recovery options;
- recommendation;
- exact resume condition.

## 4. Resume

```text
satisfy selected option
→ record recovery evidence
→ evaluate resume condition
→ revalidate task/current revisions
→ discard stale plans
→ JIT compile new bundle
→ create new Run
→ return Result referencing original blocker
```

## 5. Hard constraints

Hard constraint is never weakened automatically. If it forbids the original action, options change approach/scope, request allowed waiver, replace dependency, defer or cancel.

## 6. Scope and compensation

Blocker should be task/work-package local unless a global invariant or canonical corruption justifies project-wide stop. Runtime failure records rollback/compensation and uncertain external effects before retry.

## 7. Persisted Stage Gate blocker

`STAGE_GATE_BLOCKER` создаётся только когда `accept-stage` уже получил structurally valid, exact-bound formal review, но хотя бы один mandatory outcome/criterion/hard constraint/profile control остаётся `UNKNOWN`, `PARTIAL` или `FAIL` либо permitted-use boundary не подтверждена. Это не execution/safety blocker:

- current Task/Run отсутствуют;
- current Stage Plan и Gate имеют новые immutable `BLOCKED` revisions;
- Gate хранит exact formal conclusions, missing/failed items и candidate evidence diagnostics;
- project state имеет `project_status: BLOCKED`, `next_route: RESOLVE_STAGE_GATE`;
- Acceptance Report и следующая Stage не создаются.

Schema errors, invalid `NOT_APPLICABLE`, wrong refs и invalid evidence bindings не создают blocker и не меняют state.

Dedicated recovery:

```bash
project-harness resume-stage-gate --project <root>
```

Команда разрешена только для одного OPEN Gate blocker, повторно вычисляет canonical product baseline и exact evidence candidates, затем одной transaction создаёт новые revisions:

```text
missing final-baseline evidence → BLOCKED → ACTIVE / STAGE_ACCEPTANCE_PREPARATION
all evidence needs closed       → BLOCKED → VERIFYING / STAGE_GATE_REVIEW
```

Blocked Plan/Gate/blocker history не переписывается. Repeated recovery returns the current route idempotently. Ordinary Task `block/resume` rejects Gate blockers and remains unchanged.

## 8. Stage transaction recovery

Stage mutation failure не преобразуется в обычный resumable blocker, пока local canonical state не reconciled. Runtime сначала проверяет journal/backups и достигает ровно одного terminal состояния:

```text
all expected new digests present → COMMITTED
otherwise, with complete verified backups → ROLLED_BACK
corrupt or ambiguous recovery evidence → mutation blocked
```

Pending transaction автоматически reconciles перед новой Stage mutation и при `validate-project`. Повтор recovery terminal journal не меняет canonical state. Missing/corrupt backup запрещает speculative rollback и требует восстановления trusted transaction evidence или trusted project copy.

Render failure после canonical Stage commit имеет `FAILED_RECOVERABLE` только для derived view regeneration; сама transition остаётся `COMMITTED`.

Full specification: [`../12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md`](../12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md).
