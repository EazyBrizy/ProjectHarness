# Требования и сквозная трассировка

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Цель

Every material source statement is normalized as goal, requirement, quality attribute, constraint, assumption, unknown, decision or informational context. Duplicate/conflicting/superseded/out-of-scope classification is explicit.

## 2. Full trace chain

```text
User Request / Source / Answer / Decision
→ Project Definition and Outcome
→ Requirement + Quality Attribute + Effective Constraints
→ ADR / Architecture / Technology / Contract Artifact
→ Work Package
→ Atomic Task + Documentation Sections
→ Prompt/Context/Run Plan + Capability Grant
→ Run + Actual Changed Artifacts
→ Verification Checks
→ Evidence + Task Report + Documentation Update
→ Result Envelope + State Event + Next Route
```

## 3. Requirement contract

```yaml
requirement:
  id: REQ-SEARCH-001
  statement: "Пользователь может искать книги по части названия"
  type: FUNCTIONAL
  priority: MUST
  epistemic_status: CONFIRMED
  source_refs: [SRC-DOC-003]
  outcome_refs: [OUT-SEARCH-001]
  constraint_refs: []
  documentation_refs:
    - document: docs/requirements/search.md
      section_id: search-by-name
  acceptance_criteria:
    - id: AC-SEARCH-001
      statement: "Поиск возвращает частичное совпадение"
      verification_phase: REQUIRED_NOW
  architecture_refs: [ADR-API-004]
  work_package_refs: [WP-SEARCH-001]
  task_refs: []
  verification_refs: []
  status: ACCEPTED
```

## 4. Quality attributes

Quality requirement uses scenario where possible:

```text
stimulus → environment → response → measurable acceptance
```

Words like fast/reliable/secure without a measurable or bounded interpretation create question/assumption, not automatically ready requirement.

## 5. Coverage statuses

```text
UNASSESSED
ACCEPTED
PLANNED
IN_PROGRESS
IMPLEMENTED_UNVERIFIED
VERIFIED
DEFERRED_BY_DECISION
OUT_OF_SCOPE_BY_DECISION
SUPERSEDED
BLOCKED
```

`IMPLEMENTED_UNVERIFIED` is not completion.

## 6. Gates

- Definition: outcomes/scope/success traceable.
- Architecture/Technology: MUST requirements covered or explicitly deferred.
- Planning: accepted requirement linked to Work Package/task/non-code artifact.
- Task: criteria linked to checks and documentation impact.
- Integration/Release: release-scope MUST has current PASS evidence and constraints pass/waiver.

## 7. Constraint and documentation coverage

```text
Constraint → applicable artifacts/tasks/runs → evaluator → PASS/waiver evidence
Documentation requirement → task impact → changed section → validation evidence
```

## 8. Change

Changing a requirement preserves previous revision, source delta, impact map, successor mapping and stale evidence. Deleting text from a source does not automatically delete a feature.
