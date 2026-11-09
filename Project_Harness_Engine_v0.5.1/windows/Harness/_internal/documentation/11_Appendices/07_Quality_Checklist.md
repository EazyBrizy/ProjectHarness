# Checklist качества архитектуры и документации v0.4.1

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## Request/UX

- [ ] Request Class/Mode/Operation separated.
- [ ] Ordinary query creates no task.
- [ ] Every route returns Result Envelope.
- [ ] Next route is exact and deterministic.

## Intake

- [ ] First start question is documentation.
- [ ] Questions are bounded, understandable and source-aware.
- [ ] Unknown path and review trigger exist.
- [ ] Brownfield inventory is read-only before writes.
- [ ] Continuation/fix/improvement/stabilization routes separated.

## Definition/decisions/technology

- [ ] Project/Brownfield Definition accepted before implementation.
- [ ] Material decision has ADR; local choice does not.
- [ ] Technology versions/compatibility/skills recorded.
- [ ] Profiles come from one registry.

## Planning/prompts/skills

- [ ] One Work Package per user outcome.
- [ ] Tasks are minimum sufficient and atomic.
- [ ] Required artifacts have producers and precede consumers.
- [ ] Parallel read/write sets are conflict-free.
- [ ] Prompt compiles JIT.
- [ ] Primary skill exactly one and ACTIVE.

## Execution/verification

- [ ] Codex/tool actions bounded by grants and actual-write checks.
- [ ] Run is one attempt; retry creates new Run.
- [ ] Verification Profile proportional to task/risk.
- [ ] Test baseline distinguishes new/known/stale failures.
- [ ] Test environment avoids unnecessary full DB rebuild.
- [ ] Documentation impact/sections resolved before DONE.

## Recovery/updates

- [ ] Every blocker has options/recommendation/resume condition.
- [ ] Hard constraint not weakened silently.
- [ ] Compensation status separate and valid.
- [ ] Change Pack has exactly one target plane.
- [ ] Active run/history not rewritten by maintenance.

## Logging/security/docs

- [ ] Correlation trace covers request-to-result.
- [ ] Secrets and hidden reasoning redacted.
- [ ] No provider billing/token ledger fields.
- [ ] Human views and machine state source-mapped.
- [ ] Semantic documentation validator passes.
- [ ] Aggregates/index/manifest match source tree.
