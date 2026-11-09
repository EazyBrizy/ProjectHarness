# Project Definition и discovery

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Назначение

Project Definition is the first accepted semantic baseline. It says what project/outcome is being built, not exactly how it will be implemented.

## 2. Mandatory dimensions

```text
problem and desired outcome
target users/stakeholders
success criteria
in/out/deferred scope
system boundary and integrations
profile candidate
constraints/invariants
assumptions/unknowns/risks
decision authority
data/security/operation context
expected release shape
project ambiguity mode
```

## 3. Draft contract

```yaml
project_definition:
  id: PJD-PROJECT-001
  revision: 1
  status: DRAFT
  session_ref: SES-20260806-001
  source_refs: [SRC-DOC-001]

  name: example-project
  mode: GREENFIELD
  problem_statement: "..."
  user_refs: []
  outcome_refs: []
  goal_refs: []
  success_criterion_refs: []

  scope:
    in: []
    out: []
    deferred: []

  proposed_profile_refs: [PRF-WEB-APPLICATION]
  constraint_refs: []
  assumption_refs: []
  unknown_refs: []
  risk_refs: []
  authority_refs: []
  ambiguity_mode: PRAGMATIC

  dimension_statuses:
    purpose: CONFIRMED
    users_and_scale: ASSUMED_WITH_OWNER_AND_REVIEW_TRIGGER
    data_and_security: UNKNOWN_WITH_DECISION_PLAN
```

Identifier aliases from v0.2 are migrated through registry; machine schema selects the final prefix consistently.

## 4. Discovery behavior

```text
analyze sources
→ extract confirmed/candidate facts
→ detect conflicts/material gaps
→ ask bounded question batches
→ record answers as sources/events
→ create assumptions/unknown plans
→ rebuild draft
→ show readiness summary
```

No architecture or product implementation is accepted before the gate.

## 5. Assumptions and unknowns

Assumption includes owner, rationale, impact if false, validation/review trigger and affected refs. Unknown includes materiality, owner, resolution route and blocking gates. Empty fields are invalid.

## 6. Scope control

```text
IN_SCOPE
OUT_OF_SCOPE
DEFERRED
PROPOSED
SUPERSEDED
```

New desire discovered later becomes proposal/Change Pack; it is not silently added.

## 7. Gate

```text
ACCEPT
ACCEPT_WITH_ASSUMPTIONS
CONTINUE_DISCOVERY
REJECT
```

`ACCEPT_WITH_ASSUMPTIONS` is prohibited for unresolved material security/data/public-contract boundary.

## 8. Output and next route

- accepted Project Definition;
- goals/success/scope registries;
- assumptions/unknowns/risks;
- profile decision;
- source map;
- Result Envelope;
- next route: brownfield reconciliation or requirements/architecture preparation.

Questionnaire specification: [`../12_Implementation_Specifications/21_Project_Start_Questionnaire.md`](../12_Implementation_Specifications/21_Project_Start_Questionnaire.md).
