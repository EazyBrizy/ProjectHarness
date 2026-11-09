# Независимая модель полноты проекта

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Principle

Source coverage proves only that supplied material was processed. Project readiness requires independent dimensions and profile-specific checks.

## 2. Dimensions

### User/request

Request classification, mode, expected result, current status and next route.

### Intake/questionnaire

Documentation analyzed, material gaps asked, answers/assumptions/unknowns traceable, question budget respected.

### Project/Brownfield definition

Problem/outcomes/users/scope/success, actual repository baseline and material conflicts.

### Requirements/constraints/decisions

Functional/quality requirements, hard/soft constraints, ADR materiality, authority and acceptance.

### Architecture/technology/contracts

Alternatives, boundaries, data, public contracts, versions, compatibility, migration/rollback.

### Skills/bootstrap/planning

Active skills, build/test/docs baseline, Work Packages, artifact producers, causal order and parallel safety.

### Prompt/context/runtime

JIT compilation, source maps, output/capability compatibility, governed adapter/tools and exact revisions.

### Verification/documentation

Proportional checks, test baseline/environment, evidence, docs sections/impact and Work Package acceptance.

### Security/recovery/evolution

Permissions/data policy, blockers/options/resume, idempotency/compensation, plane-specific updates and migrations.

## 3. Unknowns

Gate may pass with unknown only when materiality, owner, affected refs, latest responsible decision point and safe temporary plan are explicit. “Unknown accounted for” is not “known”.

## 4. No universal score

A single material gap can block a gate regardless of average completeness. Decisions use mandatory dimensions and accepted gaps, not one percentage.
