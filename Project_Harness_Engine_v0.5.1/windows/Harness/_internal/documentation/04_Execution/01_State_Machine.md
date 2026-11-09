# State machine и публичные статусы

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Request

```text
RECEIVED → CLASSIFYING → CLASSIFIED → PLANNING → PLANNED → READY → EXECUTING → COMPLETED
                         ↘ WAITING_USER_INPUT | WAITING_APPROVAL
                         ↘ PARTIAL | BLOCKED | FAILED_RECOVERABLE
Any non-terminal → CANCELLED | SUPERSEDED
```

## 2. Work Package

```text
DRAFT → PLANNED → READY → IN_PROGRESS → COMPLETED
                         ↘ PARTIAL | BLOCKED
Any non-terminal → CANCELLED | SUPERSEDED
```

## 3. Task

```text
DRAFT → PLANNED → READY → CLAIMED → RUNNING → VERIFYING → DONE
                           ↘ BLOCKED | FAILED_RECOVERABLE | SPLIT
Any non-terminal → STALE | CANCELLED | SUPERSEDED
```

## 4. Run

Each Run is one attempt.

```text
PLANNED → READY → RUNNING → VERIFYING → SUCCEEDED
                       ↘ FAILED_RETRYABLE
                       ↘ FAILED_NON_RETRYABLE
                       ↘ BLOCKED | TIMED_OUT | CANCELLED
```

Retry creates a new Run with `attempt_no + 1` and `previous_run_ref`.

## 5. Change Pack and compensation

Change Pack:

```text
RECEIVED → QUARANTINED → ANALYZED → PROPOSED → VALIDATED → APPROVED
→ APPLIED → CANARY → ACTIVE
↘ REJECTED | ROLLED_BACK | FAILED_RECOVERABLE
```

Compensation status:

```text
NOT_REQUIRED
PENDING
COMPLETE
PARTIALLY_COMPENSATED
FAILED
```

`PARTIALLY_COMPENSATED` is not a general lifecycle status.

## 6. Public Result statuses

```text
ANSWERED
COMPLETED
PARTIAL
WAITING_DECISION
BLOCKED
FAILED_RECOVERABLE
NO_ACTION
CANCELLED
```

Kernel maps internal states to these statuses deterministically.

## 7. Transition invariants

- every transition emits an Event with previous/resulting revision;
- terminal/waiting state emits Result Envelope;
- `DONE/SUCCEEDED/COMPLETED` require applicable validation;
- stale input prevents execution;
- blocked state includes recovery and resume condition;
- history is append-only.

Full registry: [`../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md).

## 8. v0.4.1 entity-specific terminal mapping

Успешные terminal statuses назначаются по типу сущности, а не общим search/replace:

| Entity | Successful terminal |
|---|---|
| Agent Task Result | `COMPLETED` |
| Task | `DONE` |
| Run | `SUCCEEDED` |
| Work Package | `COMPLETED` |
| Task Report | `COMPLETED` |
| Public Result | `COMPLETED` |
| Project state | `COMPLETED` |
| Verification | `PASS` |

Новые Task/Run records со status `COMPLETED` невалидны. Для immutable history v0.4.0 validator явно сообщает compatibility mapping `Task COMPLETED → DONE` и `Run COMPLETED → SUCCEEDED` без перезаписи файлов.

## 12. v0.5.0 Stage и project execution lifecycles

```text
implementation_stage: PLANNED, ACTIVE, VERIFYING, ACCEPTED, BLOCKED, SUPERSEDED
project_execution:    ACTIVE, BLOCKED, TARGET_LEVEL_REACHED, CANCELLED
```

Для schema-v6 final ordinary mandatory Task не переводит Project в `COMPLETED`. Runtime сначала выполняет deterministic Gate-readiness evaluation на final product tree:

```text
ACTIVE + ordinary work complete
  ├─ exact evidence gaps → ACTIVE / STAGE_ACCEPTANCE_PREPARATION → VERIFYING
  └─ evidence needs already closed ─────────────────────────────→ VERIFYING
VERIFYING + valid open formal review → BLOCKED / RESOLVE_STAGE_GATE
BLOCKED + resume-stage-gate → ACTIVE preparation | VERIFYING
VERIFYING + closed formal review → ACCEPTED
```

Только successful closed Gate/approval transaction создаёт accepted baseline. Acceptance target stage устанавливает `TARGET_LEVEL_REACHED`, который может быть продолжен explicit level-up. Gate-related `BLOCKED` не является execution/safety blocker и не возобновляется ordinary `resume` route.

Legacy v0.4.x `COMPLETED` остаётся compatibility-only historical value и не доказывает accepted implementation level.

## 13. v0.5.0 internal Stage transaction lifecycle

Stage transaction status является internal recovery fact, а не заменой public Result status:

```text
PREPARED → APPLYING → COMMITTED
PREPARED/APPLYING → ROLLING_BACK → ROLLED_BACK
unverifiable recovery → RECOVERY_REQUIRED / blocking diagnostic
```

Terminal marker разрешён только после full-write-set digest verification. Public command success возвращается только вместе с durable/verified `COMMITTED`; operation error после apply возвращается только после durable/verified `ROLLED_BACK` либо explicit recovery-blocked diagnostic.

