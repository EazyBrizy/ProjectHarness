# Acceptance criteria v0.4.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 0. Release-slice rule

- `[CORE]` — обязательный gate первого end-to-end vertical release.
- `[HARDENING]` — остаётся обязательным для соответствующего roadmap slice, но не блокирует Core MVP.
- Пункт без явного tag считается `[CORE]`.

## 1. Single entry and results

- [ ] `[CORE]` Natural-language endpoint executes query/start/development/control; evolution and maintenance are at least classified and planned. `[HARDENING]` enables their full execution routes.
- [ ] Query creates no product task.
- [ ] Request/Plan/Trace and Result Envelope are schema-valid.
- [ ] Every waiting/terminal route returns exact next step.

## 2. Intake

- [ ] Every project start creates Questionnaire Session.
- [ ] First question is about documentation.
- [ ] Typical greenfield draft requires 7–12 answers and ≤15 before draft.
- [ ] Source-known answers are not asked again.
- [ ] `UNKNOWN` produces safe assumption/decision plan.
- [ ] Brownfield inventory is read-only before grants.
- [ ] Brownfield creates continuation/fix/improvement/stabilization routes.

## 3. Baselines and decisions

- [ ] Project Definition, Architecture and Technology Baselines have gates/revisions.
- [ ] Material decision creates ADR; normal implementation does not.
- [ ] Profiles/IDs/statuses come from one registry.
- [ ] Brownfield stack is not replaced silently.

## 4. Planning

- [ ] Large request creates one Work Package and minimum atomic tasks.
- [ ] Required artifact has producer/current revision.
- [ ] Future-only dependency cannot become READY.
- [ ] Deterministic next task is reproducible.
- [ ] `[HARDENING]` Shared read-only contract supports parallel consumers.
- [ ] `[HARDENING]` Parallel write/read conflicts are rejected or ordered; Core MVP runs one atomic Task at a time.

## 5. Prompts, skills and Codex

- [ ] Prompt compiles JIT only for READY task/run.
- [ ] Base Prompt Specs are reusable; no one-prompt-per-file explosion.
- [ ] Task prompt states what/why/result/verification/docs/stop/output.
- [ ] Primary skill exactly one and ACTIVE.
- [ ] Codex cannot expand scope/permissions or choose next task.
- [ ] Actual writes are mediated and traced.

## 6. Verification, docs and logs

- [ ] Every task has proportional Verification Profile.
- [ ] `[HARDENING]` Test DB avoids full rebuild per task when snapshot/clone strategy applies; Core MVP may use one fixture-compatible isolated environment.
- [ ] New regressions block completion; known unrelated failures remain visible.
- [ ] `[HARDENING]` Stale test update/delete references changed requirement/decision.
- [ ] Documentation impact and section refs are resolved before DONE.
- [ ] Correlation ID links input to Result.
- [ ] Secrets/hidden reasoning/provider billing/token ledger absent from trace.

## 7. Blockers and updates

- [ ] Every blocker has evidence, options, recommendation and resume condition.
- [ ] Hard constraint is never weakened silently.
- [ ] Retry creates new Run and checks idempotency/current revisions.
- [ ] `[CORE]` Maintenance planes are classified separately. `[HARDENING]` applies full Product/Project Control/Distribution Change Pack lifecycles.
- [ ] `[HARDENING]` One maintenance request can patch project routing/skill through full validation/rollback.

## 8. Documentation/distribution

- [ ] `[CORE]` Human and machine layers required by the vertical loop are generated/traceable; extended views remain `[HARDENING]`.
- [ ] 21 implementation specifications exist and combined guide is generated from them.
- [ ] Semantic validator detects ID/profile/status/schema/aggregate inconsistencies.
- [ ] FILE_INDEX, validation report and manifest match archive.
- [ ] Greenfield and brownfield end-to-end fixtures pass.

Core MVP is accepted when every `[CORE]` item passes. Hardening release is accepted only after its tagged items pass; it cannot retroactively redefine core contracts.
