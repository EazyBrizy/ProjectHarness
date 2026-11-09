# Совместимость исполнения и capability resolution

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Назначение

Compatibility resolution proves that a READY Task can be executed by a specific Agent/Model/Tool/Environment combination without weakening requirements or permissions.

## 2. Required dimensions

```text
INPUT/OUTPUT SCHEMA
AGENT ADAPTER
MODEL/CONTEXT
TOOLS AND VERSIONS
DATA POLICY
CAPABILITY GRANTS
REPOSITORY/WORKTREE
TEST ENVIRONMENT
SIDE-EFFECT/IDEMPOTENCY
```

## 3. Compatibility result

```yaml
compatibility_result:
  id: CMP-RUN-001
  task_ref: TSK-EXAMPLE-001@1
  adapter_ref: ADP-CODEX@1
  required_capabilities: []
  available_capabilities: []
  context_status: ACCEPTED
  data_policy_status: PASS
  environment_status: PASS
  output_schema_status: PASS
  verdict: COMPATIBLE
  reductions: []
  fallbacks: []
```

## 4. Verdicts

```text
COMPATIBLE
COMPATIBLE_WITH_REDUCTION
FALLBACK_REQUIRED
WAITING_DECISION
UNSUPPORTED
```

Reduction may remove optional context/tooling only. Mandatory requirement, constraint, evidence source or output field cannot be reduced.

## 5. Fallback

Fallback selection is explicit and recorded. Examples: local model/profile, alternate tool, task split, context source extraction, manual approval route. Unsupported task becomes Blocker with options.

## 6. Boundary

Context size is evaluated only for technical compatibility. No provider price, payment, token ledger or cost routing is created.

Related specifications: JIT compilation and Codex Adapter in section 12.
