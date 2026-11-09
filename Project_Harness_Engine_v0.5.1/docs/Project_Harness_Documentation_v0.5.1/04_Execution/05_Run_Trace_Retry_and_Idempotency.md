# Run trace, retry, timeout и idempotency

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Run model

Task describes desired result. Each Run is one immutable attempt:

```text
Task
→ Run #1
  → Run Plan / Prompt Bundle / Context / Grants
  → Tool Invocations
  → Output Validation / Evidence
→ Run #2 (retry when allowed)
```

No separate canonical `Attempt` entity.

## 2. Run contract

```yaml
run:
  id: RUN-20260806-001
  task_ref: TSK-BACKEND-040@3
  attempt_no: 1
  previous_run_ref: null
  run_plan_ref: RNP-RUN-20260806-001
  input_revision: sha256:...
  prompt_bundle_ref: CPB-RUN-20260806-001
  adapter_ref: ADP-CODEX@1
  capability_grant_refs: [CGR-RUN-001]
  status: RUNNING
  tool_invocation_refs: []
  evidence_refs: []
  compensation_status: NOT_REQUIRED
```

## 3. Error taxonomy

```text
INPUT_STALE
CONSTRAINT_VIOLATION
POLICY_DENIED
CAPABILITY_UNAVAILABLE
CONTEXT_INCOMPATIBLE
ADAPTER_UNAVAILABLE
MALFORMED_OUTPUT
COMMAND_TIMEOUT
TOOL_FAILURE
SCOPE_VIOLATION
SIDE_EFFECT_UNCERTAIN
VALIDATION_FAILED
CANCELLED_BY_USER
INTERNAL_KERNEL_ERROR
```

## 4. Retry

Allowed only when error retryable, idempotency known, side effects absent/compensated, revisions/policies/grants current and retry budget permits. Invalid deterministic input is not retried endlessly.

## 5. Idempotency

```text
PURE
IDEMPOTENT
IDEMPOTENT_WITH_KEY
CONDITIONALLY_IDEMPOTENT
NON_IDEMPOTENT
UNKNOWN
```

`UNKNOWN` is treated as non-idempotent for automatic retry.

## 6. Timeout/external effects

Timeout does not prove no external effect. External writes use prepare/execute/durable-record/verify/compensate flow. Uncertain result creates reconciliation task.

## 7. Observability

Run Trace stores revisions, timings, tool results and technical compatibility necessary for recovery. It does not store provider billing, model-call cost or token ledger.
