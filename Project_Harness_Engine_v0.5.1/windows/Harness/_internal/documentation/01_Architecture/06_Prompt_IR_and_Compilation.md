# Prompt IR и JIT-компиляция

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Базовый принцип

Prompt is a compiled execution artifact, not the project source of truth. Harness stores a small reusable Prompt IR registry and compiles only a READY task or approved parallel batch.

```text
Prompt Module
→ Prompt Spec
→ Prompt Plan
→ Compiled Prompt Bundle
→ Adapter rendering
→ Run
```

## 2. Minimal Prompt Spec registry

```text
DISCOVER
DECIDE
ARCHITECT
PLAN
IMPLEMENT
FIX
VALIDATE
DOCUMENT
UPDATE
MAINTAIN_HARNESS
```

Most tasks reuse `IMPLEMENT` or `FIX`; a new Prompt Spec is not created for each task.

## 3. JIT gate

Compilation requires:

- READY/CLAIMED Task;
- accepted required artifacts and current revisions;
- effective constraints;
- active primary skill;
- context/capability/adapter compatibility;
- output schema;
- verification and stop protocol.

Future backlog tasks do not need compiled prompts.

## 4. Instruction order

```text
1. immutable distribution/safety invariants
2. project policies and effective constraints
3. accepted project/architecture/technology facts
4. Work Package purpose and Task Contract
5. input artifacts and bounded scope
6. skill procedure and capabilities
7. verification/documentation duties
8. stop conditions and blocker protocol
9. structured output contract
10. delimited untrusted data
```

## 5. Lifecycles

Prompt Module/Spec:

```text
DRAFT → VALIDATED → ACTIVE → DEPRECATED → RETIRED
```

Prompt Plan:

```text
PLANNED → RESOLVED → CONSUMED | STALE
```

Compiled Bundle:

```text
COMPILED → DISPATCHED → EXECUTED
         ↘ EXPIRED | CANCELLED
```

`COMPILED` never describes Prompt Plan/Module/Spec.

## 6. Determinism and invalidation

Same canonical inputs and compiler version produce same normalized logical bundle/hash. Material change to task, requirement, constraint, ADR, contract, skill, context policy, adapter, capability, repository base or verification profile invalidates future plan/bundle.

## 7. Retention

Retain active Modules/Specs and immutable bundle/source map for actual Runs. Do not retain mass-generated unused bundles.

Full specification: [`../12_Implementation_Specifications/04_JIT_Prompt_Compilation.md`](../12_Implementation_Specifications/04_JIT_Prompt_Compilation.md).
