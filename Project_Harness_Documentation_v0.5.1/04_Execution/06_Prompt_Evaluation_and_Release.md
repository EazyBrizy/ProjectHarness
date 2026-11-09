# Evaluation prompts, routing, skills и documentation semantics

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Levels

| Suite | Checks |
|---|---|
| Compiler | Module order, variables, hashes, source maps, JIT readiness. |
| Routing | Request Class/Mode/Operation, decomposition and next route. |
| Constraint/Permission | Inheritance, conflicts, grants and forbidden actions. |
| Context | Required sources, overflow, staleness and data boundaries. |
| Skill | Lifecycle/readiness, behavior and negative cases. |
| Adapter | Codex structured output, tool mediation and stop signals. |
| Behavioral | Fixture repositories and expected result/evidence. |
| Adversarial | Injection, scope escape, secret/data egress and permission bypass. |
| Recovery | Retry, timeout, cancellation, blocker/resume and compensation. |
| Cross-profile | No project/profile leakage. |
| Semantic docs | Registries, IDs, statuses, links, contracts and aggregate drift. |

## 2. Deterministic first

Schemas, IDs, refs, permissions, write sets, state transitions and exact forbidden actions use deterministic assertions. Semantic judging only supplements them.

## 3. Release lifecycle

Prompt/Skill/Adapter revision:

```text
DRAFT → VALIDATION → REGRESSION/ADVERSARIAL → REVIEW → CANARY → ACTIVE
```

Regression below threshold blocks activation. Rollback restores previous active revision without rewriting run history.

## 4. Fixtures

Every fixed defect adds regression fixture. Maintenance Change Pack selects affected suites through impact analysis.

## 5. Documentation release

Archive release additionally requires semantic documentation validator, generated combined guides, file index, checksums and archive integrity PASS.
