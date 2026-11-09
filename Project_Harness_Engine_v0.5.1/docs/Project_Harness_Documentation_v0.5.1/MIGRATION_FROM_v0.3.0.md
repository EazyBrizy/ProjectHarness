# Migration notes: documentation v0.3.0 → v0.3.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE PATCH MIGRATION

## 1. Scope

v0.3.1 is a documentation-normalization patch. It preserves the product vision, greenfield/brownfield workflows, single-entry model, JIT prompts, governance and maintenance architecture.

## 2. Identifier migration

Implementation Work Package references migrate as follows:

```text
HNS-000 → WP-HARNESS-000
...
HNS-120 → WP-HARNESS-120
```

`HNS-REQ-*` remains the documentation-requirement namespace. No canonical product entity changes prefix.

## 3. Enum migration

Internal Operations now use the exact values in `registries/request_routing.yaml`. Old shorthand values such as `COMPILE`, `RUN`, `VALIDATE`, `REPORT` and `RESUME` are not emitted by new Request Plans.

Invalid examples migrate as follows:

```text
Questionnaire Session: IN_PROGRESS → QUESTIONING
Questionnaire dimension: ASSUMED_WITH_REVIEW_TRIGGER → ASSUMED_WITH_OWNER_AND_REVIEW_TRIGGER
Blocker: ACTIVE → OPEN
Skill prohibited operation: PUSH → GIT_PUSH
Test Baseline ID: TBL-* → TSB-*
```

## 4. Contract field migration

```text
BrownfieldBaseline.actual_structure_ref → accepted_actual_structure_ref
BrownfieldRouteItem.risk → estimated_risk
ParallelBatch.leases → lease_refs
ProjectDefinition.success_criteria_refs → success_criterion_refs
Task.documentation_refs → documentation
ChangePack.proposed_changes → normalized_changes
ChangePack.requested_capabilities → required_capabilities
```

Project Definition draft and accepted variants remain valid only in the combinations defined by `registries/contracts.yaml`.

## 5. Request idempotency

Repeatable transport calls must map their idempotency header/metadata to `request.idempotency_key`. Existing v0.3.0 samples without the field must be upgraded before conformance validation.

## 6. Delivery migration

Core MVP now ends at one complete, governed vertical loop. Parallel batches, automated worktrees/leases and full Change Pack activation remain planned hardening and retain their roadmap packages.

## 7. Validation

A v0.3.1 package passes only when the validator confirms registry matrices, contract aliases/variants, lifecycle applicability, capabilities, roadmap IDs and generated artifacts.
